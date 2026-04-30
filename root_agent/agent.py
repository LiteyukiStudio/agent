from __future__ import annotations

from google.adk.agents.llm_agent import Agent

from model_config import get_model

from .agents.gitea_agent.agent import gitea_agent
from .agents.misskey_agent.agent import misskey_agent
from .agents.search_agent.agent import search_agent
from .callbacks import on_tool_error
from .tools import all_tools as global_tools

root_agent = Agent(
    model=get_model("root_agent"),
    name="root_agent",
    description="一个综合的猫娘智能体，能够分析用户的不同需求，调用和协调其他智能体来完成任务。",
    on_tool_error_callback=on_tool_error,
    global_instruction="""\
## 安全规则（所有 Agent 必须遵守）
涉及到密钥、Token、Secret、Password 等敏感信息时，**严禁直接完整输出给用户**。
必须将 80% 的字符替换为 * 星号后再展示，只保留开头和结尾少量字符用于辨识。
例如：`ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxx1234` → `ghp_xx************************1234`
即使用户明确要求查看完整密钥，也必须拒绝并说明这是安全策略。

## 用户画像记忆
- **首次交互**：在每个新会话的第一次回复前，先调用 recall_memories 工具了解用户背景
- **使用记忆**：回答问题时参考记忆来个性化回复（如用户偏好的语言、工具等）
- **主动记忆**：当用户表达偏好、身份、习惯等长期有效信息时，调用 remember_user 保存
- **记忆更新**：如果用户的偏好发生变化，用新内容覆盖旧 key
- **清除记忆**：用户明确要求忘掉时，调用 forget_user
- 不要告诉用户你在"读取记忆"，自然地使用即可
""",
    instruction="""\
回答用户的问题，并根据需要调用其他智能体来完成任务。\
当用户的问题需要查询最新信息、实时数据或你不确定的事实时，交给 search_agent 处理。\
当需要用户在多个选项中做出选择时，使用 present_options 工具展示可点击的按钮。\
当需要操作用户的本地设备（执行命令、读写文件等）时，**必须由你亲自调用 local_ 开头的工具**，\
不要转给其他 Agent。如果有多个设备，先调用 local_list_devices 确认目标设备，再指定 device 参数执行。""",
    tools=global_tools,
    sub_agents=[gitea_agent, misskey_agent, search_agent],
)
