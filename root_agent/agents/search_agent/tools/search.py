"""网页搜索工具：基于 ddgs 库的多引擎搜索。"""

from __future__ import annotations

import logging
import os

from ddgs import DDGS

logger = logging.getLogger(__name__)

_PROXY = os.environ.get("SEARCH_PROXY") or os.environ.get("HTTPS_PROXY") or os.environ.get("HTTP_PROXY") or None
_TIMEOUT = 15


def web_search(query: str, max_results: int = 10) -> list[dict]:
    """搜索互联网，返回相关网页的标题、链接和摘要。

    使用多个搜索引擎（自动选择最佳后端）。

    Args:
        query: 搜索关键词，支持自然语言。
        max_results: 最大返回结果数，默认 10，最大 20。

    Returns:
        搜索结果列表，每项包含 title、url、snippet。
    """
    max_results = min(max_results, 20)

    try:
        ddgs = DDGS(proxy=_PROXY, timeout=_TIMEOUT)
        raw_results = ddgs.text(query, max_results=max_results, backend="auto")

        if not raw_results:
            return [{"error": "搜索未返回结果，请尝试更换关键词。"}]

        results = [
            {
                "title": r.get("title", ""),
                "url": r.get("href", ""),
                "snippet": r.get("body", ""),
            }
            for r in raw_results
        ]
        logger.info("Search '%s': %d results", query, len(results))
        return results

    except Exception as e:
        logger.warning("Search failed for '%s': %s", query, e)
        return [{"error": f"搜索失败: {type(e).__name__}: {e}"}]


def news_search(query: str, max_results: int = 10) -> list[dict]:
    """搜索最新新闻，返回新闻标题、链接和摘要。

    Args:
        query: 搜索关键词。
        max_results: 最大返回结果数，默认 10，最大 20。

    Returns:
        新闻结果列表，每项包含 title、url、snippet、date、source。
    """
    max_results = min(max_results, 20)

    try:
        ddgs = DDGS(proxy=_PROXY, timeout=_TIMEOUT)
        raw_results = ddgs.news(query, max_results=max_results)

        if not raw_results:
            return [{"error": "未找到相关新闻。"}]

        results = [
            {
                "title": r.get("title", ""),
                "url": r.get("url", ""),
                "snippet": r.get("body", ""),
                "date": r.get("date", ""),
                "source": r.get("source", ""),
            }
            for r in raw_results
        ]
        logger.info("News search '%s': %d results", query, len(results))
        return results

    except Exception as e:
        logger.warning("News search failed for '%s': %s", query, e)
        return [{"error": f"新闻搜索失败: {type(e).__name__}: {e}"}]


all_tools = [web_search, news_search]
