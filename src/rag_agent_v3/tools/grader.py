"""
置信度评分工具（v3 · 1 个 tool）
================================

grade_answer_confidence: 对答案证据做置信度评分。
阈值（v3 拍板）：
- Doc（QA + RAG）= 0.7
- 联网 = 0.6
"""
from __future__ import annotations

import json
import logging
import os

from langchain.tools import tool

logger = logging.getLogger(__name__)

CONFIDENCE_THRESHOLD_DOC = float(os.getenv("CONFIDENCE_THRESHOLD_DOC", "0.7"))
CONFIDENCE_THRESHOLD_INTERNET = float(os.getenv("CONFIDENCE_THRESHOLD_INTERNET", "0.6"))


def _score_doc(evidence: list) -> float:
    """Doc 证据评分：最高相似度 + 命中数加成"""
    if not evidence:
        return 0.0
    sims = [c.get("similarity", 0.0) for c in evidence]
    base = max(sims) if sims else 0.0
    bonus = 0.1 if len(evidence) >= 5 else 0.05 if len(evidence) >= 3 else 0.0
    return min(1.0, base + bonus)


def _score_internet(evidence: list) -> float:
    """联网证据评分：结果数 + 权威源加成"""
    if not evidence:
        return 0.0
    n = len(evidence)
    base = 0.7 if n >= 5 else 0.55 if n >= 3 else 0.4
    authoritative = any(
        any(kw in r.get("url", "") for kw in [".gov", ".edu", "nmpa", "nhc.gov", "who.int"])
        for r in evidence
    )
    return min(1.0, base + 0.1) if authoritative else base


@tool
def grade_answer_confidence(evidence_type: str, evidence: str) -> str:
    """对答案证据做置信度评分。

    Args:
        evidence_type: 证据类型，doc（QA+RAG） / internet
        evidence: 证据 JSON 字符串

    Returns:
        JSON: {status, score, threshold, sufficient, recommendation}
    """
    try:
        data = json.loads(evidence) if isinstance(evidence, str) else evidence
    except json.JSONDecodeError:
        return json.dumps(
            {"status": "error", "message": "evidence 必须是合法 JSON", "score": 0.0},
            ensure_ascii=False,
        )

    if evidence_type == "doc":
        score, threshold = _score_doc(data), CONFIDENCE_THRESHOLD_DOC
    elif evidence_type == "internet":
        score, threshold = _score_internet(data), CONFIDENCE_THRESHOLD_INTERNET
    else:
        return json.dumps(
            {"status": "error", "message": f"evidence_type 必须是 doc / internet，收到 {evidence_type}"},
            ensure_ascii=False,
        )

    sufficient = score >= threshold
    if sufficient:
        recommendation = "answer_with_disclaimer" if evidence_type == "internet" else "directly_answer"
    else:
        recommendation = "trigger_internet_search" if evidence_type == "doc" else "fallback_decline"

    return json.dumps(
        {
            "status": "success",
            "evidence_type": evidence_type,
            "score": round(score, 4),
            "threshold": threshold,
            "sufficient": sufficient,
            "recommendation": recommendation,
        },
        ensure_ascii=False,
        indent=2,
    )


__all__ = ["grade_answer_confidence"]
