-- V3: 为 conversation_message 表添加 thinking_steps 和 duration_sec 列

ALTER TABLE conversation_message
ADD COLUMN IF NOT EXISTS thinking_steps JSONB DEFAULT '[]';

COMMENT ON COLUMN conversation_message.thinking_steps IS 'AI思考步骤JSON数组，包含thinking/tool_start/tool_end类型，示例如 [{"type":"thinking","content":"分析中","timestamp":0.0}]';

ALTER TABLE conversation_message
ADD COLUMN IF NOT EXISTS duration_sec DOUBLE PRECISION;

COMMENT ON COLUMN conversation_message.duration_sec IS 'AI回复耗时（秒），仅role=assistant时有值';
