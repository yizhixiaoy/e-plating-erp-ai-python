-- ============================================================
-- V3__ai_assistant_schema.sql
-- AI助理模块数据库初始化脚本 (PostgreSQL 15+)
-- 所有表包含审计字段：created_by, created_at, updated_by, updated_at
-- ============================================================

-- 启用 pgvector 扩展
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;  -- 三元组模糊匹配，用于BM25

-- ============================================================
-- 1. 会话表
-- ============================================================
CREATE TABLE conversation (
    id              BIGSERIAL PRIMARY KEY,
    tenant_id       BIGINT NOT NULL,
    user_id         BIGINT NOT NULL,
    title           VARCHAR(200),               -- 会话标题（首条消息自动生成）
    session_type    VARCHAR(20) DEFAULT 'chat', -- chat / writer
    message_count   INT DEFAULT 0,              -- 消息总数
    total_tokens    INT DEFAULT 0,              -- 总Token消耗
    last_message_at TIMESTAMP,                  -- 最后消息时间
    is_pinned       BOOLEAN DEFAULT FALSE,      -- 置顶
    is_archived     BOOLEAN DEFAULT FALSE,      -- 归档
    is_deleted      BOOLEAN DEFAULT FALSE,      -- 逻辑删除
    created_by      BIGINT,                     -- 创建人用户ID
    updated_by      BIGINT,                     -- 最后修改人用户ID
    created_at      TIMESTAMP DEFAULT NOW(),
    updated_at      TIMESTAMP DEFAULT NOW()
);

COMMENT ON TABLE conversation IS 'AI对话会话表';
COMMENT ON COLUMN conversation.tenant_id IS '租户ID';
COMMENT ON COLUMN conversation.user_id IS '用户ID';
COMMENT ON COLUMN conversation.is_deleted IS '逻辑删除标记';
COMMENT ON COLUMN conversation.created_by IS '创建人用户ID';
COMMENT ON COLUMN conversation.updated_by IS '最后修改人用户ID';

CREATE INDEX idx_conv_user ON conversation (tenant_id, user_id, is_archived, last_message_at DESC);
CREATE INDEX idx_conv_created_by ON conversation (created_by);
CREATE INDEX idx_conv_updated_at ON conversation (updated_at);


-- ============================================================
-- 2. 消息表
-- ============================================================
CREATE TABLE conversation_message (
    id              BIGSERIAL PRIMARY KEY,
    conversation_id BIGINT NOT NULL REFERENCES conversation(id) ON DELETE CASCADE,
    tenant_id       BIGINT NOT NULL,
    role            VARCHAR(20) NOT NULL,       -- user / assistant / system / tool
    content         TEXT,                        -- 消息原文
    model_name      VARCHAR(50),                -- 生成该消息的模型标识（role=assistant时）
    tool_calls      JSONB,                       -- 工具调用记录（role=assistant时）
    tool_call_id    VARCHAR(100),                -- 工具调用ID（role=tool时）
    tool_result     TEXT,                        -- 工具返回结果（role=tool时）
    token_count     INT,                         -- 本条消息Token总数
    token_usage     JSONB,                       -- Token明细 {"input":500,"output":300,"total":800}
    file_ids        JSONB DEFAULT '[]',          -- 关联的临时文件ID列表（role=user时），如 ["uuid1","uuid2"]
    "references"      JSONB DEFAULT '[]',          -- 引用来源（知识库/数据查询），结构：
                                                 -- [{"source_type":"knowledge|database|upload",
                                                 --   "source_id":"doc_123",
                                                 --   "doc_title":"镀镍工艺规程.pdf",
                                                 --   "chunk_index":1,
                                                 --   "similarity":0.92,
                                                 --   "page_number":3,
                                                 --   "section_title":"镀液参数控制"}]
    thinking_steps  JSONB DEFAULT '[]',          -- AI思考步骤JSON数组
                                                 -- [{"type":"thinking|tool_start|tool_end",
                                                 --   "content":"...",
                                                 --   "toolName":"...",
                                                 --   "timestamp":0.0}]
    duration_sec    DOUBLE PRECISION,             -- AI回复耗时（秒），仅role=assistant时有值
    is_streaming    BOOLEAN DEFAULT FALSE,       -- 是否为流式中的占位消息
    is_deleted      BOOLEAN DEFAULT FALSE,       -- 逻辑删除
    created_by      BIGINT,                     -- 创建人用户ID
    updated_by      BIGINT,                     -- 最后修改人用户ID
    created_at      TIMESTAMP DEFAULT NOW(),
    updated_at      TIMESTAMP DEFAULT NOW()
);

COMMENT ON TABLE conversation_message IS 'AI对话消息表';
COMMENT ON COLUMN conversation_message.is_deleted IS '逻辑删除标记';
COMMENT ON COLUMN conversation_message.model_name IS '生成该消息的模型标识，如deepseek-chat/qwen-plus';
COMMENT ON COLUMN conversation_message.token_usage IS 'Token消耗明细JSON，如{"input":500,"output":300,"total":800}';
COMMENT ON COLUMN conversation_message.file_ids IS '关联的临时文件ID列表JSON数组，如["uuid1","uuid2"]';
COMMENT ON COLUMN conversation_message."references" IS '引用来源JSON数组，支持knowledge/database/upload三种类型';
COMMENT ON COLUMN conversation_message.created_by IS '创建人用户ID（发送者）';
COMMENT ON COLUMN conversation_message.updated_by IS '最后修改人用户ID';

CREATE INDEX idx_msg_conv ON conversation_message (conversation_id, created_at);
CREATE INDEX idx_msg_tenant ON conversation_message (tenant_id);
CREATE INDEX idx_msg_created_by ON conversation_message (created_by);
CREATE INDEX idx_msg_references ON conversation_message USING GIN ("references");
CREATE INDEX idx_msg_file_ids ON conversation_message USING GIN (file_ids);


-- ============================================================
-- 3. 知识库表
-- ============================================================
CREATE TABLE knowledge_base (
    id              BIGSERIAL PRIMARY KEY,
    tenant_id       BIGINT,                    -- 租户ID，公共库为NULL
    scope_type      VARCHAR(20) NOT NULL DEFAULT 'tenant', -- global / tenant / personal
    name            VARCHAR(100) NOT NULL,
    description     TEXT,
    embedding_model VARCHAR(50) DEFAULT 'bge-large-zh-v1.5',
    chunk_size      INT DEFAULT 500,           -- 文本切分块大小（字符数）
    chunk_overlap   INT DEFAULT 100,           -- 相邻块重叠字符数（推荐20%）
    status          VARCHAR(20) DEFAULT 'active', -- active / disabled
    doc_count       INT DEFAULT 0,             -- 文档数量统计
    chunk_count     INT DEFAULT 0,             -- 片段数量统计
    is_deleted      BOOLEAN DEFAULT FALSE,      -- 逻辑删除
    created_by      BIGINT,                    -- 创建人用户ID
    updated_by      BIGINT,                    -- 最后修改人用户ID
    created_at      TIMESTAMP DEFAULT NOW(),
    updated_at      TIMESTAMP DEFAULT NOW()
);

COMMENT ON TABLE knowledge_base IS 'AI知识库表';
COMMENT ON COLUMN knowledge_base.tenant_id IS '租户ID，公共库为NULL';
COMMENT ON COLUMN knowledge_base.scope_type IS '可见范围：global全租户/tenant当前公司/personal个人';
COMMENT ON COLUMN knowledge_base.created_by IS '创建人用户ID';
COMMENT ON COLUMN knowledge_base.updated_by IS '最后修改人用户ID';

CREATE INDEX idx_kb_scope ON knowledge_base (scope_type, tenant_id);
CREATE INDEX idx_kb_tenant ON knowledge_base (tenant_id);
CREATE INDEX idx_kb_created_by ON knowledge_base (created_by);
CREATE INDEX idx_kb_status ON knowledge_base (status);


-- ============================================================
-- 4. 文档表
-- ============================================================
CREATE TABLE knowledge_document (
    id              BIGSERIAL PRIMARY KEY,
    kb_id           BIGINT NOT NULL REFERENCES knowledge_base(id) ON DELETE CASCADE,
    tenant_id       BIGINT,                    -- 租户ID，公共库文档为NULL
    title           VARCHAR(255) NOT NULL,
    file_name       VARCHAR(255),
    file_type       VARCHAR(20),               -- pdf / docx / txt / md / xlsx / pptx / png / jpg
    file_size       BIGINT,                    -- 字节数
    file_path       VARCHAR(500),              -- 本地路径（保留兼容）
    oss_path        VARCHAR(500),              -- OSS对象存储路径（持久备份）
    content_type    VARCHAR(100),              -- MIME类型，如 application/pdf
    file_hash       VARCHAR(64),               -- 文件SHA256哈希（去重/完整性校验）
    chunk_count     INT DEFAULT 0,
    parse_status    VARCHAR(20) DEFAULT 'pending', -- pending / parsing / completed / failed
    parse_error     TEXT,                       -- 解析失败原因
    is_deleted      BOOLEAN DEFAULT FALSE,       -- 逻辑删除
    created_by      BIGINT,                    -- 上传人用户ID
    updated_by      BIGINT,                    -- 最后修改人用户ID
    created_at      TIMESTAMP DEFAULT NOW(),
    updated_at      TIMESTAMP DEFAULT NOW()
);

COMMENT ON TABLE knowledge_document IS '知识库文档表';
COMMENT ON COLUMN knowledge_document.oss_path IS 'OSS对象存储路径（持久备份，与Java FileUploadUtils共享bucket）';
COMMENT ON COLUMN knowledge_document.content_type IS 'MIME类型，如application/pdf、text/plain';
COMMENT ON COLUMN knowledge_document.file_hash IS '文件SHA256哈希值（64位十六进制），用于去重和完整性校验';
COMMENT ON COLUMN knowledge_document.created_by IS '上传人用户ID';
COMMENT ON COLUMN knowledge_document.updated_by IS '最后修改人用户ID';

CREATE INDEX idx_doc_kb ON knowledge_document (kb_id);
CREATE INDEX idx_doc_tenant ON knowledge_document (tenant_id);
CREATE INDEX idx_doc_created_by ON knowledge_document (created_by);
CREATE INDEX idx_doc_parse_status ON knowledge_document (parse_status);


-- ============================================================
-- 5. 文档片段表（含向量）
-- ============================================================
CREATE TABLE knowledge_chunk (
    id              BIGSERIAL PRIMARY KEY,
    doc_id          BIGINT NOT NULL REFERENCES knowledge_document(id) ON DELETE CASCADE,
    kb_id           BIGINT NOT NULL,
    tenant_id       BIGINT NOT NULL,
    chunk_index     INT NOT NULL,              -- 片段在文档中的序号
    content         TEXT NOT NULL,              -- 片段原文
    token_count     INT,                       -- Token数
    embedding       VECTOR(1024),              -- BGE向量，维度1024
    metadata        JSONB DEFAULT '{}',        -- 附加元数据（页码、章节标题等）
    is_deleted      BOOLEAN DEFAULT FALSE,       -- 逻辑删除
    created_by      BIGINT,                    -- 创建人用户ID
    updated_by      BIGINT,                    -- 最后修改人用户ID
    created_at      TIMESTAMP DEFAULT NOW(),
    updated_at      TIMESTAMP DEFAULT NOW()
);

COMMENT ON TABLE knowledge_chunk IS '知识库文档片段表（含向量）';
COMMENT ON COLUMN knowledge_chunk.embedding IS 'BAAI/bge-large-zh-v1.5 生成的1024维向量';
COMMENT ON COLUMN knowledge_chunk.metadata IS 'JSON元数据，如{"page_number":3,"section_title":"镀液参数控制"}';
COMMENT ON COLUMN knowledge_chunk.created_by IS '创建人用户ID';
COMMENT ON COLUMN knowledge_chunk.updated_by IS '最后修改人用户ID';

-- 向量检索索引（HNSW，冷启动友好，无需预填充数据）
CREATE INDEX idx_chunk_embedding ON knowledge_chunk
    USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);
CREATE INDEX idx_chunk_kb ON knowledge_chunk (kb_id, tenant_id);
CREATE INDEX idx_chunk_doc ON knowledge_chunk (doc_id);
CREATE INDEX idx_chunk_created_by ON knowledge_chunk (created_by);

-- 全文检索索引（BM25替代方案：pg_trgm）
CREATE INDEX idx_chunk_content_trgm ON knowledge_chunk USING GIN (content gin_trgm_ops);


-- ============================================================
-- 6. Agent-知识库关联表
-- ============================================================
CREATE TABLE agent_knowledge_binding (
    id              BIGSERIAL PRIMARY KEY,
    tenant_id       BIGINT NOT NULL,
    agent_id        VARCHAR(50) NOT NULL,       -- Agent标识
    kb_id           BIGINT NOT NULL REFERENCES knowledge_base(id) ON DELETE CASCADE,
    top_k           INT DEFAULT 5,             -- 检索时返回前K条
    score_threshold FLOAT DEFAULT 0.6,         -- 相似度最低阈值
    is_deleted      BOOLEAN DEFAULT FALSE,       -- 逻辑删除
    created_by      BIGINT,                    -- 创建人用户ID
    updated_by      BIGINT,                    -- 最后修改人用户ID
    created_at      TIMESTAMP DEFAULT NOW(),
    updated_at      TIMESTAMP DEFAULT NOW(),
    UNIQUE(agent_id, kb_id)
);

COMMENT ON TABLE agent_knowledge_binding IS 'Agent与知识库的绑定关系表';
COMMENT ON COLUMN agent_knowledge_binding.created_by IS '创建人用户ID';
COMMENT ON COLUMN agent_knowledge_binding.updated_by IS '最后修改人用户ID';

CREATE INDEX idx_akb_agent ON agent_knowledge_binding (agent_id);
CREATE INDEX idx_akb_kb ON agent_knowledge_binding (kb_id);


-- ============================================================
-- 7. 知识库标签表
-- ============================================================
CREATE TABLE knowledge_base_tag (
    id          BIGSERIAL PRIMARY KEY,
    kb_id       BIGINT NOT NULL REFERENCES knowledge_base(id) ON DELETE CASCADE,
    tenant_id   BIGINT,
    tag_name    VARCHAR(50) NOT NULL,          -- 标签名：如 "电镀工艺", "镀镍", "SOP"
    source      VARCHAR(20) DEFAULT 'manual',  -- manual / ai_recommended
    is_deleted  BOOLEAN DEFAULT FALSE,           -- 逻辑删除
    created_by  BIGINT,                        -- 创建人用户ID
    updated_by  BIGINT,                        -- 最后修改人用户ID
    created_at  TIMESTAMP DEFAULT NOW(),
    updated_at  TIMESTAMP DEFAULT NOW()
);

COMMENT ON TABLE knowledge_base_tag IS '知识库标签表，用于多知识库路由';
COMMENT ON COLUMN knowledge_base_tag.tag_name IS '标签名，如"电镀工艺""镀镍""SOP"';
COMMENT ON COLUMN knowledge_base_tag.created_by IS '创建人用户ID';
COMMENT ON COLUMN knowledge_base_tag.updated_by IS '最后修改人用户ID';

CREATE INDEX idx_kb_tag_kb ON knowledge_base_tag (kb_id);
CREATE INDEX idx_kb_tag_name ON knowledge_base_tag (tag_name);


-- ============================================================
-- 8. 用户长期记忆表
-- ============================================================
CREATE TABLE user_long_term_memory (
    id              BIGSERIAL PRIMARY KEY,
    tenant_id       BIGINT NOT NULL,
    user_id         BIGINT NOT NULL,
    memory_type     VARCHAR(50) DEFAULT 'fact', -- fact / preference / pattern
    content         TEXT NOT NULL,
    embedding       VECTOR(1024),              -- 记忆向量（可选）
    importance      FLOAT DEFAULT 0.5,         -- 重要性权重（0-1）
    access_count    INT DEFAULT 0,             -- 访问次数
    last_accessed_at TIMESTAMP,                -- 最后访问时间
    is_deleted      BOOLEAN DEFAULT FALSE,       -- 逻辑删除
    created_by      BIGINT,                    -- 创建人用户ID
    updated_by      BIGINT,                    -- 最后修改人用户ID
    created_at      TIMESTAMP DEFAULT NOW(),
    updated_at      TIMESTAMP DEFAULT NOW()
);

COMMENT ON TABLE user_long_term_memory IS '用户长期记忆表（Mem0管理）';
COMMENT ON COLUMN user_long_term_memory.memory_type IS 'fact事实/preference偏好/pattern模式';
COMMENT ON COLUMN user_long_term_memory.importance IS '重要性权重0-1';
COMMENT ON COLUMN user_long_term_memory.created_by IS '创建人用户ID';
COMMENT ON COLUMN user_long_term_memory.updated_by IS '最后修改人用户ID';

CREATE INDEX idx_ltm_user ON user_long_term_memory (tenant_id, user_id);
CREATE INDEX idx_ltm_importance ON user_long_term_memory (importance DESC, access_count DESC);
CREATE INDEX idx_ltm_embedding ON user_long_term_memory
    USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);


-- ============================================================
-- 9. 临时上传文档表（24小时自动清理）
-- ============================================================
CREATE TABLE temp_document (
    id              BIGSERIAL PRIMARY KEY,
    file_id         VARCHAR(100) UNIQUE NOT NULL, -- 文件唯一标识（UUID）
    tenant_id       BIGINT NOT NULL,
    user_id         BIGINT NOT NULL,
    conversation_id BIGINT,                      -- 所属会话ID（NULL表示未关联到具体会话）
    file_name       VARCHAR(255) NOT NULL,
    file_type       VARCHAR(20) NOT NULL,
    file_size       BIGINT DEFAULT 0,
    file_path       VARCHAR(500) NOT NULL,       -- 文件路径（兼容字段）
    oss_path        VARCHAR(500),                -- OSS临时存储路径（对话文档备份）
    content_type    VARCHAR(100),                -- MIME类型，如 application/pdf
    parsed_text     TEXT,                        -- 解析后的纯文本
    parse_status    VARCHAR(20) DEFAULT 'pending', -- pending / parsing / completed / failed
    is_deleted      BOOLEAN DEFAULT FALSE,       -- 逻辑删除（配合定时清理）
    expires_at      TIMESTAMP NOT NULL,          -- 过期时间（创建后24小时）
    created_by      BIGINT,                      -- 创建人用户ID
    updated_by      BIGINT,                      -- 最后修改人用户ID
    created_at      TIMESTAMP DEFAULT NOW(),
    updated_at      TIMESTAMP DEFAULT NOW()
);

COMMENT ON TABLE temp_document IS '对话框中临时上传的文档，24小时后自动清理';
COMMENT ON COLUMN temp_document.file_id IS '文件唯一标识UUID';
COMMENT ON COLUMN temp_document.conversation_id IS '所属会话ID，用于按会话管理临时文件';
COMMENT ON COLUMN temp_document.oss_path IS 'OSS临时存储路径（对话文档备份，与Java FileUploadUtils共享bucket）';
COMMENT ON COLUMN temp_document.content_type IS 'MIME类型，如application/pdf、text/plain';
COMMENT ON COLUMN temp_document.expires_at IS '过期时间，创建后24小时';
COMMENT ON COLUMN temp_document.created_by IS '创建人用户ID';
COMMENT ON COLUMN temp_document.updated_by IS '最后修改人用户ID';

CREATE INDEX idx_tmp_doc_file ON temp_document (file_id);
CREATE INDEX idx_tmp_doc_user ON temp_document (tenant_id, user_id);
CREATE INDEX idx_tmp_doc_conv ON temp_document (conversation_id);
CREATE INDEX idx_tmp_doc_expires ON temp_document (expires_at);

-- 定时清理函数（建议通过pg_cron或应用层定时任务执行）
-- SELECT * FROM temp_document WHERE expires_at < NOW();


-- ============================================================
-- 12. 增量迁移：OSS相关字段补全（已有数据库执行此段即可）
-- ============================================================

-- knowledge_document 新增列
ALTER TABLE knowledge_document ADD COLUMN IF NOT EXISTS oss_path VARCHAR(500);
ALTER TABLE knowledge_document ADD COLUMN IF NOT EXISTS content_type VARCHAR(100);
ALTER TABLE knowledge_document ADD COLUMN IF NOT EXISTS file_hash VARCHAR(64);
COMMENT ON COLUMN knowledge_document.oss_path IS 'OSS对象存储路径（持久备份）';
COMMENT ON COLUMN knowledge_document.content_type IS 'MIME类型';
COMMENT ON COLUMN knowledge_document.file_hash IS '文件SHA256哈希（去重/完整性校验）';

-- temp_document 新增列
ALTER TABLE temp_document ADD COLUMN IF NOT EXISTS oss_path VARCHAR(500);
ALTER TABLE temp_document ADD COLUMN IF NOT EXISTS content_type VARCHAR(100);
COMMENT ON COLUMN temp_document.oss_path IS 'OSS临时存储路径（对话文档备份）';
COMMENT ON COLUMN temp_document.content_type IS 'MIME类型';


-- ============================================================
-- 13. 过期临时文档自动清理函数
-- ============================================================
CREATE OR REPLACE FUNCTION cleanup_expired_temp_documents()
RETURNS integer AS $$
DECLARE
    deleted_count integer;
BEGIN
    -- 逻辑删除已过期的临时文档
    UPDATE temp_document
    SET is_deleted = TRUE, updated_at = NOW()
    WHERE expires_at < NOW() AND is_deleted = FALSE;
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION cleanup_expired_temp_documents() IS '标记已过期的临时文档为逻辑删除，可通过pg_cron定期执行: SELECT cleanup_expired_temp_documents()';


-- ============================================================
-- 10. AI操作审计日志表
-- ============================================================
CREATE TABLE ai_audit_log (
    id              BIGSERIAL PRIMARY KEY,
    tenant_id       BIGINT NOT NULL,
    user_id         BIGINT NOT NULL,
    action          VARCHAR(50) NOT NULL,       -- 操作类型：chat/write/knowledge_search/upload
    target_type     VARCHAR(50),                -- 目标类型：conversation/knowledge_base/document
    target_id       VARCHAR(100),               -- 目标ID
    request_data    JSONB,                      -- 请求数据（脱敏后）
    response_summary TEXT,                      -- 响应摘要
    tool_calls      JSONB,                      -- 工具调用记录
    token_usage     JSONB,                      -- Token消耗 {"input": 500, "output": 300}
    duration_ms     INT,                        -- 耗时毫秒
    ip_address      VARCHAR(50),
    user_agent      VARCHAR(500),               -- 客户端UA（区分Web/Mobile/桌面端）
    is_deleted      BOOLEAN DEFAULT FALSE,       -- 逻辑删除
    created_by      BIGINT,                    -- 创建人用户ID（操作者）
    updated_by      BIGINT,                    -- 最后修改人用户ID
    created_at      TIMESTAMP DEFAULT NOW(),
    updated_at      TIMESTAMP DEFAULT NOW()
);

COMMENT ON TABLE ai_audit_log IS 'AI操作审计日志表';
COMMENT ON COLUMN ai_audit_log.action IS '操作类型：chat对话/write写作/knowledge_search知识检索/upload上传';
COMMENT ON COLUMN ai_audit_log.created_by IS '操作者用户ID';
COMMENT ON COLUMN ai_audit_log.updated_by IS '最后修改人用户ID';

CREATE INDEX idx_audit_tenant ON ai_audit_log (tenant_id);
CREATE INDEX idx_audit_user ON ai_audit_log (user_id);
CREATE INDEX idx_audit_action ON ai_audit_log (action, created_at DESC);
CREATE INDEX idx_audit_created_at ON ai_audit_log (created_at DESC);
CREATE INDEX idx_audit_target ON ai_audit_log (target_type, target_id);


-- ============================================================
-- 11. 插入默认数据
-- ============================================================

-- 插入一个默认的全租户共享知识库（用于行业通用知识）
INSERT INTO knowledge_base (tenant_id, scope_type, name, description, status, is_deleted, created_by, updated_by, created_at, updated_at)
VALUES (NULL, 'global', '电镀行业通用知识库', '电镀行业通用标准、工艺知识、环保法规等', 'active', FALSE, 1, 1, NOW(), NOW())
ON CONFLICT DO NOTHING;


-- ============================================================
-- 完成日志
-- ============================================================
DO $$
BEGIN
    RAISE NOTICE 'AI助理数据库Schema初始化完成！';
    RAISE NOTICE '已创建表: conversation, conversation_message, knowledge_base, knowledge_document, knowledge_chunk, agent_knowledge_binding, knowledge_base_tag, user_long_term_memory, temp_document, ai_audit_log';
    RAISE NOTICE '所有表均已包含审计字段: created_by, created_at, updated_by, updated_at';
END $$;
