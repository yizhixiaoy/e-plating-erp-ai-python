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
    CORS_ORIGINS: list[str] = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:8080").split(",")
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))

    # PostgreSQL
    PG_HOST: str = os.getenv("PG_HOST", "localhost")
    PG_PORT: int = int(os.getenv("PG_PORT", "5432"))
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
    QWEN_MODEL: str = os.getenv("QWEN_MODEL", "qwen-max")                        # Qwen3.7-Max

    # Embedding
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "BAAI/bge-large-zh-v1.5")
    EMBEDDING_DIM: int = int(os.getenv("EMBEDDING_DIM", "1024"))
    RERANK_MODEL: str = os.getenv("RERANK_MODEL", "BAAI/bge-reranker-v2-m3")

    # Java后端API
    JAVA_API_BASE_URL: str = os.getenv("JAVA_API_BASE_URL", "http://localhost:8080")
    JAVA_API_KEY: str = os.getenv("JAVA_API_KEY", "807a4f25de31d333437d71f771bc2b30")
    JAVA_API_TIMEOUT: int = int(os.getenv("JAVA_API_TIMEOUT", "30"))

    # MinIO / OSS
    OSS_ENDPOINT: str = os.getenv("OSS_ENDPOINT", "localhost:9000")
    OSS_ACCESS_KEY: str = os.getenv("OSS_ACCESS_KEY", "minioadmin")
    OSS_SECRET_KEY: str = os.getenv("OSS_SECRET_KEY", "minioadmin")
    OSS_BUCKET: str = os.getenv("OSS_BUCKET", "ai-knowledge")
    OSS_SECURE: bool = os.getenv("OSS_SECURE", "false").lower() == "true"

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

    # 上下文窗口
    MAX_CONTEXT_TOKENS: int = int(os.getenv("MAX_CONTEXT_TOKENS", "8000"))
    SYSTEM_PROMPT_BUDGET: int = int(os.getenv("SYSTEM_PROMPT_BUDGET", "3000"))
    HISTORY_BUDGET: int = int(os.getenv("HISTORY_BUDGET", "2500"))

    # 审计
    AUDIT_ENABLED: bool = os.getenv("AUDIT_ENABLED", "true").lower() == "true"


settings = Settings()
