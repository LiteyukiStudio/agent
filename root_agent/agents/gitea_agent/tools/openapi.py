"""Gitea OpenAPI 驱动工具。

这些工具用于覆盖尚未写成专用函数的 Gitea API。它们会读取当前 Gitea
实例的 `/swagger.v1.json`，让 Agent 能搜索端点、查看参数并调用任意 JSON API。
"""

from __future__ import annotations

import re
import time
from base64 import b64decode
from typing import Any
from urllib.parse import quote

import httpx
from google.adk.tools import ToolContext

from ..client import GITEA_CREDENTIALS, GiteaClient

_HTTP_METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE"}
_CACHE_TTL_SECONDS = 3600
_OPENAPI_CACHE: dict[str, tuple[float, dict[str, Any]]] = {}


def _normalize_api_path(path: str) -> str:
    path = path.strip()
    if path.startswith(("http://", "https://")):
        match = re.search(r"/api/v1(?P<path>/.*)$", path)
        if match:
            path = match.group("path")
    if path.startswith("/api/v1/"):
        path = path.removeprefix("/api/v1")
    if not path.startswith("/"):
        path = f"/{path}"
    return path


def _path_shape(path: str) -> str:
    return re.sub(r"\{[^}/]+\}", "{}", path)


def _path_template_to_regex(path: str) -> re.Pattern[str]:
    pattern = re.escape(path)
    pattern = re.sub(r"\\\{[^}/]+\\\}", r"[^/]+", pattern)
    return re.compile(f"^{pattern}$")


def _operation_entries(spec: dict[str, Any]) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    paths = spec.get("paths", {})
    if not isinstance(paths, dict):
        return entries
    for path, path_item in paths.items():
        if not isinstance(path_item, dict):
            continue
        for method, operation in path_item.items():
            method_upper = method.upper()
            if method_upper not in _HTTP_METHODS or not isinstance(operation, dict):
                continue
            entries.append(
                {
                    "method": method_upper,
                    "path": path,
                    "tag": (operation.get("tags") or ["untagged"])[0],
                    "operation_id": operation.get("operationId", ""),
                    "summary": operation.get("summary", ""),
                    "description": operation.get("description", ""),
                    "parameters": operation.get("parameters", []),
                }
            )
    return entries


def _fetch_openapi(tool_context: ToolContext, refresh: bool = False) -> dict[str, Any]:
    creds = GITEA_CREDENTIALS.resolve(tool_context)
    base_url = creds["base_url"].rstrip("/")
    cached = _OPENAPI_CACHE.get(base_url)
    if cached and not refresh and time.monotonic() - cached[0] < _CACHE_TTL_SECONDS:
        return cached[1]

    headers = {"Accept": "application/json"}
    if creds.get("token"):
        headers["Authorization"] = f"token {creds['token']}"

    try:
        with httpx.Client(timeout=30.0, headers=headers) as client:
            resp = client.get(f"{base_url}/swagger.v1.json")
            resp.raise_for_status()
            spec = resp.json()
    except httpx.HTTPError as e:
        return {"error": True, "message": f"Failed to fetch Gitea OpenAPI document: {e}"}
    except ValueError as e:
        return {"error": True, "message": f"Invalid Gitea OpenAPI JSON: {e}"}

    _OPENAPI_CACHE[base_url] = (time.monotonic(), spec)
    return spec


def _find_operation(spec: dict[str, Any], method: str, path: str) -> dict[str, Any] | None:
    method = method.upper()
    path = _normalize_api_path(path)
    paths = spec.get("paths", {})
    if not isinstance(paths, dict):
        return None

    exact = paths.get(path)
    if isinstance(exact, dict) and isinstance(exact.get(method.lower()), dict):
        op = dict(exact[method.lower()])
        op["path"] = path
        return op

    target_shape = _path_shape(path)
    for template, path_item in paths.items():
        if not isinstance(path_item, dict) or not isinstance(path_item.get(method.lower()), dict):
            continue
        if _path_shape(template) == target_shape or _path_template_to_regex(template).match(path):
            op = dict(path_item[method.lower()])
            op["path"] = template
            return op
    return None


def _render_path(path: str, path_params: dict[str, Any] | None) -> str:
    path = _normalize_api_path(path)
    if not path_params:
        return path

    rendered = path
    for key, value in path_params.items():
        rendered = rendered.replace(f"{{{key}}}", quote(str(value), safe=""))
    return rendered


def _endpoint_score(entry: dict[str, Any], query: str) -> int:
    if not query:
        return 1
    haystack = " ".join(
        [
            entry.get("method", ""),
            entry.get("path", ""),
            entry.get("tag", ""),
            entry.get("operation_id", ""),
            entry.get("summary", ""),
            entry.get("description", ""),
        ]
    ).lower()
    score = 0
    for token in query.lower().split():
        if token in haystack:
            score += 1
    return score


def get_gitea_api_summary(tool_context: ToolContext, refresh: bool = False) -> dict:
    """Get the OpenAPI summary for the configured Gitea instance.

    Args:
        refresh: Force refresh instead of using the one-hour in-memory cache
    """
    spec = _fetch_openapi(tool_context, refresh=refresh)
    if spec.get("error"):
        return spec

    entries = _operation_entries(spec)
    by_tag: dict[str, int] = {}
    for entry in entries:
        tag = entry["tag"]
        by_tag[tag] = by_tag.get(tag, 0) + 1

    return {
        "title": spec.get("info", {}).get("title", "Gitea API"),
        "version": spec.get("info", {}).get("version", ""),
        "paths": len(spec.get("paths", {})),
        "operations": len(entries),
        "by_tag": dict(sorted(by_tag.items())),
        "base_path": spec.get("basePath", "/api/v1"),
    }


def search_gitea_api_endpoints(
    tool_context: ToolContext,
    query: str = "",
    tag: str = "",
    method: str = "",
    path_contains: str = "",
    limit: int = 30,
) -> dict:
    """Search Gitea API endpoints from the configured instance's OpenAPI document.

    Args:
        query: Free text query, such as "release asset" or "team member"
        tag: Optional OpenAPI tag filter, such as "repository", "issue", "admin"
        method: Optional HTTP method filter, such as "GET" or "POST"
        path_contains: Optional substring filter for API paths
        limit: Maximum number of endpoints to return
    """
    spec = _fetch_openapi(tool_context)
    if spec.get("error"):
        return spec

    method = method.upper().strip()
    tag = tag.strip().lower()
    path_contains = path_contains.strip().lower()
    results: list[dict[str, Any]] = []

    for entry in _operation_entries(spec):
        if method and entry["method"] != method:
            continue
        if tag and entry["tag"].lower() != tag:
            continue
        if path_contains and path_contains not in entry["path"].lower():
            continue
        score = _endpoint_score(entry, query)
        if query and score == 0:
            continue
        results.append(
            {
                "method": entry["method"],
                "path": entry["path"],
                "tag": entry["tag"],
                "operation_id": entry["operation_id"],
                "summary": entry["summary"],
                "score": score,
            }
        )

    results.sort(key=lambda x: (-x["score"], x["tag"], x["path"], x["method"]))
    return {"count": len(results), "results": results[: max(1, min(limit, 100))]}


def get_gitea_api_endpoint(method: str, path: str, tool_context: ToolContext) -> dict:
    """Get detailed OpenAPI metadata for one Gitea API endpoint.

    Args:
        method: HTTP method, such as "GET" or "POST"
        path: API path, such as "/repos/{owner}/{repo}/issues"
    """
    method = method.upper().strip()
    if method not in _HTTP_METHODS:
        return {"error": True, "message": f"Unsupported method: {method}"}

    spec = _fetch_openapi(tool_context)
    if spec.get("error"):
        return spec

    operation = _find_operation(spec, method, path)
    if operation is None:
        return {
            "error": True,
            "message": f"Endpoint not found in Gitea OpenAPI: {method} {_normalize_api_path(path)}",
        }

    return {
        "method": method,
        "path": operation.get("path", _normalize_api_path(path)),
        "tag": (operation.get("tags") or ["untagged"])[0],
        "operation_id": operation.get("operationId", ""),
        "summary": operation.get("summary", ""),
        "description": operation.get("description", ""),
        "parameters": operation.get("parameters", []),
        "responses": operation.get("responses", {}),
    }


def call_gitea_api(
    method: str,
    path: str,
    tool_context: ToolContext,
    path_params: dict[str, Any] | None = None,
    query_params: dict[str, Any] | None = None,
    json_body: dict[str, Any] | list[Any] | None = None,
    allow_unknown_endpoint: bool = False,
) -> dict:
    """Call any JSON-compatible Gitea API endpoint.

    Use search_gitea_api_endpoints and get_gitea_api_endpoint first when you are
    unsure about the exact path, parameters, or request body.

    Args:
        method: HTTP method, such as "GET", "POST", "PUT", "PATCH", or "DELETE"
        path: API path relative to /api/v1, e.g. "/repos/{owner}/{repo}/issues"
        path_params: Values for path placeholders, e.g. {"owner": "alice", "repo": "demo"}
        query_params: Query parameters
        json_body: JSON request body for POST/PUT/PATCH/DELETE endpoints
        allow_unknown_endpoint: Allow calling paths not found in the OpenAPI document
    """
    method = method.upper().strip()
    if method not in _HTTP_METHODS:
        return {"error": True, "message": f"Unsupported method: {method}"}

    spec = _fetch_openapi(tool_context)
    rendered_path = _render_path(path, path_params)
    endpoint_info: dict[str, Any] = {}
    if not spec.get("error"):
        operation = _find_operation(spec, method, path)
        if operation is None and not allow_unknown_endpoint:
            suggestions = search_gitea_api_endpoints(
                tool_context,
                query=path.replace("/", " "),
                method=method,
                limit=5,
            )
            return {
                "error": True,
                "message": f"Endpoint not found in Gitea OpenAPI: {method} {_normalize_api_path(path)}",
                "suggestions": suggestions.get("results", []),
            }
        if operation is not None:
            endpoint_info = {
                "template": operation.get("path", _normalize_api_path(path)),
                "operation_id": operation.get("operationId", ""),
                "tag": (operation.get("tags") or ["untagged"])[0],
                "summary": operation.get("summary", ""),
            }

    with GiteaClient.from_context(tool_context) as client:
        response = client.request(method, rendered_path, params=query_params, json_data=json_body)

    return {
        "request": {
            "method": method,
            "path": rendered_path,
            "query_params": query_params or {},
            "endpoint": endpoint_info,
        },
        "response": response,
    }


def upload_gitea_api_asset(
    path: str,
    file_name: str,
    file_content_base64: str,
    tool_context: ToolContext,
    path_params: dict[str, Any] | None = None,
    query_params: dict[str, Any] | None = None,
    form_field: str = "attachment",
    content_type: str = "application/octet-stream",
) -> dict:
    """Upload an asset to a multipart/form-data Gitea API endpoint.

    This covers issue attachments, comment attachments, and release assets.
    Use get_gitea_api_endpoint first to confirm the endpoint expects a file.

    Args:
        path: API path, e.g. "/repos/{owner}/{repo}/releases/{id}/assets"
        file_name: Uploaded file name
        file_content_base64: Base64-encoded file content
        path_params: Values for path placeholders
        query_params: Query parameters, commonly {"name": "asset-name.ext"}
        form_field: Multipart file field name, normally "attachment"
        content_type: Uploaded file content type
    """
    spec = _fetch_openapi(tool_context)
    if not spec.get("error"):
        operation = _find_operation(spec, "POST", path)
        if operation is None:
            return {
                "error": True,
                "message": f"Endpoint not found in Gitea OpenAPI: POST {_normalize_api_path(path)}",
            }
        parameters = operation.get("parameters", [])
        has_file = any(param.get("in") == "formData" and param.get("type") == "file" for param in parameters)
        if not has_file:
            return {
                "error": True,
                "message": f"Endpoint is not a multipart file upload endpoint: POST {_normalize_api_path(path)}",
            }

    try:
        file_content = b64decode(file_content_base64, validate=True)
    except ValueError as e:
        return {"error": True, "message": f"Invalid base64 file content: {e}"}

    rendered_path = _render_path(path, path_params)
    files = {form_field: (file_name, file_content, content_type)}
    with GiteaClient.from_context(tool_context) as client:
        response = client.multipart("POST", rendered_path, params=query_params, files=files)

    return {
        "request": {
            "method": "POST",
            "path": rendered_path,
            "query_params": query_params or {},
            "file_name": file_name,
            "form_field": form_field,
            "content_type": content_type,
            "size": len(file_content),
        },
        "response": response,
    }


all_tools: list = [
    get_gitea_api_summary,
    search_gitea_api_endpoints,
    get_gitea_api_endpoint,
    call_gitea_api,
    upload_gitea_api_asset,
]
