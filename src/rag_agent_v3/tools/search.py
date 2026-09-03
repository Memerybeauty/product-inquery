"""
联网搜索工具（v3 · 1 个 tool）
==============================

internet_search: duckduckgo-search 兜底，本地无 key 直接跑。
"""
from __future__ import annotations

import json
import logging
import os

from langchain.tools import tool

logger = logging.getLogger(__name__)

INTERNET_SEARCH_ENABLED = os.getenv("INTERNET_SEARCH_ENABLED", "true").lower() == "true"


def _duckduckgo_search(query: str, max_results: int) -> dict:
    """调 duckduckgo-search 库"""
    try:
        from duckduckgo_search import DDGS
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
        return {
            "success": True,
            "source": "duckduckgo",
            "results": [
                {
                    "title": r.get("title", ""),
                    "snippet": r.get("body", ""),
                    "url": r.get("href", ""),
                }
                for r in results
            ],
        }
    except Exception as e:
        logger.error("duckduckgo 搜索失败: %s", e)
        return {"success": False, "error": str(e), "results": []}


@tool
def internet_search(query: str, max_results: int = 5) -> str:
    """联网搜索兜底。

    当 QA + RAG 检索置信度 < 0.7 时调用，附 disclaimer。

    Args:
        query: 搜索关键词
        max_results: 返回数量，默认 5

    Returns:
        JSON: {status, source, results: [{title, snippet, url}], _meta}
    """
    if not INTERNET_SEARCH_ENABLED:
        return json.dumps(
            {"status": "disabled", "message": "联网搜索未启用", "results": []},
            ensure_ascii=False,
        )

    result = _duckduckgo_search(query, max_results)
    if not result["success"]:
        return json.dumps(
            {"status": "error", "message": result["error"], "results": []},
            ensure_ascii=False,
        )

    if not result["results"]:
        return json.dumps(
            {
                "status": "no_match",
                "message": f"联网未找到与「{query}」相关的可信结果",
                "results": [],
            },
            ensure_ascii=False,
        )

    return json.dumps(
        {
            "status": "success",
            "query": query,
            "source": result["source"],
            "total": len(result["results"]),
            "results": result["results"],
            "_meta": {"used_internet_search": True},  # 触发 disclaimer 中间件
        },
        ensure_ascii=False,
        indent=2,
    )


__all__ = ["internet_search"]
