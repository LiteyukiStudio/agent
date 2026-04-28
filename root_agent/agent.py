from google.adk.agents.llm_agent import Agent

from gitea_agent.agent import gitea_agent
from model_config import get_model

root_agent = Agent(
    model=get_model("root_agent"),
    name="root_agent",
    description="一个综合的智能体，能够分析用户的不同需求，调用和协调其他智能体来完成任务。",
    instruction="回答用户的问题，并根据需要调用其他智能体来完成任务。",
    sub_agents=[gitea_agent],
)
