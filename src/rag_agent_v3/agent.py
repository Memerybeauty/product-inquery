"""
DeepAgent 编排入口（v3）
========================

基于 LangChain 1.0 `create_agent` + LangGraph checkpointer：
- 11 个 tool（v3 三路径）
- 6 件套合规中间件（焊死）
- system_prompt 三路径规则
- 多轮对话上下文增强（自动注入最近 10 条历史的产品主语）

LLM 适配：MiniMaxChat（自定义，MiniMax 公开 API OpenAI 兼容协议）。

== 用法 ==

```python
from rag_agent_v3 import build_agent
agent = build_agent()
result = agent.invoke(
    {"messages": [{"role": "user", "content": "它有什么副作用"}]},  # 省略主语
    config={"configurable": {"thread_id": "user-123"}},
)
# 自动增强为："关于酮洛芬：它有什么副作用"
```
"""
from __future__ import annotations

import logging
import os
from typing import Any

from langchain.agents import create_agent
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.base import BaseCheckpointSaver

from rag_agent_v3.config import load_llm_config, load_prompt
from rag_agent_v3.context import augment_query
from rag_agent_v3.llm import build_minimax_chat
from rag_agent_v3.middleware import get_compliance_middleware_list
from rag_agent_v3.storage import get_checkpointer
from rag_agent_v3.tools import ALL_TOOLS

logger = logging.getLogger(__name__)


def _load_prompts() -> str:
    """组合 system_prompt：base + 三路径细则"""
    parts = [load_prompt("base")]
    for name in ("path_question", "path_file", "path_other"):
        parts.append("\n\n---\n\n")
        parts.append(load_prompt(name))
    return "".join(parts)


def _build_llm(cfg: dict) -> Any:
    """构建 LLM 实例（MiniMax 自定义 ChatModel）"""
    model_cfg = cfg.get("config", {})
    return build_minimax_chat(
        temperature=model_cfg.get("temperature", 0.3),
        max_tokens=model_cfg.get("max_completion_tokens", 4096),
    )


def build_agent(
    checkpointer: BaseCheckpointSaver | None = None,
    tools: list | None = None,
    enable_context_augment: bool = True,
) -> Any:
    """构建 v3 DeepAgent 实例（带上下文增强包装）。

    Args:
        checkpointer: 自定义 checkpointer（默认 in-memory）
        tools: 自定义 tool 列表（默认 ALL_TOOLS）
        enable_context_augment: 是否开启上下文增强（默认 True）

    Returns:
        ContextAwareAgent 包装（如果开启），或原始 LangGraph agent
    """
    cfg = load_llm_config()
    system_prompt = _load_prompts()

    llm = _build_llm(cfg)
    middleware = get_compliance_middleware_list()
    tools = tools or ALL_TOOLS
    checkpointer = checkpointer or get_checkpointer()

    logger.info(
        "Building v3 agent: model=%s, tools=%d, middleware=%d, checkpointer=%s, context_augment=%s",
        cfg["config"].get("model", "default"),
        len(tools),
        len(middleware),
        type(checkpointer).__name__,
        enable_context_augment,
    )

    inner_agent = create_agent(
        model=llm,
        system_prompt=system_prompt,
        tools=tools,
        middleware=middleware,
        checkpointer=checkpointer,
    )

    if enable_context_augment:
        return ContextAwareAgent(inner_agent)
    return inner_agent


class ContextAwareAgent:
    """上下文增强的 agent 包装

    自动从 checkpointer 拿最近历史，提取最后提到的产品，
    当前 query 没产品名时重写为"关于{产品}：{query}"。
    """

    def __init__(self, inner_agent: Any) -> None:
        self.inner = inner_agent

    def _get_history(self, config: dict | None) -> list:
        """从 checkpointer 拿历史消息"""
        if not config:
            return []
        try:
            state = self.inner.get_state(config)
            if state and state.values:
                return list(state.values.get("messages", []))
        except Exception as e:
            logger.debug("get_state failed: %s", e)
        return []

    def _get_current_text(self, message: Any) -> str:
        """从 message 提取文本"""
        if isinstance(message, dict):
            return message.get("content", "") or ""
        return getattr(message, "content", "") or ""

    def _augment_input(self, input_dict: dict, config: dict | None) -> dict:
        """增强 input 中的最后一条 user message"""
        messages = input_dict.get("messages", [])
        if not messages:
            return input_dict

        last = messages[-1]
        text = self._get_current_text(last)
        if not text:
            return input_dict

        # 拿历史（不包含当前）
        history = self._get_history(config)

        # 增强
        enhanced = augment_query(history, text)
        if enhanced == text:
            return input_dict  # 无需增强

        # 替换最后一条
        logger.info("[ctx_aug] '%s' → '%s'", text, enhanced)
        if isinstance(last, dict):
            new_msg = {**last, "content": enhanced}
            new_messages = list(messages[:-1]) + [new_msg]
        else:
            new_msg = HumanMessage(content=enhanced)
            new_messages = list(messages[:-1]) + [new_msg]

        return {**input_dict, "messages": new_messages}

    def invoke(self, input: Any, config: dict | None = None, **kwargs: Any) -> Any:
        """同步调用（带上下文增强）"""
        if isinstance(input, dict) and "messages" in input:
            input = self._augment_input(input, config)
        return self.inner.invoke(input, config=config, **kwargs)

    async def ainvoke(self, input: Any, config: dict | None = None, **kwargs: Any) -> Any:
        """异步调用（带上下文增强）"""
        if isinstance(input, dict) and "messages" in input:
            input = self._augment_input(input, config=config)
        return await self.inner.ainvoke(input, config=config, **kwargs)

    def stream(self, input: Any, config: dict | None = None, **kwargs: Any) -> Any:
        """流式调用（带上下文增强）"""
        if isinstance(input, dict) and "messages" in input:
            input = self._augment_input(input, config=config)
        return self.inner.stream(input, config=config, **kwargs)

    def get_state(self, *args: Any, **kwargs: Any) -> Any:
        return self.inner.get_state(*args, **kwargs)

    def __getattr__(self, name: str) -> Any:
        """其他属性透传给 inner agent"""
        return getattr(self.inner, name)


__all__ = ["build_agent", "ContextAwareAgent"]
