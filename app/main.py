"""FastAPI入口 - AI助理Python服务"""
import asyncio
import logging
import os
import asyncpg
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings

# 全局日志配置（必须在其他模块导入之前，确保所有 logger.info 可见）
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S"
)
# 抑制 httpx 的大量 HTTP 请求日志（模型加载时每个文件都会打印多次请求）
logging.getLogger("httpx").setLevel(logging.WARNING)
# 抑制 huggingface_hub 的下载日志
logging.getLogger("huggingface_hub").setLevel(logging.WARNING)
# 抑制 urllib3 连接重试日志（MinIO不可用时大量重试日志会淹没输出）
logging.getLogger("urllib3").setLevel(logging.ERROR)
# 抑制 transformers tokenizer 性能提示（XLMRobertaTokenizerFast __call__ 警告）
logging.getLogger("transformers.tokenization_utils_base").setLevel(logging.ERROR)

# HuggingFace 国内镜像：必须在任何 FlagEmbedding 导入之前设置
os.environ.setdefault("HF_ENDPOINT", settings.HF_ENDPOINT)
# Windows 不支持 symlink 缓存，消除重复警告
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

from app.api import chat, write, knowledge, health, files, goods
from app.middleware.auth import AuthMiddleware
from app.services.llm_factory import create_chat_llm, create_agent_llm
from app.services.memory import MemoryService
from app.services.oss_storage import OssStorageService
from app.tools.erp_query import ErpQueryTool
from app.tools.stats import StatsTool
from app.tools.knowledge import KnowledgeTool
from app.tools.doc_process import DocProcessTool


async def _preload_embedding_model(knowledge_tool: KnowledgeTool):
    """后台任务：预加载Embedding + Reranker模型，避免首次查询时长时间阻塞"""
    try:
        import logging
        logger = logging.getLogger(__name__)
        logger.info("[启动] 开始后台预加载Embedding模型: %s", settings.EMBEDDING_MODEL)
        # 触发Embedding模型的懒加载
        _ = await knowledge_tool._get_query_embedding("preload warmup")
        logger.info("[启动] Embedding模型预加载完成")

        # 预加载Reranker模型（bge-reranker-v2-m3，首次加载约30-60s）
        if knowledge_tool.rerank_enabled:
            logger.info("[启动] 开始后台预加载Reranker模型: %s", settings.RERANK_MODEL)
            from FlagEmbedding import FlagReranker
            import time as _t
            _t0 = _t.time()
            knowledge_tool.reranker = await asyncio.to_thread(
                lambda: FlagReranker(settings.RERANK_MODEL, use_fp16=True)
            )
            logger.info("[启动] Reranker模型预加载完成: %.1fs", _t.time() - _t0)
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error("[启动] 模型预加载失败（首次检索时将重试）: %s", e)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时
    print(f"[启动] {settings.APP_NAME} v{settings.APP_VERSION}")
    print(f"[数据库] 连接 PostgreSQL: {settings.PG_HOST}:{settings.PG_PORT}/{settings.PG_DATABASE}")

    # 创建数据库连接池
    app.state.db_pool = await asyncpg.create_pool(
        host=settings.PG_HOST,
        port=settings.PG_PORT,
        user=settings.PG_USER,
        password=settings.PG_PASSWORD,
        database=settings.PG_DATABASE,
        min_size=settings.PG_POOL_MIN,
        max_size=settings.PG_POOL_MAX
    )
    print("[数据库] 连接池创建成功")

    # 确保pgvector扩展已启用
    async with app.state.db_pool.acquire() as conn:
        await conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
        print("[数据库] pgvector扩展已确认")

    # 初始化LLM（按设计文档7.1模型选型矩阵）
    app.state.chat_llm = create_chat_llm(streaming=True)
    app.state.agent_llm = create_agent_llm()
    print(f"[LLM] 对话模型: {settings.LLM_MODEL_CHAT} (高性价比对话)")
    print(f"[LLM] 智能体模型: {settings.QWEN_MODEL} (任务规划/决策)")

    # 初始化OSS对象存储服务（与Java后端FileUploadUtils共享bucket）
    app.state.oss_service = OssStorageService()
    print(f"[OSS] 对象存储: {'已启用' if app.state.oss_service.enabled else '已禁用'} (provider={app.state.oss_service._provider})")

    # 初始化工具
    auth_headers = {}
    app.state.tools = {
        "erp_query_tool": ErpQueryTool(auth_headers=auth_headers),
        "stats_tool": StatsTool(),
        "knowledge_tool": KnowledgeTool(db_pool=app.state.db_pool, oss_service=app.state.oss_service),
        "doc_process_tool": DocProcessTool(db_pool=app.state.db_pool)
    }
    print(f"[工具] 已注册 {len(app.state.tools)} 个工具: {list(app.state.tools.keys())}")

    # 初始化Redis（Schema缓存 + 知识库列表缓存 + 会话列表缓存）
    from app.services.cache import ensure_redis
    await ensure_redis()

    # 预加载Embedding模型（避免首次检索时阻塞）
    asyncio.create_task(_preload_embedding_model(app.state.tools["knowledge_tool"]))

    # 初始化长期记忆服务
    app.state.memory_service = MemoryService(db_pool=app.state.db_pool)
    print(f"[Memory] 长期记忆服务: {'已启用' if settings.MEM0_ENABLED else '已禁用'}")

    # 初始化LangGraph Checkpointer(异步PostgresSaver)
    # 注意: from_conn_string 返回 async context manager,需要跨 yield 保持
    checkpointer = None
    try:
        from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
        from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
            
        # 配置允许反序列化的自定义模块(避免MessagePack警告)
        serde = JsonPlusSerializer(
            allowed_msgpack_modules=[("app.models.schemas", "UserContext")]
        )
            
        # 构建连接字符串
        conn_string = (
            f"postgresql://{settings.PG_USER}:{settings.PG_PASSWORD}"
            f"@{settings.PG_HOST}:{settings.PG_PORT}/{settings.PG_DATABASE}"
        )
            
        # 手动管理 async generator context manager
        checkpointer_gen = AsyncPostgresSaver.from_conn_string(
            conn_string,
            serde=serde
        )
        # 调用 __aenter__ 进入上下文
        checkpointer = await checkpointer_gen.__aenter__()
        # 保存到 app.state 用于关闭时清理
        app.state.checkpointer_gen = checkpointer_gen
            
        # 自动创建 checkpoints 等必要的表
        await checkpointer.setup()
        print("[Checkpoint] 数据库表结构已就绪,Agent状态将持久化到PostgreSQL")
    except ImportError:
        print("[Checkpoint] langgraph-checkpoint-postgres未安装,跳过Checkpointer")
    except Exception as e:
        print(f"[Checkpoint] Checkpointer初始化失败: {e},将以无状态模式运行")
        checkpointer = None

    # 构建Agent图
    from app.agent.graph import build_agent_graph
    app.state.agent_graph = build_agent_graph(
        chat_llm=app.state.chat_llm,
        agent_llm=app.state.agent_llm,
        tools=app.state.tools,
        checkpointer=checkpointer
    )
    app.state.checkpointer = checkpointer
    print("[Agent] LangGraph图已构建")

    yield

    # 关闭时:调用 __aexit__ 退出 checkpointer 上下文
    if hasattr(app.state, 'checkpointer_gen') and app.state.checkpointer_gen:
        try:
            await app.state.checkpointer_gen.__aexit__(None, None, None)
            print("[关闭] Checkpointer已释放")
        except Exception as e:
            print(f"[关闭] Checkpointer关闭异常: {e}")
    # 关闭Redis
    from app.services.cache import close_redis
    await close_redis()
    await app.state.db_pool.close()
    print("[关闭] 服务已停止")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan
)

# CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 认证中间件（需在CORS之后）
app.add_middleware(AuthMiddleware)

# 审计中间件（db_pool 通过 request.scope["app"].state.db_pool 动态获取）
from app.middleware.audit import AuditMiddleware
app.add_middleware(AuditMiddleware)
app.include_router(chat.router)
app.include_router(chat.conversations_router)
app.include_router(write.router)
app.include_router(knowledge.router)
app.include_router(files.router)
app.include_router(files.upload_router)
app.include_router(goods.router)
app.include_router(health.router)


@app.get("/")
async def root():
    """根路径"""
    return {
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "health": "/health"
    }
