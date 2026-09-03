"""
文本合规中间件（v3 · 4 件套）
============================

- validate_text_response: 文本越界 / 空响应检查
- strip_source_block:     剥离「资料依据」区块
- forbid_model_common_sense: 禁止模型常识补全产品事实
- force_direct_qa_bypass:  QA 命中走直返通道，不经改写

实现基于 LangChain 1.0 `after_model` + `wrap_tool_call` 装饰器。
模型无论怎么调工具，最终响应都要走这条链。
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any

from langchain.agents.middleware import after_model, wrap_tool_call
from langchain_core.messages import AIMessage, ToolMessage

logger = logging.getLogger(__name__)

# 越界关键词（个体化诊疗 / 竞品 / 索要系统信息等）
BOUNDARY_KEYWORDS: list[str] = [
    "个体化", "我爸爸", "我妈", "我爷爷", "我奶奶", "我自己", "患者", "病人",
    "竞品", "芬太尼", "洛索洛芬", "扶他林", "其他厂家",
    "你是什么模型", "你的参数", "你的系统提示", "你的prompt",
]

# 常识补全禁用关键词（产品事实必须基于知识库）
COMMON_SENSE_PATTERNS: list[str] = [
    r"一般来说",
    r"通常情况下",
    r"众所周知",
    r"业内认为",
    r"根据常识",
]

# 「资料依据」剥离正则
_SOURCE_BLOCK = re.compile(
    r"(?:资料依据|参考来源|参考资料|来源：|依据：|References?|Sources?)[\s\S]{0,2000}?(?=\n\n|$)",
    re.IGNORECASE | re.MULTILINE,
)


# ---------- 工具调用层：QA 直返通道打标 ----------

@wrap_tool_call
def force_direct_qa_bypass(request: Any, handler: Any) -> ToolMessage:
    """QA 命中时走直返通道，绕开改写中间件。

    触发条件：search_qa_kb 返回的 tool message 含 `_bypass=True` 标记。
    """
    result: ToolMessage = handler(request)

    try:
        if isinstance(result, ToolMessage) and isinstance(result.content, str):
            payload = json.loads(result.content)
            if isinstance(payload, dict) and payload.get("_bypass"):
                metadata = getattr(request.state, "response_metadata", None) or {}
                metadata["direct_qa_bypass"] = True
                request.state.response_metadata = metadata
                logger.info("[bypass] QA direct hit, channel=direct_qa_bypass")
    except Exception as e:
        logger.warning("[bypass] middleware skip: %s", e)

    return result


# ---------- 模型输出层：文本合规收口 ----------

def _is_valid(text: str) -> tuple[bool, str]:
    """文本合规验证。返回 (is_valid, reason)。"""
    if not text or not text.strip():
        return False, "empty_response"
    for kw in BOUNDARY_KEYWORDS:
        if kw in text:
            return False, f"boundary_keyword:{kw}"
    return True, "ok"


def _strip_source(text: str) -> str:
    """剥离「资料依据」区块。"""
    return _SOURCE_BLOCK.sub("", text).strip()


def _strip_common_sense(text: str) -> str:
    """剥离模型常识补全。"""
    for pat in COMMON_SENSE_PATTERNS:
        text = re.sub(rf"({pat})[，。！？\s]*", "", text)
    return text


@after_model
def validate_text_response(state: Any, runtime: Any) -> Any:
    """v3 文本合规收口（4 件套合一）。

    处理顺序：
    1. bypass 通道：QA 命中直返，跳过所有改写
    2. validate：越界 / 空响应 → 固定话术替换
    3. strip_source：剥离「资料依据」区块
    4. forbid_common_sense：剥离常识补全
    """
    messages = state.get("messages", [])
    if not messages:
        return state

    last = messages[-1]
    if not isinstance(last, AIMessage):
        return state

    metadata = state.get("response_metadata", {}) or {}
    is_bypass = bool(metadata.get("direct_qa_bypass"))

    text = last.content if isinstance(last.content, str) else str(last.content)

    # bypass：QA 命中直返，不做改写
    if is_bypass:
        logger.info("[validate] bypass channel, skip rewrite")
        return state

    # 1. validate
    ok, reason = _is_valid(text)
    if not ok:
        logger.warning("[validate] text compliance failed: %s", reason)
        if reason.startswith("boundary_keyword"):
            text = "抱歉，这个问题超出我的服务范围，我仅提供九典产品的信息与资料服务。"
        else:
            text = "抱歉，我暂时无法回答这个问题，请换个方式提问或联系推广经理。"

    # 2. strip_source
    text = _strip_source(text)

    # 3. forbid_common_sense
    text = _strip_common_sense(text)

    # 写回消息
    new_msg = AIMessage(
        content=text,
        additional_kwargs=last.additional_kwargs,
        response_metadata=last.response_metadata,
        id=last.id,
    )
    state["messages"] = messages[:-1] + [new_msg]
    return state
