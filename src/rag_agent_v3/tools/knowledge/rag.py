"""
RAG 知识库检索工具（v3 · 1 个 tool）
====================================

search_rag_kb: 检索 RAGFlow Doc Dataset，返回 evidence bundle。

支持 product_id / category / version 过滤，向量 + 关键词 RRF 融合。
"""
from __future__ import annotations

import json
import logging
import os
from typing import Any

import httpx
from langchain.tools import tool

logger = logging.getLogger(__name__)

# RAGFlow 配置
RAGFLOW_BASE_URL = os.getenv("RAGFLOW_BASE_URL", "http://localhost:8081")
RAGFLOW_API_KEY = os.getenv("RAGFLOW_API_KEY", "")
RAGFLOW_DATASET_TLF = os.getenv("RAGFLOW_DATASET_TLF", "")  # 酮洛芬
RAGFLOW_DATASET_DW = os.getenv("RAGFLOW_DATASET_DW", "")    # 代温灸膏

# 产品 → Dataset 映射
DATASET_MAPPING: dict[str, str] = {
    "酮洛芬": RAGFLOW_DATASET_TLF,
    "代温灸膏": RAGFLOW_DATASET_DW,
}


def _call_ragflow_doc(query: str, product_id: str, category: str) -> dict:
    """HTTP 调 RAGFlow Doc 检索"""
    # 解析 dataset
    dataset_ids: list[str] = []
    if product_id and product_id in DATASET_MAPPING and DATASET_MAPPING[product_id]:
        dataset_ids.append(DATASET_MAPPING[product_id])
    else:
        dataset_ids = [v for v in DATASET_MAPPING.values() if v]

    if not dataset_ids:
        return {
            "success": False,
            "error": "未配置 RAGFlow Dataset",
            "chunks": [],
        }

    # 构建 conditions
    conditions: list[dict] = []
    if category:
        conditions.append({"field": "category", "operator": "eq", "value": category})
    if product_id:
        conditions.append({"field": "product_id", "operator": "eq", "value": product_id})

    payload: dict[str, Any] = {
        "question": query,
        "dataset_ids": dataset_ids,
        "top_k": 5,
        "similarity_threshold": 0.2,
        "vector_similarity_weight": 0.7,
    }
    if conditions:
        payload["conditions"] = conditions

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
    except httpx.TimeoutException:
        logger.error("RAGFlow 检索超时: %s", query)
        return {"success": False, "error": "知识库检索超时", "chunks": []}
    except Exception as e:
        logger.error("RAGFlow 检索异常: %s", e)
        return {"success": False, "error": str(e), "chunks": []}


@tool
def search_rag_kb(
    question: str,
    product_id: str = "",
    category: str = "",
) -> str:
    """检索 RAG 知识库（Doc Dataset）。

    Args:
        question: 检索问题
        product_id: 产品标识（酮洛芬 / 代温灸膏），可选
        category: 知识类目（产品基本信息/产品卖点/历史问题QA/市场推广材料），可选

    Returns:
        JSON: {status, chunks: [...], total}
    """
    result = _call_ragflow_doc(question, product_id, category)

    if not result["success"]:
        return json.dumps(
            {"status": "error", "message": result["error"], "chunks": []},
            ensure_ascii=False,
        )

    if result["total"] == 0:
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
            "query": question,
            "product_id": product_id,
            "category": category,
            "total": result["total"],
            "chunks": result["chunks"],
        },
        ensure_ascii=False,
        indent=2,
    )


__all__ = ["search_rag_kb"]
