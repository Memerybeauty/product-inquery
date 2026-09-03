"""
rag-agent-v3 CLI 入口（本地 demo）
==================================

用法：
    uv run python -m rag_agent_v3
    uv run python -m rag_agent_v3 --query "酮洛芬的适应症"
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# 加载 .env
load_dotenv()

logger = logging.getLogger(__name__)


def _setup_logging() -> None:
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO"),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )


def _run_demo(agent: object, query: str, thread_id: str = "demo") -> None:
    """跑一次单轮 demo"""
    from langchain_core.runnables import RunnableConfig

    config: RunnableConfig = {"configurable": {"thread_id": thread_id}}
    result = agent.invoke(
        {"messages": [{"role": "user", "content": query}]},
        config=config,
    )
    messages = result.get("messages", [])
    if messages:
        last = messages[-1]
        content = last.content if hasattr(last, "content") else str(last)
        print(f"\n>>> {content}\n")


def _run_interactive(agent: object) -> None:
    """交互式 demo"""
    from langchain_core.runnables import RunnableConfig

    thread_id = "interactive"
    config: RunnableConfig = {"configurable": {"thread_id": thread_id}}
    print("=" * 60)
    print("  九典AI助手 · v3 demo (输入 'exit' 退出)")
    print("=" * 60)
    while True:
        try:
            query = input("\n您: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not query or query.lower() == "exit":
            break
        try:
            result = agent.invoke(
                {"messages": [{"role": "user", "content": query}]},
                config=config,
            )
            messages = result.get("messages", [])
            if messages:
                last = messages[-1]
                content = last.content if hasattr(last, "content") else str(last)
                print(f"\n助手: {content}")
        except Exception as e:
            print(f"\n[错误] {e}", file=sys.stderr)


def main() -> None:
    _setup_logging()
    parser = argparse.ArgumentParser(description="rag-agent-v3 demo")
    parser.add_argument("--query", "-q", type=str, default=None, help="单轮查询")
    parser.add_argument("--interactive", "-i", action="store_true", help="交互模式")
    args = parser.parse_args()

    # 延迟导入（避免未装依赖时也能 --help）
    from rag_agent_v3 import build_agent

    logger.info("Building v3 agent...")
    agent = build_agent()

    if args.query:
        _run_demo(agent, args.query)
    elif args.interactive:
        _run_interactive(agent)
    else:
        # 默认：跑几个预设 case
        for q in [
            "你好",
            "酮洛芬的适应症是什么？",
            "发代温灸膏的说明书",
        ]:
            print(f"\n>>> Query: {q}")
            _run_demo(agent, q, thread_id=f"preset-{hash(q) % 1000}")


if __name__ == "__main__":
    main()
