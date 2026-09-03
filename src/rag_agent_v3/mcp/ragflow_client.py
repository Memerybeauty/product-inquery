"""
RAGFlow MCP 客户端（v3 · 接入 RAG 检索）
=========================================

启动 stdio MCP server（ragflow_bridge.py），通过 MCP 协议调用
`search_knowledge` tool，封装为 Python 函数供 RAG 工具使用。

== 用法 ==

```python
from rag_agent_v3.mcp.ragflow_client import RAGFlowMCPClient

client = RAGFlowMCPClient(bridge_script="path/to/ragflow_bridge.py")
result = client.search("酮洛芬的适应症", top_k=5)
client.close()
```
"""
from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class RAGFlowMCPClient:
    """RAGFlow MCP stdio 客户端

    启动 ragflow_bridge.py 作为子进程，通过 MCP 协议调用 tool。
    """

    def __init__(
        self,
        bridge_script: str | Path,
        env: dict[str, str] | None = None,
        timeout: float = 30.0,
    ) -> None:
        self.bridge_script = Path(bridge_script)
        self.timeout = timeout
        # 合并环境变量（继承当前 + 用户传入）
        self.env = {**os.environ, **(env or {})}
        self._proc: subprocess.Popen | None = None
        self._session: Any = None  # mcp.ClientSession
        self._loop: Any = None
        self._ready = False

    def _ensure_started(self) -> None:
        """懒启动：首次调用时启动 MCP server"""
        if self._ready:
            return
        if not self.bridge_script.exists():
            raise FileNotFoundError(f"MCP bridge script not found: {self.bridge_script}")

        # 启动 stdio 子进程
        self._proc = subprocess.Popen(
            [sys.executable, str(self.bridge_script)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=self.env,
            text=False,
            bufsize=0,
        )
        logger.info("MCP server started, pid=%d", self._proc.pid)

        # 用官方 mcp SDK 建 session
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client

        server_params = StdioServerParameters(
            command=sys.executable,
            args=[str(self.bridge_script)],
            env=self.env,
        )

        # 异步 session 在同步上下文里跑
        import asyncio
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)

        # 启 transport + session
        self._stdio_ctx = stdio_client(server_params)
        read_stream, write_stream = self._loop.run_until_complete(self._stdio_ctx.__aenter__())
        self._session = ClientSession(read_stream, write_stream)
        self._loop.run_until_complete(self._session.__aenter__())
        self._loop.run_until_complete(self._session.initialize())
        self._ready = True
        logger.info("MCP session initialized")

    def search(self, query: str, top_k: int = 5) -> str:
        """调用 search_knowledge tool

        Args:
            query: 自然语言查询
            top_k: 返回数量

        Returns:
            MCP 返回的文本内容
        """
        self._ensure_started()
        assert self._session is not None
        result = self._loop.run_until_complete(
            self._session.call_tool(
                "search_knowledge",
                {"query": query, "top_k": top_k},
            )
        )
        # result.content 是 list[TextContent]
        if result.content and hasattr(result.content[0], "text"):
            return result.content[0].text
        return str(result.content)

    def close(self) -> None:
        """关闭 session + 子进程"""
        if not self._ready:
            return
        try:
            if self._session:
                self._loop.run_until_complete(self._session.__aexit__(None, None, None))
            if hasattr(self, "_stdio_ctx"):
                self._loop.run_until_complete(self._stdio_ctx.__aexit__(None, None, None))
            if self._loop:
                self._loop.close()
        except Exception as e:
            logger.warning("Error closing MCP session: %s", e)
        finally:
            if self._proc and self._proc.poll() is None:
                self._proc.terminate()
                try:
                    self._proc.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    self._proc.kill()
            self._ready = False
            logger.info("MCP server closed")

    def __enter__(self) -> "RAGFlowMCPClient":
        self._ensure_started()
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()


# 全局单例（懒加载）
_client: RAGFlowMCPClient | None = None


def get_ragflow_client() -> RAGFlowMCPClient:
    """获取全局 MCP client 单例"""
    global _client
    if _client is None:
        # 默认从仓库根 _bridge/ 目录加载
        bridge_path = Path(__file__).parent.parent.parent.parent / "_bridge" / "ragflow_bridge.py"
        if not bridge_path.exists():
            # 备选：环境变量指定
            env_path = os.getenv("RAGFLOW_BRIDGE_SCRIPT")
            if env_path:
                bridge_path = Path(env_path)
        if not bridge_path.exists():
            raise FileNotFoundError(
                f"RAGFlow bridge script not found. Place at {bridge_path} or set RAGFLOW_BRIDGE_SCRIPT env."
            )
        _client = RAGFlowMCPClient(bridge_path)
    return _client


__all__ = ["RAGFlowMCPClient", "get_ragflow_client"]
