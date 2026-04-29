"""Misskey Agent 工具汇总。"""

from .drive import all_tools as drive_tools
from .note import all_tools as note_tools
from .notification import all_tools as notification_tools
from .reaction import all_tools as reaction_tools
from .setup import all_tools as setup_tools
from .user import all_tools as user_tools

all_tools: list = [
    *setup_tools,
    *note_tools,
    *user_tools,
    *reaction_tools,
    *notification_tools,
    *drive_tools,
]
