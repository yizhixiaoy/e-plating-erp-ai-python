-- ============================================================
-- 货物开单功能：AI服务PostgreSQL图片特征向量表
-- 用于CLIP图片相似度搜索和交叉比对
-- ============================================================

-- 创建 vector 扩展（pgvector）
CREATE EXTENSION IF NOT EXISTS vector;

-- 货物图片特征向量表
-- 注意：ViT-B-32 CLIP 模型输出 512 维向量，embedding 必须使用 vector(512)
-- 如果将来切换到 ViT-L-14（1024 维），需同步修改此处
CREATE TABLE IF NOT EXISTS goods_image_feature (
    id BIGINT PRIMARY KEY,
    tenant_id BIGINT NOT NULL,
    order_id BIGINT,
    item_id BIGINT,
    node_id BIGINT,
    record_id BIGINT,
    image_type VARCHAR(20) NOT NULL,
    embedding vector(512),
    oss_path VARCHAR(512) NOT NULL,
    image_url VARCHAR(512),
    thumbnail_url VARCHAR(512) DEFAULT '',
    file_size BIGINT DEFAULT 0,
    is_deleted BOOLEAN DEFAULT FALSE,
    created_by BIGINT,
    updated_by BIGINT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================================
-- HNSW索引（余弦相似度搜索加速）
-- m=16: 每个节点最多16个邻居，平衡搜索速度和内存占用
-- ef_construction=64: 构建索引时的候选集大小
-- 搜索时需设置: SET hnsw.ef_search = 64;（默认100）
-- ============================================================
CREATE INDEX IF NOT EXISTS idx_goods_image_feat_embedding ON goods_image_feature
    USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);

-- ============================================================
-- 常规查询索引
-- ============================================================

-- 租户隔离的延迟删除过滤索引（最常用查询场景）
CREATE INDEX IF NOT EXISTS idx_goods_image_feat_tenant ON goods_image_feature (tenant_id, is_deleted) WHERE is_deleted = FALSE;

-- 按开单/明细/节点查询（用于版本快照、追溯页面）
CREATE INDEX IF NOT EXISTS idx_goods_image_feat_order ON goods_image_feature (order_id);
CREATE INDEX IF NOT EXISTS idx_goods_image_feat_item ON goods_image_feature (item_id);
CREATE INDEX IF NOT EXISTS idx_goods_image_feat_node ON goods_image_feature (node_id);
CREATE INDEX IF NOT EXISTS idx_goods_image_feat_record ON goods_image_feature (record_id);

-- 按图片类型筛选（搜索时只查 SAMPLE 类型）
CREATE INDEX IF NOT EXISTS idx_goods_image_feat_type ON goods_image_feature (image_type);

-- 复合索引：租户+图片类型（用于交叉比对时获取某货物的所有样品照）
CREATE INDEX IF NOT EXISTS idx_goods_image_feat_tenant_type
    ON goods_image_feature (tenant_id, image_type) WHERE is_deleted = FALSE;

-- 按 OSS 路径查询（用于特征注册时去重检查）
CREATE INDEX IF NOT EXISTS idx_goods_image_feat_oss_path ON goods_image_feature (oss_path);
