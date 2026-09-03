"""
直接调 agent 的测试脚本（绕过飞书 bot）
========================================

不依赖飞书 WebSocket / 事件订阅，直接模拟飞书用户消息调 agent。
用于本地测试 v3 三路径 + 中间件，不被飞书后端配置卡住。

== 用法 ==

```bash
# 跑预设 6 个 case（覆盖三路径）
uv run python scripts/test_bot_direct.py

# 自定义单条
uv run python scripts/test_bot_direct.py --query "酮洛芬的适应症"

# 多条
uv run python scripts/test_bot_direct.py --queries "你好" "酮洛芬的适应症" "扶他林的副作用"

# 交互模式（输入 exit 退出）
uv run python scripts/test_bot_direct.py --interactive
```
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from pathlib import Path

# 加载 .env
from dotenv import load_dotenv
load_dotenv()

# 加 src 到 path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# 预设测试用例：覆盖三路径
DEFAULT_CASES = [
    ("你好", "capability"),
    ("酮洛芬的适应症是什么", "question"),
    ("代温灸膏怎么用", "question"),
    ("发代温灸膏的说明书", "file"),
    ("酮洛芬的PPT", "file"),
    ("扶他林的副作用", "reject"),
    ("你是什么模型", "reject"),
]


def run_query(agent, query: str, user_id: str = "test_user") -> dict:
    """跑单条查询"""
    from langchain_core.runnables import RunnableConfig

    config: RunnableConfig = {"configurable": {"thread_id": f"direct:{user_id}"}}

    t0 = time.time()
    try:
        result = agent.invoke(
            {"messages": [{"role": "user", "content": query}]},
            config=config,
        )
        messages = result.get("messages", [])
        elapsed = time.time() - t0

        if not messages:
            return {"query": query, "error": "no messages", "elapsed_s": elapsed}

        last = messages[-1]
        content = last.content if hasattr(last, "content") else str(last)

        # 统计 tool_calls
        tool_calls = sum(
            len(m.tool_calls or [])
            for m in messages
            if hasattr(m, "tool_calls")
        )

        return {
            "query": query,
            "response": content if isinstance(content, str) else str(content),
            "tool_calls": tool_calls,
            "elapsed_s": round(elapsed, 2),
            "msgs_count": len(messages),
        }
    except Exception as e:
        return {
            "query": query,
            "error": f"{type(e).__name__}: {e}",
            "elapsed_s": round(time.time() - t0, 2),
        }


def print_result(result: dict, expected: str | None = None) -> None:
    """打印单条结果"""
    print("\n" + "=" * 70)
    print(f"Q: {result['query']}")
    if expected:
        print(f"   预期路径: {expected}")
    if "error" in result:
        print(f"❌ 错误: {result['error']}")
        print(f"⏱  耗时: {result['elapsed_s']}s")
        return
    print(f"⏱  耗时: {result['elapsed_s']}s · tool_calls={result['tool_calls']} · msgs={result['msgs_count']}")
    print("-" * 70)
    print(result["response"])


def main() -> None:
    parser = argparse.ArgumentParser(description="直接调 agent 测试（绕过飞书）")
    parser.add_argument("--query", "-q", type=str, help="单条问题")
    parser.add_argument("--queries", nargs="+", help="多条问题")
    parser.add_argument("--interactive", "-i", action="store_true", help="交互模式")
    parser.add_argument("--user", type=str, default="test_user", help="模拟用户 ID")
    parser.add_argument("--multi-turn", "-m", nargs="+", help="多轮对话（顺序传入）")
    args = parser.parse_args()

    # 加载 agent
    from rag_agent_v3 import build_agent
    logger.info("Building v3 agent...")
    agent = build_agent()
    logger.info("Agent ready")

    if args.interactive:
        print("=" * 70)
        print("  直接调 agent 测试（输入 exit 退出）")
        print("=" * 70)
        while True:
            try:
                query = input("\nQ: ").strip()
            except (EOFError, KeyboardInterrupt):
                break
            if not query or query.lower() == "exit":
                break
            result = run_query(agent, query, args.user)
            print_result(result)
        return

    # 多轮对话模式：测试上下文增强
    if args.multi_turn:
        print(f"\n>>> 多轮对话测试 · 共 {len(args.multi_turn)} 轮\n")
        from langchain_core.runnables import RunnableConfig
        config = RunnableConfig(configurable={"thread_id": f"multi-turn:{args.user}"})

        for i, q in enumerate(args.multi_turn, 1):
            print(f"\n[第 {i} 轮]")
            result = run_query(agent, q, args.user)
            print_result(result)
        return

    # 决定测试集
    if args.query:
        cases = [(args.query, None)]
    elif args.queries:
        cases = [(q, None) for q in args.queries]
    else:
        cases = DEFAULT_CASES

    print(f"\n>>> 直接调 agent 测试 · 共 {len(cases)} 条\n")

    passed = 0
    failed = 0
    for query, expected in cases:
        result = run_query(agent, query, args.user)
        print_result(result, expected)
        if "error" in result:
            failed += 1
        else:
            passed += 1

    print("\n" + "=" * 70)
    print(f"汇总: 通过 {passed} · 失败 {failed} · 总计 {len(cases)}")
    print("=" * 70)


def demo_conversation() -> None:
    """演示多轮对话上下文增强"""
    from rag_agent_v3 import build_agent
    from rag_agent_v3.context import augment_query, get_last_product
    from langchain_core.runnables import RunnableConfig

    print("=" * 70)
    print("  多轮对话上下文增强 demo")
    print("=" * 70)

    # 演示增强器
    history = [
        {"role": "user", "content": "酮洛芬的适应症是什么？"},
        {"role": "assistant", "content": "酮洛芬适用于骨关节炎..."},
        {"role": "user", "content": "代温灸膏呢？"},
        {"role": "assistant", "content": "代温灸膏用于风寒痹病..."},
        {"role": "user", "content": "它有什么副作用？"},  # "它" 指代？
    ]
    current = "它有什么副作用？"
    enhanced = augment_query(history, current)
    print(f"\n历史最后提到: {get_last_product(history)}")
    print(f"原始 query:  {current}")
    print(f"增强 query:  {enhanced}")

    # 真实跑 agent
    print("\n>>> 真跑 agent（多轮）")
    agent = build_agent()
    config = RunnableConfig(configurable={"thread_id": "context-demo"})

    for q in ["酮洛芬的适应症是什么？", "它有什么副作用？", "代温灸膏呢？", "它能长期用吗？"]:
        enhanced = augment_query(
            [m for m in [{"role": "user", "content": "（历史）"}]],
            q,
        )
        # 实际跑用 history messages 通过 checkpointer 维持
        result = agent.invoke(
            {"messages": [{"role": "user", "content": q}]},
            config=config,
        )
        last = result["messages"][-1]
        response = last.content if hasattr(last, "content") else str(last)
        print(f"\nQ: {q}")
        print(f"A: {response[:200]}")


if __name__ == "__main__":
    main()
