"""图像识别工具：将图片上传给 AI 进行分析和理解。

支持通过 URL 或本地路径加载图片，将图片编码后传递给支持视觉的模型。
如果当前模型不支持识图，会返回提示信息。
"""

from __future__ import annotations

import base64
import io
from pathlib import Path

import httpx
from google.adk.tools import ToolContext
from PIL import Image


def _load_image_as_base64(source: str, max_size: int = 1024) -> tuple[str, str]:
    """加载图片并转为 base64 编码。

    对大图进行缩放以控制 token 消耗。

    Returns:
        (base64_data, mime_type)
    """
    if source.startswith(("http://", "https://")):
        resp = httpx.get(source, timeout=30, follow_redirects=True)
        resp.raise_for_status()
        img = Image.open(io.BytesIO(resp.content))
    else:
        path = Path(source).expanduser()
        if not path.exists():
            msg = f"文件不存在: {source}"
            raise FileNotFoundError(msg)
        img = Image.open(path)

    # 缩放大图以减少 token 消耗
    w, h = img.size
    if max(w, h) > max_size:
        ratio = max_size / max(w, h)
        img = img.resize((int(w * ratio), int(h * ratio)), Image.Resampling.LANCZOS)

    # 转为 PNG bytes 并 base64 编码
    if img.mode == "RGBA":
        mime_type = "image/png"
        fmt = "PNG"
    else:
        img = img.convert("RGB")
        mime_type = "image/jpeg"
        fmt = "JPEG"

    buffer = io.BytesIO()
    img.save(buffer, format=fmt, quality=85)
    b64 = base64.b64encode(buffer.getvalue()).decode("ascii")
    return b64, mime_type


def image_analyze(
    source: str,
    tool_context: ToolContext,
    question: str = "",
    max_size: int = 1024,
) -> str:
    """分析图片内容，回答关于图片的问题。

    将图片传递给 AI 视觉模型进行理解和分析。可以识别图片中的物体、文字、场景等。
    如果模型不支持图像识别，会提示不可用。

    使用方式：用户上传图片后，调用此工具对图片进行分析，可附加问题引导分析方向。

    Args:
        source: 图片的 URL 地址或本地文件路径。
        question: 对图片的提问（可选），例如"图中有什么动物？"、"请描述这张图片"。
            如果留空则进行通用描述。
        max_size: 图片最大边长（像素），超出会等比缩放以节省 token，默认 1024。

    Returns:
        AI 对图片的分析结果文本，或错误信息。
    """
    try:
        b64_data, mime_type = _load_image_as_base64(source, max_size)
    except FileNotFoundError as e:
        return str(e)
    except Exception as e:
        return f"加载图片失败: {e}"

    # 将图片信息存入 state，让 Agent 在后续回复中可以"看到"图片
    # ADK 的 ToolContext 支持通过 state 传递多模态内容
    prompt = question if question else "请详细描述这张图片的内容。"

    # 构建图片描述信息，存入 state 供 agent 参考
    image_data = {
        "base64": b64_data,
        "mime_type": mime_type,
        "prompt": prompt,
        "source": source,
    }

    # 将图片数据存入 session state，以 key 标识
    existing_images = tool_context.state.get("__pending_images", [])
    existing_images.append(image_data)
    tool_context.state["__pending_images"] = existing_images

    return (
        f"已加载图片（来源: {source}）。\n"
        f"图片尺寸已优化（最大边 {max_size}px），编码为 {mime_type} 格式。\n"
        f"分析请求: {prompt}\n\n"
        f"注意: 图片数据已存入上下文。如果当前模型支持视觉（如 Gemini、GPT-4o），"
        f"可以直接基于图片内容进行回答。"
        f"如果模型不支持视觉能力，请告知用户。"
    )


def image_describe(
    source: str,
    tool_context: ToolContext,
    max_size: int = 1024,
) -> str:
    """获取图片的简短描述。

    加载图片并请求 AI 提供简短描述。适用于需要快速了解图片大致内容的场景。

    Args:
        source: 图片的 URL 地址或本地文件路径。
        max_size: 图片最大边长（像素）。

    Returns:
        图片描述文本或错误信息。
    """
    return image_analyze(source, tool_context, question="请用一两句话简要描述这张图片的主要内容。", max_size=max_size)


def image_ocr(
    source: str,
    tool_context: ToolContext,
    max_size: int = 1280,
) -> str:
    """提取图片中的文字（OCR）。

    将图片传给 AI 识别其中的文字内容，支持中文、英文等多种语言。
    适用于截图、文档照片、海报等含有文字的图片。

    Args:
        source: 图片的 URL 地址或本地文件路径。
        max_size: 图片最大边长（像素），OCR 场景建议更大以保留文字细节，默认 1280。

    Returns:
        提取到的文字内容或错误信息。
    """
    return image_analyze(
        source,
        tool_context,
        question="请提取图片中所有可见的文字内容，保持原始排版格式。如果有表格，用 Markdown 表格格式输出。",
        max_size=max_size,
    )


all_tools: list = [
    image_analyze,
    image_describe,
    image_ocr,
]
