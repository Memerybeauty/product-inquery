"""
DeepAgent 编排入口（v3）
========================

基于 LangChain 1.0 `create_agent` + LangGraph checkpointer：
- 11 个 tool（v3 三路径）
- 6 件套合规中间件（焊死）
- system_prompt 三路径规则

== 用法 ==

```python
from rag_agent_v3 import build_agent
agent = build_agent()
result = agent.invoke({"messages": [{"role": "user", "content": "酮洛芬的适应症"}]})
```
"""
from __future__ import annotations

import logging
import os
from typing import Any

from langchain.agents import create_agent
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.base import BaseCheckpointSaver

from rag_agent_v3.config import load_llm_config, load_prompt
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


def _build_llm(cfg: dict) -> ChatOpenAI:
    """构建 LLM 实例"""
    api_key = os.getenv("OPENAI_API_KEY") or os.getenv("COZE_WORKLOAD_IDENTITY_API_KEY", "")
    base_url = os.getenv("OPENAI_BASE_URL") or os.getenv("COZE_INTEGRATION_MODEL_BASE_URL")
    model_cfg = cfg.get("config", {})

    return ChatOpenAI(
        model=model_cfg.get("model"),
        api_key=api_key,
        base_url=base_url,
        temperature=model_cfg.get("temperature", 0.3),
        streaming=True,
        timeout=model_cfg.get("timeout", 600),
        extra_body={"thinking": {"type": model_cfg.get("thinking", "disabled")}},
    )


def build_agent(
    checkpointer: BaseCheckpointSaver | None = None,
    tools: list | None = None,
) -> Any:
    """构建 v3 DeepAgent 实例。

    Args:
        checkpointer: 自定义 checkpointer（默认 in-memory）
        tools: 自定义 tool 列表（默认 ALL_TOOLS）

    Returns:
        编译后的 LangGraph agent
    """
    cfg = load_llm_config()
    system_prompt = _load_prompts()

    llm = _build_llm(cfg)
    middleware = get_compliance_middleware_list()
    tools = tools or ALL_TOOLS
    checkpointer = checkpointer or get_checkpointer()

    logger.info(
        "Building v3 agent: tools=%d, middleware=%d, checkpointer=%s",
        len(tools),
        len(middleware),
        type(checkpointer).__name__,
    )

    return create_agent(
        model=llm,
        system_prompt=system_prompt,
        tools=tools,
        middleware=middleware,
        checkpointer=checkpointer,
    )


__all__ = ["build_agent"]
