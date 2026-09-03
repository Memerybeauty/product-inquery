"""
短路中间件：tool_call → final_answer
====================================

LLM 调某些 tool 后（如 reject_request），不再让 LLM 重新生成文本，
直接把 tool result 转为 final answer。

实现：在 `wrap_tool_call` 阶段（tool 执行后），检测是否是短路 tool，
是的话**直接结束 turn**（不再触发 LLM 重新生成）。
"""
from __future__ import annotations

import logging
from typing import Any

from langchain.agents.middleware import wrap_tool_call
from langchain_core.messages import AIMessage, ToolMessage

logger = logging.getLogger(__name__)

# 短路 tool：调了之后直接用 tool result 作为 final answer
SHORT_CIRCUIT_TOOLS: set[str] = {"reject_request", "clarify_user", "reply_capability"}


@wrap_tool_call
def short_circuit_tool_result(request: Any, handler: Any) -> Any:
    """tool 执行后检测短路 tool，是的话把 tool result 注入到 state 让 LLM 不再生成"""
    result = handler(request)
    if not isinstance(result, ToolMessage):
        return result

    # 提取 tool name（多种可能形式）
    tool_name = None
    tc = getattr(request, "tool_call", None)
    if tc is None and hasattr(request, "tool_call_id"):
        tool_name = None
    if isinstance(tc, dict):
        tool_name = tc.get("name")
    elif tc is not None:
        tool_name = getattr(tc, "name", None) or getattr(tc, "tool_name", None)

    if tool_name not in SHORT_CIRCUIT_TOOLS:
        return result

    # 标记到 state metadata，告知 after_model 阶段停止 LLM 重新生成
    try:
        state = getattr(request, "state", None)
        if state is not None:
            metadata = getattr(state, "response_metadata", None)
            if metadata is None:
                # 尝试 dict-like
                try:
                    metadata = state.get("response_metadata", {}) or {}
                except Exception:
                    metadata = {}
            metadata["short_circuit_final"] = True
            metadata["short_circuit_tool"] = tool_name
            try:
                state.response_metadata = metadata
            except Exception:
                try:
                    state["response_metadata"] = metadata
                except Exception:
                    pass
            logger.info("[short_circuit] tool=%s marked as final", tool_name)
    except Exception as e:
        logger.warning("[short_circuit] state mark failed: %s", e)

    return result
