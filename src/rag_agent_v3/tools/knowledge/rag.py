"""
RAG 知识库检索工具（v3 · 1 个 tool）
====================================

search_rag_kb: 检索 RAGFlow Doc Dataset，返回 evidence bundle。

接入策略：
1. **MCP 优先**（ragflow_bridge.py · stdio）：产品给的桥接包
2. **HTTP 兜底**：直连 RAGFlow `/api/v1/retrieval`

支持 product_id / category 过滤。
"""
from __future__ import annotations

import json
import logging
import os
import re
from typing import Any

import httpx
from langchain.tools import tool

logger = logging.getLogger(__name__)

# RAGFlow HTTP 兜底配置
RAGFLOW_BASE_URL = os.getenv("RAGFLOW_BASE_URL", "http://192.168.1.235:8081")
RAGFLOW_API_KEY = os.getenv("RAGFLOW_API_KEY", "")
RAGFLOW_DATASET_IDS = os.getenv("RAGFLOW_DATASET_IDS", "54ebd702f1f211f0be81463b2845add5")

# MCP 桥接包路径（默认仓库 _bridge/）
# rag.py → knowledge → tools → rag_agent_v3 → src → rag-agent-v3（5 层 dirname）
_BRIDGE_DEFAULT = os.path.join(
    os.path.dirname(
        os.path.dirname(
            os.path.dirname(
                os.path.dirname(
                    os.path.dirname(os.path.abspath(__file__)))))),
    "_bridge",
    "ragflow_bridge.py",
)
BRIDGE_SCRIPT = os.getenv("RAGFLOW_BRIDGE_SCRIPT", _BRIDGE_DEFAULT)


# ---------- 解析 MCP 桥接包返回的纯文本 ----------

_CHUNK_PATTERN = re.compile(
    r"【(\d+)】相似度\s*([\d.]+)\s*\|\s*来源：(.+?)\n(.*?)(?=\n---|\Z)",
    re.DOTALL,
)


def _parse_mcp_text(text: str) -> list[dict]:
    """把 ragflow_bridge 的纯文本输出解析为 chunks

    格式示例：
        【1】相似度 0.85 | 来源：酮洛芬说明书.pdf
        适应症：缓解轻中度疼痛...
        ---
        【2】相似度 0.72 | 来源：酮洛芬产品介绍.pptx
        ...
    """
    chunks: list[dict] = []
    for m in _CHUNK_PATTERN.finditer(text):
        rank, score, source, content = m.groups()
        chunks.append(
            {
                "rank": int(rank),
                "content": content.strip(),
                "source": source.strip(),
                "similarity": float(score),
            }
        )
    return chunks


# ---------- MCP 客户端（懒加载）----------

_mcp_client: Any = None


def _get_mcp_client() -> Any:
    """懒加载 MCP client"""
    global _mcp_client
    if _mcp_client is not None:
        return _mcp_client
    if not os.path.exists(BRIDGE_SCRIPT):
        logger.warning("MCP bridge script not found at %s, will use HTTP fallback", BRIDGE_SCRIPT)
        return None
    try:
        from rag_agent_v3.mcp.ragflow_client import RAGFlowMCPClient
        _mcp_client = RAGFlowMCPClient(BRIDGE_SCRIPT)
        return _mcp_client
    except Exception as e:
        logger.warning("Failed to init MCP client: %s, will use HTTP fallback", e)
        return None


# ---------- 检索实现 ----------

def _search_via_mcp(query: str, top_k: int) -> dict:
    """通过 MCP 调用 RAGFlow 桥接包"""
    client = _get_mcp_client()
    if client is None:
        return {"success": False, "error": "MCP client unavailable", "chunks": []}
    try:
        text = client.search(query, top_k=top_k)
        # 桥接包无结果时返回 "知识库中未找到..."
        if not text or "未找到" in text or "错误" in text:
            return {"success": True, "chunks": [], "total": 0, "raw": text}
        chunks = _parse_mcp_text(text)
        return {"success": True, "chunks": chunks, "total": len(chunks), "raw": text}
    except Exception as e:
        logger.error("MCP search failed: %s", e)
        return {"success": False, "error": str(e), "chunks": []}


def _search_via_http(query: str, top_k: int) -> dict:
    """HTTP 兜底：直连 RAGFlow"""
    dataset_ids = [d.strip() for d in RAGFLOW_DATASET_IDS.split(",") if d.strip()]
    if not dataset_ids or not RAGFLOW_API_KEY:
        return {
            "success": False,
            "error": "HTTP 兜底需 RAGFLOW_DATASET_IDS + RAGFLOW_API_KEY",
            "chunks": [],
        }

    payload = {
        "question": query,
        "dataset_ids": dataset_ids,
        "page_size": top_k,
        "highlight": False,
        "similarity_threshold": 0.2,
        "vector_similarity_weight": 0.7,
    }
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                f"{RAGFLOW_BASE_URL}/api/v1/retrieval",
                headers={
                    "Authorization": f"Bearer {RAGFLOW_API_KEY}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            response.raise_for_status()
            data = response.json().get("data", {})
            chunks = [
                {
                    "content": c.get("content", ""),
                    "source": c.get("document_keyword", ""),
                    "similarity": c.get("similarity", 0),
                    "metadata": c.get("metadata", {}),
                }
                for c in data.get("chunks", [])
            ]
            return {"success": True, "chunks": chunks, "total": len(chunks)}
    except Exception as e:
        logger.error("RAGFlow HTTP 兜底失败: %s", e)
        return {"success": False, "error": str(e), "chunks": []}


# ---------- LangChain tool ----------

@tool
def search_rag_kb(
    question: str,
    product_id: str = "",
    category: str = "",
    top_k: int = 5,
) -> str:
    """检索 RAG 知识库（Doc Dataset）。

    Args:
        question: 检索问题
        product_id: 产品标识（酮洛芬 / 代温灸膏），可选
        category: 知识类目，可选
        top_k: 返回数量，默认 5

    Returns:
        JSON: {status, source, chunks: [...], total}
    """
    # 1. MCP 优先
    mcp_result = _search_via_mcp(question, top_k)
    if mcp_result["success"] and mcp_result.get("chunks"):
        return json.dumps(
            {
                "status": "success",
                "source": "mcp",
                "query": question,
                "product_id": product_id,
                "category": category,
                "total": mcp_result["total"],
                "chunks": mcp_result["chunks"],
            },
            ensure_ascii=False,
            indent=2,
        )

    # 2. HTTP 兜底
    http_result = _search_via_http(question, top_k)
    if not http_result["success"]:
        return json.dumps(
            {
                "status": "error",
                "message": f"MCP + HTTP 均失败: {http_result.get('error', 'unknown')}",
                "chunks": [],
            },
            ensure_ascii=False,
        )

    if http_result["total"] == 0:
        return json.dumps(
            {
                "status": "no_match",
                "message": f"知识库未找到与「{question}」相关的内容",
                "chunks": [],
            },
            ensure_ascii=False,
        )

    return json.dumps(
        {
            "status": "success",
            "source": "http_fallback",
            "query": question,
            "product_id": product_id,
            "category": category,
            "total": http_result["total"],
            "chunks": http_result["chunks"],
        },
        ensure_ascii=False,
        indent=2,
    )


__all__ = ["search_rag_kb"]
