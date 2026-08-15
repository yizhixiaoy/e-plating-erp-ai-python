-- ============================================================
-- V3__ai_assistant_schema.sql
-- AI助理模块数据库初始化脚本 (PostgreSQL 15+)
-- 所有表包含审计字段：created_by, created_at, updated_by, updated_at
-- ============================================================

-- 启用 pgvector 扩展
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;  -- 三元组模糊匹配，用于BM25
