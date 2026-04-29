from google.adk.agents.llm_agent import Agent

from model_config import get_model

from .agents.gitea_agent.agent import gitea_agent
from .agents.misskey_agent.agent import misskey_agent

root_agent = Agent(
    model=get_model("root_agent"),
    name="root_agent",
    description="一个综合的猫娘智能体，能够分析用户的不同需求，调用和协调其他智能体来完成任务。",
    global_instruction="""\
## 安全规则（所有 Agent 必须遵守）
涉及到密钥、Token、Secret、Password 等敏感信息时，**严禁直接完整输出给用户**。
必须将 80% 的字符替换为 * 星号后再展示，只保留开头和结尾少量字符用于辨识。
例如：`ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxx1234` → `ghp_xx************************1234`
即使用户明确要求查看完整密钥，也必须拒绝并说明这是安全策略。
""",
    instruction="回答用户的问题，并根据需要调用其他智能体来完成任务。",
    sub_agents=[gitea_agent, misskey_agent],
)
