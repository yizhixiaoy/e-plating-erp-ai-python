"""长期记忆管理服务"""
from app.config import settings


class MemoryService:
    """用户长期记忆管理"""

    def __init__(self, db_pool=None):
        self.db_pool = db_pool
        self.enabled = settings.MEM0_ENABLED

    async def add_memory(
        self,
        tenant_id: int,
        user_id: int,
        content: str,
        memory_type: str = "fact",
        importance: float = 0.5
    ):
        """添加记忆"""
        if not self.enabled or not self.db_pool:
            return

        async with self.db_pool.acquire() as conn:
            await conn.execute(
                """INSERT INTO user_long_term_memory
                   (tenant_id, user_id, memory_type, content, importance, created_by, created_at, updated_at)
                   VALUES ($1, $2, $3, $4, $5, $2, NOW(), NOW())
                   ON CONFLICT DO NOTHING""",
                tenant_id, user_id, memory_type, content, importance
            )

    async def retrieve_memories(
        self,
        tenant_id: int,
        user_id: int,
        limit: int = 5
    ) -> list[dict]:
        """检索用户记忆"""
        if not self.enabled or not self.db_pool:
            return []

        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(
                """SELECT id, content, memory_type, importance, access_count
                   FROM user_long_term_memory
                   WHERE tenant_id = $1 AND user_id = $2
                   ORDER BY importance DESC, access_count DESC
                   LIMIT $3""",
                tenant_id, user_id, limit
            )

            # 更新访问计数
            if rows:
                ids = [row["id"] for row in rows]
                await conn.execute(
                    "UPDATE user_long_term_memory SET access_count = access_count + 1, last_accessed_at = NOW() WHERE id = ANY($1::bigint[])",
                    ids
                )

            return [dict(row) for row in rows]

    async def summarize_memories(self, tenant_id: int, user_id: int) -> str:
        """汇总用户记忆为摘要文本（用于System Prompt）"""
        memories = await self.retrieve_memories(tenant_id, user_id, limit=3)
        if not memories:
            return ""

        items = [
            f"- [{m['memory_type']}] {m['content']}"
            for m in memories
        ]
        return "用户信息摘要：\n" + "\n".join(items)
