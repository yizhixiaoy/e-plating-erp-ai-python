"""FastAPI入口 - AI助理Python服务"""
import asyncpg
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.api import chat, write, knowledge, health, files
from app.middleware.auth import AuthMiddleware
from app.services.llm_factory import create_chat_llm, create_agent_llm
from app.services.memory import MemoryService
from app.services.oss_storage import OssStorageService
from app.tools.erp_query import ErpQueryTool
from app.tools.stats import StatsTool
from app.tools.knowledge import KnowledgeTool
from app.tools.doc_process import DocProcessTool


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
    print(f"[OSS] 对象存储: {'已启用' if app.state.oss_service.enabled else '已禁用'}")

    # 初始化工具
    auth_headers = {}
    app.state.tools = {
        "erp_query_tool": ErpQueryTool(auth_headers=auth_headers),
        "stats_tool": StatsTool(),
        "knowledge_tool": KnowledgeTool(db_pool=app.state.db_pool, oss_service=app.state.oss_service),
        "doc_process_tool": DocProcessTool(db_pool=app.state.db_pool)
    }
    print(f"[工具] 已注册 {len(app.state.tools)} 个工具: {list(app.state.tools.keys())}")

    # 初始化长期记忆服务
    app.state.memory_service = MemoryService(db_pool=app.state.db_pool)
    print(f"[Memory] 长期记忆服务: {'已启用' if settings.MEM0_ENABLED else '已禁用'}")

    # 初始化LangGraph Checkpointer（异步PostgresSaver）
    checkpointer = None
    try:
        from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
        async with AsyncPostgresSaver.from_conn_string(
            f"postgresql://{settings.PG_USER}:{settings.PG_PASSWORD}"
            f"@{settings.PG_HOST}:{settings.PG_PORT}/{settings.PG_DATABASE}"
        ) as saver:
            checkpointer = saver
        print("[Checkpoint] AsyncPostgresSaver已启用，Agent状态将持久化到PostgreSQL")
    except ImportError:
        print("[Checkpoint] langgraph-checkpoint-postgres未安装，跳过Checkpointer")
    except Exception as e:
        print(f"[Checkpoint] Checkpointer初始化失败: {e}，将以无状态模式运行")

    # 构建Agent图
    from app.agent.graph import build_agent_graph
    app.state.agent_graph = build_agent_graph(
        chat_llm=app.state.chat_llm,
        agent_llm=app.state.agent_llm,
        tools=app.state.tools,
        checkpointer=checkpointer
    )
    print("[Agent] LangGraph图已构建")

    yield

    # 关闭时
    print("[关闭] 释放数据库连接池")
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
app.include_router(write.router)
app.include_router(knowledge.router)
app.include_router(files.router)
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
