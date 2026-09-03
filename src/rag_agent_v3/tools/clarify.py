"""
澄清工具（v3 · 1 个 tool）
==========================

clarify_user: 当用户意图不明（信息不足）时，引导用户澄清。
返回澄清话术 + Pending 标记（用于上下文恢复）。
"""
from __future__ import annotations

import json

from langchain.tools import tool


@tool
def clarify_user(text: str, original_request: str = "") -> str:
    """引导用户澄清意图。

    Args:
        text: 澄清话术（如"您是想了解酮洛芬还是代温灸膏？"）
        original_request: 用户原始请求（用于 Pending 恢复）

    Returns:
        JSON: {status: "clarify", message, pending: {original_request}}
    """
    return json.dumps(
        {
            "status": "clarify",
            "message": text,
            "pending": {"original_request": original_request},
        },
        ensure_ascii=False,
    )


__all__ = ["clarify_user"]
