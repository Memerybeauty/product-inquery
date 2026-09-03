"""
QA 知识库检索工具（v3 · 1 个 tool）
==================================

search_qa_kb: 检索历史 QA 知识库，命中走 force_direct_qa_bypass 通道。

MCP 接入：MCP_CONFIG_PATH 环境变量指定 mcp.json 路径。
RAGFlow 兜底：当 MCP 不可用时，HTTP 调 RAGFlow QA Dataset。
"""
from __future__ import annotations

import json
import logging
import os
from typing import Any

import httpx
from langchain.tools import tool

logger = logging.getLogger(__name__)

# MCP / RAGFlow 配置
MCP_CONFIG_PATH = os.getenv("MCP_CONFIG_PATH", "./config/mcp.json")
RAGFLOW_BASE_URL = os.getenv("RAGFLOW_BASE_URL", "http://localhost:8081")
RAGFLOW_API_KEY = os.getenv("RAGFLOW_API_KEY", "")
QA_DATASET_ID = os.getenv("RAGFLOW_QA_DATASET_ID", "")


def _call_mcp_qa(question: str) -> dict | None:
    """通过 MCP 调用 QA 检索（用户给 mcp.json 之前返回 None）"""
    import os
    if not os.path.exists(MCP_CONFIG_PATH):
        return None
    # TODO: 用户给 mcp.json 后接入 MCP 客户端
    return None


def _call_ragflow_qa(question: str) -> dict:
    """兜底：HTTP 调 RAGFlow QA Dataset"""
    if not QA_DATASET_ID or not RAGFLOW_API_KEY:
        return {"success": False, "error": "RAGFlow QA Dataset 未配置", "qa": None}

    try:
        with httpx.Client(timeout=15.0) as client:
            response = client.post(
                f"{RAGFLOW_BASE_URL}/api/v1/retrieval",
                headers={"Authorization": f"Bearer {RAGFLOW_API_KEY}"},
                json={
                    "question": question,
                    "dataset_ids": [QA_DATASET_ID],
                    "top_k": 3,
                },
            )
            response.raise_for_status()
            data = response.json().get("data", {})
            chunks = data.get("chunks", [])
            if not chunks:
                return {"success": True, "qa": None}

            top = chunks[0]
            return {
                "success": True,
                "qa": {
                    "qa_id": top.get("id", ""),
                    "serving_answer": top.get("content", ""),
                    "similarity": top.get("similarity", 0),
                },
            }
    except Exception as e:
        logger.error("RAGFlow QA 检索失败: %s", e)
        return {"success": False, "error": str(e), "qa": None}


@tool
def search_qa_kb(question: str) -> str:
    """检索历史 QA 知识库。

    命中时返回的 payload 含 `_bypass=True` 标记，触发 force_direct_qa_bypass 中间件，
    serving_answer 走直返通道，不经改写。

    Args:
        question: 用户原始问题

    Returns:
        JSON: {status, qa: {qa_id, serving_answer, similarity}, _bypass}
    """
    # 1. 优先 MCP
    mcp_result = _call_mcp_qa(question)
    if mcp_result and mcp_result.get("success") and mcp_result.get("qa"):
        return json.dumps(
            {
                "status": "success",
                "source": "mcp",
                "qa": mcp_result["qa"],
                "_bypass": True,  # 触发 force_direct_qa_bypass
            },
            ensure_ascii=False,
        )

    # 2. RAGFlow 兜底
    result = _call_ragflow_qa(question)
    if not result.get("success") or not result.get("qa"):
        return json.dumps(
            {"status": "no_match", "message": f"QA 库未找到与「{question}」匹配的历史问题"},
            ensure_ascii=False,
        )

    return json.dumps(
        {
            "status": "success",
            "source": "ragflow",
            "qa": result["qa"],
            "_bypass": True,
        },
        ensure_ascii=False,
    )


__all__ = ["search_qa_kb"]
