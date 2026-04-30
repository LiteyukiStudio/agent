"""用户信息工具：获取当前登录用户的基本信息。"""

from __future__ import annotations

from google.adk.tools import ToolContext


async def get_current_user_info(tool_context: ToolContext) -> str:
    """获取当前登录用户的基本信息（用户名、邮箱、角色等）。

    Returns:
        用户信息（JSON 格式），包含 username、email、role 等字段。
    """
    from sqlalchemy import select

    from server.database import async_session_factory
    from server.models.user import User

    user_id = tool_context.state.get("__user_id")
    if not user_id:
        return "无法获取用户信息：未找到用户标识。"

    async with async_session_factory() as db:
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()

    if not user:
        return "用户不存在。"

    import json

    return json.dumps(
        {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "avatar_url": user.avatar_url,
            "role": user.role,
        },
        ensure_ascii=False,
    )


all_tools = [get_current_user_info]
