"""
联网 disclaimer 中间件（v3 · 1 件套）
====================================

append_internet_disclaimer: 联网结果必须附免责声明

固定模板（v3 拍板）：
    以下内容来自互联网，仅供参考，不构成医疗建议。
    用药相关问题请咨询医师或药师。

触发条件：response_metadata.used_internet_search == True
"""
from __future__ import annotations

import logging
from typing import Any

from langchain.agents.middleware import after_model
from langchain_core.messages import AIMessage

logger = logging.getLogger(__name__)

INTERNET_DISCLAIMER: str = (
    "\n\n---\n📌 **以上内容来自互联网，仅供参考，不构成医疗建议。"
    "用药相关问题请咨询医师或药师。**"
)


@after_model
def append_internet_disclaimer(state: Any, runtime: Any) -> Any:
    """联网结果必须附免责声明。"""
    metadata = state.get("response_metadata", {}) or {}
    if not metadata.get("used_internet_search"):
        return state

    messages = state.get("messages", [])
    if not messages:
        return state

    last = messages[-1]
    if not isinstance(last, AIMessage):
        return state

    text = last.content if isinstance(last.content, str) else str(last.content)
    if INTERNET_DISCLAIMER in text:
        return state  # 已附，跳过

    text = text + INTERNET_DISCLAIMER
    new_msg = AIMessage(
        content=text,
        additional_kwargs=last.additional_kwargs,
        response_metadata=last.response_metadata,
        id=last.id,
    )
    state["messages"] = messages[:-1] + [new_msg]
    logger.info("[disclaimer] internet disclaimer appended")
    return state
