"""
越界拒绝工具（v3 · 1 个 tool）
==============================

reject_request: 处理越界请求（个体化诊疗 / 竞品 / 系统信息 / 其他越界）。
返回固定话术，不调用任何工具。
"""
from __future__ import annotations

import json

from langchain.tools import tool

# 越界场景固定话术
REJECTION_REASONS: dict[str, str] = {
    "individual_treatment": "抱歉，我无法提供个体化诊疗建议，请咨询医师或药师。",
    "competitor": "我仅提供九典自有产品信息，不涉及竞品。",
    "system_info": "无法提供系统内部信息，技术问题请联系管理员。",
    "out_of_scope": "抱歉，这个问题超出我的服务范围，我仅提供九典产品的信息与资料服务。",
}


@tool
def reject_request(reason: str) -> str:
    """拒绝越界请求，输出固定话术。

    Args:
        reason: 越界原因，可选值：
            - individual_treatment（个体化诊疗）
            - competitor（竞品）
            - system_info（系统信息）
            - out_of_scope（其他越界）

    Returns:
        JSON: {status: "rejected", refusal_reason, message}
    """
    message = REJECTION_REASONS.get(reason, REJECTION_REASONS["out_of_scope"])
    return json.dumps(
        {
            "status": "rejected",
            "refusal_reason": reason,
            "message": message,
        },
        ensure_ascii=False,
    )


__all__ = ["reject_request", "REJECTION_REASONS"]
