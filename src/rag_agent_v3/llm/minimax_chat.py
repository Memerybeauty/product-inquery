"""
MiniMax LLM 适配（v3 · 自定义 ChatModel）
==========================================

MiniMax 公开 API（api.minimaxi.com）的 path 不标准（`/v1/text/chatcompletion_v2`），
不能直接用 `ChatOpenAI`。本类继承 `BaseChatModel`，用 httpx 调原生端点，
但保持 LangChain tool_call 协议兼容（用于 v3 DeepAgent 编排）。

== 配置 ==

```bash
MINIMAX_API_KEY=sk-cp-...
MINIMAX_BASE_URL=https://api.minimaxi.com/v1/text
MINIMAX_MODEL=MiniMax-Text-01
```
"""
from __future__ import annotations

import json
import logging
import os
from typing import Any, Iterator, Optional

import httpx
from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import (
    AIMessage,
    AIMessageChunk,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolCall,
    ToolMessage,
)
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.runnables import RunnableBinding

logger = logging.getLogger(__name__)

DEFAULT_BASE_URL = "https://api.minimaxi.com/v1/text"
DEFAULT_MODEL = "MiniMax-Text-01"
DEFAULT_TIMEOUT = 60.0


def _convert_message(msg: BaseMessage) -> dict:
    """LangChain BaseMessage → MiniMax 协议 dict"""
    if isinstance(msg, HumanMessage):
        return {"role": "user", "content": msg.content}
    if isinstance(msg, SystemMessage):
        return {"role": "system", "content": msg.content}
    if isinstance(msg, AIMessage):
        d: dict[str, Any] = {"role": "assistant", "content": msg.content}
        if msg.tool_calls:
            d["tool_calls"] = [
                {
                    "id": tc["id"],
                    "type": "function",
                    "function": {
                        "name": tc["name"],
                        "arguments": json.dumps(tc["args"], ensure_ascii=False),
                    },
                }
                for tc in msg.tool_calls
            ]
        return d
    if isinstance(msg, ToolMessage):
        return {
            "role": "tool",
            "tool_call_id": msg.tool_call_id,
            "content": msg.content if isinstance(msg.content, str) else json.dumps(msg.content, ensure_ascii=False),
        }
    # 兜底
    return {"role": "user", "content": str(msg.content)}


def _convert_tool(tool: Any) -> dict:
    """LangChain tool → MiniMax tool schema"""
    if hasattr(tool, "args") and hasattr(tool, "name"):
        return {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.args,
            },
        }
    if isinstance(tool, dict):
        return tool
    raise ValueError(f"Unsupported tool type: {type(tool)}")


def _parse_response(data: dict) -> AIMessage:
    """MiniMax 响应 → LangChain AIMessage"""
    choice = data["choices"][0]
    msg = choice["message"]
    content = msg.get("content", "") or ""
    tool_calls: list[ToolCall] = []
    for tc in msg.get("tool_calls") or []:
        fn = tc.get("function", {})
        try:
            args = json.loads(fn.get("arguments", "{}"))
        except json.JSONDecodeError:
            args = {"_raw": fn.get("arguments", "")}
        tool_calls.append(
            ToolCall(
                id=tc.get("id", ""),
                name=fn.get("name", ""),
                args=args,
            )
        )
    return AIMessage(content=content, tool_calls=tool_calls)


class MiniMaxChat(BaseChatModel):
    """MiniMax 自定义 ChatModel（兼容 LangChain tool_call 协议）"""

    api_key: str
    base_url: str = DEFAULT_BASE_URL
    model: str = DEFAULT_MODEL
    timeout: float = DEFAULT_TIMEOUT
    temperature: float = 0.3
    max_tokens: int = 4096

    @property
    def _llm_type(self) -> str:
        return "minimax-chat"

    @property
    def _identifying_params(self) -> dict:
        return {"model": self.model, "base_url": self.base_url}

    def _build_payload(
        self,
        messages: list[BaseMessage],
        stop: Optional[list[str]] = None,
        **kwargs: Any,
    ) -> dict:
        # 优先从 kwargs 取（bind_tools 时传入），其次从 self.kwargs 取
        bound_kwargs: dict[str, Any] = getattr(self, "kwargs", {}) or {}
        tools = kwargs.get("tools") or bound_kwargs.get("tools")
        tool_choice = kwargs.get("tool_choice") or bound_kwargs.get("tool_choice") or "auto"
        temperature = kwargs.get("temperature", bound_kwargs.get("temperature", self.temperature))
        max_tokens = kwargs.get("max_tokens", bound_kwargs.get("max_tokens", self.max_tokens))

        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [_convert_message(m) for m in messages],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if tools:
            payload["tools"] = [_convert_tool(t) for t in tools]
            payload["tool_choice"] = tool_choice
        if stop:
            payload["stop"] = stop
        return payload

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: Optional[list[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        payload = self._build_payload(messages, stop=stop, **kwargs)
        url = f"{self.base_url.rstrip('/')}/chatcompletion_v2"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        logger.debug("MiniMax POST %s · model=%s · msgs=%d", url, self.model, len(messages))

        with httpx.Client(timeout=self.timeout) as client:
            resp = client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()

        # Robust: 处理 choices 为 None 或缺失的情况
        if not data or not data.get("choices"):
            err_msg = data.get("base_resp", {}).get("status_msg") if data else "empty response"
            logger.error("MiniMax returned no choices: %s", err_msg)
            # 降级返回空内容 + 工具调用空，触发上层兜底
            return ChatResult(
                generations=[
                    ChatGeneration(
                        message=AIMessage(content="抱歉，服务暂时不可用，请稍后重试。")
                    )
                ]
            )

        ai_msg = _parse_response(data)
        return ChatResult(generations=[ChatGeneration(message=ai_msg)])

    def _stream(
        self,
        messages: list[BaseMessage],
        stop: Optional[list[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> Iterator[AIMessageChunk]:
        # 简化：非流式
        result = self._generate(messages, stop=stop, run_manager=run_manager, **kwargs)
        msg = result.generations[0].message
        yield AIMessageChunk(
            content=msg.content,
            tool_calls=[
                {
                    "id": tc["id"],
                    "name": tc["name"],
                    "args": tc["args"],
                    "index": i,
                }
                for i, tc in enumerate(msg.tool_calls or [])
            ] if msg.tool_calls else [],
        )

    def bind_tools(
        self,
        tools: list[Any],
        *,
        tool_choice: Optional[str] = None,
        **kwargs: Any,
    ) -> RunnableBinding:
        """绑定 tools 供 DeepAgent 编排使用

        实际工具 schema 在 _generate 时从 kwargs['tools'] 读取，
        这里只需返回一个 RunnableBinding 标记 tools 已绑定。
        """
        return self.bind(tools=list(tools), tool_choice=tool_choice or "auto")


def build_minimax_chat(
    api_key: str | None = None,
    model: str | None = None,
    base_url: str | None = None,
    temperature: float = 0.3,
    max_tokens: int = 4096,
) -> MiniMaxChat:
    """从环境变量构建 MiniMaxChat"""
    return MiniMaxChat(
        api_key=api_key or os.getenv("MINIMAX_API_KEY", ""),
        base_url=base_url or os.getenv("MINIMAX_BASE_URL", DEFAULT_BASE_URL),
        model=model or os.getenv("MINIMAX_MODEL", DEFAULT_MODEL),
        temperature=temperature,
        max_tokens=max_tokens,
    )


__all__ = ["MiniMaxChat", "build_minimax_chat"]
