"""AI 自动生成会话标题。

根据用户首条消息和 AI 首条回复，生成简短的会话标题。
自动脱敏：不会在标题中包含 Token、密码等敏感信息。
"""

from __future__ import annotations

import logging

import litellm

from model_config import _is_gemini, _resolve_env

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """\
你是一个会话标题生成器。根据用户的问题和AI的回答，生成一个简短的中文标题（不超过20字）。

规则：
1. 标题应概括对话的核心主题
2. **严禁包含任何敏感信息**：Token、密码、密钥、API Key、邮箱、手机号等一律不得出现在标题中
3. 如果用户在配置凭据，标题应写为"配置XX服务"而非暴露具体凭据内容
4. 只输出标题文本，不要加引号、标点符号或其他格式
5. 保持简洁，像聊天软件的对话标题一样"""


async def generate_title(user_message: str, assistant_reply: str) -> str | None:
    """用 LLM 生成会话标题。

    Args:
        user_message: 用户的首条消息。
        assistant_reply: AI 的首条回复（截取前 200 字）。

    Returns:
        生成的标题字符串，失败返回 None。
    """
    # 截取避免 prompt 过长
    user_text = user_message[:200]
    reply_text = assistant_reply[:200]

    prompt = f"用户: {user_text}\nAI: {reply_text}"

    try:
        # 用全局模型配置（与 root_agent 一致）
        model_name = _resolve_env("ROOT_AGENT", "MODEL") or "gemini-2.5-flash"
        token = _resolve_env("ROOT_AGENT", "TOKEN")
        api_url = _resolve_env("ROOT_AGENT", "API")

        if _is_gemini(model_name):
            # 用 litellm 统一调用 Gemini
            model_name = f"gemini/{model_name}"

        kwargs: dict = {
            "model": model_name,
            "messages": [
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            "max_tokens": 100,
            "temperature": 0.3,
        }
        if token:
            kwargs["api_key"] = token
        if api_url:
            kwargs["api_base"] = api_url

        response = await litellm.acompletion(**kwargs)
        title = response.choices[0].message.content.strip()
        # 去掉可能的引号和多余标点
        for ch in '"\'""「」《》':
            if title.startswith(ch):
                title = title[1:]
            if title.endswith(ch):
                title = title[:-1]
        # 限制长度
        if len(title) > 30:
            title = title[:27] + "..."
        return title or None

    except Exception:
        logger.exception("自动标题生成失败 (model=%s, api_base=%s)", model_name, api_url)
        return None
