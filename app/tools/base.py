"""工具基类"""
from abc import ABC, abstractmethod
from typing import Any, Optional
from app.models.schemas import UserContext


class BaseTool(ABC):
    """Agent工具基类"""

    name: str = ""
    description: str = ""

    # 工具执行所需权限（子类覆盖）
    required_permission: Optional[str] = None

    @abstractmethod
    async def execute(self, **kwargs) -> Any:
        """执行工具，返回结果"""
        raise NotImplementedError

    def check_permission(self, user_context: Optional[UserContext] = None) -> bool:
        """检查用户是否有执行该工具的权限"""
        if self.required_permission is None:
            return True  # 无权限要求的工具（兼容）
        if user_context is None:
            return False
        from app.services.permissions import has_perm
        return has_perm(user_context, self.required_permission)

    def to_dict(self) -> dict:
        """转为字典格式供LLM理解"""
        return {
            "name": self.name,
            "description": self.description
        }
