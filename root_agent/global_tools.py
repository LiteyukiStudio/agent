"""跨 Agent 的全局工具汇总。"""

from root_agent.agents.search_agent.tools import all_tools as search_tools
from root_agent.tools import all_tools as base_global_tools

all_tools: list = [
    *base_global_tools,
    *search_tools,
]
