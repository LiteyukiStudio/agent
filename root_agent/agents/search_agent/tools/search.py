"""网页搜索工具：使用 DuckDuckGo HTML 搜索。"""

from __future__ import annotations

import logging
import re
from html import unescape
from urllib.parse import unquote

import httpx

logger = logging.getLogger(__name__)

_TIMEOUT = 10.0
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}

# DuckDuckGo HTML 版搜索结果解析
_RESULT_PATTERN = re.compile(
    r'<a[^>]+rel="nofollow"[^>]+href="([^"]+)"[^>]*class="[^"]*result__a[^"]*"[^>]*>(.*?)</a>.*?'
    r'<a[^>]+class="[^"]*result__snippet[^"]*"[^>]*>(.*?)</a>',
    re.DOTALL,
)

# 备用：更宽松的模式
_RESULT_PATTERN_ALT = re.compile(
    r'class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>.*?'
    r'class="result__snippet"[^>]*>(.*?)</a>',
    re.DOTALL,
)

# DuckDuckGo Lite 版解析
_LITE_LINK_PATTERN = re.compile(
    r'<a[^>]+class="result-link"[^>]*href="([^"]+)"[^>]*>(.*?)</a>',
    re.DOTALL,
)
_LITE_SNIPPET_PATTERN = re.compile(
    r'<td[^>]*class="result-snippet"[^>]*>(.*?)</td>',
    re.DOTALL,
)


def _strip_tags(html: str) -> str:
    """去除 HTML 标签，保留纯文本。"""
    text = re.sub(r"<[^>]+>", "", html)
    return unescape(text).strip()


def _extract_url(raw: str) -> str:
    """从 DuckDuckGo 重定向链接中提取真实 URL。"""
    # //duckduckgo.com/l/?uddg=https%3A%2F%2F... → 真实 URL
    if "uddg=" in raw:
        match = re.search(r"uddg=([^&]+)", raw)
        if match:
            return unquote(match.group(1))
    return raw


def _parse_html_results(html: str) -> list[dict]:
    """从 DuckDuckGo HTML 搜索页面解析结果。"""
    results = []

    # 尝试 HTML 版解析
    for pattern in [_RESULT_PATTERN, _RESULT_PATTERN_ALT]:
        for m in pattern.finditer(html):
            url = _extract_url(m.group(1))
            title = _strip_tags(m.group(2))
            snippet = _strip_tags(m.group(3))
            if url and title:
                results.append({"title": title, "url": url, "snippet": snippet})
        if results:
            return results

    # 尝试 Lite 版解析
    links = _LITE_LINK_PATTERN.findall(html)
    snippets = _LITE_SNIPPET_PATTERN.findall(html)
    for i, (url, title_html) in enumerate(links):
        title = _strip_tags(title_html)
        url = _extract_url(url)
        snippet = _strip_tags(snippets[i]) if i < len(snippets) else ""
        if url and title and not url.startswith("//duckduckgo.com"):
            results.append({"title": title, "url": url, "snippet": snippet})

    return results


def web_search(query: str, max_results: int = 10) -> list[dict]:
    """搜索互联网，返回相关网页的标题、链接和摘要。

    使用 DuckDuckGo 搜索引擎，无需 API 密钥。

    Args:
        query: 搜索关键词，支持自然语言。
        max_results: 最大返回结果数，默认 10，最大 20。

    Returns:
        搜索结果列表，每项包含 title、url、snippet。
    """
    max_results = min(max_results, 20)

    # 优先尝试 DuckDuckGo HTML 版
    for search_url in [
        f"https://html.duckduckgo.com/html/?q={query}",
        f"https://lite.duckduckgo.com/lite/?q={query}",
    ]:
        try:
            with httpx.Client(timeout=_TIMEOUT, headers=_HEADERS, follow_redirects=True) as client:
                resp = client.get(search_url)
                resp.raise_for_status()
                results = _parse_html_results(resp.text)
                if results:
                    return results[:max_results]
        except Exception as e:
            logger.warning("Search failed for %s: %s", search_url, e)
            continue

    return [{"error": "搜索未返回结果，请尝试更换关键词"}]


def news_search(query: str, max_results: int = 10) -> list[dict]:
    """搜索最新新闻，返回新闻标题、链接和摘要。

    Args:
        query: 搜索关键词。
        max_results: 最大返回结果数，默认 10，最大 20。

    Returns:
        新闻结果列表，每项包含 title、url、snippet。
    """
    # DuckDuckGo 新闻搜索通过添加 "news" 到查询实现
    return web_search(f"{query} news", max_results=max_results)


all_tools = [web_search, news_search]
