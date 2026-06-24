"""应用配置管理，从环境变量读取所有配置"""
import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    """全局配置"""

    # 服务
    APP_NAME: str = os.getenv("APP_NAME", "ERP AI Assistant")
    APP_VERSION: str = os.getenv("APP_VERSION", "1.0.0")
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    CORS_ORIGINS: list[str] = os.getenv("CORS_ORIGINS", "http://127.0.0.1:5173,http://127.0.0.1:8080").split(",")
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))

    # PostgreSQL
    PG_HOST: str = os.getenv("PG_HOST", "3.tcp.cpolar.top")
    PG_PORT: int = int(os.getenv("PG_PORT", "12026"))
    PG_USER: str = os.getenv("PG_USER", "postgres")
    PG_PASSWORD: str = os.getenv("PG_PASSWORD", "postgres")
    PG_DATABASE: str = os.getenv("PG_DATABASE", "erp_ai")
    PG_POOL_MIN: int = int(os.getenv("PG_POOL_MIN", "2"))
    PG_POOL_MAX: int = int(os.getenv("PG_POOL_MAX", "10"))

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"postgresql://{self.PG_USER}:{self.PG_PASSWORD}"
            f"@{self.PG_HOST}:{self.PG_PORT}/{self.PG_DATABASE}"
        )

    # LLM - DeepSeek（高性价比对话 & 复杂推理）
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "deepseek")  # deepseek / qwen
    LLM_API_KEY: str = os.getenv("LLM_API_KEY", "sk-416efaf437694b2fa59bdf22d8839d37")
    LLM_BASE_URL: str = os.getenv("LLM_BASE_URL", "https://api.deepseek.com/v1")
    LLM_MODEL_CHAT: str = os.getenv("LLM_MODEL_CHAT", "deepseek-v4-flash")       # 高性价比对话
    LLM_MODEL_REASON: str = os.getenv("LLM_MODEL_REASON", "deepseek-v4-pro")     # 复杂推理
    LLM_TEMPERATURE: float = float(os.getenv("LLM_TEMPERATURE", "0.3"))
    LLM_REASONING_TEMPERATURE: float = float(os.getenv("LLM_REASONING_TEMPERATURE", "0.1"))
    LLM_MAX_TOKENS: int = int(os.getenv("LLM_MAX_TOKENS", "4096"))

    # LLM - Qwen（智能体决策/任务规划）
    QWEN_API_KEY: str = os.getenv("QWEN_API_KEY", "sk-1f9d720eecb14b629ea92f2f0ef2285b")
    QWEN_BASE_URL: str = os.getenv("QWEN_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
    QWEN_MODEL: str = os.getenv("QWEN_MODEL", "qwen3.7-max")                   # Qwen3.7-Max 旗舰模型

    # HuggingFace 镜像（国内环境自动使用 hf-mirror.com）
    # 如果 hf-mirror.com 也不稳定，可以换为 https://hf.xeduapi.com 或 https://hf-mirror.vip 等备用镜像
    HF_ENDPOINT: str = os.getenv("HF_ENDPOINT", "https://hf-mirror.com")

    # Embedding
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "BAAI/bge-large-zh-v1.5")
    EMBEDDING_DIM: int = int(os.getenv("EMBEDDING_DIM", "1024"))
    RERANK_MODEL: str = os.getenv("RERANK_MODEL", "BAAI/bge-reranker-v2-m3")

    # Java后端API
    JAVA_API_BASE_URL: str = os.getenv("JAVA_API_BASE_URL", "http://127.0.0.1:8080")
    JAVA_API_KEY: str = os.getenv("JAVA_API_KEY", "807a4f25de31d333437d71f771bc2b30")
    JAVA_API_TIMEOUT: int = int(os.getenv("JAVA_API_TIMEOUT", "30"))

    # Redis
    REDIS_HOST: str = os.getenv("REDIS_HOST", "3.tcp.cpolar.top")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "11414"))
    REDIS_PASSWORD: str = os.getenv("REDIS_PASSWORD", "")
    REDIS_DB: int = int(os.getenv("REDIS_DB", "0"))
    REDIS_PREFIX: str = os.getenv("REDIS_PREFIX", "erp_ai:")

    @property
    def REDIS_URL(self) -> str:
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    # MinIO / OSS
    OSS_ENABLED: bool = os.getenv("OSS_ENABLED", "true").lower() == "true"
    OSS_ENDPOINT: str = os.getenv("OSS_ENDPOINT", "127.0.0.1:9000")
    OSS_ACCESS_KEY: str = os.getenv("OSS_ACCESS_KEY", "minioadmin")
    OSS_SECRET_KEY: str = os.getenv("OSS_SECRET_KEY", "minioadmin")
    OSS_BUCKET: str = os.getenv("OSS_BUCKET", "ai-knowledge")
    OSS_SECURE: bool = os.getenv("OSS_SECURE", "false").lower() == "true"

    # 文件上传限制
    MAX_KB_FILE_SIZE: int = int(os.getenv("MAX_KB_FILE_SIZE", str(50 * 1024 * 1024)))    # 知识库文档50MB
    MAX_TEMP_FILE_SIZE: int = int(os.getenv("MAX_TEMP_FILE_SIZE", str(20 * 1024 * 1024)))  # 对话临时文件20MB
    ALLOWED_FILE_TYPES: list[str] = os.getenv(
        "ALLOWED_FILE_TYPES", "pdf,docx,doc,xlsx,xls,pptx,txt,md,csv,json,png,jpg,jpeg"
    ).split(",")

    # Mem0长期记忆
    MEM0_ENABLED: bool = os.getenv("MEM0_ENABLED", "true").lower() == "true"

    # Agent配置
    AGENT_MAX_STEPS: int = int(os.getenv("AGENT_MAX_STEPS", "10"))
    AGENT_CONFIRM_THRESHOLD: str = os.getenv("AGENT_CONFIRM_THRESHOLD", "complex")

    # RAG配置
    RAG_TOP_K: int = int(os.getenv("RAG_TOP_K", "5"))
    RAG_SIMILARITY_THRESHOLD: float = float(os.getenv("RAG_SIMILARITY_THRESHOLD", "0.6"))
    CHUNK_SIZE: int = int(os.getenv("CHUNK_SIZE", "500"))
    CHUNK_OVERLAP: int = int(os.getenv("CHUNK_OVERLAP", "100"))

    # 上下文窗口（DeepSeek-V4 支持128K上下文，8000偏低）
    MAX_CONTEXT_TOKENS: int = int(os.getenv("MAX_CONTEXT_TOKENS", "16000"))
    SYSTEM_PROMPT_BUDGET: int = int(os.getenv("SYSTEM_PROMPT_BUDGET", "4000"))
    HISTORY_BUDGET: int = int(os.getenv("HISTORY_BUDGET", "4000"))
    OUTPUT_RESERVE_TOKENS: int = int(os.getenv("OUTPUT_RESERVE_TOKENS", "2000"))

    # 历史压缩
    COMPRESS_KEEP_RECENT: int = int(os.getenv("COMPRESS_KEEP_RECENT", "6"))
    COMPRESS_TEMPERATURE: float = float(os.getenv("COMPRESS_TEMPERATURE", "0.3"))
    COMPRESS_MAX_TOKENS: int = int(os.getenv("COMPRESS_MAX_TOKENS", "300"))
    COMPRESS_MAX_CHARS: int = int(os.getenv("COMPRESS_MAX_CHARS", "200"))

    # 会话管理
    CHAT_COMPRESS_HISTORY_THRESHOLD: int = int(os.getenv("CHAT_COMPRESS_HISTORY_THRESHOLD", "20"))
    CHAT_COMPRESS_KEEP_RECENT: int = int(os.getenv("CHAT_COMPRESS_KEEP_RECENT", "6"))
    CONVERSATION_TITLE_MAX_LENGTH: int = int(os.getenv("CONVERSATION_TITLE_MAX_LENGTH", "15"))

    # LLM温度和Token（各节点独立配置，默认继承全局LLM_TEMPERATURE）
    LLM_WRITER_TEMPERATURE: float = float(os.getenv("LLM_WRITER_TEMPERATURE", "0.7"))
    CLASSIFIER_TEMPERATURE: float = float(os.getenv("CLASSIFIER_TEMPERATURE", "0.0"))
    CLASSIFIER_MAX_TOKENS: int = int(os.getenv("CLASSIFIER_MAX_TOKENS", "500"))
    PLANNER_TEMPERATURE: float = float(os.getenv("PLANNER_TEMPERATURE", "0.2"))
    PLANNER_MAX_TOKENS: int = int(os.getenv("PLANNER_MAX_TOKENS", "1000"))
    EXECUTOR_TOOL_SELECT_TEMP: float = float(os.getenv("EXECUTOR_TOOL_SELECT_TEMP", "0.0"))
    EXECUTOR_MAX_TOKENS: int = int(os.getenv("EXECUTOR_MAX_TOKENS", "1000"))
    TITLE_GEN_TEMPERATURE: float = float(os.getenv("TITLE_GEN_TEMPERATURE", "0.1"))
    TITLE_GEN_MAX_TOKENS: int = int(os.getenv("TITLE_GEN_MAX_TOKENS", "50"))

    # ── 各节点 Thinking / Streaming 控制 ──
    # classifier: 快速分类，不需要thinking和streaming
    CLASSIFIER_THINKING: bool = os.getenv("CLASSIFIER_THINKING", "false").lower() == "true"
    CLASSIFIER_STREAMING: bool = os.getenv("CLASSIFIER_STREAMING", "false").lower() == "true"
    # planner: 任务规划，不需要thinking显示和streaming
    PLANNER_THINKING: bool = os.getenv("PLANNER_THINKING", "false").lower() == "true"
    PLANNER_STREAMING: bool = os.getenv("PLANNER_STREAMING", "false").lower() == "true"
    # executor: 工具选择+执行，不需要thinking和streaming
    EXECUTOR_THINKING: bool = os.getenv("EXECUTOR_THINKING", "false").lower() == "true"
    EXECUTOR_STREAMING: bool = os.getenv("EXECUTOR_STREAMING", "false").lower() == "true"
    # aggregator: 最终回答生成 → 需要thinking（展示推理过程）+ streaming（实时流式输出）
    AGGREGATOR_THINKING: bool = os.getenv("AGGREGATOR_THINKING", "true").lower() == "true"
    AGGREGATOR_STREAMING: bool = os.getenv("AGGREGATOR_STREAMING", "true").lower() == "true"

    # Agent规划器
    AGENT_PLANNER_RECENT_HISTORY: int = int(os.getenv("AGENT_PLANNER_RECENT_HISTORY", "6"))
    AGENT_PLANNER_HISTORY_TRUNC: int = int(os.getenv("AGENT_PLANNER_HISTORY_TRUNC", "100"))

    # 长期记忆
    MEMORY_DEFAULT_IMPORTANCE: float = float(os.getenv("MEMORY_DEFAULT_IMPORTANCE", "0.3"))
    MEMORY_EXTRACT_MAX_LENGTH: int = int(os.getenv("MEMORY_EXTRACT_MAX_LENGTH", "200"))

    # 临时文件
    TEMP_FILE_EXPIRE_HOURS: int = int(os.getenv("TEMP_FILE_EXPIRE_HOURS", "24"))
    TEMP_FILE_LIST_LIMIT: int = int(os.getenv("TEMP_FILE_LIST_LIMIT", "50"))
    TEMP_FILE_PARSE_MAX_CHARS: int = int(os.getenv("TEMP_FILE_PARSE_MAX_CHARS", "50000"))

    # Chunker切分清洗阈值
    CHUNK_CLEAN_MIN_LENGTH: int = int(os.getenv("CHUNK_CLEAN_MIN_LENGTH", "10"))
    CHUNK_CLEAN_MERGE_LENGTH: int = int(os.getenv("CHUNK_CLEAN_MERGE_LENGTH", "50"))

    # 审计
    AUDIT_ENABLED: bool = os.getenv("AUDIT_ENABLED", "true").lower() == "true"


settings = Settings()
