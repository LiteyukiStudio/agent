"""联网搜索和网页内容提取工具。"""

from .fetch import all_tools as fetch_tools
from .search import all_tools as search_tools

all_tools: list = [
    *search_tools,
    *fetch_tools,
]
