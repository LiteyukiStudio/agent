"""全局工具：为所有 Agent 提供用户交互、记忆和本地操作能力。"""

from .interaction import present_options
from .local_agent import all_tools as local_agent_tools
from .memory import all_tools as memory_tools

all_tools: list = [present_options, *memory_tools, *local_agent_tools]
