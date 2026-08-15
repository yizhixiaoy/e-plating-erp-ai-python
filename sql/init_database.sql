-- ============================================================
-- init_database.sql
-- AI助理模块 - 数据库初始化脚本
-- 用途：创建 erp_ai 数据库 + 安装必需扩展
-- 执行方式：psql -U postgres -f init_database.sql
-- 依赖：PostgreSQL 15+，已在系统级安装 vector、pg_trgm 扩展
-- ============================================================

-- 1. 创建数据库（编码 UTF8，中文排序规则）
--    如果数据库已存在则不重建，避免误删数据
SELECT 'CREATE DATABASE erp_ai'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'erp_ai')\gexec

-- 2. 连接新库并安装扩展
\c erp_ai

CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- 3. 验证结果
DO $$
BEGIN
    RAISE NOTICE '数据库 erp_ai 初始化完成';
    RAISE NOTICE '  编码:    %', (SELECT pg_encoding_to_char(encoding) FROM pg_database WHERE datname = 'erp_ai');
    RAISE NOTICE '  Collate: %', (SELECT datcollate FROM pg_database WHERE datname = 'erp_ai');
    RAISE NOTICE '  Ctype:   %', (SELECT datctype FROM pg_database WHERE datname = 'erp_ai');
    RAISE NOTICE '  扩展:    vector = %, pg_trgm = %',
        (SELECT extversion FROM pg_extension WHERE extname = 'vector'),
        (SELECT extversion FROM pg_extension WHERE extname = 'pg_trgm');
END $$;

-- ============================================================
-- 附：手动建库命令（如果上面的 \gexec 方式不生效）
-- 请先连接到 template0 以外的任意库，然后执行：
--
-- CREATE DATABASE erp_ai
--   ENCODING 'UTF8'
--   LC_COLLATE = 'zh_CN.UTF-8'
--   LC_CTYPE = 'zh_CN.UTF-8'
--   TEMPLATE template0;
--
-- Windows 下如果 zh_CN.UTF-8 不可用，改用 C + ICU：
-- CREATE DATABASE erp_ai
--   ENCODING 'UTF8'
--   LOCALE_PROVIDER = 'icu'
--   ICU_LOCALE = 'zh-Hans-CN'
--   TEMPLATE template0;
-- ============================================================
