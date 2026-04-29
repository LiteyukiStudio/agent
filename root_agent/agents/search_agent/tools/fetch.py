"""网页内容提取工具：获取网页并转为干净的文本/Markdown。"""

from __future__ import annotations

import logging

import httpx
import trafilatura

logger = logging.getLogger(__name__)

_TIMEOUT = 15.0
_MAX_CONTENT_LENGTH = 50000  # 截断过长内容，避免占满 LLM 上下文
_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; LiteyukiBot/1.0; +https://liteyuki.org)",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}


def _extract(html: str, url: str) -> str:
    """从 HTML 提取正文，优先 Markdown 格式。"""
    # trafilatura 提取：输出 Markdown，保留链接和结构
    text = trafilatura.extract(
        html,
        url=url,
        output_format="txt",
        include_links=True,
        include_tables=True,
        include_comments=False,
        favor_recall=True,
    )
    if text:
        return text[:_MAX_CONTENT_LENGTH]
    return "(未能提取到有效内容)"


def fetch_page(url: str) -> dict:
    """获取单个网页的正文内容。

    自动去除 HTML 标签、广告、导航栏等干扰，只保留文章主体文本。

    Args:
        url: 要获取的网页 URL。

    Returns:
        包含 url、title、content 的字典。content 为提取的纯文本。
    """
    try:
        with httpx.Client(timeout=_TIMEOUT, headers=_HEADERS, follow_redirects=True) as client:
            resp = client.get(url)
            resp.raise_for_status()
            html = resp.text
    except Exception as e:
        return {"url": url, "error": f"请求失败: {e}"}

    content = _extract(html, url)

    # 尝试提取标题
    title = ""
    meta = trafilatura.extract_metadata(html, default_url=url)
    if meta and meta.title:
        title = meta.title

    return {
        "url": url,
        "title": title,
        "content": content,
    }


def fetch_pages(urls: list[str]) -> list[dict]:
    """批量获取多个网页的正文内容。

    适合搜索后批量提取多个结果页面的内容。每个 URL 独立请求，单个失败不影响其他。

    Args:
        urls: URL 列表，最多 5 个。

    Returns:
        结果列表，每项包含 url、title、content（或 error）。
    """
    urls = urls[:5]  # 限制最多 5 个
    results = []
    for url in urls:
        results.append(fetch_page(url))
    return results


all_tools = [fetch_page, fetch_pages]
