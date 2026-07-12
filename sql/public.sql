/*
 Navicat Premium Dump SQL

 Source Server         : tx-pgsql
 Source Server Type    : PostgreSQL
 Source Server Version : 180000 (180000)
 Source Host           : 127.0.0.1:5432
 Source Catalog        : erp_ai
 Source Schema         : public

 Target Server Type    : PostgreSQL
 Target Server Version : 180000 (180000)
 File Encoding         : 65001

 Date: 09/07/2026 21:20:10
*/


-- ----------------------------
-- Type structure for gtrgm
-- ----------------------------
DROP TYPE IF EXISTS "public"."gtrgm";
CREATE TYPE "public"."gtrgm" (
  INPUT = "public"."gtrgm_in",
  OUTPUT = "public"."gtrgm_out",
  INTERNALLENGTH = VARIABLE,
  CATEGORY = U,
  DELIMITER = ','
);
ALTER TYPE "public"."gtrgm" OWNER TO "postgres";

-- ----------------------------
-- Type structure for halfvec
-- ----------------------------
DROP TYPE IF EXISTS "public"."halfvec";
CREATE TYPE "public"."halfvec" (
  INPUT = "public"."halfvec_in",
  OUTPUT = "public"."halfvec_out",
  RECEIVE = "public"."halfvec_recv",
  SEND = "public"."halfvec_send",
  TYPMOD_IN = "public"."halfvec_typmod_in",
  INTERNALLENGTH = VARIABLE,
  STORAGE = external,
  CATEGORY = U,
  DELIMITER = ','
);
ALTER TYPE "public"."halfvec" OWNER TO "postgres";

-- ----------------------------
-- Type structure for sparsevec
-- ----------------------------
DROP TYPE IF EXISTS "public"."sparsevec";
CREATE TYPE "public"."sparsevec" (
  INPUT = "public"."sparsevec_in",
  OUTPUT = "public"."sparsevec_out",
  RECEIVE = "public"."sparsevec_recv",
  SEND = "public"."sparsevec_send",
  TYPMOD_IN = "public"."sparsevec_typmod_in",
  INTERNALLENGTH = VARIABLE,
  STORAGE = external,
  CATEGORY = U,
  DELIMITER = ','
);
ALTER TYPE "public"."sparsevec" OWNER TO "postgres";

-- ----------------------------
-- Type structure for vector
-- ----------------------------
DROP TYPE IF EXISTS "public"."vector";
CREATE TYPE "public"."vector" (
  INPUT = "public"."vector_in",
  OUTPUT = "public"."vector_out",
  RECEIVE = "public"."vector_recv",
  SEND = "public"."vector_send",
  TYPMOD_IN = "public"."vector_typmod_in",
  INTERNALLENGTH = VARIABLE,
  STORAGE = external,
  CATEGORY = U,
  DELIMITER = ','
);
ALTER TYPE "public"."vector" OWNER TO "postgres";

-- ----------------------------
-- Sequence structure for agent_knowledge_binding_id_seq
-- ----------------------------
DROP SEQUENCE IF EXISTS "public"."agent_knowledge_binding_id_seq";
CREATE SEQUENCE "public"."agent_knowledge_binding_id_seq" 
INCREMENT 1
MINVALUE  1
MAXVALUE 9223372036854775807
START 1
CACHE 1;
ALTER SEQUENCE "public"."agent_knowledge_binding_id_seq" OWNER TO "postgres";

-- ----------------------------
-- Sequence structure for ai_audit_log_id_seq
-- ----------------------------
DROP SEQUENCE IF EXISTS "public"."ai_audit_log_id_seq";
CREATE SEQUENCE "public"."ai_audit_log_id_seq" 
INCREMENT 1
MINVALUE  1
MAXVALUE 9223372036854775807
START 1
CACHE 1;
ALTER SEQUENCE "public"."ai_audit_log_id_seq" OWNER TO "postgres";

-- ----------------------------
-- Sequence structure for conversation_id_seq
-- ----------------------------
DROP SEQUENCE IF EXISTS "public"."conversation_id_seq";
CREATE SEQUENCE "public"."conversation_id_seq" 
INCREMENT 1
MINVALUE  1
MAXVALUE 9223372036854775807
START 1
CACHE 1;
ALTER SEQUENCE "public"."conversation_id_seq" OWNER TO "postgres";

-- ----------------------------
-- Sequence structure for conversation_message_id_seq
-- ----------------------------
DROP SEQUENCE IF EXISTS "public"."conversation_message_id_seq";
CREATE SEQUENCE "public"."conversation_message_id_seq" 
INCREMENT 1
MINVALUE  1
MAXVALUE 9223372036854775807
START 1
CACHE 1;
ALTER SEQUENCE "public"."conversation_message_id_seq" OWNER TO "postgres";

-- ----------------------------
-- Sequence structure for knowledge_base_id_seq
-- ----------------------------
DROP SEQUENCE IF EXISTS "public"."knowledge_base_id_seq";
CREATE SEQUENCE "public"."knowledge_base_id_seq" 
INCREMENT 1
MINVALUE  1
MAXVALUE 9223372036854775807
START 1
CACHE 1;
ALTER SEQUENCE "public"."knowledge_base_id_seq" OWNER TO "postgres";

-- ----------------------------
-- Sequence structure for knowledge_base_tag_id_seq
-- ----------------------------
DROP SEQUENCE IF EXISTS "public"."knowledge_base_tag_id_seq";
CREATE SEQUENCE "public"."knowledge_base_tag_id_seq" 
INCREMENT 1
MINVALUE  1
MAXVALUE 9223372036854775807
START 1
CACHE 1;
ALTER SEQUENCE "public"."knowledge_base_tag_id_seq" OWNER TO "postgres";

-- ----------------------------
-- Sequence structure for knowledge_chunk_id_seq
-- ----------------------------
DROP SEQUENCE IF EXISTS "public"."knowledge_chunk_id_seq";
CREATE SEQUENCE "public"."knowledge_chunk_id_seq" 
INCREMENT 1
MINVALUE  1
MAXVALUE 9223372036854775807
START 1
CACHE 1;
ALTER SEQUENCE "public"."knowledge_chunk_id_seq" OWNER TO "postgres";

-- ----------------------------
-- Sequence structure for knowledge_document_id_seq
-- ----------------------------
DROP SEQUENCE IF EXISTS "public"."knowledge_document_id_seq";
CREATE SEQUENCE "public"."knowledge_document_id_seq" 
INCREMENT 1
MINVALUE  1
MAXVALUE 9223372036854775807
START 1
CACHE 1;
ALTER SEQUENCE "public"."knowledge_document_id_seq" OWNER TO "postgres";

-- ----------------------------
-- Sequence structure for temp_document_id_seq
-- ----------------------------
DROP SEQUENCE IF EXISTS "public"."temp_document_id_seq";
CREATE SEQUENCE "public"."temp_document_id_seq" 
INCREMENT 1
MINVALUE  1
MAXVALUE 9223372036854775807
START 1
CACHE 1;
ALTER SEQUENCE "public"."temp_document_id_seq" OWNER TO "postgres";

-- ----------------------------
-- Sequence structure for user_long_term_memory_id_seq
-- ----------------------------
DROP SEQUENCE IF EXISTS "public"."user_long_term_memory_id_seq";
CREATE SEQUENCE "public"."user_long_term_memory_id_seq" 
INCREMENT 1
MINVALUE  1
MAXVALUE 9223372036854775807
START 1
CACHE 1;
ALTER SEQUENCE "public"."user_long_term_memory_id_seq" OWNER TO "postgres";

-- ----------------------------
-- Table structure for agent_knowledge_binding
-- ----------------------------
DROP TABLE IF EXISTS "public"."agent_knowledge_binding";
CREATE TABLE "public"."agent_knowledge_binding" (
  "id" int8 NOT NULL DEFAULT nextval('agent_knowledge_binding_id_seq'::regclass),
  "tenant_id" int8 NOT NULL,
  "agent_id" varchar(50) COLLATE "pg_catalog"."default" NOT NULL,
  "kb_id" int8 NOT NULL,
  "top_k" int4 DEFAULT 5,
  "score_threshold" float8 DEFAULT 0.6,
  "is_deleted" bool DEFAULT false,
  "created_by" int8,
  "updated_by" int8,
  "created_at" timestamp(6) DEFAULT now(),
  "updated_at" timestamp(6) DEFAULT now()
)
;
ALTER TABLE "public"."agent_knowledge_binding" OWNER TO "postgres";
COMMENT ON COLUMN "public"."agent_knowledge_binding"."created_by" IS '创建人用户ID';
COMMENT ON COLUMN "public"."agent_knowledge_binding"."updated_by" IS '最后修改人用户ID';
COMMENT ON TABLE "public"."agent_knowledge_binding" IS 'Agent与知识库的绑定关系表';

-- ----------------------------
-- Records of agent_knowledge_binding
-- ----------------------------
BEGIN;
COMMIT;

-- ----------------------------
-- Table structure for ai_audit_log
-- ----------------------------
DROP TABLE IF EXISTS "public"."ai_audit_log";
CREATE TABLE "public"."ai_audit_log" (
  "id" int8 NOT NULL DEFAULT nextval('ai_audit_log_id_seq'::regclass),
  "tenant_id" int8 NOT NULL,
  "user_id" int8 NOT NULL,
  "action" varchar(50) COLLATE "pg_catalog"."default" NOT NULL,
  "target_type" varchar(50) COLLATE "pg_catalog"."default",
  "target_id" varchar(100) COLLATE "pg_catalog"."default",
  "request_data" jsonb,
  "response_summary" text COLLATE "pg_catalog"."default",
  "tool_calls" jsonb,
  "token_usage" jsonb,
  "duration_ms" int4,
  "ip_address" varchar(50) COLLATE "pg_catalog"."default",
  "user_agent" varchar(500) COLLATE "pg_catalog"."default",
  "is_deleted" bool DEFAULT false,
  "created_by" int8,
  "updated_by" int8,
  "created_at" timestamp(6) DEFAULT now(),
  "updated_at" timestamp(6) DEFAULT now()
)
;
ALTER TABLE "public"."ai_audit_log" OWNER TO "postgres";
COMMENT ON COLUMN "public"."ai_audit_log"."action" IS '操作类型：chat对话/write写作/knowledge_search知识检索/upload上传';
COMMENT ON COLUMN "public"."ai_audit_log"."created_by" IS '操作者用户ID';
COMMENT ON COLUMN "public"."ai_audit_log"."updated_by" IS '最后修改人用户ID';
COMMENT ON TABLE "public"."ai_audit_log" IS 'AI操作审计日志表';

-- ----------------------------
-- Records of ai_audit_log
-- ----------------------------
BEGIN;
INSERT INTO "public"."ai_audit_log" ("id", "tenant_id", "user_id", "action", "target_type", "target_id", "request_data", "response_summary", "tool_calls", "token_usage", "duration_ms", "ip_address", "user_agent", "is_deleted", "created_by", "updated_by", "created_at", "updated_at") VALUES (1, 1, 1, '/api/ai/conversations', 'GET', NULL, NULL, NULL, NULL, NULL, 343, '127.0.0.1', NULL, 'f', 1, NULL, '2026-07-06 21:48:45.720309', '2026-07-06 21:48:45.720309');
INSERT INTO "public"."ai_audit_log" ("id", "tenant_id", "user_id", "action", "target_type", "target_id", "request_data", "response_summary", "tool_calls", "token_usage", "duration_ms", "ip_address", "user_agent", "is_deleted", "created_by", "updated_by", "created_at", "updated_at") VALUES (2, 1, 1, '/api/ai/chat', 'POST', NULL, NULL, NULL, NULL, NULL, 9, '127.0.0.1', NULL, 'f', 1, NULL, '2026-07-06 22:38:36.346638', '2026-07-06 22:38:36.346638');
INSERT INTO "public"."ai_audit_log" ("id", "tenant_id", "user_id", "action", "target_type", "target_id", "request_data", "response_summary", "tool_calls", "token_usage", "duration_ms", "ip_address", "user_agent", "is_deleted", "created_by", "updated_by", "created_at", "updated_at") VALUES (3, 1, 1, '/api/ai/write', 'POST', NULL, NULL, NULL, NULL, NULL, 9, '127.0.0.1', NULL, 'f', 1, NULL, '2026-07-06 22:41:24.49054', '2026-07-06 22:41:24.49054');
COMMIT;

-- ----------------------------
-- Table structure for checkpoint_blobs
-- ----------------------------
DROP TABLE IF EXISTS "public"."checkpoint_blobs";
CREATE TABLE "public"."checkpoint_blobs" (
  "thread_id" text COLLATE "pg_catalog"."default" NOT NULL,
  "checkpoint_ns" text COLLATE "pg_catalog"."default" NOT NULL DEFAULT ''::text,
  "channel" text COLLATE "pg_catalog"."default" NOT NULL,
  "version" text COLLATE "pg_catalog"."default" NOT NULL,
  "type" text COLLATE "pg_catalog"."default" NOT NULL,
  "blob" bytea
)
;
ALTER TABLE "public"."checkpoint_blobs" OWNER TO "postgres";

-- ----------------------------
-- Records of checkpoint_blobs
-- ----------------------------
BEGIN;
INSERT INTO "public"."checkpoint_blobs" ("thread_id", "checkpoint_ns", "channel", "version", "type", "blob") VALUES ('conv_1', '', '__start__', '00000000000000000000000000000001.0.17317361918105634', 'msgpack', E'\\336\\000\\024\\250messages\\221\\307\\213\\005\\224\\275langchain_core.messages.human\\254HumanMessage\\206\\247content\\246\\344\\275\\240\\345\\245\\275\\261additional_kwargs\\200\\261response_metadata\\200\\244type\\245human\\244name\\300\\242id\\300\\263model_validate_json\\245query\\246\\344\\275\\240\\345\\245\\275\\254user_context\\310\\004\\202\\005\\224\\262app.models.schemas\\253UserContext\\210\\251tenant_id\\001\\247user_id\\001\\250username\\246system\\250nickname\\240\\245roles\\221\\256PLATFORM_ADMIN\\253permissions\\334\\000D\\251dept:view\\262goods:customer:add\\256workbench:view\\251dict:view\\254profile:view\\253tenant:view\\257goods:order:add\\251menu:view\\261message:email:add\\251user:view\\250log:view\\254ai:chat:view\\255position:view\\251role:view\\251chat:send\\256ai:writer:view\\261ai:knowledge:view\\254message:view\\253chat:recall\\253message:add\\252tenant:add\\250role:add\\250user:add\\250menu:add\\263goods:customer:edit\\250dict:add\\254position:add\\272ai:knowledge:manage_global\\250dept:add\\262message:email:edit\\254profile:edit\\260goods:order:edit\\252log:export\\251dict:edit\\251dept:edit\\255position:edit\\251role:edit\\251menu:edit\\257message:publish\\253chat:create\\251user:edit\\253tenant:edit\\265goods:customer:delete\\264message:email:delete\\262goods:order:delete\\260profile:password\\272ai:knowledge:manage_tenant\\274ai:knowledge:manage_personal\\257position:delete\\254company:edit\\262message:email:send\\256message:revoke\\262goods:order:submit\\253dept:delete\\255tenant:status\\254user:disable\\253dict:delete\\253menu:delete\\252role:grant\\253role:delete\\266goods:order:distribute\\262message:email:view\\253user:enable\\262goods:order:cancel\\257message:mp:view\\255user:resetPwd\\260user:view:tenant\\257user:add:tenant\\252data_scope\\244NONE\\251auth_mode\\255authenticated\\263model_validate_json\\257conversation_id\\001\\246kb_ids\\300\\250file_ids\\300\\257task_complexity\\246simple\\265requires_confirmation\\302\\252plan_steps\\220\\256plan_confirmed\\302\\262tool_calls_pending\\220\\254tool_results\\220\\261knowledge_context\\300\\252references\\220\\256memory_summary\\240\\264conversation_history\\220\\256final_response\\300\\253token_usage\\200\\245error\\300\\255token_expired\\300');
INSERT INTO "public"."checkpoint_blobs" ("thread_id", "checkpoint_ns", "channel", "version", "type", "blob") VALUES ('conv_1', '', 'messages', '00000000000000000000000000000002.0.27291788420695784', 'msgpack', E'\\221\\307\\260\\005\\224\\275langchain_core.messages.human\\254HumanMessage\\206\\247content\\246\\344\\275\\240\\345\\245\\275\\261additional_kwargs\\200\\261response_metadata\\200\\244type\\245human\\244name\\300\\242id\\331$997f74a4-5131-48f7-9342-37e484b47b92\\263model_validate_json');
INSERT INTO "public"."checkpoint_blobs" ("thread_id", "checkpoint_ns", "channel", "version", "type", "blob") VALUES ('conv_1', '', 'user_context', '00000000000000000000000000000002.0.27291788420695784', 'msgpack', E'\\310\\004\\202\\005\\224\\262app.models.schemas\\253UserContext\\210\\251tenant_id\\001\\247user_id\\001\\250username\\246system\\250nickname\\240\\245roles\\221\\256PLATFORM_ADMIN\\253permissions\\334\\000D\\251dept:view\\262goods:customer:add\\256workbench:view\\251dict:view\\254profile:view\\253tenant:view\\257goods:order:add\\251menu:view\\261message:email:add\\251user:view\\250log:view\\254ai:chat:view\\255position:view\\251role:view\\251chat:send\\256ai:writer:view\\261ai:knowledge:view\\254message:view\\253chat:recall\\253message:add\\252tenant:add\\250role:add\\250user:add\\250menu:add\\263goods:customer:edit\\250dict:add\\254position:add\\272ai:knowledge:manage_global\\250dept:add\\262message:email:edit\\254profile:edit\\260goods:order:edit\\252log:export\\251dict:edit\\251dept:edit\\255position:edit\\251role:edit\\251menu:edit\\257message:publish\\253chat:create\\251user:edit\\253tenant:edit\\265goods:customer:delete\\264message:email:delete\\262goods:order:delete\\260profile:password\\272ai:knowledge:manage_tenant\\274ai:knowledge:manage_personal\\257position:delete\\254company:edit\\262message:email:send\\256message:revoke\\262goods:order:submit\\253dept:delete\\255tenant:status\\254user:disable\\253dict:delete\\253menu:delete\\252role:grant\\253role:delete\\266goods:order:distribute\\262message:email:view\\253user:enable\\262goods:order:cancel\\257message:mp:view\\255user:resetPwd\\260user:view:tenant\\257user:add:tenant\\252data_scope\\244NONE\\251auth_mode\\255authenticated\\263model_validate_json');
INSERT INTO "public"."checkpoint_blobs" ("thread_id", "checkpoint_ns", "channel", "version", "type", "blob") VALUES ('conv_1', '', 'plan_steps', '00000000000000000000000000000002.0.27291788420695784', 'msgpack', E'\\220');
INSERT INTO "public"."checkpoint_blobs" ("thread_id", "checkpoint_ns", "channel", "version", "type", "blob") VALUES ('conv_1', '', 'tool_calls_pending', '00000000000000000000000000000002.0.27291788420695784', 'msgpack', E'\\220');
INSERT INTO "public"."checkpoint_blobs" ("thread_id", "checkpoint_ns", "channel", "version", "type", "blob") VALUES ('conv_1', '', 'tool_results', '00000000000000000000000000000002.0.27291788420695784', 'msgpack', E'\\220');
INSERT INTO "public"."checkpoint_blobs" ("thread_id", "checkpoint_ns", "channel", "version", "type", "blob") VALUES ('conv_1', '', 'references', '00000000000000000000000000000002.0.27291788420695784', 'msgpack', E'\\220');
INSERT INTO "public"."checkpoint_blobs" ("thread_id", "checkpoint_ns", "channel", "version", "type", "blob") VALUES ('conv_1', '', 'conversation_history', '00000000000000000000000000000002.0.27291788420695784', 'msgpack', E'\\220');
INSERT INTO "public"."checkpoint_blobs" ("thread_id", "checkpoint_ns", "channel", "version", "type", "blob") VALUES ('conv_1', '', 'token_usage', '00000000000000000000000000000002.0.27291788420695784', 'msgpack', E'\\200');
INSERT INTO "public"."checkpoint_blobs" ("thread_id", "checkpoint_ns", "channel", "version", "type", "blob") VALUES ('conv_1', '', 'tool_calls_pending', '00000000000000000000000000000004.0.9640618856581671', 'msgpack', E'\\220');
INSERT INTO "public"."checkpoint_blobs" ("thread_id", "checkpoint_ns", "channel", "version", "type", "blob") VALUES ('conv_1', '', 'tool_results', '00000000000000000000000000000004.0.9640618856581671', 'msgpack', E'\\220');
INSERT INTO "public"."checkpoint_blobs" ("thread_id", "checkpoint_ns", "channel", "version", "type", "blob") VALUES ('conv_1', '', 'references', '00000000000000000000000000000004.0.9640618856581671', 'msgpack', E'\\220');
INSERT INTO "public"."checkpoint_blobs" ("thread_id", "checkpoint_ns", "channel", "version", "type", "blob") VALUES ('conv_1', '', 'references', '00000000000000000000000000000005.0.13691035902030346', 'msgpack', E'\\220');
INSERT INTO "public"."checkpoint_blobs" ("thread_id", "checkpoint_ns", "channel", "version", "type", "blob") VALUES ('conv_1', '', 'token_usage', '00000000000000000000000000000005.0.13691035902030346', 'msgpack', E'\\202\\245input\\315\\0017\\246outputJ');
COMMIT;

-- ----------------------------
-- Table structure for checkpoint_migrations
-- ----------------------------
DROP TABLE IF EXISTS "public"."checkpoint_migrations";
CREATE TABLE "public"."checkpoint_migrations" (
  "v" int4 NOT NULL
)
;
ALTER TABLE "public"."checkpoint_migrations" OWNER TO "postgres";

-- ----------------------------
-- Records of checkpoint_migrations
-- ----------------------------
BEGIN;
INSERT INTO "public"."checkpoint_migrations" ("v") VALUES (0);
INSERT INTO "public"."checkpoint_migrations" ("v") VALUES (1);
INSERT INTO "public"."checkpoint_migrations" ("v") VALUES (2);
INSERT INTO "public"."checkpoint_migrations" ("v") VALUES (3);
INSERT INTO "public"."checkpoint_migrations" ("v") VALUES (4);
INSERT INTO "public"."checkpoint_migrations" ("v") VALUES (5);
INSERT INTO "public"."checkpoint_migrations" ("v") VALUES (6);
INSERT INTO "public"."checkpoint_migrations" ("v") VALUES (7);
INSERT INTO "public"."checkpoint_migrations" ("v") VALUES (8);
INSERT INTO "public"."checkpoint_migrations" ("v") VALUES (9);
COMMIT;

-- ----------------------------
-- Table structure for checkpoint_writes
-- ----------------------------
DROP TABLE IF EXISTS "public"."checkpoint_writes";
CREATE TABLE "public"."checkpoint_writes" (
  "thread_id" text COLLATE "pg_catalog"."default" NOT NULL,
  "checkpoint_ns" text COLLATE "pg_catalog"."default" NOT NULL DEFAULT ''::text,
  "checkpoint_id" text COLLATE "pg_catalog"."default" NOT NULL,
  "task_id" text COLLATE "pg_catalog"."default" NOT NULL,
  "idx" int4 NOT NULL,
  "channel" text COLLATE "pg_catalog"."default" NOT NULL,
  "type" text COLLATE "pg_catalog"."default",
  "blob" bytea NOT NULL,
  "task_path" text COLLATE "pg_catalog"."default" NOT NULL DEFAULT ''::text
)
;
ALTER TABLE "public"."checkpoint_writes" OWNER TO "postgres";

-- ----------------------------
-- Records of checkpoint_writes
-- ----------------------------
BEGIN;
INSERT INTO "public"."checkpoint_writes" ("thread_id", "checkpoint_ns", "checkpoint_id", "task_id", "idx", "channel", "type", "blob", "task_path") VALUES ('conv_1', '', '1f179485-f43f-63e6-bfff-c0e33778e759', '2572d2e5-63ca-dd63-3192-789b6b427e31', 0, 'messages', 'msgpack', E'\\221\\307\\213\\005\\224\\275langchain_core.messages.human\\254HumanMessage\\206\\247content\\246\\344\\275\\240\\345\\245\\275\\261additional_kwargs\\200\\261response_metadata\\200\\244type\\245human\\244name\\300\\242id\\300\\263model_validate_json', '~__pregel_pull, __start__');
INSERT INTO "public"."checkpoint_writes" ("thread_id", "checkpoint_ns", "checkpoint_id", "task_id", "idx", "channel", "type", "blob", "task_path") VALUES ('conv_1', '', '1f179485-f43f-63e6-bfff-c0e33778e759', '2572d2e5-63ca-dd63-3192-789b6b427e31', 1, 'query', 'msgpack', E'\\246\\344\\275\\240\\345\\245\\275', '~__pregel_pull, __start__');
INSERT INTO "public"."checkpoint_writes" ("thread_id", "checkpoint_ns", "checkpoint_id", "task_id", "idx", "channel", "type", "blob", "task_path") VALUES ('conv_1', '', '1f179485-f43f-63e6-bfff-c0e33778e759', '2572d2e5-63ca-dd63-3192-789b6b427e31', 2, 'user_context', 'msgpack', E'\\310\\004\\202\\005\\224\\262app.models.schemas\\253UserContext\\210\\251tenant_id\\001\\247user_id\\001\\250username\\246system\\250nickname\\240\\245roles\\221\\256PLATFORM_ADMIN\\253permissions\\334\\000D\\251dept:view\\262goods:customer:add\\256workbench:view\\251dict:view\\254profile:view\\253tenant:view\\257goods:order:add\\251menu:view\\261message:email:add\\251user:view\\250log:view\\254ai:chat:view\\255position:view\\251role:view\\251chat:send\\256ai:writer:view\\261ai:knowledge:view\\254message:view\\253chat:recall\\253message:add\\252tenant:add\\250role:add\\250user:add\\250menu:add\\263goods:customer:edit\\250dict:add\\254position:add\\272ai:knowledge:manage_global\\250dept:add\\262message:email:edit\\254profile:edit\\260goods:order:edit\\252log:export\\251dict:edit\\251dept:edit\\255position:edit\\251role:edit\\251menu:edit\\257message:publish\\253chat:create\\251user:edit\\253tenant:edit\\265goods:customer:delete\\264message:email:delete\\262goods:order:delete\\260profile:password\\272ai:knowledge:manage_tenant\\274ai:knowledge:manage_personal\\257position:delete\\254company:edit\\262message:email:send\\256message:revoke\\262goods:order:submit\\253dept:delete\\255tenant:status\\254user:disable\\253dict:delete\\253menu:delete\\252role:grant\\253role:delete\\266goods:order:distribute\\262message:email:view\\253user:enable\\262goods:order:cancel\\257message:mp:view\\255user:resetPwd\\260user:view:tenant\\257user:add:tenant\\252data_scope\\244NONE\\251auth_mode\\255authenticated\\263model_validate_json', '~__pregel_pull, __start__');
INSERT INTO "public"."checkpoint_writes" ("thread_id", "checkpoint_ns", "checkpoint_id", "task_id", "idx", "channel", "type", "blob", "task_path") VALUES ('conv_1', '', '1f179485-f43f-63e6-bfff-c0e33778e759', '2572d2e5-63ca-dd63-3192-789b6b427e31', 3, 'conversation_id', 'msgpack', E'\\001', '~__pregel_pull, __start__');
INSERT INTO "public"."checkpoint_writes" ("thread_id", "checkpoint_ns", "checkpoint_id", "task_id", "idx", "channel", "type", "blob", "task_path") VALUES ('conv_1', '', '1f179485-f43f-63e6-bfff-c0e33778e759', '2572d2e5-63ca-dd63-3192-789b6b427e31', 4, 'kb_ids', 'null', '', '~__pregel_pull, __start__');
INSERT INTO "public"."checkpoint_writes" ("thread_id", "checkpoint_ns", "checkpoint_id", "task_id", "idx", "channel", "type", "blob", "task_path") VALUES ('conv_1', '', '1f179485-f43f-63e6-bfff-c0e33778e759', '2572d2e5-63ca-dd63-3192-789b6b427e31', 5, 'file_ids', 'null', '', '~__pregel_pull, __start__');
INSERT INTO "public"."checkpoint_writes" ("thread_id", "checkpoint_ns", "checkpoint_id", "task_id", "idx", "channel", "type", "blob", "task_path") VALUES ('conv_1', '', '1f179485-f43f-63e6-bfff-c0e33778e759', '2572d2e5-63ca-dd63-3192-789b6b427e31', 6, 'task_complexity', 'msgpack', E'\\246simple', '~__pregel_pull, __start__');
INSERT INTO "public"."checkpoint_writes" ("thread_id", "checkpoint_ns", "checkpoint_id", "task_id", "idx", "channel", "type", "blob", "task_path") VALUES ('conv_1', '', '1f179485-f43f-63e6-bfff-c0e33778e759', '2572d2e5-63ca-dd63-3192-789b6b427e31', 7, 'requires_confirmation', 'msgpack', E'\\302', '~__pregel_pull, __start__');
INSERT INTO "public"."checkpoint_writes" ("thread_id", "checkpoint_ns", "checkpoint_id", "task_id", "idx", "channel", "type", "blob", "task_path") VALUES ('conv_1', '', '1f179485-f43f-63e6-bfff-c0e33778e759', '2572d2e5-63ca-dd63-3192-789b6b427e31', 8, 'plan_steps', 'msgpack', E'\\220', '~__pregel_pull, __start__');
INSERT INTO "public"."checkpoint_writes" ("thread_id", "checkpoint_ns", "checkpoint_id", "task_id", "idx", "channel", "type", "blob", "task_path") VALUES ('conv_1', '', '1f179485-f43f-63e6-bfff-c0e33778e759', '2572d2e5-63ca-dd63-3192-789b6b427e31', 9, 'plan_confirmed', 'msgpack', E'\\302', '~__pregel_pull, __start__');
INSERT INTO "public"."checkpoint_writes" ("thread_id", "checkpoint_ns", "checkpoint_id", "task_id", "idx", "channel", "type", "blob", "task_path") VALUES ('conv_1', '', '1f179485-f43f-63e6-bfff-c0e33778e759', '2572d2e5-63ca-dd63-3192-789b6b427e31', 10, 'tool_calls_pending', 'msgpack', E'\\220', '~__pregel_pull, __start__');
INSERT INTO "public"."checkpoint_writes" ("thread_id", "checkpoint_ns", "checkpoint_id", "task_id", "idx", "channel", "type", "blob", "task_path") VALUES ('conv_1', '', '1f179485-f43f-63e6-bfff-c0e33778e759', '2572d2e5-63ca-dd63-3192-789b6b427e31', 11, 'tool_results', 'msgpack', E'\\220', '~__pregel_pull, __start__');
INSERT INTO "public"."checkpoint_writes" ("thread_id", "checkpoint_ns", "checkpoint_id", "task_id", "idx", "channel", "type", "blob", "task_path") VALUES ('conv_1', '', '1f179485-f43f-63e6-bfff-c0e33778e759', '2572d2e5-63ca-dd63-3192-789b6b427e31', 12, 'knowledge_context', 'null', '', '~__pregel_pull, __start__');
INSERT INTO "public"."checkpoint_writes" ("thread_id", "checkpoint_ns", "checkpoint_id", "task_id", "idx", "channel", "type", "blob", "task_path") VALUES ('conv_1', '', '1f179485-f43f-63e6-bfff-c0e33778e759', '2572d2e5-63ca-dd63-3192-789b6b427e31', 13, 'references', 'msgpack', E'\\220', '~__pregel_pull, __start__');
INSERT INTO "public"."checkpoint_writes" ("thread_id", "checkpoint_ns", "checkpoint_id", "task_id", "idx", "channel", "type", "blob", "task_path") VALUES ('conv_1', '', '1f179485-f43f-63e6-bfff-c0e33778e759', '2572d2e5-63ca-dd63-3192-789b6b427e31', 14, 'memory_summary', 'msgpack', E'\\240', '~__pregel_pull, __start__');
INSERT INTO "public"."checkpoint_writes" ("thread_id", "checkpoint_ns", "checkpoint_id", "task_id", "idx", "channel", "type", "blob", "task_path") VALUES ('conv_1', '', '1f179485-f43f-63e6-bfff-c0e33778e759', '2572d2e5-63ca-dd63-3192-789b6b427e31', 15, 'conversation_history', 'msgpack', E'\\220', '~__pregel_pull, __start__');
INSERT INTO "public"."checkpoint_writes" ("thread_id", "checkpoint_ns", "checkpoint_id", "task_id", "idx", "channel", "type", "blob", "task_path") VALUES ('conv_1', '', '1f179485-f43f-63e6-bfff-c0e33778e759', '2572d2e5-63ca-dd63-3192-789b6b427e31', 16, 'final_response', 'null', '', '~__pregel_pull, __start__');
INSERT INTO "public"."checkpoint_writes" ("thread_id", "checkpoint_ns", "checkpoint_id", "task_id", "idx", "channel", "type", "blob", "task_path") VALUES ('conv_1', '', '1f179485-f43f-63e6-bfff-c0e33778e759', '2572d2e5-63ca-dd63-3192-789b6b427e31', 17, 'token_usage', 'msgpack', E'\\200', '~__pregel_pull, __start__');
INSERT INTO "public"."checkpoint_writes" ("thread_id", "checkpoint_ns", "checkpoint_id", "task_id", "idx", "channel", "type", "blob", "task_path") VALUES ('conv_1', '', '1f179485-f43f-63e6-bfff-c0e33778e759', '2572d2e5-63ca-dd63-3192-789b6b427e31', 18, 'error', 'null', '', '~__pregel_pull, __start__');
INSERT INTO "public"."checkpoint_writes" ("thread_id", "checkpoint_ns", "checkpoint_id", "task_id", "idx", "channel", "type", "blob", "task_path") VALUES ('conv_1', '', '1f179485-f43f-63e6-bfff-c0e33778e759', '2572d2e5-63ca-dd63-3192-789b6b427e31', 19, 'token_expired', 'null', '', '~__pregel_pull, __start__');
INSERT INTO "public"."checkpoint_writes" ("thread_id", "checkpoint_ns", "checkpoint_id", "task_id", "idx", "channel", "type", "blob", "task_path") VALUES ('conv_1', '', '1f179485-f43f-63e6-bfff-c0e33778e759', '2572d2e5-63ca-dd63-3192-789b6b427e31', 20, 'branch:to:classifier', 'null', '', '~__pregel_pull, __start__');
INSERT INTO "public"."checkpoint_writes" ("thread_id", "checkpoint_ns", "checkpoint_id", "task_id", "idx", "channel", "type", "blob", "task_path") VALUES ('conv_1', '', '1f179485-f454-6fca-8000-d9731e047bfe', '6345052b-f2c1-45ec-0d35-1b9e8bd49a91', 0, 'task_complexity', 'msgpack', E'\\246simple', '~__pregel_pull, classifier');
INSERT INTO "public"."checkpoint_writes" ("thread_id", "checkpoint_ns", "checkpoint_id", "task_id", "idx", "channel", "type", "blob", "task_path") VALUES ('conv_1', '', '1f179485-f454-6fca-8000-d9731e047bfe', '6345052b-f2c1-45ec-0d35-1b9e8bd49a91', 1, 'requires_confirmation', 'msgpack', E'\\302', '~__pregel_pull, classifier');
INSERT INTO "public"."checkpoint_writes" ("thread_id", "checkpoint_ns", "checkpoint_id", "task_id", "idx", "channel", "type", "blob", "task_path") VALUES ('conv_1', '', '1f179485-f454-6fca-8000-d9731e047bfe', '6345052b-f2c1-45ec-0d35-1b9e8bd49a91', 2, 'branch:to:executor', 'null', '', '~__pregel_pull, classifier');
INSERT INTO "public"."checkpoint_writes" ("thread_id", "checkpoint_ns", "checkpoint_id", "task_id", "idx", "channel", "type", "blob", "task_path") VALUES ('conv_1', '', '1f179485-fd23-6eb2-8001-3e8ffd5c8ce4', 'ce5049ef-2115-19ff-ea1a-2c3d9fc612d8', 0, 'tool_calls_pending', 'msgpack', E'\\220', '~__pregel_pull, executor');
INSERT INTO "public"."checkpoint_writes" ("thread_id", "checkpoint_ns", "checkpoint_id", "task_id", "idx", "channel", "type", "blob", "task_path") VALUES ('conv_1', '', '1f179485-fd23-6eb2-8001-3e8ffd5c8ce4', 'ce5049ef-2115-19ff-ea1a-2c3d9fc612d8', 1, 'tool_results', 'msgpack', E'\\220', '~__pregel_pull, executor');
INSERT INTO "public"."checkpoint_writes" ("thread_id", "checkpoint_ns", "checkpoint_id", "task_id", "idx", "channel", "type", "blob", "task_path") VALUES ('conv_1', '', '1f179485-fd23-6eb2-8001-3e8ffd5c8ce4', 'ce5049ef-2115-19ff-ea1a-2c3d9fc612d8', 2, 'knowledge_context', 'null', '', '~__pregel_pull, executor');
INSERT INTO "public"."checkpoint_writes" ("thread_id", "checkpoint_ns", "checkpoint_id", "task_id", "idx", "channel", "type", "blob", "task_path") VALUES ('conv_1', '', '1f179485-fd23-6eb2-8001-3e8ffd5c8ce4', 'ce5049ef-2115-19ff-ea1a-2c3d9fc612d8', 3, 'references', 'msgpack', E'\\220', '~__pregel_pull, executor');
INSERT INTO "public"."checkpoint_writes" ("thread_id", "checkpoint_ns", "checkpoint_id", "task_id", "idx", "channel", "type", "blob", "task_path") VALUES ('conv_1', '', '1f179485-fd23-6eb2-8001-3e8ffd5c8ce4', 'ce5049ef-2115-19ff-ea1a-2c3d9fc612d8', 4, 'branch:to:aggregator', 'null', '', '~__pregel_pull, executor');
INSERT INTO "public"."checkpoint_writes" ("thread_id", "checkpoint_ns", "checkpoint_id", "task_id", "idx", "channel", "type", "blob", "task_path") VALUES ('conv_1', '', '1f179486-0938-6c20-8002-2453a3c2d279', '973bbae6-ac86-b62a-abe9-5b2e690f0871', 0, 'final_response', 'msgpack', E'\\331\\375\\344\\275\\240\\345\\245\\275\\357\\274\\201\\346\\210\\221\\346\\230\\257\\346\\231\\272\\351\\225\\200\\344\\272\\221AI\\357\\274\\214\\347\\224\\265\\351\\225\\200\\350\\241\\214\\344\\270\\232ERP\\347\\263\\273\\347\\273\\237\\347\\232\\204\\346\\231\\272\\350\\203\\275\\345\\212\\251\\347\\220\\206\\343\\200\\202\\345\\276\\210\\351\\253\\230\\345\\205\\264\\344\\270\\272\\346\\202\\250\\346\\234\\215\\345\\212\\241\\357\\275\\236\\012\\012\\346\\210\\221\\345\\217\\257\\344\\273\\245\\345\\270\\256\\346\\202\\250\\350\\247\\243\\347\\255\\224\\347\\224\\265\\351\\225\\200\\345\\267\\245\\350\\211\\272\\351\\227\\256\\351\\242\\230\\343\\200\\201\\346\\237\\245\\350\\257\\242\\345\\210\\206\\346\\236\\220\\344\\270\\232\\345\\212\\241\\346\\225\\260\\346\\215\\256\\343\\200\\201\\347\\224\\237\\346\\210\\220\\345\\267\\245\\344\\275\\234\\346\\212\\245\\345\\221\\212\\357\\274\\214\\346\\210\\226\\350\\200\\205\\346\\214\\207\\345\\257\\274\\346\\202\\250\\344\\275\\277\\347\\224\\250\\347\\263\\273\\347\\273\\237\\345\\212\\237\\350\\203\\275\\343\\200\\202\\350\\257\\267\\351\\227\\256\\346\\234\\211\\344\\273\\200\\344\\271\\210\\345\\217\\257\\344\\273\\245\\345\\270\\256\\346\\202\\250\\347\\232\\204\\357\\274\\237', '~__pregel_pull, aggregator');
INSERT INTO "public"."checkpoint_writes" ("thread_id", "checkpoint_ns", "checkpoint_id", "task_id", "idx", "channel", "type", "blob", "task_path") VALUES ('conv_1', '', '1f179486-0938-6c20-8002-2453a3c2d279', '973bbae6-ac86-b62a-abe9-5b2e690f0871', 1, 'token_usage', 'msgpack', E'\\202\\245input\\315\\0017\\246outputJ', '~__pregel_pull, aggregator');
INSERT INTO "public"."checkpoint_writes" ("thread_id", "checkpoint_ns", "checkpoint_id", "task_id", "idx", "channel", "type", "blob", "task_path") VALUES ('conv_1', '', '1f179486-0938-6c20-8002-2453a3c2d279', '973bbae6-ac86-b62a-abe9-5b2e690f0871', 2, 'references', 'msgpack', E'\\220', '~__pregel_pull, aggregator');
COMMIT;

-- ----------------------------
-- Table structure for checkpoints
-- ----------------------------
DROP TABLE IF EXISTS "public"."checkpoints";
CREATE TABLE "public"."checkpoints" (
  "thread_id" text COLLATE "pg_catalog"."default" NOT NULL,
  "checkpoint_ns" text COLLATE "pg_catalog"."default" NOT NULL DEFAULT ''::text,
  "checkpoint_id" text COLLATE "pg_catalog"."default" NOT NULL,
  "parent_checkpoint_id" text COLLATE "pg_catalog"."default",
  "type" text COLLATE "pg_catalog"."default",
  "checkpoint" jsonb NOT NULL,
  "metadata" jsonb NOT NULL DEFAULT '{}'::jsonb
)
;
ALTER TABLE "public"."checkpoints" OWNER TO "postgres";

-- ----------------------------
-- Records of checkpoints
-- ----------------------------
BEGIN;
INSERT INTO "public"."checkpoints" ("thread_id", "checkpoint_ns", "checkpoint_id", "parent_checkpoint_id", "type", "checkpoint", "metadata") VALUES ('conv_1', '', '1f179485-f43f-63e6-bfff-c0e33778e759', NULL, NULL, '{"v": 4, "id": "1f179485-f43f-63e6-bfff-c0e33778e759", "ts": "2026-07-06T14:38:36.809090+00:00", "versions_seen": {"__input__": {}}, "channel_values": {}, "channel_versions": {"__start__": "00000000000000000000000000000001.0.17317361918105634"}, "updated_channels": ["__start__"]}', '{"step": -1, "source": "input", "parents": {}}');
INSERT INTO "public"."checkpoints" ("thread_id", "checkpoint_ns", "checkpoint_id", "parent_checkpoint_id", "type", "checkpoint", "metadata") VALUES ('conv_1', '', '1f179485-f454-6fca-8000-d9731e047bfe', '1f179485-f43f-63e6-bfff-c0e33778e759', NULL, '{"v": 4, "id": "1f179485-f454-6fca-8000-d9731e047bfe", "ts": "2026-07-06T14:38:36.817979+00:00", "versions_seen": {"__input__": {}, "__start__": {"__start__": "00000000000000000000000000000001.0.17317361918105634"}}, "channel_values": {"error": null, "query": "你好", "kb_ids": null, "file_ids": null, "token_expired": null, "final_response": null, "memory_summary": "", "plan_confirmed": false, "conversation_id": 1, "task_complexity": "simple", "knowledge_context": null, "branch:to:classifier": null, "requires_confirmation": false}, "channel_versions": {"error": "00000000000000000000000000000002.0.27291788420695784", "query": "00000000000000000000000000000002.0.27291788420695784", "kb_ids": "00000000000000000000000000000002.0.27291788420695784", "file_ids": "00000000000000000000000000000002.0.27291788420695784", "messages": "00000000000000000000000000000002.0.27291788420695784", "__start__": "00000000000000000000000000000002.0.27291788420695784", "plan_steps": "00000000000000000000000000000002.0.27291788420695784", "references": "00000000000000000000000000000002.0.27291788420695784", "token_usage": "00000000000000000000000000000002.0.27291788420695784", "tool_results": "00000000000000000000000000000002.0.27291788420695784", "user_context": "00000000000000000000000000000002.0.27291788420695784", "token_expired": "00000000000000000000000000000002.0.27291788420695784", "final_response": "00000000000000000000000000000002.0.27291788420695784", "memory_summary": "00000000000000000000000000000002.0.27291788420695784", "plan_confirmed": "00000000000000000000000000000002.0.27291788420695784", "conversation_id": "00000000000000000000000000000002.0.27291788420695784", "task_complexity": "00000000000000000000000000000002.0.27291788420695784", "knowledge_context": "00000000000000000000000000000002.0.27291788420695784", "tool_calls_pending": "00000000000000000000000000000002.0.27291788420695784", "branch:to:classifier": "00000000000000000000000000000002.0.27291788420695784", "conversation_history": "00000000000000000000000000000002.0.27291788420695784", "requires_confirmation": "00000000000000000000000000000002.0.27291788420695784"}, "updated_channels": ["branch:to:classifier", "conversation_history", "conversation_id", "error", "file_ids", "final_response", "kb_ids", "knowledge_context", "memory_summary", "messages", "plan_confirmed", "plan_steps", "query", "references", "requires_confirmation", "task_complexity", "token_expired", "token_usage", "tool_calls_pending", "tool_results", "user_context"]}', '{"step": 0, "source": "loop", "parents": {}}');
INSERT INTO "public"."checkpoints" ("thread_id", "checkpoint_ns", "checkpoint_id", "parent_checkpoint_id", "type", "checkpoint", "metadata") VALUES ('conv_1', '', '1f179485-fd23-6eb2-8001-3e8ffd5c8ce4', '1f179485-f454-6fca-8000-d9731e047bfe', NULL, '{"v": 4, "id": "1f179485-fd23-6eb2-8001-3e8ffd5c8ce4", "ts": "2026-07-06T14:38:37.741615+00:00", "versions_seen": {"__input__": {}, "__start__": {"__start__": "00000000000000000000000000000001.0.17317361918105634"}, "classifier": {"branch:to:classifier": "00000000000000000000000000000002.0.27291788420695784"}}, "channel_values": {"error": null, "query": "你好", "kb_ids": null, "file_ids": null, "token_expired": null, "final_response": null, "memory_summary": "", "plan_confirmed": false, "conversation_id": 1, "task_complexity": "simple", "knowledge_context": null, "branch:to:executor": null, "requires_confirmation": false}, "channel_versions": {"error": "00000000000000000000000000000002.0.27291788420695784", "query": "00000000000000000000000000000002.0.27291788420695784", "kb_ids": "00000000000000000000000000000002.0.27291788420695784", "file_ids": "00000000000000000000000000000002.0.27291788420695784", "messages": "00000000000000000000000000000002.0.27291788420695784", "__start__": "00000000000000000000000000000002.0.27291788420695784", "plan_steps": "00000000000000000000000000000002.0.27291788420695784", "references": "00000000000000000000000000000002.0.27291788420695784", "token_usage": "00000000000000000000000000000002.0.27291788420695784", "tool_results": "00000000000000000000000000000002.0.27291788420695784", "user_context": "00000000000000000000000000000002.0.27291788420695784", "token_expired": "00000000000000000000000000000002.0.27291788420695784", "final_response": "00000000000000000000000000000002.0.27291788420695784", "memory_summary": "00000000000000000000000000000002.0.27291788420695784", "plan_confirmed": "00000000000000000000000000000002.0.27291788420695784", "conversation_id": "00000000000000000000000000000002.0.27291788420695784", "task_complexity": "00000000000000000000000000000003.0.7140894666036767", "knowledge_context": "00000000000000000000000000000002.0.27291788420695784", "branch:to:executor": "00000000000000000000000000000003.0.7140894666036767", "tool_calls_pending": "00000000000000000000000000000002.0.27291788420695784", "branch:to:classifier": "00000000000000000000000000000003.0.7140894666036767", "conversation_history": "00000000000000000000000000000002.0.27291788420695784", "requires_confirmation": "00000000000000000000000000000003.0.7140894666036767"}, "updated_channels": ["branch:to:executor", "requires_confirmation", "task_complexity"]}', '{"step": 1, "source": "loop", "parents": {}}');
INSERT INTO "public"."checkpoints" ("thread_id", "checkpoint_ns", "checkpoint_id", "parent_checkpoint_id", "type", "checkpoint", "metadata") VALUES ('conv_1', '', '1f179486-0938-6c20-8002-2453a3c2d279', '1f179485-fd23-6eb2-8001-3e8ffd5c8ce4', NULL, '{"v": 4, "id": "1f179486-0938-6c20-8002-2453a3c2d279", "ts": "2026-07-06T14:38:39.008420+00:00", "versions_seen": {"executor": {"branch:to:executor": "00000000000000000000000000000003.0.7140894666036767"}, "__input__": {}, "__start__": {"__start__": "00000000000000000000000000000001.0.17317361918105634"}, "classifier": {"branch:to:classifier": "00000000000000000000000000000002.0.27291788420695784"}}, "channel_values": {"error": null, "query": "你好", "kb_ids": null, "file_ids": null, "token_expired": null, "final_response": null, "memory_summary": "", "plan_confirmed": false, "conversation_id": 1, "task_complexity": "simple", "knowledge_context": null, "branch:to:aggregator": null, "requires_confirmation": false}, "channel_versions": {"error": "00000000000000000000000000000002.0.27291788420695784", "query": "00000000000000000000000000000002.0.27291788420695784", "kb_ids": "00000000000000000000000000000002.0.27291788420695784", "file_ids": "00000000000000000000000000000002.0.27291788420695784", "messages": "00000000000000000000000000000002.0.27291788420695784", "__start__": "00000000000000000000000000000002.0.27291788420695784", "plan_steps": "00000000000000000000000000000002.0.27291788420695784", "references": "00000000000000000000000000000004.0.9640618856581671", "token_usage": "00000000000000000000000000000002.0.27291788420695784", "tool_results": "00000000000000000000000000000004.0.9640618856581671", "user_context": "00000000000000000000000000000002.0.27291788420695784", "token_expired": "00000000000000000000000000000002.0.27291788420695784", "final_response": "00000000000000000000000000000002.0.27291788420695784", "memory_summary": "00000000000000000000000000000002.0.27291788420695784", "plan_confirmed": "00000000000000000000000000000002.0.27291788420695784", "conversation_id": "00000000000000000000000000000002.0.27291788420695784", "task_complexity": "00000000000000000000000000000003.0.7140894666036767", "knowledge_context": "00000000000000000000000000000004.0.9640618856581671", "branch:to:executor": "00000000000000000000000000000004.0.9640618856581671", "tool_calls_pending": "00000000000000000000000000000004.0.9640618856581671", "branch:to:aggregator": "00000000000000000000000000000004.0.9640618856581671", "branch:to:classifier": "00000000000000000000000000000003.0.7140894666036767", "conversation_history": "00000000000000000000000000000002.0.27291788420695784", "requires_confirmation": "00000000000000000000000000000003.0.7140894666036767"}, "updated_channels": ["branch:to:aggregator", "knowledge_context", "references", "tool_calls_pending", "tool_results"]}', '{"step": 2, "source": "loop", "parents": {}}');
INSERT INTO "public"."checkpoints" ("thread_id", "checkpoint_ns", "checkpoint_id", "parent_checkpoint_id", "type", "checkpoint", "metadata") VALUES ('conv_1', '', '1f179486-1b80-6018-8003-5dad80da98d9', '1f179486-0938-6c20-8002-2453a3c2d279', NULL, '{"v": 4, "id": "1f179486-1b80-6018-8003-5dad80da98d9", "ts": "2026-07-06T14:38:40.925038+00:00", "versions_seen": {"executor": {"branch:to:executor": "00000000000000000000000000000003.0.7140894666036767"}, "__input__": {}, "__start__": {"__start__": "00000000000000000000000000000001.0.17317361918105634"}, "aggregator": {"branch:to:aggregator": "00000000000000000000000000000004.0.9640618856581671"}, "classifier": {"branch:to:classifier": "00000000000000000000000000000002.0.27291788420695784"}}, "channel_values": {"error": null, "query": "你好", "kb_ids": null, "file_ids": null, "token_expired": null, "final_response": "你好！我是智镀云AI，电镀行业ERP系统的智能助理。很高兴为您服务～\n\n我可以帮您解答电镀工艺问题、查询分析业务数据、生成工作报告，或者指导您使用系统功能。请问有什么可以帮您的？", "memory_summary": "", "plan_confirmed": false, "conversation_id": 1, "task_complexity": "simple", "knowledge_context": null, "requires_confirmation": false}, "channel_versions": {"error": "00000000000000000000000000000002.0.27291788420695784", "query": "00000000000000000000000000000002.0.27291788420695784", "kb_ids": "00000000000000000000000000000002.0.27291788420695784", "file_ids": "00000000000000000000000000000002.0.27291788420695784", "messages": "00000000000000000000000000000002.0.27291788420695784", "__start__": "00000000000000000000000000000002.0.27291788420695784", "plan_steps": "00000000000000000000000000000002.0.27291788420695784", "references": "00000000000000000000000000000005.0.13691035902030346", "token_usage": "00000000000000000000000000000005.0.13691035902030346", "tool_results": "00000000000000000000000000000004.0.9640618856581671", "user_context": "00000000000000000000000000000002.0.27291788420695784", "token_expired": "00000000000000000000000000000002.0.27291788420695784", "final_response": "00000000000000000000000000000005.0.13691035902030346", "memory_summary": "00000000000000000000000000000002.0.27291788420695784", "plan_confirmed": "00000000000000000000000000000002.0.27291788420695784", "conversation_id": "00000000000000000000000000000002.0.27291788420695784", "task_complexity": "00000000000000000000000000000003.0.7140894666036767", "knowledge_context": "00000000000000000000000000000004.0.9640618856581671", "branch:to:executor": "00000000000000000000000000000004.0.9640618856581671", "tool_calls_pending": "00000000000000000000000000000004.0.9640618856581671", "branch:to:aggregator": "00000000000000000000000000000005.0.13691035902030346", "branch:to:classifier": "00000000000000000000000000000003.0.7140894666036767", "conversation_history": "00000000000000000000000000000002.0.27291788420695784", "requires_confirmation": "00000000000000000000000000000003.0.7140894666036767"}, "updated_channels": ["final_response", "references", "token_usage"]}', '{"step": 3, "source": "loop", "parents": {}}');
COMMIT;

-- ----------------------------
-- Table structure for conversation
-- ----------------------------
DROP TABLE IF EXISTS "public"."conversation";
CREATE TABLE "public"."conversation" (
  "id" int8 NOT NULL DEFAULT nextval('conversation_id_seq'::regclass),
  "tenant_id" int8 NOT NULL,
  "user_id" int8 NOT NULL,
  "title" varchar(200) COLLATE "pg_catalog"."default",
  "session_type" varchar(20) COLLATE "pg_catalog"."default" DEFAULT 'chat'::character varying,
  "message_count" int4 DEFAULT 0,
  "total_tokens" int4 DEFAULT 0,
  "last_message_at" timestamp(6),
  "is_pinned" bool DEFAULT false,
  "is_archived" bool DEFAULT false,
  "is_deleted" bool DEFAULT false,
  "created_by" int8,
  "updated_by" int8,
  "created_at" timestamp(6) DEFAULT now(),
  "updated_at" timestamp(6) DEFAULT now()
)
;
ALTER TABLE "public"."conversation" OWNER TO "postgres";
COMMENT ON COLUMN "public"."conversation"."tenant_id" IS '租户ID';
COMMENT ON COLUMN "public"."conversation"."user_id" IS '用户ID';
COMMENT ON COLUMN "public"."conversation"."is_deleted" IS '逻辑删除标记';
COMMENT ON COLUMN "public"."conversation"."created_by" IS '创建人用户ID';
COMMENT ON COLUMN "public"."conversation"."updated_by" IS '最后修改人用户ID';
COMMENT ON TABLE "public"."conversation" IS 'AI对话会话表';

-- ----------------------------
-- Records of conversation
-- ----------------------------
BEGIN;
INSERT INTO "public"."conversation" ("id", "tenant_id", "user_id", "title", "session_type", "message_count", "total_tokens", "last_message_at", "is_pinned", "is_archived", "is_deleted", "created_by", "updated_by", "created_at", "updated_at") VALUES (1, 1, 1, '你好', 'chat', 2, 385, '2026-07-06 22:38:41.13587', 'f', 'f', 'f', 1, 1, '2026-07-06 22:38:36.317253', '2026-07-06 22:38:42.123517');
COMMIT;

-- ----------------------------
-- Table structure for conversation_message
-- ----------------------------
DROP TABLE IF EXISTS "public"."conversation_message";
CREATE TABLE "public"."conversation_message" (
  "id" int8 NOT NULL DEFAULT nextval('conversation_message_id_seq'::regclass),
  "conversation_id" int8 NOT NULL,
  "tenant_id" int8 NOT NULL,
  "role" varchar(20) COLLATE "pg_catalog"."default" NOT NULL,
  "content" text COLLATE "pg_catalog"."default",
  "model_name" varchar(50) COLLATE "pg_catalog"."default",
  "tool_calls" jsonb,
  "tool_call_id" varchar(100) COLLATE "pg_catalog"."default",
  "tool_result" text COLLATE "pg_catalog"."default",
  "token_count" int4,
  "token_usage" jsonb,
  "file_ids" jsonb DEFAULT '[]'::jsonb,
  "references" jsonb DEFAULT '[]'::jsonb,
  "thinking_steps" jsonb DEFAULT '[]'::jsonb,
  "duration_sec" float8,
  "is_streaming" bool DEFAULT false,
  "is_deleted" bool DEFAULT false,
  "created_by" int8,
  "updated_by" int8,
  "created_at" timestamp(6) DEFAULT now(),
  "updated_at" timestamp(6) DEFAULT now()
)
;
ALTER TABLE "public"."conversation_message" OWNER TO "postgres";
COMMENT ON COLUMN "public"."conversation_message"."model_name" IS '生成该消息的模型标识，如deepseek-chat/qwen-plus';
COMMENT ON COLUMN "public"."conversation_message"."token_usage" IS 'Token消耗明细JSON，如{"input":500,"output":300,"total":800}';
COMMENT ON COLUMN "public"."conversation_message"."file_ids" IS '关联的临时文件ID列表JSON数组，如["uuid1","uuid2"]';
COMMENT ON COLUMN "public"."conversation_message"."references" IS '引用来源JSON数组，支持knowledge/database/upload三种类型';
COMMENT ON COLUMN "public"."conversation_message"."thinking_steps" IS 'AI思考步骤JSON数组，包含thinking/tool_start/tool_end类型，示例如 [{"type":"thinking","content":"分析中","timestamp":0.0}]';
COMMENT ON COLUMN "public"."conversation_message"."duration_sec" IS 'AI回复耗时（秒），仅role=assistant时有值';
COMMENT ON COLUMN "public"."conversation_message"."is_deleted" IS '逻辑删除标记';
COMMENT ON COLUMN "public"."conversation_message"."created_by" IS '创建人用户ID（发送者）';
COMMENT ON COLUMN "public"."conversation_message"."updated_by" IS '最后修改人用户ID';
COMMENT ON TABLE "public"."conversation_message" IS 'AI对话消息表';

-- ----------------------------
-- Records of conversation_message
-- ----------------------------
BEGIN;
INSERT INTO "public"."conversation_message" ("id", "conversation_id", "tenant_id", "role", "content", "model_name", "tool_calls", "tool_call_id", "tool_result", "token_count", "token_usage", "file_ids", "references", "thinking_steps", "duration_sec", "is_streaming", "is_deleted", "created_by", "updated_by", "created_at", "updated_at") VALUES (1, 1, 1, 'user', '你好', NULL, NULL, NULL, NULL, 1, NULL, '[]', '[]', '[]', NULL, 'f', 'f', 1, NULL, '2026-07-06 22:38:41.009232', '2026-07-06 22:38:41.009232');
INSERT INTO "public"."conversation_message" ("id", "conversation_id", "tenant_id", "role", "content", "model_name", "tool_calls", "tool_call_id", "tool_result", "token_count", "token_usage", "file_ids", "references", "thinking_steps", "duration_sec", "is_streaming", "is_deleted", "created_by", "updated_by", "created_at", "updated_at") VALUES (2, 1, 1, 'assistant', '你好！我是智镀云AI，电镀行业ERP系统的智能助理。很高兴为您服务～

我可以帮您解答电镀工艺问题、查询分析业务数据、生成工作报告，或者指导您使用系统功能。请问有什么可以帮您的？', 'deepseek-v4-flash', NULL, NULL, NULL, NULL, '{"input": 311, "output": 74}', '[]', '[]', '[{"type": "thinking", "content": "收到您的问题，正在分析...", "timestamp": 0.0}, {"type": "thinking", "content": "我们被要求以智镀云AI的身份回复。用户说“你好”，所以简单问候并介绍自己。", "timestamp": 3.1}]', 4.84, 'f', 'f', 1, NULL, '2026-07-06 22:38:41.072904', '2026-07-06 22:38:41.072904');
COMMIT;

-- ----------------------------
-- Table structure for goods_image_feature
-- ----------------------------
DROP TABLE IF EXISTS "public"."goods_image_feature";
CREATE TABLE "public"."goods_image_feature" (
  "id" int8 NOT NULL,
  "tenant_id" int8 NOT NULL,
  "order_id" int8,
  "item_id" int8,
  "node_id" int8,
  "record_id" int8,
  "image_type" varchar(20) COLLATE "pg_catalog"."default" NOT NULL,
  "embedding" vector(512),
  "oss_path" varchar(512) COLLATE "pg_catalog"."default" NOT NULL,
  "image_url" varchar(512) COLLATE "pg_catalog"."default",
  "thumbnail_url" varchar(512) COLLATE "pg_catalog"."default" DEFAULT ''::character varying,
  "file_size" int8 DEFAULT 0,
  "is_deleted" bool DEFAULT false,
  "created_by" int8,
  "updated_by" int8,
  "created_at" timestamptz(6) DEFAULT now(),
  "updated_at" timestamptz(6) DEFAULT now()
)
;
ALTER TABLE "public"."goods_image_feature" OWNER TO "postgres";

-- ----------------------------
-- Records of goods_image_feature
-- ----------------------------
BEGIN;
COMMIT;

-- ----------------------------
-- Table structure for knowledge_base
-- ----------------------------
DROP TABLE IF EXISTS "public"."knowledge_base";
CREATE TABLE "public"."knowledge_base" (
  "id" int8 NOT NULL DEFAULT nextval('knowledge_base_id_seq'::regclass),
  "tenant_id" int8,
  "scope_type" varchar(20) COLLATE "pg_catalog"."default" NOT NULL DEFAULT 'tenant'::character varying,
  "name" varchar(100) COLLATE "pg_catalog"."default" NOT NULL,
  "description" text COLLATE "pg_catalog"."default",
  "embedding_model" varchar(50) COLLATE "pg_catalog"."default" DEFAULT 'bge-large-zh-v1.5'::character varying,
  "chunk_size" int4 DEFAULT 500,
  "chunk_overlap" int4 DEFAULT 100,
  "status" varchar(20) COLLATE "pg_catalog"."default" DEFAULT 'active'::character varying,
  "doc_count" int4 DEFAULT 0,
  "chunk_count" int4 DEFAULT 0,
  "is_deleted" bool DEFAULT false,
  "created_by" int8,
  "updated_by" int8,
  "created_at" timestamp(6) DEFAULT now(),
  "updated_at" timestamp(6) DEFAULT now()
)
;
ALTER TABLE "public"."knowledge_base" OWNER TO "postgres";
COMMENT ON COLUMN "public"."knowledge_base"."tenant_id" IS '租户ID，公共库为NULL';
COMMENT ON COLUMN "public"."knowledge_base"."scope_type" IS '可见范围：global全租户/tenant当前公司/personal个人';
COMMENT ON COLUMN "public"."knowledge_base"."created_by" IS '创建人用户ID';
COMMENT ON COLUMN "public"."knowledge_base"."updated_by" IS '最后修改人用户ID';
COMMENT ON TABLE "public"."knowledge_base" IS 'AI知识库表';

-- ----------------------------
-- Records of knowledge_base
-- ----------------------------
BEGIN;
INSERT INTO "public"."knowledge_base" ("id", "tenant_id", "scope_type", "name", "description", "embedding_model", "chunk_size", "chunk_overlap", "status", "doc_count", "chunk_count", "is_deleted", "created_by", "updated_by", "created_at", "updated_at") VALUES (1, NULL, 'global', '电镀行业通用知识库', '电镀行业通用标准、工艺知识、环保法规等', 'bge-large-zh-v1.5', 500, 100, 'active', 0, 0, 'f', 1, 1, '2026-07-06 21:28:51.220476', '2026-07-06 21:28:51.220476');
COMMIT;

-- ----------------------------
-- Table structure for knowledge_base_tag
-- ----------------------------
DROP TABLE IF EXISTS "public"."knowledge_base_tag";
CREATE TABLE "public"."knowledge_base_tag" (
  "id" int8 NOT NULL DEFAULT nextval('knowledge_base_tag_id_seq'::regclass),
  "kb_id" int8 NOT NULL,
  "tenant_id" int8,
  "tag_name" varchar(50) COLLATE "pg_catalog"."default" NOT NULL,
  "source" varchar(20) COLLATE "pg_catalog"."default" DEFAULT 'manual'::character varying,
  "is_deleted" bool DEFAULT false,
  "created_by" int8,
  "updated_by" int8,
  "created_at" timestamp(6) DEFAULT now(),
  "updated_at" timestamp(6) DEFAULT now()
)
;
ALTER TABLE "public"."knowledge_base_tag" OWNER TO "postgres";
COMMENT ON COLUMN "public"."knowledge_base_tag"."tag_name" IS '标签名，如"电镀工艺""镀镍""SOP"';
COMMENT ON COLUMN "public"."knowledge_base_tag"."created_by" IS '创建人用户ID';
COMMENT ON COLUMN "public"."knowledge_base_tag"."updated_by" IS '最后修改人用户ID';
COMMENT ON TABLE "public"."knowledge_base_tag" IS '知识库标签表，用于多知识库路由';

-- ----------------------------
-- Records of knowledge_base_tag
-- ----------------------------
BEGIN;
COMMIT;

-- ----------------------------
-- Table structure for knowledge_chunk
-- ----------------------------
DROP TABLE IF EXISTS "public"."knowledge_chunk";
CREATE TABLE "public"."knowledge_chunk" (
  "id" int8 NOT NULL DEFAULT nextval('knowledge_chunk_id_seq'::regclass),
  "doc_id" int8 NOT NULL,
  "kb_id" int8 NOT NULL,
  "tenant_id" int8 NOT NULL,
  "chunk_index" int4 NOT NULL,
  "content" text COLLATE "pg_catalog"."default" NOT NULL,
  "token_count" int4,
  "embedding" vector(1024),
  "metadata" jsonb DEFAULT '{}'::jsonb,
  "is_deleted" bool DEFAULT false,
  "created_by" int8,
  "updated_by" int8,
  "created_at" timestamp(6) DEFAULT now(),
  "updated_at" timestamp(6) DEFAULT now()
)
;
ALTER TABLE "public"."knowledge_chunk" OWNER TO "postgres";
COMMENT ON COLUMN "public"."knowledge_chunk"."embedding" IS 'BAAI/bge-large-zh-v1.5 生成的1024维向量';
COMMENT ON COLUMN "public"."knowledge_chunk"."metadata" IS 'JSON元数据，如{"page_number":3,"section_title":"镀液参数控制"}';
COMMENT ON COLUMN "public"."knowledge_chunk"."created_by" IS '创建人用户ID';
COMMENT ON COLUMN "public"."knowledge_chunk"."updated_by" IS '最后修改人用户ID';
COMMENT ON TABLE "public"."knowledge_chunk" IS '知识库文档片段表（含向量）';

-- ----------------------------
-- Records of knowledge_chunk
-- ----------------------------
BEGIN;
COMMIT;

-- ----------------------------
-- Table structure for knowledge_document
-- ----------------------------
DROP TABLE IF EXISTS "public"."knowledge_document";
CREATE TABLE "public"."knowledge_document" (
  "id" int8 NOT NULL DEFAULT nextval('knowledge_document_id_seq'::regclass),
  "kb_id" int8 NOT NULL,
  "tenant_id" int8,
  "title" varchar(255) COLLATE "pg_catalog"."default" NOT NULL,
  "file_name" varchar(255) COLLATE "pg_catalog"."default",
  "file_type" varchar(20) COLLATE "pg_catalog"."default",
  "file_size" int8,
  "file_path" varchar(500) COLLATE "pg_catalog"."default",
  "oss_path" varchar(500) COLLATE "pg_catalog"."default",
  "content_type" varchar(100) COLLATE "pg_catalog"."default",
  "file_hash" varchar(64) COLLATE "pg_catalog"."default",
  "chunk_count" int4 DEFAULT 0,
  "parse_status" varchar(20) COLLATE "pg_catalog"."default" DEFAULT 'pending'::character varying,
  "parse_error" text COLLATE "pg_catalog"."default",
  "is_deleted" bool DEFAULT false,
  "created_by" int8,
  "updated_by" int8,
  "created_at" timestamp(6) DEFAULT now(),
  "updated_at" timestamp(6) DEFAULT now()
)
;
ALTER TABLE "public"."knowledge_document" OWNER TO "postgres";
COMMENT ON COLUMN "public"."knowledge_document"."oss_path" IS 'OSS对象存储路径（持久备份）';
COMMENT ON COLUMN "public"."knowledge_document"."content_type" IS 'MIME类型';
COMMENT ON COLUMN "public"."knowledge_document"."file_hash" IS '文件SHA256哈希（去重/完整性校验）';
COMMENT ON COLUMN "public"."knowledge_document"."created_by" IS '上传人用户ID';
COMMENT ON COLUMN "public"."knowledge_document"."updated_by" IS '最后修改人用户ID';
COMMENT ON TABLE "public"."knowledge_document" IS '知识库文档表';

-- ----------------------------
-- Records of knowledge_document
-- ----------------------------
BEGIN;
COMMIT;

-- ----------------------------
-- Table structure for temp_document
-- ----------------------------
DROP TABLE IF EXISTS "public"."temp_document";
CREATE TABLE "public"."temp_document" (
  "id" int8 NOT NULL DEFAULT nextval('temp_document_id_seq'::regclass),
  "file_id" varchar(100) COLLATE "pg_catalog"."default" NOT NULL,
  "tenant_id" int8 NOT NULL,
  "user_id" int8 NOT NULL,
  "conversation_id" int8,
  "file_name" varchar(255) COLLATE "pg_catalog"."default" NOT NULL,
  "file_type" varchar(20) COLLATE "pg_catalog"."default" NOT NULL,
  "file_size" int8 DEFAULT 0,
  "file_path" varchar(500) COLLATE "pg_catalog"."default" NOT NULL,
  "oss_path" varchar(500) COLLATE "pg_catalog"."default",
  "content_type" varchar(100) COLLATE "pg_catalog"."default",
  "parsed_text" text COLLATE "pg_catalog"."default",
  "parse_status" varchar(20) COLLATE "pg_catalog"."default" DEFAULT 'pending'::character varying,
  "is_deleted" bool DEFAULT false,
  "expires_at" timestamp(6) NOT NULL,
  "created_by" int8,
  "updated_by" int8,
  "created_at" timestamp(6) DEFAULT now(),
  "updated_at" timestamp(6) DEFAULT now()
)
;
ALTER TABLE "public"."temp_document" OWNER TO "postgres";
COMMENT ON COLUMN "public"."temp_document"."file_id" IS '文件唯一标识UUID';
COMMENT ON COLUMN "public"."temp_document"."conversation_id" IS '所属会话ID，用于按会话管理临时文件';
COMMENT ON COLUMN "public"."temp_document"."oss_path" IS 'OSS临时存储路径（对话文档备份）';
COMMENT ON COLUMN "public"."temp_document"."content_type" IS 'MIME类型';
COMMENT ON COLUMN "public"."temp_document"."expires_at" IS '过期时间，创建后24小时';
COMMENT ON COLUMN "public"."temp_document"."created_by" IS '创建人用户ID';
COMMENT ON COLUMN "public"."temp_document"."updated_by" IS '最后修改人用户ID';
COMMENT ON TABLE "public"."temp_document" IS '对话框中临时上传的文档，24小时后自动清理';

-- ----------------------------
-- Records of temp_document
-- ----------------------------
BEGIN;
COMMIT;

-- ----------------------------
-- Table structure for user_long_term_memory
-- ----------------------------
DROP TABLE IF EXISTS "public"."user_long_term_memory";
CREATE TABLE "public"."user_long_term_memory" (
  "id" int8 NOT NULL DEFAULT nextval('user_long_term_memory_id_seq'::regclass),
  "tenant_id" int8 NOT NULL,
  "user_id" int8 NOT NULL,
  "memory_type" varchar(50) COLLATE "pg_catalog"."default" DEFAULT 'fact'::character varying,
  "content" text COLLATE "pg_catalog"."default" NOT NULL,
  "embedding" vector(1024),
  "importance" float8 DEFAULT 0.5,
  "access_count" int4 DEFAULT 0,
  "last_accessed_at" timestamp(6),
  "is_deleted" bool DEFAULT false,
  "created_by" int8,
  "updated_by" int8,
  "created_at" timestamp(6) DEFAULT now(),
  "updated_at" timestamp(6) DEFAULT now()
)
;
ALTER TABLE "public"."user_long_term_memory" OWNER TO "postgres";
COMMENT ON COLUMN "public"."user_long_term_memory"."memory_type" IS 'fact事实/preference偏好/pattern模式';
COMMENT ON COLUMN "public"."user_long_term_memory"."importance" IS '重要性权重0-1';
COMMENT ON COLUMN "public"."user_long_term_memory"."created_by" IS '创建人用户ID';
COMMENT ON COLUMN "public"."user_long_term_memory"."updated_by" IS '最后修改人用户ID';
COMMENT ON TABLE "public"."user_long_term_memory" IS '用户长期记忆表（Mem0管理）';

-- ----------------------------
-- Records of user_long_term_memory
-- ----------------------------
BEGIN;
INSERT INTO "public"."user_long_term_memory" ("id", "tenant_id", "user_id", "memory_type", "content", "embedding", "importance", "access_count", "last_accessed_at", "is_deleted", "created_by", "updated_by", "created_at", "updated_at") VALUES (1, 1, 1, 'fact', '用户提问: 你好
AI回答摘要: 你好！我是智镀云AI，电镀行业ERP系统的智能助理。很高兴为您服务～

我可以帮您解答电镀工艺问题、查询分析业务数据、生成工作报告，或者指导您使用系统功能。请问有什么可以帮您的？', NULL, 0.3, 0, NULL, 'f', 1, NULL, '2026-07-06 22:38:41.281385', '2026-07-06 22:38:41.281385');
COMMIT;

-- ----------------------------
-- Function structure for array_to_halfvec
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."array_to_halfvec"(_numeric, int4, bool);
CREATE FUNCTION "public"."array_to_halfvec"(_numeric, int4, bool)
  RETURNS "public"."halfvec" AS '$libdir/vector', 'array_to_halfvec'
  LANGUAGE c IMMUTABLE STRICT
  COST 1;
ALTER FUNCTION "public"."array_to_halfvec"(_numeric, int4, bool) OWNER TO "postgres";

-- ----------------------------
-- Function structure for array_to_halfvec
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."array_to_halfvec"(_int4, int4, bool);
CREATE FUNCTION "public"."array_to_halfvec"(_int4, int4, bool)
  RETURNS "public"."halfvec" AS '$libdir/vector', 'array_to_halfvec'
  LANGUAGE c IMMUTABLE STRICT
  COST 1;
ALTER FUNCTION "public"."array_to_halfvec"(_int4, int4, bool) OWNER TO "postgres";

-- ----------------------------
-- Function structure for array_to_halfvec
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."array_to_halfvec"(_float4, int4, bool);
CREATE FUNCTION "public"."array_to_halfvec"(_float4, int4, bool)
  RETURNS "public"."halfvec" AS '$libdir/vector', 'array_to_halfvec'
  LANGUAGE c IMMUTABLE STRICT
  COST 1;
ALTER FUNCTION "public"."array_to_halfvec"(_float4, int4, bool) OWNER TO "postgres";

-- ----------------------------
-- Function structure for array_to_halfvec
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."array_to_halfvec"(_float8, int4, bool);
CREATE FUNCTION "public"."array_to_halfvec"(_float8, int4, bool)
  RETURNS "public"."halfvec" AS '$libdir/vector', 'array_to_halfvec'
  LANGUAGE c IMMUTABLE STRICT
  COST 1;
ALTER FUNCTION "public"."array_to_halfvec"(_float8, int4, bool) OWNER TO "postgres";

-- ----------------------------
-- Function structure for array_to_sparsevec
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."array_to_sparsevec"(_float8, int4, bool);
CREATE FUNCTION "public"."array_to_sparsevec"(_float8, int4, bool)
  RETURNS "public"."sparsevec" AS '$libdir/vector', 'array_to_sparsevec'
  LANGUAGE c IMMUTABLE STRICT
  COST 1;
ALTER FUNCTION "public"."array_to_sparsevec"(_float8, int4, bool) OWNER TO "postgres";

-- ----------------------------
-- Function structure for array_to_sparsevec
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."array_to_sparsevec"(_int4, int4, bool);
CREATE FUNCTION "public"."array_to_sparsevec"(_int4, int4, bool)
  RETURNS "public"."sparsevec" AS '$libdir/vector', 'array_to_sparsevec'
  LANGUAGE c IMMUTABLE STRICT
  COST 1;
ALTER FUNCTION "public"."array_to_sparsevec"(_int4, int4, bool) OWNER TO "postgres";

-- ----------------------------
-- Function structure for array_to_sparsevec
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."array_to_sparsevec"(_float4, int4, bool);
CREATE FUNCTION "public"."array_to_sparsevec"(_float4, int4, bool)
  RETURNS "public"."sparsevec" AS '$libdir/vector', 'array_to_sparsevec'
  LANGUAGE c IMMUTABLE STRICT
  COST 1;
ALTER FUNCTION "public"."array_to_sparsevec"(_float4, int4, bool) OWNER TO "postgres";

-- ----------------------------
-- Function structure for array_to_sparsevec
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."array_to_sparsevec"(_numeric, int4, bool);
CREATE FUNCTION "public"."array_to_sparsevec"(_numeric, int4, bool)
  RETURNS "public"."sparsevec" AS '$libdir/vector', 'array_to_sparsevec'
  LANGUAGE c IMMUTABLE STRICT
  COST 1;
ALTER FUNCTION "public"."array_to_sparsevec"(_numeric, int4, bool) OWNER TO "postgres";

-- ----------------------------
-- Function structure for array_to_vector
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."array_to_vector"(_int4, int4, bool);
CREATE FUNCTION "public"."array_to_vector"(_int4, int4, bool)
  RETURNS "public"."vector" AS '$libdir/vector', 'array_to_vector'
  LANGUAGE c IMMUTABLE STRICT
  COST 1;
ALTER FUNCTION "public"."array_to_vector"(_int4, int4, bool) OWNER TO "postgres";

-- ----------------------------
-- Function structure for array_to_vector
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."array_to_vector"(_numeric, int4, bool);
CREATE FUNCTION "public"."array_to_vector"(_numeric, int4, bool)
  RETURNS "public"."vector" AS '$libdir/vector', 'array_to_vector'
  LANGUAGE c IMMUTABLE STRICT
  COST 1;
ALTER FUNCTION "public"."array_to_vector"(_numeric, int4, bool) OWNER TO "postgres";

-- ----------------------------
-- Function structure for array_to_vector
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."array_to_vector"(_float4, int4, bool);
CREATE FUNCTION "public"."array_to_vector"(_float4, int4, bool)
  RETURNS "public"."vector" AS '$libdir/vector', 'array_to_vector'
  LANGUAGE c IMMUTABLE STRICT
  COST 1;
ALTER FUNCTION "public"."array_to_vector"(_float4, int4, bool) OWNER TO "postgres";

-- ----------------------------
-- Function structure for array_to_vector
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."array_to_vector"(_float8, int4, bool);
CREATE FUNCTION "public"."array_to_vector"(_float8, int4, bool)
  RETURNS "public"."vector" AS '$libdir/vector', 'array_to_vector'
  LANGUAGE c IMMUTABLE STRICT
  COST 1;
ALTER FUNCTION "public"."array_to_vector"(_float8, int4, bool) OWNER TO "postgres";

-- ----------------------------
-- Function structure for binary_quantize
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."binary_quantize"("public"."vector");
CREATE FUNCTION "public"."binary_quantize"("public"."vector")
  RETURNS "pg_catalog"."bit" AS '$libdir/vector', 'binary_quantize'
  LANGUAGE c IMMUTABLE STRICT
  COST 1;
ALTER FUNCTION "public"."binary_quantize"("public"."vector") OWNER TO "postgres";

-- ----------------------------
-- Function structure for binary_quantize
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."binary_quantize"("public"."halfvec");
CREATE FUNCTION "public"."binary_quantize"("public"."halfvec")
  RETURNS "pg_catalog"."bit" AS '$libdir/vector', 'halfvec_binary_quantize'
  LANGUAGE c IMMUTABLE STRICT
  COST 1;
ALTER FUNCTION "public"."binary_quantize"("public"."halfvec") OWNER TO "postgres";

-- ----------------------------
-- Function structure for cleanup_expired_temp_documents
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."cleanup_expired_temp_documents"();
CREATE FUNCTION "public"."cleanup_expired_temp_documents"()
  RETURNS "pg_catalog"."int4" AS $BODY$
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
$BODY$
  LANGUAGE plpgsql VOLATILE
  COST 100;
ALTER FUNCTION "public"."cleanup_expired_temp_documents"() OWNER TO "postgres";
COMMENT ON FUNCTION "public"."cleanup_expired_temp_documents"() IS '标记已过期的临时文档为逻辑删除，可通过pg_cron定期执行: SELECT cleanup_expired_temp_documents()';

-- ----------------------------
-- Function structure for cosine_distance
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."cosine_distance"("public"."sparsevec", "public"."sparsevec");
CREATE FUNCTION "public"."cosine_distance"("public"."sparsevec", "public"."sparsevec")
  RETURNS "pg_catalog"."float8" AS '$libdir/vector', 'sparsevec_cosine_distance'
  LANGUAGE c IMMUTABLE STRICT
  COST 1;
ALTER FUNCTION "public"."cosine_distance"("public"."sparsevec", "public"."sparsevec") OWNER TO "postgres";

-- ----------------------------
-- Function structure for cosine_distance
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."cosine_distance"("public"."vector", "public"."vector");
CREATE FUNCTION "public"."cosine_distance"("public"."vector", "public"."vector")
  RETURNS "pg_catalog"."float8" AS '$libdir/vector', 'cosine_distance'
  LANGUAGE c IMMUTABLE STRICT
  COST 1;
ALTER FUNCTION "public"."cosine_distance"("public"."vector", "public"."vector") OWNER TO "postgres";

-- ----------------------------
-- Function structure for cosine_distance
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."cosine_distance"("public"."halfvec", "public"."halfvec");
CREATE FUNCTION "public"."cosine_distance"("public"."halfvec", "public"."halfvec")
  RETURNS "pg_catalog"."float8" AS '$libdir/vector', 'halfvec_cosine_distance'
  LANGUAGE c IMMUTABLE STRICT
  COST 1;
ALTER FUNCTION "public"."cosine_distance"("public"."halfvec", "public"."halfvec") OWNER TO "postgres";

-- ----------------------------
-- Function structure for gin_extract_query_trgm
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."gin_extract_query_trgm"(text, internal, int2, internal, internal, internal, internal);
CREATE FUNCTION "public"."gin_extract_query_trgm"(text, internal, int2, internal, internal, internal, internal)
  RETURNS "pg_catalog"."internal" AS '$libdir/pg_trgm', 'gin_extract_query_trgm'
  LANGUAGE c IMMUTABLE STRICT
  COST 1;
ALTER FUNCTION "public"."gin_extract_query_trgm"(text, internal, int2, internal, internal, internal, internal) OWNER TO "postgres";

-- ----------------------------
-- Function structure for gin_extract_value_trgm
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."gin_extract_value_trgm"(text, internal);
CREATE FUNCTION "public"."gin_extract_value_trgm"(text, internal)
  RETURNS "pg_catalog"."internal" AS '$libdir/pg_trgm', 'gin_extract_value_trgm'
  LANGUAGE c IMMUTABLE STRICT
  COST 1;
ALTER FUNCTION "public"."gin_extract_value_trgm"(text, internal) OWNER TO "postgres";

-- ----------------------------
-- Function structure for gin_trgm_consistent
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."gin_trgm_consistent"(internal, int2, text, int4, internal, internal, internal, internal);
CREATE FUNCTION "public"."gin_trgm_consistent"(internal, int2, text, int4, internal, internal, internal, internal)
  RETURNS "pg_catalog"."bool" AS '$libdir/pg_trgm', 'gin_trgm_consistent'
  LANGUAGE c IMMUTABLE STRICT
  COST 1;
ALTER FUNCTION "public"."gin_trgm_consistent"(internal, int2, text, int4, internal, internal, internal, internal) OWNER TO "postgres";

-- ----------------------------
-- Function structure for gin_trgm_triconsistent
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."gin_trgm_triconsistent"(internal, int2, text, int4, internal, internal, internal);
CREATE FUNCTION "public"."gin_trgm_triconsistent"(internal, int2, text, int4, internal, internal, internal)
  RETURNS "pg_catalog"."char" AS '$libdir/pg_trgm', 'gin_trgm_triconsistent'
  LANGUAGE c IMMUTABLE STRICT
  COST 1;
ALTER FUNCTION "public"."gin_trgm_triconsistent"(internal, int2, text, int4, internal, internal, internal) OWNER TO "postgres";

-- ----------------------------
-- Function structure for gtrgm_compress
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."gtrgm_compress"(internal);
CREATE FUNCTION "public"."gtrgm_compress"(internal)
  RETURNS "pg_catalog"."internal" AS '$libdir/pg_trgm', 'gtrgm_compress'
  LANGUAGE c IMMUTABLE STRICT
  COST 1;
ALTER FUNCTION "public"."gtrgm_compress"(internal) OWNER TO "postgres";

-- ----------------------------
-- Function structure for gtrgm_consistent
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."gtrgm_consistent"(internal, text, int2, oid, internal);
CREATE FUNCTION "public"."gtrgm_consistent"(internal, text, int2, oid, internal)
  RETURNS "pg_catalog"."bool" AS '$libdir/pg_trgm', 'gtrgm_consistent'
  LANGUAGE c IMMUTABLE STRICT
  COST 1;
ALTER FUNCTION "public"."gtrgm_consistent"(internal, text, int2, oid, internal) OWNER TO "postgres";

-- ----------------------------
-- Function structure for gtrgm_decompress
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."gtrgm_decompress"(internal);
CREATE FUNCTION "public"."gtrgm_decompress"(internal)
  RETURNS "pg_catalog"."internal" AS '$libdir/pg_trgm', 'gtrgm_decompress'
  LANGUAGE c IMMUTABLE STRICT
  COST 1;
ALTER FUNCTION "public"."gtrgm_decompress"(internal) OWNER TO "postgres";

-- ----------------------------
-- Function structure for gtrgm_distance
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."gtrgm_distance"(internal, text, int2, oid, internal);
CREATE FUNCTION "public"."gtrgm_distance"(internal, text, int2, oid, internal)
  RETURNS "pg_catalog"."float8" AS '$libdir/pg_trgm', 'gtrgm_distance'
  LANGUAGE c IMMUTABLE STRICT
  COST 1;
ALTER FUNCTION "public"."gtrgm_distance"(internal, text, int2, oid, internal) OWNER TO "postgres";

-- ----------------------------
-- Function structure for gtrgm_in
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."gtrgm_in"(cstring);
CREATE FUNCTION "public"."gtrgm_in"(cstring)
  RETURNS "public"."gtrgm" AS '$libdir/pg_trgm', 'gtrgm_in'
  LANGUAGE c IMMUTABLE STRICT
  COST 1;
ALTER FUNCTION "public"."gtrgm_in"(cstring) OWNER TO "postgres";

-- ----------------------------
-- Function structure for gtrgm_options
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."gtrgm_options"(internal);
CREATE FUNCTION "public"."gtrgm_options"(internal)
  RETURNS "pg_catalog"."void" AS '$libdir/pg_trgm', 'gtrgm_options'
  LANGUAGE c IMMUTABLE
  COST 1;
ALTER FUNCTION "public"."gtrgm_options"(internal) OWNER TO "postgres";

-- ----------------------------
-- Function structure for gtrgm_out
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."gtrgm_out"("public"."gtrgm");
CREATE FUNCTION "public"."gtrgm_out"("public"."gtrgm")
  RETURNS "pg_catalog"."cstring" AS '$libdir/pg_trgm', 'gtrgm_out'
  LANGUAGE c IMMUTABLE STRICT
  COST 1;
ALTER FUNCTION "public"."gtrgm_out"("public"."gtrgm") OWNER TO "postgres";

-- ----------------------------
-- Function structure for gtrgm_penalty
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."gtrgm_penalty"(internal, internal, internal);
CREATE FUNCTION "public"."gtrgm_penalty"(internal, internal, internal)
  RETURNS "pg_catalog"."internal" AS '$libdir/pg_trgm', 'gtrgm_penalty'
  LANGUAGE c IMMUTABLE STRICT
  COST 1;
ALTER FUNCTION "public"."gtrgm_penalty"(internal, internal, internal) OWNER TO "postgres";

-- ----------------------------
-- Function structure for gtrgm_picksplit
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."gtrgm_picksplit"(internal, internal);
CREATE FUNCTION "public"."gtrgm_picksplit"(internal, internal)
  RETURNS "pg_catalog"."internal" AS '$libdir/pg_trgm', 'gtrgm_picksplit'
  LANGUAGE c IMMUTABLE STRICT
  COST 1;
ALTER FUNCTION "public"."gtrgm_picksplit"(internal, internal) OWNER TO "postgres";

-- ----------------------------
-- Function structure for gtrgm_same
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."gtrgm_same"("public"."gtrgm", "public"."gtrgm", internal);
CREATE FUNCTION "public"."gtrgm_same"("public"."gtrgm", "public"."gtrgm", internal)
  RETURNS "pg_catalog"."internal" AS '$libdir/pg_trgm', 'gtrgm_same'
  LANGUAGE c IMMUTABLE STRICT
  COST 1;
ALTER FUNCTION "public"."gtrgm_same"("public"."gtrgm", "public"."gtrgm", internal) OWNER TO "postgres";

-- ----------------------------
-- Function structure for gtrgm_union
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."gtrgm_union"(internal, internal);
CREATE FUNCTION "public"."gtrgm_union"(internal, internal)
  RETURNS "public"."gtrgm" AS '$libdir/pg_trgm', 'gtrgm_union'
  LANGUAGE c IMMUTABLE STRICT
  COST 1;
ALTER FUNCTION "public"."gtrgm_union"(internal, internal) OWNER TO "postgres";

-- ----------------------------
-- Function structure for halfvec
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."halfvec"("public"."halfvec", int4, bool);
CREATE FUNCTION "public"."halfvec"("public"."halfvec", int4, bool)
  RETURNS "public"."halfvec" AS '$libdir/vector', 'halfvec'
  LANGUAGE c IMMUTABLE STRICT
  COST 1;
ALTER FUNCTION "public"."halfvec"("public"."halfvec", int4, bool) OWNER TO "postgres";

-- ----------------------------
-- Function structure for halfvec_accum
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."halfvec_accum"(_float8, "public"."halfvec");
CREATE FUNCTION "public"."halfvec_accum"(_float8, "public"."halfvec")
  RETURNS "pg_catalog"."_float8" AS '$libdir/vector', 'halfvec_accum'
  LANGUAGE c IMMUTABLE STRICT
  COST 1;
ALTER FUNCTION "public"."halfvec_accum"(_float8, "public"."halfvec") OWNER TO "postgres";

-- ----------------------------
-- Function structure for halfvec_add
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."halfvec_add"("public"."halfvec", "public"."halfvec");
CREATE FUNCTION "public"."halfvec_add"("public"."halfvec", "public"."halfvec")
  RETURNS "public"."halfvec" AS '$libdir/vector', 'halfvec_add'
  LANGUAGE c IMMUTABLE STRICT
  COST 1;
ALTER FUNCTION "public"."halfvec_add"("public"."halfvec", "public"."halfvec") OWNER TO "postgres";

-- ----------------------------
-- Function structure for halfvec_avg
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."halfvec_avg"(_float8);
CREATE FUNCTION "public"."halfvec_avg"(_float8)
  RETURNS "public"."halfvec" AS '$libdir/vector', 'halfvec_avg'
  LANGUAGE c IMMUTABLE STRICT
  COST 1;
ALTER FUNCTION "public"."halfvec_avg"(_float8) OWNER TO "postgres";

-- ----------------------------
-- Function structure for halfvec_cmp
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."halfvec_cmp"("public"."halfvec", "public"."halfvec");
CREATE FUNCTION "public"."halfvec_cmp"("public"."halfvec", "public"."halfvec")
  RETURNS "pg_catalog"."int4" AS '$libdir/vector', 'halfvec_cmp'
  LANGUAGE c IMMUTABLE STRICT
  COST 1;
ALTER FUNCTION "public"."halfvec_cmp"("public"."halfvec", "public"."halfvec") OWNER TO "postgres";

-- ----------------------------
-- Function structure for halfvec_combine
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."halfvec_combine"(_float8, _float8);
CREATE FUNCTION "public"."halfvec_combine"(_float8, _float8)
  RETURNS "pg_catalog"."_float8" AS '$libdir/vector', 'vector_combine'
  LANGUAGE c IMMUTABLE STRICT
  COST 1;
ALTER FUNCTION "public"."halfvec_combine"(_float8, _float8) OWNER TO "postgres";

-- ----------------------------
-- Function structure for halfvec_concat
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."halfvec_concat"("public"."halfvec", "public"."halfvec");
CREATE FUNCTION "public"."halfvec_concat"("public"."halfvec", "public"."halfvec")
  RETURNS "public"."halfvec" AS '$libdir/vector', 'halfvec_concat'
  LANGUAGE c IMMUTABLE STRICT
  COST 1;
ALTER FUNCTION "public"."halfvec_concat"("public"."halfvec", "public"."halfvec") OWNER TO "postgres";

-- ----------------------------
-- Function structure for halfvec_eq
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."halfvec_eq"("public"."halfvec", "public"."halfvec");
CREATE FUNCTION "public"."halfvec_eq"("public"."halfvec", "public"."halfvec")
  RETURNS "pg_catalog"."bool" AS '$libdir/vector', 'halfvec_eq'
  LANGUAGE c IMMUTABLE STRICT
  COST 1;
ALTER FUNCTION "public"."halfvec_eq"("public"."halfvec", "public"."halfvec") OWNER TO "postgres";

-- ----------------------------
-- Function structure for halfvec_ge
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."halfvec_ge"("public"."halfvec", "public"."halfvec");
CREATE FUNCTION "public"."halfvec_ge"("public"."halfvec", "public"."halfvec")
  RETURNS "pg_catalog"."bool" AS '$libdir/vector', 'halfvec_ge'
  LANGUAGE c IMMUTABLE STRICT
  COST 1;
ALTER FUNCTION "public"."halfvec_ge"("public"."halfvec", "public"."halfvec") OWNER TO "postgres";

-- ----------------------------
-- Function structure for halfvec_gt
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."halfvec_gt"("public"."halfvec", "public"."halfvec");
CREATE FUNCTION "public"."halfvec_gt"("public"."halfvec", "public"."halfvec")
  RETURNS "pg_catalog"."bool" AS '$libdir/vector', 'halfvec_gt'
  LANGUAGE c IMMUTABLE STRICT
  COST 1;
ALTER FUNCTION "public"."halfvec_gt"("public"."halfvec", "public"."halfvec") OWNER TO "postgres";

-- ----------------------------
-- Function structure for halfvec_in
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."halfvec_in"(cstring, oid, int4);
CREATE FUNCTION "public"."halfvec_in"(cstring, oid, int4)
  RETURNS "public"."halfvec" AS '$libdir/vector', 'halfvec_in'
  LANGUAGE c IMMUTABLE STRICT
  COST 1;
ALTER FUNCTION "public"."halfvec_in"(cstring, oid, int4) OWNER TO "postgres";

-- ----------------------------
-- Function structure for halfvec_l2_squared_distance
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."halfvec_l2_squared_distance"("public"."halfvec", "public"."halfvec");
CREATE FUNCTION "public"."halfvec_l2_squared_distance"("public"."halfvec", "public"."halfvec")
  RETURNS "pg_catalog"."float8" AS '$libdir/vector', 'halfvec_l2_squared_distance'
  LANGUAGE c IMMUTABLE STRICT
  COST 1;
ALTER FUNCTION "public"."halfvec_l2_squared_distance"("public"."halfvec", "public"."halfvec") OWNER TO "postgres";

-- ----------------------------
-- Function structure for halfvec_le
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."halfvec_le"("public"."halfvec", "public"."halfvec");
CREATE FUNCTION "public"."halfvec_le"("public"."halfvec", "public"."halfvec")
  RETURNS "pg_catalog"."bool" AS '$libdir/vector', 'halfvec_le'
  LANGUAGE c IMMUTABLE STRICT
  COST 1;
ALTER FUNCTION "public"."halfvec_le"("public"."halfvec", "public"."halfvec") OWNER TO "postgres";

-- ----------------------------
-- Function structure for halfvec_lt
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."halfvec_lt"("public"."halfvec", "public"."halfvec");
CREATE FUNCTION "public"."halfvec_lt"("public"."halfvec", "public"."halfvec")
  RETURNS "pg_catalog"."bool" AS '$libdir/vector', 'halfvec_lt'
  LANGUAGE c IMMUTABLE STRICT
  COST 1;
ALTER FUNCTION "public"."halfvec_lt"("public"."halfvec", "public"."halfvec") OWNER TO "postgres";

-- ----------------------------
-- Function structure for halfvec_mul
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."halfvec_mul"("public"."halfvec", "public"."halfvec");
CREATE FUNCTION "public"."halfvec_mul"("public"."halfvec", "public"."halfvec")
  RETURNS "public"."halfvec" AS '$libdir/vector', 'halfvec_mul'
  LANGUAGE c IMMUTABLE STRICT
  COST 1;
ALTER FUNCTION "public"."halfvec_mul"("public"."halfvec", "public"."halfvec") OWNER TO "postgres";

-- ----------------------------
-- Function structure for halfvec_ne
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."halfvec_ne"("public"."halfvec", "public"."halfvec");
CREATE FUNCTION "public"."halfvec_ne"("public"."halfvec", "public"."halfvec")
  RETURNS "pg_catalog"."bool" AS '$libdir/vector', 'halfvec_ne'
  LANGUAGE c IMMUTABLE STRICT
  COST 1;
ALTER FUNCTION "public"."halfvec_ne"("public"."halfvec", "public"."halfvec") OWNER TO "postgres";

-- ----------------------------
-- Function structure for halfvec_negative_inner_product
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."halfvec_negative_inner_product"("public"."halfvec", "public"."halfvec");
CREATE FUNCTION "public"."halfvec_negative_inner_product"("public"."halfvec", "public"."halfvec")
  RETURNS "pg_catalog"."float8" AS '$libdir/vector', 'halfvec_negative_inner_product'
  LANGUAGE c IMMUTABLE STRICT
  COST 1;
ALTER FUNCTION "public"."halfvec_negative_inner_product"("public"."halfvec", "public"."halfvec") OWNER TO "postgres";

-- ----------------------------
-- Function structure for halfvec_out
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."halfvec_out"("public"."halfvec");
CREATE FUNCTION "public"."halfvec_out"("public"."halfvec")
  RETURNS "pg_catalog"."cstring" AS '$libdir/vector', 'halfvec_out'
  LANGUAGE c IMMUTABLE STRICT
  COST 1;
ALTER FUNCTION "public"."halfvec_out"("public"."halfvec") OWNER TO "postgres";

-- ----------------------------
-- Function structure for halfvec_recv
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."halfvec_recv"(internal, oid, int4);
CREATE FUNCTION "public"."halfvec_recv"(internal, oid, int4)
  RETURNS "public"."halfvec" AS '$libdir/vector', 'halfvec_recv'
  LANGUAGE c IMMUTABLE STRICT
  COST 1;
ALTER FUNCTION "public"."halfvec_recv"(internal, oid, int4) OWNER TO "postgres";

-- ----------------------------
-- Function structure for halfvec_send
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."halfvec_send"("public"."halfvec");
CREATE FUNCTION "public"."halfvec_send"("public"."halfvec")
  RETURNS "pg_catalog"."bytea" AS '$libdir/vector', 'halfvec_send'
  LANGUAGE c IMMUTABLE STRICT
  COST 1;
ALTER FUNCTION "public"."halfvec_send"("public"."halfvec") OWNER TO "postgres";

-- ----------------------------
-- Function structure for halfvec_spherical_distance
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."halfvec_spherical_distance"("public"."halfvec", "public"."halfvec");
CREATE FUNCTION "public"."halfvec_spherical_distance"("public"."halfvec", "public"."halfvec")
  RETURNS "pg_catalog"."float8" AS '$libdir/vector', 'halfvec_spherical_distance'
  LANGUAGE c IMMUTABLE STRICT
  COST 1;
ALTER FUNCTION "public"."halfvec_spherical_distance"("public"."halfvec", "public"."halfvec") OWNER TO "postgres";

-- ----------------------------
-- Function structure for halfvec_sub
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."halfvec_sub"("public"."halfvec", "public"."halfvec");
CREATE FUNCTION "public"."halfvec_sub"("public"."halfvec", "public"."halfvec")
  RETURNS "public"."halfvec" AS '$libdir/vector', 'halfvec_sub'
  LANGUAGE c IMMUTABLE STRICT
  COST 1;
ALTER FUNCTION "public"."halfvec_sub"("public"."halfvec", "public"."halfvec") OWNER TO "postgres";

-- ----------------------------
-- Function structure for halfvec_to_float4
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."halfvec_to_float4"("public"."halfvec", int4, bool);
CREATE FUNCTION "public"."halfvec_to_float4"("public"."halfvec", int4, bool)
  RETURNS "pg_catalog"."_float4" AS '$libdir/vector', 'halfvec_to_float4'
  LANGUAGE c IMMUTABLE STRICT
  COST 1;
ALTER FUNCTION "public"."halfvec_to_float4"("public"."halfvec", int4, bool) OWNER TO "postgres";

-- ----------------------------
-- Function structure for halfvec_to_sparsevec
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."halfvec_to_sparsevec"("public"."halfvec", int4, bool);
CREATE FUNCTION "public"."halfvec_to_sparsevec"("public"."halfvec", int4, bool)
  RETURNS "public"."sparsevec" AS '$libdir/vector', 'halfvec_to_sparsevec'
  LANGUAGE c IMMUTABLE STRICT
  COST 1;
ALTER FUNCTION "public"."halfvec_to_sparsevec"("public"."halfvec", int4, bool) OWNER TO "postgres";

-- ----------------------------
-- Function structure for halfvec_to_vector
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."halfvec_to_vector"("public"."halfvec", int4, bool);
CREATE FUNCTION "public"."halfvec_to_vector"("public"."halfvec", int4, bool)
  RETURNS "public"."vector" AS '$libdir/vector', 'halfvec_to_vector'
  LANGUAGE c IMMUTABLE STRICT
  COST 1;
ALTER FUNCTION "public"."halfvec_to_vector"("public"."halfvec", int4, bool) OWNER TO "postgres";

-- ----------------------------
-- Function structure for halfvec_typmod_in
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."halfvec_typmod_in"(_cstring);
CREATE FUNCTION "public"."halfvec_typmod_in"(_cstring)
  RETURNS "pg_catalog"."int4" AS '$libdir/vector', 'halfvec_typmod_in'
  LANGUAGE c IMMUTABLE STRICT
  COST 1;
ALTER FUNCTION "public"."halfvec_typmod_in"(_cstring) OWNER TO "postgres";

-- ----------------------------
-- Function structure for hamming_distance
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."hamming_distance"(bit, bit);
CREATE FUNCTION "public"."hamming_distance"(bit, bit)
  RETURNS "pg_catalog"."float8" AS '$libdir/vector', 'hamming_distance'
  LANGUAGE c IMMUTABLE STRICT
  COST 1;
ALTER FUNCTION "public"."hamming_distance"(bit, bit) OWNER TO "postgres";

-- ----------------------------
-- Function structure for hnsw_bit_support
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."hnsw_bit_support"(internal);
CREATE FUNCTION "public"."hnsw_bit_support"(internal)
  RETURNS "pg_catalog"."internal" AS '$libdir/vector', 'hnsw_bit_support'
  LANGUAGE c VOLATILE
  COST 1;
ALTER FUNCTION "public"."hnsw_bit_support"(internal) OWNER TO "postgres";

-- ----------------------------
-- Function structure for hnsw_halfvec_support
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."hnsw_halfvec_support"(internal);
CREATE FUNCTION "public"."hnsw_halfvec_support"(internal)
  RETURNS "pg_catalog"."internal" AS '$libdir/vector', 'hnsw_halfvec_support'
  LANGUAGE c VOLATILE
  COST 1;
ALTER FUNCTION "public"."hnsw_halfvec_support"(internal) OWNER TO "postgres";

-- ----------------------------
-- Function structure for hnsw_sparsevec_support
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."hnsw_sparsevec_support"(internal);
CREATE FUNCTION "public"."hnsw_sparsevec_support"(internal)
  RETURNS "pg_catalog"."internal" AS '$libdir/vector', 'hnsw_sparsevec_support'
  LANGUAGE c VOLATILE
  COST 1;
ALTER FUNCTION "public"."hnsw_sparsevec_support"(internal) OWNER TO "postgres";

-- ----------------------------
-- Function structure for hnswhandler
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."hnswhandler"(internal);
CREATE FUNCTION "public"."hnswhandler"(internal)
  RETURNS "pg_catalog"."index_am_handler" AS '$libdir/vector', 'hnswhandler'
  LANGUAGE c VOLATILE
  COST 1;
ALTER FUNCTION "public"."hnswhandler"(internal) OWNER TO "postgres";

-- ----------------------------
-- Function structure for inner_product
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."inner_product"("public"."sparsevec", "public"."sparsevec");
CREATE FUNCTION "public"."inner_product"("public"."sparsevec", "public"."sparsevec")
  RETURNS "pg_catalog"."float8" AS '$libdir/vector', 'sparsevec_inner_product'
  LANGUAGE c IMMUTABLE STRICT
  COST 1;
ALTER FUNCTION "public"."inner_product"("public"."sparsevec", "public"."sparsevec") OWNER TO "postgres";

-- ----------------------------
-- Function structure for inner_product
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."inner_product"("public"."vector", "public"."vector");
CREATE FUNCTION "public"."inner_product"("public"."vector", "public"."vector")
  RETURNS "pg_catalog"."float8" AS '$libdir/vector', 'inner_product'
  LANGUAGE c IMMUTABLE STRICT
  COST 1;
ALTER FUNCTION "public"."inner_product"("public"."vector", "public"."vector") OWNER TO "postgres";

-- ----------------------------
-- Function structure for inner_product
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."inner_product"("public"."halfvec", "public"."halfvec");
CREATE FUNCTION "public"."inner_product"("public"."halfvec", "public"."halfvec")
  RETURNS "pg_catalog"."float8" AS '$libdir/vector', 'halfvec_inner_product'
  LANGUAGE c IMMUTABLE STRICT
  COST 1;
ALTER FUNCTION "public"."inner_product"("public"."halfvec", "public"."halfvec") OWNER TO "postgres";

-- ----------------------------
-- Function structure for ivfflat_bit_support
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."ivfflat_bit_support"(internal);
CREATE FUNCTION "public"."ivfflat_bit_support"(internal)
  RETURNS "pg_catalog"."internal" AS '$libdir/vector', 'ivfflat_bit_support'
  LANGUAGE c VOLATILE
  COST 1;
ALTER FUNCTION "public"."ivfflat_bit_support"(internal) OWNER TO "postgres";

-- ----------------------------
-- Function structure for ivfflat_halfvec_support
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."ivfflat_halfvec_support"(internal);
CREATE FUNCTION "public"."ivfflat_halfvec_support"(internal)
  RETURNS "pg_catalog"."internal" AS '$libdir/vector', 'ivfflat_halfvec_support'
  LANGUAGE c VOLATILE
  COST 1;
ALTER FUNCTION "public"."ivfflat_halfvec_support"(internal) OWNER TO "postgres";

-- ----------------------------
-- Function structure for ivfflathandler
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."ivfflathandler"(internal);
CREATE FUNCTION "public"."ivfflathandler"(internal)
  RETURNS "pg_catalog"."index_am_handler" AS '$libdir/vector', 'ivfflathandler'
  LANGUAGE c VOLATILE
  COST 1;
ALTER FUNCTION "public"."ivfflathandler"(internal) OWNER TO "postgres";

-- ----------------------------
-- Function structure for jaccard_distance
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."jaccard_distance"(bit, bit);
CREATE FUNCTION "public"."jaccard_distance"(bit, bit)
  RETURNS "pg_catalog"."float8" AS '$libdir/vector', 'jaccard_distance'
  LANGUAGE c IMMUTABLE STRICT
  COST 1;
ALTER FUNCTION "public"."jaccard_distance"(bit, bit) OWNER TO "postgres";

-- ----------------------------
-- Function structure for l1_distance
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."l1_distance"("public"."halfvec", "public"."halfvec");
CREATE FUNCTION "public"."l1_distance"("public"."halfvec", "public"."halfvec")
  RETURNS "pg_catalog"."float8" AS '$libdir/vector', 'halfvec_l1_distance'
  LANGUAGE c IMMUTABLE STRICT
  COST 1;
ALTER FUNCTION "public"."l1_distance"("public"."halfvec", "public"."halfvec") OWNER TO "postgres";

-- ----------------------------
-- Function structure for l1_distance
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."l1_distance"("public"."sparsevec", "public"."sparsevec");
CREATE FUNCTION "public"."l1_distance"("public"."sparsevec", "public"."sparsevec")
  RETURNS "pg_catalog"."float8" AS '$libdir/vector', 'sparsevec_l1_distance'
  LANGUAGE c IMMUTABLE STRICT
  COST 1;
ALTER FUNCTION "public"."l1_distance"("public"."sparsevec", "public"."sparsevec") OWNER TO "postgres";

-- ----------------------------
-- Function structure for l1_distance
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."l1_distance"("public"."vector", "public"."vector");
CREATE FUNCTION "public"."l1_distance"("public"."vector", "public"."vector")
  RETURNS "pg_catalog"."float8" AS '$libdir/vector', 'l1_distance'
  LANGUAGE c IMMUTABLE STRICT
  COST 1;
ALTER FUNCTION "public"."l1_distance"("public"."vector", "public"."vector") OWNER TO "postgres";

-- ----------------------------
-- Function structure for l2_distance
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."l2_distance"("public"."halfvec", "public"."halfvec");
CREATE FUNCTION "public"."l2_distance"("public"."halfvec", "public"."halfvec")
  RETURNS "pg_catalog"."float8" AS '$libdir/vector', 'halfvec_l2_distance'
  LANGUAGE c IMMUTABLE STRICT
  COST 1;
ALTER FUNCTION "public"."l2_distance"("public"."halfvec", "public"."halfvec") OWNER TO "postgres";

-- ----------------------------
-- Function structure for l2_distance
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."l2_distance"("public"."vector", "public"."vector");
CREATE FUNCTION "public"."l2_distance"("public"."vector", "public"."vector")
  RETURNS "pg_catalog"."float8" AS '$libdir/vector', 'l2_distance'
  LANGUAGE c IMMUTABLE STRICT
  COST 1;
ALTER FUNCTION "public"."l2_distance"("public"."vector", "public"."vector") OWNER TO "postgres";

-- ----------------------------
-- Function structure for l2_distance
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."l2_distance"("public"."sparsevec", "public"."sparsevec");
CREATE FUNCTION "public"."l2_distance"("public"."sparsevec", "public"."sparsevec")
  RETURNS "pg_catalog"."float8" AS '$libdir/vector', 'sparsevec_l2_distance'
  LANGUAGE c IMMUTABLE STRICT
  COST 1;
ALTER FUNCTION "public"."l2_distance"("public"."sparsevec", "public"."sparsevec") OWNER TO "postgres";

-- ----------------------------
-- Function structure for l2_norm
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."l2_norm"("public"."halfvec");
CREATE FUNCTION "public"."l2_norm"("public"."halfvec")
  RETURNS "pg_catalog"."float8" AS '$libdir/vector', 'halfvec_l2_norm'
  LANGUAGE c IMMUTABLE STRICT
  COST 1;
ALTER FUNCTION "public"."l2_norm"("public"."halfvec") OWNER TO "postgres";

-- ----------------------------
-- Function structure for l2_norm
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."l2_norm"("public"."sparsevec");
CREATE FUNCTION "public"."l2_norm"("public"."sparsevec")
  RETURNS "pg_catalog"."float8" AS '$libdir/vector', 'sparsevec_l2_norm'
  LANGUAGE c IMMUTABLE STRICT
  COST 1;
ALTER FUNCTION "public"."l2_norm"("public"."sparsevec") OWNER TO "postgres";

-- ----------------------------
-- Function structure for l2_normalize
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."l2_normalize"("public"."sparsevec");
CREATE FUNCTION "public"."l2_normalize"("public"."sparsevec")
  RETURNS "public"."sparsevec" AS '$libdir/vector', 'sparsevec_l2_normalize'
  LANGUAGE c IMMUTABLE STRICT
  COST 1;
ALTER FUNCTION "public"."l2_normalize"("public"."sparsevec") OWNER TO "postgres";

-- ----------------------------
-- Function structure for l2_normalize
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."l2_normalize"("public"."halfvec");
CREATE FUNCTION "public"."l2_normalize"("public"."halfvec")
  RETURNS "public"."halfvec" AS '$libdir/vector', 'halfvec_l2_normalize'
  LANGUAGE c IMMUTABLE STRICT
  COST 1;
ALTER FUNCTION "public"."l2_normalize"("public"."halfvec") OWNER TO "postgres";

-- ----------------------------
-- Function structure for l2_normalize
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."l2_normalize"("public"."vector");
CREATE FUNCTION "public"."l2_normalize"("public"."vector")
  RETURNS "public"."vector" AS '$libdir/vector', 'l2_normalize'
  LANGUAGE c IMMUTABLE STRICT
  COST 1;
ALTER FUNCTION "public"."l2_normalize"("public"."vector") OWNER TO "postgres";

-- ----------------------------
-- Function structure for set_limit
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."set_limit"(float4);
CREATE FUNCTION "public"."set_limit"(float4)
  RETURNS "pg_catalog"."float4" AS '$libdir/pg_trgm', 'set_limit'
  LANGUAGE c VOLATILE STRICT
  COST 1;
ALTER FUNCTION "public"."set_limit"(float4) OWNER TO "postgres";

-- ----------------------------
-- Function structure for show_limit
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."show_limit"();
CREATE FUNCTION "public"."show_limit"()
  RETURNS "pg_catalog"."float4" AS '$libdir/pg_trgm', 'show_limit'
  LANGUAGE c STABLE STRICT
  COST 1;
ALTER FUNCTION "public"."show_limit"() OWNER TO "postgres";

-- ----------------------------
-- Function structure for show_trgm
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."show_trgm"(text);
CREATE FUNCTION "public"."show_trgm"(text)
  RETURNS "pg_catalog"."_text" AS '$libdir/pg_trgm', 'show_trgm'
  LANGUAGE c IMMUTABLE STRICT
  COST 1;
ALTER FUNCTION "public"."show_trgm"(text) OWNER TO "postgres";

-- ----------------------------
-- Function structure for similarity
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."similarity"(text, text);
CREATE FUNCTION "public"."similarity"(text, text)
  RETURNS "pg_catalog"."float4" AS '$libdir/pg_trgm', 'similarity'
  LANGUAGE c IMMUTABLE STRICT
  COST 1;
ALTER FUNCTION "public"."similarity"(text, text) OWNER TO "postgres";

-- ----------------------------
-- Function structure for similarity_dist
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."similarity_dist"(text, text);
CREATE FUNCTION "public"."similarity_dist"(text, text)
  RETURNS "pg_catalog"."float4" AS '$libdir/pg_trgm', 'similarity_dist'
  LANGUAGE c IMMUTABLE STRICT
  COST 1;
ALTER FUNCTION "public"."similarity_dist"(text, text) OWNER TO "postgres";

-- ----------------------------
-- Function structure for similarity_op
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."similarity_op"(text, text);
CREATE FUNCTION "public"."similarity_op"(text, text)
  RETURNS "pg_catalog"."bool" AS '$libdir/pg_trgm', 'similarity_op'
  LANGUAGE c STABLE STRICT
  COST 1;
ALTER FUNCTION "public"."similarity_op"(text, text) OWNER TO "postgres";

-- ----------------------------
-- Function structure for sparsevec
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."sparsevec"("public"."sparsevec", int4, bool);
CREATE FUNCTION "public"."sparsevec"("public"."sparsevec", int4, bool)
  RETURNS "public"."sparsevec" AS '$libdir/vector', 'sparsevec'
  LANGUAGE c IMMUTABLE STRICT
  COST 1;
ALTER FUNCTION "public"."sparsevec"("public"."sparsevec", int4, bool) OWNER TO "postgres";

-- ----------------------------
-- Function structure for sparsevec_cmp
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."sparsevec_cmp"("public"."sparsevec", "public"."sparsevec");
CREATE FUNCTION "public"."sparsevec_cmp"("public"."sparsevec", "public"."sparsevec")
  RETURNS "pg_catalog"."int4" AS '$libdir/vector', 'sparsevec_cmp'
  LANGUAGE c IMMUTABLE STRICT
  COST 1;
ALTER FUNCTION "public"."sparsevec_cmp"("public"."sparsevec", "public"."sparsevec") OWNER TO "postgres";

-- ----------------------------
-- Function structure for sparsevec_eq
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."sparsevec_eq"("public"."sparsevec", "public"."sparsevec");
CREATE FUNCTION "public"."sparsevec_eq"("public"."sparsevec", "public"."sparsevec")
  RETURNS "pg_catalog"."bool" AS '$libdir/vector', 'sparsevec_eq'
  LANGUAGE c IMMUTABLE STRICT
  COST 1;
ALTER FUNCTION "public"."sparsevec_eq"("public"."sparsevec", "public"."sparsevec") OWNER TO "postgres";

-- ----------------------------
-- Function structure for sparsevec_ge
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."sparsevec_ge"("public"."sparsevec", "public"."sparsevec");
CREATE FUNCTION "public"."sparsevec_ge"("public"."sparsevec", "public"."sparsevec")
  RETURNS "pg_catalog"."bool" AS '$libdir/vector', 'sparsevec_ge'
  LANGUAGE c IMMUTABLE STRICT
  COST 1;
ALTER FUNCTION "public"."sparsevec_ge"("public"."sparsevec", "public"."sparsevec") OWNER TO "postgres";

-- ----------------------------
-- Function structure for sparsevec_gt
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."sparsevec_gt"("public"."sparsevec", "public"."sparsevec");
CREATE FUNCTION "public"."sparsevec_gt"("public"."sparsevec", "public"."sparsevec")
  RETURNS "pg_catalog"."bool" AS '$libdir/vector', 'sparsevec_gt'
  LANGUAGE c IMMUTABLE STRICT
  COST 1;
ALTER FUNCTION "public"."sparsevec_gt"("public"."sparsevec", "public"."sparsevec") OWNER TO "postgres";

-- ----------------------------
-- Function structure for sparsevec_in
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."sparsevec_in"(cstring, oid, int4);
CREATE FUNCTION "public"."sparsevec_in"(cstring, oid, int4)
  RETURNS "public"."sparsevec" AS '$libdir/vector', 'sparsevec_in'
  LANGUAGE c IMMUTABLE STRICT
  COST 1;
ALTER FUNCTION "public"."sparsevec_in"(cstring, oid, int4) OWNER TO "postgres";

-- ----------------------------
-- Function structure for sparsevec_l2_squared_distance
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."sparsevec_l2_squared_distance"("public"."sparsevec", "public"."sparsevec");
CREATE FUNCTION "public"."sparsevec_l2_squared_distance"("public"."sparsevec", "public"."sparsevec")
  RETURNS "pg_catalog"."float8" AS '$libdir/vector', 'sparsevec_l2_squared_distance'
  LANGUAGE c IMMUTABLE STRICT
  COST 1;
ALTER FUNCTION "public"."sparsevec_l2_squared_distance"("public"."sparsevec", "public"."sparsevec") OWNER TO "postgres";

-- ----------------------------
-- Function structure for sparsevec_le
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."sparsevec_le"("public"."sparsevec", "public"."sparsevec");
CREATE FUNCTION "public"."sparsevec_le"("public"."sparsevec", "public"."sparsevec")
  RETURNS "pg_catalog"."bool" AS '$libdir/vector', 'sparsevec_le'
  LANGUAGE c IMMUTABLE STRICT
  COST 1;
ALTER FUNCTION "public"."sparsevec_le"("public"."sparsevec", "public"."sparsevec") OWNER TO "postgres";

-- ----------------------------
-- Function structure for sparsevec_lt
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."sparsevec_lt"("public"."sparsevec", "public"."sparsevec");
CREATE FUNCTION "public"."sparsevec_lt"("public"."sparsevec", "public"."sparsevec")
  RETURNS "pg_catalog"."bool" AS '$libdir/vector', 'sparsevec_lt'
  LANGUAGE c IMMUTABLE STRICT
  COST 1;
ALTER FUNCTION "public"."sparsevec_lt"("public"."sparsevec", "public"."sparsevec") OWNER TO "postgres";

-- ----------------------------
-- Function structure for sparsevec_ne
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."sparsevec_ne"("public"."sparsevec", "public"."sparsevec");
CREATE FUNCTION "public"."sparsevec_ne"("public"."sparsevec", "public"."sparsevec")
  RETURNS "pg_catalog"."bool" AS '$libdir/vector', 'sparsevec_ne'
  LANGUAGE c IMMUTABLE STRICT
  COST 1;
ALTER FUNCTION "public"."sparsevec_ne"("public"."sparsevec", "public"."sparsevec") OWNER TO "postgres";

-- ----------------------------
-- Function structure for sparsevec_negative_inner_product
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."sparsevec_negative_inner_product"("public"."sparsevec", "public"."sparsevec");
CREATE FUNCTION "public"."sparsevec_negative_inner_product"("public"."sparsevec", "public"."sparsevec")
  RETURNS "pg_catalog"."float8" AS '$libdir/vector', 'sparsevec_negative_inner_product'
  LANGUAGE c IMMUTABLE STRICT
  COST 1;
ALTER FUNCTION "public"."sparsevec_negative_inner_product"("public"."sparsevec", "public"."sparsevec") OWNER TO "postgres";

-- ----------------------------
-- Function structure for sparsevec_out
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."sparsevec_out"("public"."sparsevec");
CREATE FUNCTION "public"."sparsevec_out"("public"."sparsevec")
  RETURNS "pg_catalog"."cstring" AS '$libdir/vector', 'sparsevec_out'
  LANGUAGE c IMMUTABLE STRICT
  COST 1;
ALTER FUNCTION "public"."sparsevec_out"("public"."sparsevec") OWNER TO "postgres";

-- ----------------------------
-- Function structure for sparsevec_recv
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."sparsevec_recv"(internal, oid, int4);
CREATE FUNCTION "public"."sparsevec_recv"(internal, oid, int4)
  RETURNS "public"."sparsevec" AS '$libdir/vector', 'sparsevec_recv'
  LANGUAGE c IMMUTABLE STRICT
  COST 1;
ALTER FUNCTION "public"."sparsevec_recv"(internal, oid, int4) OWNER TO "postgres";

-- ----------------------------
-- Function structure for sparsevec_send
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."sparsevec_send"("public"."sparsevec");
CREATE FUNCTION "public"."sparsevec_send"("public"."sparsevec")
  RETURNS "pg_catalog"."bytea" AS '$libdir/vector', 'sparsevec_send'
  LANGUAGE c IMMUTABLE STRICT
  COST 1;
ALTER FUNCTION "public"."sparsevec_send"("public"."sparsevec") OWNER TO "postgres";

-- ----------------------------
-- Function structure for sparsevec_to_halfvec
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."sparsevec_to_halfvec"("public"."sparsevec", int4, bool);
CREATE FUNCTION "public"."sparsevec_to_halfvec"("public"."sparsevec", int4, bool)
  RETURNS "public"."halfvec" AS '$libdir/vector', 'sparsevec_to_halfvec'
  LANGUAGE c IMMUTABLE STRICT
  COST 1;
ALTER FUNCTION "public"."sparsevec_to_halfvec"("public"."sparsevec", int4, bool) OWNER TO "postgres";

-- ----------------------------
-- Function structure for sparsevec_to_vector
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."sparsevec_to_vector"("public"."sparsevec", int4, bool);
CREATE FUNCTION "public"."sparsevec_to_vector"("public"."sparsevec", int4, bool)
  RETURNS "public"."vector" AS '$libdir/vector', 'sparsevec_to_vector'
  LANGUAGE c IMMUTABLE STRICT
  COST 1;
ALTER FUNCTION "public"."sparsevec_to_vector"("public"."sparsevec", int4, bool) OWNER TO "postgres";

-- ----------------------------
-- Function structure for sparsevec_typmod_in
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."sparsevec_typmod_in"(_cstring);
CREATE FUNCTION "public"."sparsevec_typmod_in"(_cstring)
  RETURNS "pg_catalog"."int4" AS '$libdir/vector', 'sparsevec_typmod_in'
  LANGUAGE c IMMUTABLE STRICT
  COST 1;
ALTER FUNCTION "public"."sparsevec_typmod_in"(_cstring) OWNER TO "postgres";

-- ----------------------------
-- Function structure for strict_word_similarity
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."strict_word_similarity"(text, text);
CREATE FUNCTION "public"."strict_word_similarity"(text, text)
  RETURNS "pg_catalog"."float4" AS '$libdir/pg_trgm', 'strict_word_similarity'
  LANGUAGE c IMMUTABLE STRICT
  COST 1;
ALTER FUNCTION "public"."strict_word_similarity"(text, text) OWNER TO "postgres";

-- ----------------------------
-- Function structure for strict_word_similarity_commutator_op
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."strict_word_similarity_commutator_op"(text, text);
CREATE FUNCTION "public"."strict_word_similarity_commutator_op"(text, text)
  RETURNS "pg_catalog"."bool" AS '$libdir/pg_trgm', 'strict_word_similarity_commutator_op'
  LANGUAGE c STABLE STRICT
  COST 1;
ALTER FUNCTION "public"."strict_word_similarity_commutator_op"(text, text) OWNER TO "postgres";

-- ----------------------------
-- Function structure for strict_word_similarity_dist_commutator_op
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."strict_word_similarity_dist_commutator_op"(text, text);
CREATE FUNCTION "public"."strict_word_similarity_dist_commutator_op"(text, text)
  RETURNS "pg_catalog"."float4" AS '$libdir/pg_trgm', 'strict_word_similarity_dist_commutator_op'
  LANGUAGE c IMMUTABLE STRICT
  COST 1;
ALTER FUNCTION "public"."strict_word_similarity_dist_commutator_op"(text, text) OWNER TO "postgres";

-- ----------------------------
-- Function structure for strict_word_similarity_dist_op
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."strict_word_similarity_dist_op"(text, text);
CREATE FUNCTION "public"."strict_word_similarity_dist_op"(text, text)
  RETURNS "pg_catalog"."float4" AS '$libdir/pg_trgm', 'strict_word_similarity_dist_op'
  LANGUAGE c IMMUTABLE STRICT
  COST 1;
ALTER FUNCTION "public"."strict_word_similarity_dist_op"(text, text) OWNER TO "postgres";

-- ----------------------------
-- Function structure for strict_word_similarity_op
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."strict_word_similarity_op"(text, text);
CREATE FUNCTION "public"."strict_word_similarity_op"(text, text)
  RETURNS "pg_catalog"."bool" AS '$libdir/pg_trgm', 'strict_word_similarity_op'
  LANGUAGE c STABLE STRICT
  COST 1;
ALTER FUNCTION "public"."strict_word_similarity_op"(text, text) OWNER TO "postgres";

-- ----------------------------
-- Function structure for subvector
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."subvector"("public"."halfvec", int4, int4);
CREATE FUNCTION "public"."subvector"("public"."halfvec", int4, int4)
  RETURNS "public"."halfvec" AS '$libdir/vector', 'halfvec_subvector'
  LANGUAGE c IMMUTABLE STRICT
  COST 1;
ALTER FUNCTION "public"."subvector"("public"."halfvec", int4, int4) OWNER TO "postgres";

-- ----------------------------
-- Function structure for subvector
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."subvector"("public"."vector", int4, int4);
CREATE FUNCTION "public"."subvector"("public"."vector", int4, int4)
  RETURNS "public"."vector" AS '$libdir/vector', 'subvector'
  LANGUAGE c IMMUTABLE STRICT
  COST 1;
ALTER FUNCTION "public"."subvector"("public"."vector", int4, int4) OWNER TO "postgres";

-- ----------------------------
-- Function structure for vector
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."vector"("public"."vector", int4, bool);
CREATE FUNCTION "public"."vector"("public"."vector", int4, bool)
  RETURNS "public"."vector" AS '$libdir/vector', 'vector'
  LANGUAGE c IMMUTABLE STRICT
  COST 1;
ALTER FUNCTION "public"."vector"("public"."vector", int4, bool) OWNER TO "postgres";

-- ----------------------------
-- Function structure for vector_accum
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."vector_accum"(_float8, "public"."vector");
CREATE FUNCTION "public"."vector_accum"(_float8, "public"."vector")
  RETURNS "pg_catalog"."_float8" AS '$libdir/vector', 'vector_accum'
  LANGUAGE c IMMUTABLE STRICT
  COST 1;
ALTER FUNCTION "public"."vector_accum"(_float8, "public"."vector") OWNER TO "postgres";

-- ----------------------------
-- Function structure for vector_add
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."vector_add"("public"."vector", "public"."vector");
CREATE FUNCTION "public"."vector_add"("public"."vector", "public"."vector")
  RETURNS "public"."vector" AS '$libdir/vector', 'vector_add'
  LANGUAGE c IMMUTABLE STRICT
  COST 1;
ALTER FUNCTION "public"."vector_add"("public"."vector", "public"."vector") OWNER TO "postgres";

-- ----------------------------
-- Function structure for vector_avg
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."vector_avg"(_float8);
CREATE FUNCTION "public"."vector_avg"(_float8)
  RETURNS "public"."vector" AS '$libdir/vector', 'vector_avg'
  LANGUAGE c IMMUTABLE STRICT
  COST 1;
ALTER FUNCTION "public"."vector_avg"(_float8) OWNER TO "postgres";

-- ----------------------------
-- Function structure for vector_cmp
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."vector_cmp"("public"."vector", "public"."vector");
CREATE FUNCTION "public"."vector_cmp"("public"."vector", "public"."vector")
  RETURNS "pg_catalog"."int4" AS '$libdir/vector', 'vector_cmp'
  LANGUAGE c IMMUTABLE STRICT
  COST 1;
ALTER FUNCTION "public"."vector_cmp"("public"."vector", "public"."vector") OWNER TO "postgres";

-- ----------------------------
-- Function structure for vector_combine
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."vector_combine"(_float8, _float8);
CREATE FUNCTION "public"."vector_combine"(_float8, _float8)
  RETURNS "pg_catalog"."_float8" AS '$libdir/vector', 'vector_combine'
  LANGUAGE c IMMUTABLE STRICT
  COST 1;
ALTER FUNCTION "public"."vector_combine"(_float8, _float8) OWNER TO "postgres";

-- ----------------------------
-- Function structure for vector_concat
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."vector_concat"("public"."vector", "public"."vector");
CREATE FUNCTION "public"."vector_concat"("public"."vector", "public"."vector")
  RETURNS "public"."vector" AS '$libdir/vector', 'vector_concat'
  LANGUAGE c IMMUTABLE STRICT
  COST 1;
ALTER FUNCTION "public"."vector_concat"("public"."vector", "public"."vector") OWNER TO "postgres";

-- ----------------------------
-- Function structure for vector_dims
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."vector_dims"("public"."halfvec");
CREATE FUNCTION "public"."vector_dims"("public"."halfvec")
  RETURNS "pg_catalog"."int4" AS '$libdir/vector', 'halfvec_vector_dims'
  LANGUAGE c IMMUTABLE STRICT
  COST 1;
ALTER FUNCTION "public"."vector_dims"("public"."halfvec") OWNER TO "postgres";

-- ----------------------------
-- Function structure for vector_dims
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."vector_dims"("public"."vector");
CREATE FUNCTION "public"."vector_dims"("public"."vector")
  RETURNS "pg_catalog"."int4" AS '$libdir/vector', 'vector_dims'
  LANGUAGE c IMMUTABLE STRICT
  COST 1;
ALTER FUNCTION "public"."vector_dims"("public"."vector") OWNER TO "postgres";

-- ----------------------------
-- Function structure for vector_eq
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."vector_eq"("public"."vector", "public"."vector");
CREATE FUNCTION "public"."vector_eq"("public"."vector", "public"."vector")
  RETURNS "pg_catalog"."bool" AS '$libdir/vector', 'vector_eq'
  LANGUAGE c IMMUTABLE STRICT
  COST 1;
ALTER FUNCTION "public"."vector_eq"("public"."vector", "public"."vector") OWNER TO "postgres";

-- ----------------------------
-- Function structure for vector_ge
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."vector_ge"("public"."vector", "public"."vector");
CREATE FUNCTION "public"."vector_ge"("public"."vector", "public"."vector")
  RETURNS "pg_catalog"."bool" AS '$libdir/vector', 'vector_ge'
  LANGUAGE c IMMUTABLE STRICT
  COST 1;
ALTER FUNCTION "public"."vector_ge"("public"."vector", "public"."vector") OWNER TO "postgres";

-- ----------------------------
-- Function structure for vector_gt
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."vector_gt"("public"."vector", "public"."vector");
CREATE FUNCTION "public"."vector_gt"("public"."vector", "public"."vector")
  RETURNS "pg_catalog"."bool" AS '$libdir/vector', 'vector_gt'
  LANGUAGE c IMMUTABLE STRICT
  COST 1;
ALTER FUNCTION "public"."vector_gt"("public"."vector", "public"."vector") OWNER TO "postgres";

-- ----------------------------
-- Function structure for vector_in
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."vector_in"(cstring, oid, int4);
CREATE FUNCTION "public"."vector_in"(cstring, oid, int4)
  RETURNS "public"."vector" AS '$libdir/vector', 'vector_in'
  LANGUAGE c IMMUTABLE STRICT
  COST 1;
ALTER FUNCTION "public"."vector_in"(cstring, oid, int4) OWNER TO "postgres";

-- ----------------------------
-- Function structure for vector_l2_squared_distance
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."vector_l2_squared_distance"("public"."vector", "public"."vector");
CREATE FUNCTION "public"."vector_l2_squared_distance"("public"."vector", "public"."vector")
  RETURNS "pg_catalog"."float8" AS '$libdir/vector', 'vector_l2_squared_distance'
  LANGUAGE c IMMUTABLE STRICT
  COST 1;
ALTER FUNCTION "public"."vector_l2_squared_distance"("public"."vector", "public"."vector") OWNER TO "postgres";

-- ----------------------------
-- Function structure for vector_le
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."vector_le"("public"."vector", "public"."vector");
CREATE FUNCTION "public"."vector_le"("public"."vector", "public"."vector")
  RETURNS "pg_catalog"."bool" AS '$libdir/vector', 'vector_le'
  LANGUAGE c IMMUTABLE STRICT
  COST 1;
ALTER FUNCTION "public"."vector_le"("public"."vector", "public"."vector") OWNER TO "postgres";

-- ----------------------------
-- Function structure for vector_lt
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."vector_lt"("public"."vector", "public"."vector");
CREATE FUNCTION "public"."vector_lt"("public"."vector", "public"."vector")
  RETURNS "pg_catalog"."bool" AS '$libdir/vector', 'vector_lt'
  LANGUAGE c IMMUTABLE STRICT
  COST 1;
ALTER FUNCTION "public"."vector_lt"("public"."vector", "public"."vector") OWNER TO "postgres";

-- ----------------------------
-- Function structure for vector_mul
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."vector_mul"("public"."vector", "public"."vector");
CREATE FUNCTION "public"."vector_mul"("public"."vector", "public"."vector")
  RETURNS "public"."vector" AS '$libdir/vector', 'vector_mul'
  LANGUAGE c IMMUTABLE STRICT
  COST 1;
ALTER FUNCTION "public"."vector_mul"("public"."vector", "public"."vector") OWNER TO "postgres";

-- ----------------------------
-- Function structure for vector_ne
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."vector_ne"("public"."vector", "public"."vector");
CREATE FUNCTION "public"."vector_ne"("public"."vector", "public"."vector")
  RETURNS "pg_catalog"."bool" AS '$libdir/vector', 'vector_ne'
  LANGUAGE c IMMUTABLE STRICT
  COST 1;
ALTER FUNCTION "public"."vector_ne"("public"."vector", "public"."vector") OWNER TO "postgres";

-- ----------------------------
-- Function structure for vector_negative_inner_product
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."vector_negative_inner_product"("public"."vector", "public"."vector");
CREATE FUNCTION "public"."vector_negative_inner_product"("public"."vector", "public"."vector")
  RETURNS "pg_catalog"."float8" AS '$libdir/vector', 'vector_negative_inner_product'
  LANGUAGE c IMMUTABLE STRICT
  COST 1;
ALTER FUNCTION "public"."vector_negative_inner_product"("public"."vector", "public"."vector") OWNER TO "postgres";

-- ----------------------------
-- Function structure for vector_norm
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."vector_norm"("public"."vector");
CREATE FUNCTION "public"."vector_norm"("public"."vector")
  RETURNS "pg_catalog"."float8" AS '$libdir/vector', 'vector_norm'
  LANGUAGE c IMMUTABLE STRICT
  COST 1;
ALTER FUNCTION "public"."vector_norm"("public"."vector") OWNER TO "postgres";

-- ----------------------------
-- Function structure for vector_out
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."vector_out"("public"."vector");
CREATE FUNCTION "public"."vector_out"("public"."vector")
  RETURNS "pg_catalog"."cstring" AS '$libdir/vector', 'vector_out'
  LANGUAGE c IMMUTABLE STRICT
  COST 1;
ALTER FUNCTION "public"."vector_out"("public"."vector") OWNER TO "postgres";

-- ----------------------------
-- Function structure for vector_recv
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."vector_recv"(internal, oid, int4);
CREATE FUNCTION "public"."vector_recv"(internal, oid, int4)
  RETURNS "public"."vector" AS '$libdir/vector', 'vector_recv'
  LANGUAGE c IMMUTABLE STRICT
  COST 1;
ALTER FUNCTION "public"."vector_recv"(internal, oid, int4) OWNER TO "postgres";

-- ----------------------------
-- Function structure for vector_send
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."vector_send"("public"."vector");
CREATE FUNCTION "public"."vector_send"("public"."vector")
  RETURNS "pg_catalog"."bytea" AS '$libdir/vector', 'vector_send'
  LANGUAGE c IMMUTABLE STRICT
  COST 1;
ALTER FUNCTION "public"."vector_send"("public"."vector") OWNER TO "postgres";

-- ----------------------------
-- Function structure for vector_spherical_distance
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."vector_spherical_distance"("public"."vector", "public"."vector");
CREATE FUNCTION "public"."vector_spherical_distance"("public"."vector", "public"."vector")
  RETURNS "pg_catalog"."float8" AS '$libdir/vector', 'vector_spherical_distance'
  LANGUAGE c IMMUTABLE STRICT
  COST 1;
ALTER FUNCTION "public"."vector_spherical_distance"("public"."vector", "public"."vector") OWNER TO "postgres";

-- ----------------------------
-- Function structure for vector_sub
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."vector_sub"("public"."vector", "public"."vector");
CREATE FUNCTION "public"."vector_sub"("public"."vector", "public"."vector")
  RETURNS "public"."vector" AS '$libdir/vector', 'vector_sub'
  LANGUAGE c IMMUTABLE STRICT
  COST 1;
ALTER FUNCTION "public"."vector_sub"("public"."vector", "public"."vector") OWNER TO "postgres";

-- ----------------------------
-- Function structure for vector_to_float4
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."vector_to_float4"("public"."vector", int4, bool);
CREATE FUNCTION "public"."vector_to_float4"("public"."vector", int4, bool)
  RETURNS "pg_catalog"."_float4" AS '$libdir/vector', 'vector_to_float4'
  LANGUAGE c IMMUTABLE STRICT
  COST 1;
ALTER FUNCTION "public"."vector_to_float4"("public"."vector", int4, bool) OWNER TO "postgres";

-- ----------------------------
-- Function structure for vector_to_halfvec
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."vector_to_halfvec"("public"."vector", int4, bool);
CREATE FUNCTION "public"."vector_to_halfvec"("public"."vector", int4, bool)
  RETURNS "public"."halfvec" AS '$libdir/vector', 'vector_to_halfvec'
  LANGUAGE c IMMUTABLE STRICT
  COST 1;
ALTER FUNCTION "public"."vector_to_halfvec"("public"."vector", int4, bool) OWNER TO "postgres";

-- ----------------------------
-- Function structure for vector_to_sparsevec
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."vector_to_sparsevec"("public"."vector", int4, bool);
CREATE FUNCTION "public"."vector_to_sparsevec"("public"."vector", int4, bool)
  RETURNS "public"."sparsevec" AS '$libdir/vector', 'vector_to_sparsevec'
  LANGUAGE c IMMUTABLE STRICT
  COST 1;
ALTER FUNCTION "public"."vector_to_sparsevec"("public"."vector", int4, bool) OWNER TO "postgres";

-- ----------------------------
-- Function structure for vector_typmod_in
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."vector_typmod_in"(_cstring);
CREATE FUNCTION "public"."vector_typmod_in"(_cstring)
  RETURNS "pg_catalog"."int4" AS '$libdir/vector', 'vector_typmod_in'
  LANGUAGE c IMMUTABLE STRICT
  COST 1;
ALTER FUNCTION "public"."vector_typmod_in"(_cstring) OWNER TO "postgres";

-- ----------------------------
-- Function structure for word_similarity
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."word_similarity"(text, text);
CREATE FUNCTION "public"."word_similarity"(text, text)
  RETURNS "pg_catalog"."float4" AS '$libdir/pg_trgm', 'word_similarity'
  LANGUAGE c IMMUTABLE STRICT
  COST 1;
ALTER FUNCTION "public"."word_similarity"(text, text) OWNER TO "postgres";

-- ----------------------------
-- Function structure for word_similarity_commutator_op
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."word_similarity_commutator_op"(text, text);
CREATE FUNCTION "public"."word_similarity_commutator_op"(text, text)
  RETURNS "pg_catalog"."bool" AS '$libdir/pg_trgm', 'word_similarity_commutator_op'
  LANGUAGE c STABLE STRICT
  COST 1;
ALTER FUNCTION "public"."word_similarity_commutator_op"(text, text) OWNER TO "postgres";

-- ----------------------------
-- Function structure for word_similarity_dist_commutator_op
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."word_similarity_dist_commutator_op"(text, text);
CREATE FUNCTION "public"."word_similarity_dist_commutator_op"(text, text)
  RETURNS "pg_catalog"."float4" AS '$libdir/pg_trgm', 'word_similarity_dist_commutator_op'
  LANGUAGE c IMMUTABLE STRICT
  COST 1;
ALTER FUNCTION "public"."word_similarity_dist_commutator_op"(text, text) OWNER TO "postgres";

-- ----------------------------
-- Function structure for word_similarity_dist_op
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."word_similarity_dist_op"(text, text);
CREATE FUNCTION "public"."word_similarity_dist_op"(text, text)
  RETURNS "pg_catalog"."float4" AS '$libdir/pg_trgm', 'word_similarity_dist_op'
  LANGUAGE c IMMUTABLE STRICT
  COST 1;
ALTER FUNCTION "public"."word_similarity_dist_op"(text, text) OWNER TO "postgres";

-- ----------------------------
-- Function structure for word_similarity_op
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."word_similarity_op"(text, text);
CREATE FUNCTION "public"."word_similarity_op"(text, text)
  RETURNS "pg_catalog"."bool" AS '$libdir/pg_trgm', 'word_similarity_op'
  LANGUAGE c STABLE STRICT
  COST 1;
ALTER FUNCTION "public"."word_similarity_op"(text, text) OWNER TO "postgres";

-- ----------------------------
-- Alter sequences owned by
-- ----------------------------
ALTER SEQUENCE "public"."agent_knowledge_binding_id_seq"
OWNED BY "public"."agent_knowledge_binding"."id";
SELECT setval('"public"."agent_knowledge_binding_id_seq"', 1, false);

-- ----------------------------
-- Alter sequences owned by
-- ----------------------------
ALTER SEQUENCE "public"."ai_audit_log_id_seq"
OWNED BY "public"."ai_audit_log"."id";
SELECT setval('"public"."ai_audit_log_id_seq"', 3, true);

-- ----------------------------
-- Alter sequences owned by
-- ----------------------------
ALTER SEQUENCE "public"."conversation_id_seq"
OWNED BY "public"."conversation"."id";
SELECT setval('"public"."conversation_id_seq"', 1, true);

-- ----------------------------
-- Alter sequences owned by
-- ----------------------------
ALTER SEQUENCE "public"."conversation_message_id_seq"
OWNED BY "public"."conversation_message"."id";
SELECT setval('"public"."conversation_message_id_seq"', 2, true);

-- ----------------------------
-- Alter sequences owned by
-- ----------------------------
ALTER SEQUENCE "public"."knowledge_base_id_seq"
OWNED BY "public"."knowledge_base"."id";
SELECT setval('"public"."knowledge_base_id_seq"', 1, true);

-- ----------------------------
-- Alter sequences owned by
-- ----------------------------
ALTER SEQUENCE "public"."knowledge_base_tag_id_seq"
OWNED BY "public"."knowledge_base_tag"."id";
SELECT setval('"public"."knowledge_base_tag_id_seq"', 1, false);

-- ----------------------------
-- Alter sequences owned by
-- ----------------------------
ALTER SEQUENCE "public"."knowledge_chunk_id_seq"
OWNED BY "public"."knowledge_chunk"."id";
SELECT setval('"public"."knowledge_chunk_id_seq"', 1, false);

-- ----------------------------
-- Alter sequences owned by
-- ----------------------------
ALTER SEQUENCE "public"."knowledge_document_id_seq"
OWNED BY "public"."knowledge_document"."id";
SELECT setval('"public"."knowledge_document_id_seq"', 1, false);

-- ----------------------------
-- Alter sequences owned by
-- ----------------------------
ALTER SEQUENCE "public"."temp_document_id_seq"
OWNED BY "public"."temp_document"."id";
SELECT setval('"public"."temp_document_id_seq"', 1, false);

-- ----------------------------
-- Alter sequences owned by
-- ----------------------------
ALTER SEQUENCE "public"."user_long_term_memory_id_seq"
OWNED BY "public"."user_long_term_memory"."id";
SELECT setval('"public"."user_long_term_memory_id_seq"', 1, true);

-- ----------------------------
-- Indexes structure for table agent_knowledge_binding
-- ----------------------------
CREATE INDEX "idx_akb_agent" ON "public"."agent_knowledge_binding" USING btree (
  "agent_id" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST
);
CREATE INDEX "idx_akb_kb" ON "public"."agent_knowledge_binding" USING btree (
  "kb_id" "pg_catalog"."int8_ops" ASC NULLS LAST
);

-- ----------------------------
-- Uniques structure for table agent_knowledge_binding
-- ----------------------------
ALTER TABLE "public"."agent_knowledge_binding" ADD CONSTRAINT "agent_knowledge_binding_agent_id_kb_id_key" UNIQUE ("agent_id", "kb_id");

-- ----------------------------
-- Primary Key structure for table agent_knowledge_binding
-- ----------------------------
ALTER TABLE "public"."agent_knowledge_binding" ADD CONSTRAINT "agent_knowledge_binding_pkey" PRIMARY KEY ("id");

-- ----------------------------
-- Indexes structure for table ai_audit_log
-- ----------------------------
CREATE INDEX "idx_audit_action" ON "public"."ai_audit_log" USING btree (
  "action" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST,
  "created_at" "pg_catalog"."timestamp_ops" DESC NULLS FIRST
);
CREATE INDEX "idx_audit_created_at" ON "public"."ai_audit_log" USING btree (
  "created_at" "pg_catalog"."timestamp_ops" DESC NULLS FIRST
);
CREATE INDEX "idx_audit_target" ON "public"."ai_audit_log" USING btree (
  "target_type" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST,
  "target_id" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST
);
CREATE INDEX "idx_audit_tenant" ON "public"."ai_audit_log" USING btree (
  "tenant_id" "pg_catalog"."int8_ops" ASC NULLS LAST
);
CREATE INDEX "idx_audit_user" ON "public"."ai_audit_log" USING btree (
  "user_id" "pg_catalog"."int8_ops" ASC NULLS LAST
);

-- ----------------------------
-- Primary Key structure for table ai_audit_log
-- ----------------------------
ALTER TABLE "public"."ai_audit_log" ADD CONSTRAINT "ai_audit_log_pkey" PRIMARY KEY ("id");

-- ----------------------------
-- Indexes structure for table checkpoint_blobs
-- ----------------------------
CREATE INDEX "checkpoint_blobs_thread_id_idx" ON "public"."checkpoint_blobs" USING btree (
  "thread_id" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST
);

-- ----------------------------
-- Primary Key structure for table checkpoint_blobs
-- ----------------------------
ALTER TABLE "public"."checkpoint_blobs" ADD CONSTRAINT "checkpoint_blobs_pkey" PRIMARY KEY ("thread_id", "checkpoint_ns", "channel", "version");

-- ----------------------------
-- Primary Key structure for table checkpoint_migrations
-- ----------------------------
ALTER TABLE "public"."checkpoint_migrations" ADD CONSTRAINT "checkpoint_migrations_pkey" PRIMARY KEY ("v");

-- ----------------------------
-- Indexes structure for table checkpoint_writes
-- ----------------------------
CREATE INDEX "checkpoint_writes_thread_id_idx" ON "public"."checkpoint_writes" USING btree (
  "thread_id" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST
);

-- ----------------------------
-- Primary Key structure for table checkpoint_writes
-- ----------------------------
ALTER TABLE "public"."checkpoint_writes" ADD CONSTRAINT "checkpoint_writes_pkey" PRIMARY KEY ("thread_id", "checkpoint_ns", "checkpoint_id", "task_id", "idx");

-- ----------------------------
-- Indexes structure for table checkpoints
-- ----------------------------
CREATE INDEX "checkpoints_thread_id_idx" ON "public"."checkpoints" USING btree (
  "thread_id" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST
);

-- ----------------------------
-- Primary Key structure for table checkpoints
-- ----------------------------
ALTER TABLE "public"."checkpoints" ADD CONSTRAINT "checkpoints_pkey" PRIMARY KEY ("thread_id", "checkpoint_ns", "checkpoint_id");

-- ----------------------------
-- Indexes structure for table conversation
-- ----------------------------
CREATE INDEX "idx_conv_created_by" ON "public"."conversation" USING btree (
  "created_by" "pg_catalog"."int8_ops" ASC NULLS LAST
);
CREATE INDEX "idx_conv_updated_at" ON "public"."conversation" USING btree (
  "updated_at" "pg_catalog"."timestamp_ops" ASC NULLS LAST
);
CREATE INDEX "idx_conv_user" ON "public"."conversation" USING btree (
  "tenant_id" "pg_catalog"."int8_ops" ASC NULLS LAST,
  "user_id" "pg_catalog"."int8_ops" ASC NULLS LAST,
  "is_archived" "pg_catalog"."bool_ops" ASC NULLS LAST,
  "last_message_at" "pg_catalog"."timestamp_ops" DESC NULLS FIRST
);

-- ----------------------------
-- Primary Key structure for table conversation
-- ----------------------------
ALTER TABLE "public"."conversation" ADD CONSTRAINT "conversation_pkey" PRIMARY KEY ("id");

-- ----------------------------
-- Indexes structure for table conversation_message
-- ----------------------------
CREATE INDEX "idx_msg_conv" ON "public"."conversation_message" USING btree (
  "conversation_id" "pg_catalog"."int8_ops" ASC NULLS LAST,
  "created_at" "pg_catalog"."timestamp_ops" ASC NULLS LAST
);
CREATE INDEX "idx_msg_created_by" ON "public"."conversation_message" USING btree (
  "created_by" "pg_catalog"."int8_ops" ASC NULLS LAST
);
CREATE INDEX "idx_msg_file_ids" ON "public"."conversation_message" USING gin (
  "file_ids" "pg_catalog"."jsonb_ops"
);
CREATE INDEX "idx_msg_references" ON "public"."conversation_message" USING gin (
  "references" "pg_catalog"."jsonb_ops"
);
CREATE INDEX "idx_msg_tenant" ON "public"."conversation_message" USING btree (
  "tenant_id" "pg_catalog"."int8_ops" ASC NULLS LAST
);

-- ----------------------------
-- Primary Key structure for table conversation_message
-- ----------------------------
ALTER TABLE "public"."conversation_message" ADD CONSTRAINT "conversation_message_pkey" PRIMARY KEY ("id");

-- ----------------------------
-- Indexes structure for table goods_image_feature
-- ----------------------------
CREATE INDEX "idx_goods_image_feat_embedding" ON "public"."goods_image_feature" USING hnsw (
  "embedding" "public"."vector_cosine_ops"
);
CREATE INDEX "idx_goods_image_feat_item" ON "public"."goods_image_feature" USING btree (
  "item_id" "pg_catalog"."int8_ops" ASC NULLS LAST
);
CREATE INDEX "idx_goods_image_feat_node" ON "public"."goods_image_feature" USING btree (
  "node_id" "pg_catalog"."int8_ops" ASC NULLS LAST
);
CREATE INDEX "idx_goods_image_feat_order" ON "public"."goods_image_feature" USING btree (
  "order_id" "pg_catalog"."int8_ops" ASC NULLS LAST
);
CREATE INDEX "idx_goods_image_feat_oss_path" ON "public"."goods_image_feature" USING btree (
  "oss_path" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST
);
CREATE INDEX "idx_goods_image_feat_record" ON "public"."goods_image_feature" USING btree (
  "record_id" "pg_catalog"."int8_ops" ASC NULLS LAST
);
CREATE INDEX "idx_goods_image_feat_tenant" ON "public"."goods_image_feature" USING btree (
  "tenant_id" "pg_catalog"."int8_ops" ASC NULLS LAST,
  "is_deleted" "pg_catalog"."bool_ops" ASC NULLS LAST
) WHERE is_deleted = false;
CREATE INDEX "idx_goods_image_feat_tenant_type" ON "public"."goods_image_feature" USING btree (
  "tenant_id" "pg_catalog"."int8_ops" ASC NULLS LAST,
  "image_type" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST
) WHERE is_deleted = false;
CREATE INDEX "idx_goods_image_feat_type" ON "public"."goods_image_feature" USING btree (
  "image_type" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST
);

-- ----------------------------
-- Primary Key structure for table goods_image_feature
-- ----------------------------
ALTER TABLE "public"."goods_image_feature" ADD CONSTRAINT "goods_image_feature_pkey" PRIMARY KEY ("id");

-- ----------------------------
-- Indexes structure for table knowledge_base
-- ----------------------------
CREATE INDEX "idx_kb_created_by" ON "public"."knowledge_base" USING btree (
  "created_by" "pg_catalog"."int8_ops" ASC NULLS LAST
);
CREATE INDEX "idx_kb_scope" ON "public"."knowledge_base" USING btree (
  "scope_type" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST,
  "tenant_id" "pg_catalog"."int8_ops" ASC NULLS LAST
);
CREATE INDEX "idx_kb_status" ON "public"."knowledge_base" USING btree (
  "status" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST
);
CREATE INDEX "idx_kb_tenant" ON "public"."knowledge_base" USING btree (
  "tenant_id" "pg_catalog"."int8_ops" ASC NULLS LAST
);

-- ----------------------------
-- Primary Key structure for table knowledge_base
-- ----------------------------
ALTER TABLE "public"."knowledge_base" ADD CONSTRAINT "knowledge_base_pkey" PRIMARY KEY ("id");

-- ----------------------------
-- Indexes structure for table knowledge_base_tag
-- ----------------------------
CREATE INDEX "idx_kb_tag_kb" ON "public"."knowledge_base_tag" USING btree (
  "kb_id" "pg_catalog"."int8_ops" ASC NULLS LAST
);
CREATE INDEX "idx_kb_tag_name" ON "public"."knowledge_base_tag" USING btree (
  "tag_name" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST
);

-- ----------------------------
-- Primary Key structure for table knowledge_base_tag
-- ----------------------------
ALTER TABLE "public"."knowledge_base_tag" ADD CONSTRAINT "knowledge_base_tag_pkey" PRIMARY KEY ("id");

-- ----------------------------
-- Indexes structure for table knowledge_chunk
-- ----------------------------
CREATE INDEX "idx_chunk_content_trgm" ON "public"."knowledge_chunk" USING gin (
  "content" COLLATE "pg_catalog"."default" "public"."gin_trgm_ops"
);
CREATE INDEX "idx_chunk_created_by" ON "public"."knowledge_chunk" USING btree (
  "created_by" "pg_catalog"."int8_ops" ASC NULLS LAST
);
CREATE INDEX "idx_chunk_doc" ON "public"."knowledge_chunk" USING btree (
  "doc_id" "pg_catalog"."int8_ops" ASC NULLS LAST
);
CREATE INDEX "idx_chunk_embedding" ON "public"."knowledge_chunk" USING hnsw (
  "embedding" "public"."vector_cosine_ops"
);
CREATE INDEX "idx_chunk_kb" ON "public"."knowledge_chunk" USING btree (
  "kb_id" "pg_catalog"."int8_ops" ASC NULLS LAST,
  "tenant_id" "pg_catalog"."int8_ops" ASC NULLS LAST
);

-- ----------------------------
-- Primary Key structure for table knowledge_chunk
-- ----------------------------
ALTER TABLE "public"."knowledge_chunk" ADD CONSTRAINT "knowledge_chunk_pkey" PRIMARY KEY ("id");

-- ----------------------------
-- Indexes structure for table knowledge_document
-- ----------------------------
CREATE INDEX "idx_doc_created_by" ON "public"."knowledge_document" USING btree (
  "created_by" "pg_catalog"."int8_ops" ASC NULLS LAST
);
CREATE INDEX "idx_doc_kb" ON "public"."knowledge_document" USING btree (
  "kb_id" "pg_catalog"."int8_ops" ASC NULLS LAST
);
CREATE INDEX "idx_doc_parse_status" ON "public"."knowledge_document" USING btree (
  "parse_status" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST
);
CREATE INDEX "idx_doc_tenant" ON "public"."knowledge_document" USING btree (
  "tenant_id" "pg_catalog"."int8_ops" ASC NULLS LAST
);

-- ----------------------------
-- Primary Key structure for table knowledge_document
-- ----------------------------
ALTER TABLE "public"."knowledge_document" ADD CONSTRAINT "knowledge_document_pkey" PRIMARY KEY ("id");

-- ----------------------------
-- Indexes structure for table temp_document
-- ----------------------------
CREATE INDEX "idx_tmp_doc_conv" ON "public"."temp_document" USING btree (
  "conversation_id" "pg_catalog"."int8_ops" ASC NULLS LAST
);
CREATE INDEX "idx_tmp_doc_expires" ON "public"."temp_document" USING btree (
  "expires_at" "pg_catalog"."timestamp_ops" ASC NULLS LAST
);
CREATE INDEX "idx_tmp_doc_file" ON "public"."temp_document" USING btree (
  "file_id" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST
);
CREATE INDEX "idx_tmp_doc_user" ON "public"."temp_document" USING btree (
  "tenant_id" "pg_catalog"."int8_ops" ASC NULLS LAST,
  "user_id" "pg_catalog"."int8_ops" ASC NULLS LAST
);

-- ----------------------------
-- Uniques structure for table temp_document
-- ----------------------------
ALTER TABLE "public"."temp_document" ADD CONSTRAINT "temp_document_file_id_key" UNIQUE ("file_id");

-- ----------------------------
-- Primary Key structure for table temp_document
-- ----------------------------
ALTER TABLE "public"."temp_document" ADD CONSTRAINT "temp_document_pkey" PRIMARY KEY ("id");

-- ----------------------------
-- Indexes structure for table user_long_term_memory
-- ----------------------------
CREATE INDEX "idx_ltm_embedding" ON "public"."user_long_term_memory" USING hnsw (
  "embedding" "public"."vector_cosine_ops"
);
CREATE INDEX "idx_ltm_importance" ON "public"."user_long_term_memory" USING btree (
  "importance" "pg_catalog"."float8_ops" DESC NULLS FIRST,
  "access_count" "pg_catalog"."int4_ops" DESC NULLS FIRST
);
CREATE INDEX "idx_ltm_user" ON "public"."user_long_term_memory" USING btree (
  "tenant_id" "pg_catalog"."int8_ops" ASC NULLS LAST,
  "user_id" "pg_catalog"."int8_ops" ASC NULLS LAST
);

-- ----------------------------
-- Primary Key structure for table user_long_term_memory
-- ----------------------------
ALTER TABLE "public"."user_long_term_memory" ADD CONSTRAINT "user_long_term_memory_pkey" PRIMARY KEY ("id");

-- ----------------------------
-- Foreign Keys structure for table agent_knowledge_binding
-- ----------------------------
ALTER TABLE "public"."agent_knowledge_binding" ADD CONSTRAINT "agent_knowledge_binding_kb_id_fkey" FOREIGN KEY ("kb_id") REFERENCES "public"."knowledge_base" ("id") ON DELETE CASCADE ON UPDATE NO ACTION;

-- ----------------------------
-- Foreign Keys structure for table conversation_message
-- ----------------------------
ALTER TABLE "public"."conversation_message" ADD CONSTRAINT "conversation_message_conversation_id_fkey" FOREIGN KEY ("conversation_id") REFERENCES "public"."conversation" ("id") ON DELETE CASCADE ON UPDATE NO ACTION;

-- ----------------------------
-- Foreign Keys structure for table knowledge_base_tag
-- ----------------------------
ALTER TABLE "public"."knowledge_base_tag" ADD CONSTRAINT "knowledge_base_tag_kb_id_fkey" FOREIGN KEY ("kb_id") REFERENCES "public"."knowledge_base" ("id") ON DELETE CASCADE ON UPDATE NO ACTION;

-- ----------------------------
-- Foreign Keys structure for table knowledge_chunk
-- ----------------------------
ALTER TABLE "public"."knowledge_chunk" ADD CONSTRAINT "knowledge_chunk_doc_id_fkey" FOREIGN KEY ("doc_id") REFERENCES "public"."knowledge_document" ("id") ON DELETE CASCADE ON UPDATE NO ACTION;

-- ----------------------------
-- Foreign Keys structure for table knowledge_document
-- ----------------------------
ALTER TABLE "public"."knowledge_document" ADD CONSTRAINT "knowledge_document_kb_id_fkey" FOREIGN KEY ("kb_id") REFERENCES "public"."knowledge_base" ("id") ON DELETE CASCADE ON UPDATE NO ACTION;
