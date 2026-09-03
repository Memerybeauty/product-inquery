"""
越界拒绝工具（v3 · 1 个 tool）
==============================

reject_request: 处理越界请求（个体化诊疗 / 系统信息 / 其他越界）。

**v3 设计**：竞品 / 外部产品**不是**越界条件，必须走查问题路径。

**关键设计**：返回**纯文本话术**（不是 JSON），让 LLM 直接呈现。
"""
from __future__ import annotations

from langchain.tools import tool

# 越界场景固定话术（v3 · 3 类，无 competitor）
REJECTION_REASONS: dict[str, str] = {
    "individual_treatment": "抱歉，我无法提供个体化诊疗建议，请咨询医师或药师。",
    "system_info": "无法提供系统内部信息，技术问题请联系管理员。",
    "out_of_scope": "抱歉，这个问题超出我的服务范围，我仅提供九典产品的信息与资料服务。",
}


@tool
def reject_request(reason: str) -> str:
    """拒绝越界请求，输出固定话术（直接返回纯文本，供 LLM 呈现）。

    Args:
        reason: 越界原因，可选值：
            - individual_treatment（个体化诊疗）
            - system_info（系统信息）
            - out_of_scope（其他越界）

    Returns:
        纯文本拒答话术
    """
    return REJECTION_REASONS.get(reason, REJECTION_REASONS["out_of_scope"])


__all__ = ["reject_request", "REJECTION_REASONS"]
