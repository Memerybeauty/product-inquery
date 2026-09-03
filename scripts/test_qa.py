"""
问答测试脚本
============

通过 MCP 桥接包 + RAGFlow 真实环境跑问答测试。

== 用法 ==

```bash
# 默认 3 个测试问题
uv run python scripts/test_qa.py

# 自定义问题
uv run python scripts/test_qa.py --query "酮洛芬的适应症是什么"

# 指定多个问题
uv run python scripts/test_qa.py --queries "问题1" "问题2"
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

DEFAULT_QUERIES = [
    "酮洛芬的适应症是什么？",
    "代温灸膏怎么用？",
    "酮洛芬和布洛芬有什么区别？",
]


def run_query(query: str, top_k: int = 5) -> dict:
    """跑单条查询"""
    from rag_agent_v3.mcp.ragflow_client import get_ragflow_client

    client = get_ragflow_client()
    try:
        t0 = time.time()
        result = client.search(query, top_k=top_k)
        elapsed = time.time() - t0
        return {
            "query": query,
            "elapsed_s": round(elapsed, 3),
            "raw": result,
        }
    except Exception as e:
        return {
            "query": query,
            "error": str(e),
            "elapsed_s": 0,
        }
    finally:
        try:
            client.close()
        except Exception:
            pass


def main() -> None:
    parser = argparse.ArgumentParser(description="问答测试")
    parser.add_argument("--query", "-q", type=str, help="单条问题")
    parser.add_argument("--queries", nargs="+", help="多条问题")
    parser.add_argument("--top-k", type=int, default=5, help="top_k")
    args = parser.parse_args()

    if args.query:
        queries = [args.query]
    elif args.queries:
        queries = args.queries
    else:
        queries = DEFAULT_QUERIES

    print("=" * 70)
    print(f"问答测试 · 共 {len(queries)} 条")
    print("=" * 70)

    for i, q in enumerate(queries, 1):
        print(f"\n[{i}/{len(queries)}] Q: {q}")
        result = run_query(q, top_k=args.top_k)
        if "error" in result:
            print(f"  ❌ 错误: {result['error']}")
        else:
            print(f"  ⏱  耗时: {result['elapsed_s']}s")
            raw = result["raw"]
            # 显示前 500 字符
            preview = raw[:500] + ("..." if len(raw) > 500 else "")
            print(f"  📄 响应:\n{preview}")

    print("\n" + "=" * 70)
    print("测试完成")


if __name__ == "__main__":
    main()
