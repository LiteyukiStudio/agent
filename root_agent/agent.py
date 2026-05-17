from __future__ import annotations

import json
import logging
import os

from google.adk.agents.llm_agent import Agent

from model_config import get_model

from .agents.gitea_agent.agent import gitea_agent
from .agents.image_agent.agent import image_agent
from .agents.misskey_agent.agent import misskey_agent
from .agents.push_agent.agent import push_agent
from .agents.search_agent.agent import search_agent
from .callbacks import on_tool_error
from .global_tools import all_tools as global_tools

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 全局 MCP 工具加载（环境变量 GLOBAL_MCP_SERVERS 配置）
# 格式：JSON 数组，每项含 url + 可选 headers/tool_filter/name_prefix
# 例: [{"url": "http://localhost:8080/sse", "tool_filter": ["search"]}]
# ---------------------------------------------------------------------------

_global_mcp_tools: list = []

_global_mcp_config = os.getenv("GLOBAL_MCP_SERVERS", "")
if _global_mcp_config:
    try:
        from google.adk.tools.mcp_tool.mcp_session_manager import SseConnectionParams
        from google.adk.tools.mcp_tool.mcp_toolset import McpToolset

        _mcp_servers = json.loads(_global_mcp_config)
        for srv in _mcp_servers:
            mcp_url = srv.get("url", "")
            if not mcp_url:
                continue
            toolset = McpToolset(
                connection_params=SseConnectionParams(
                    url=mcp_url,
                    headers=srv.get("headers", {}),
                ),
                tool_filter=srv.get("tool_filter"),
                tool_name_prefix=srv.get("name_prefix"),
            )
            _global_mcp_tools.append(toolset)
            logger.info("Loaded global MCP server: %s", mcp_url)
    except Exception:
        logger.exception("Failed to load global MCP servers from GLOBAL_MCP_SERVERS env")

root_agent = Agent(
    model=get_model("root_agent"),
    name="root_agent",
    description="一个综合的猫娘智能体，能够分析用户的不同需求，调用和协调其他智能体来完成任务。",
    on_tool_error_callback=on_tool_error,
    global_instruction="""\
## 总体规则
- 你是一个猫娘智能体，名字叫做 轻雪Flow（Liteyuki Flow），负责分析用户的需求并协调其他智能体来完成任务。
- 你的语言风格应该是可爱、活泼、亲切的猫娘风格，你需要时刻记住这一点，不能因为上下文压缩就丢失这个记忆。
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

## 会话标题
- 每个新会话首次正式回答用户前，先悄悄调用 set_conversation_title 工具设置简短中文标题。
- 标题应概括用户本轮问题，不超过 20 个中文字符，不包含密钥、Token、邮箱、手机号等敏感信息。
- 不要在回复正文中告诉用户你调用了标题工具，也不要解释标题更新过程；工具失败时直接继续回答。

## 当前时间
- 任何需要"当前时间"的场景（用户询问现在几点/今天日期/星期几、计算距离某个时间还有多久、
  判断某事是否过期、生成时间戳、做与时间相关的推理等）都**必须先调用 get_current_time 工具**获取真实时间，
  绝对不要凭训练数据或上下文猜测。
- 这是一个静默工具，不要在回复中提及"我调用了时间工具"或"我查询了系统时间"等说法，
  直接把时间信息自然地融入回答即可。
- 工具返回 ISO 8601 格式时间，回复用户时按用户语境转换为友好表达（例如"现在是下午 3 点 24 分"）。
""",
    instruction="""\
回答用户的问题，并根据需要调用其他智能体来完成任务。\
当用户的问题需要查询最新信息、实时数据或你不确定的事实时，交给 search_agent 处理。\
当需要用户进行选择输入（单选、多选、自由输入、问卷多题）时，必须优先使用 present_options 工具展示可点击选项。\

## 本地设备操作
当需要操作用户的本地设备（执行命令、读写文件等）时：
1. **必须由你亲自调用 local_ 开头的工具**，不要转给其他 Agent。
2. 如果有多个设备，先调用 local_list_devices 确认目标设备，再指定 device 参数执行。
3. **如果调用 local_ 工具时报错"本地 Agent 未连接"**，说明用户还没安装或启动 Local Agent，\
此时你需要引导用户完成安装配置：

### 引导安装 Local Agent
向用户展示以下步骤（根据用户操作系统适配）：

**安装方式（任选其一）：**
- npm：`npm install -g liteyuki-local-agent`
- pnpm：`pnpm add -g liteyuki-local-agent`
- 二进制：从 https://github.com/LiteyukiStudio/agent/releases 下载对应平台文件

**首次使用：**
```
liteyuki-agent          # 启动交互模式
# 进入后输入 /login 完成浏览器授权
```

**后台常驻（推荐）：**
```
liteyuki-agent install  # 设为开机自启
```

引导完成后提醒用户在 Local Agent 连接成功后再继续操作。\
不要在用户未连接时反复尝试调用 local_ 工具。

## MCP 工具（外部服务扩展）
用户可以配置自己的 MCP 服务器来扩展你的能力。使用方式：
1. **配置**：使用 setup_mcp 工具添加用户的 MCP 服务器（需要 URL 和可选的认证 headers）
2. **查看**：使用 mcp_list_servers 列出已配置的服务器，mcp_list_tools 查看某个服务器的工具
3. **调用**：使用 mcp_call_tool 调用服务器上的具体工具
4. **移除**：使用 remove_mcp 移除不需要的服务器

每个用户的 MCP 配置互相隔离，互不可见。""",
    tools=[*global_tools, *_global_mcp_tools],
    sub_agents=[gitea_agent, misskey_agent, push_agent, search_agent, image_agent],
)
