"""
能力说明工具（v3 · 1 个 tool）
==============================

reply_capability: 当用户问候或询问"你能做什么"时，输出能力说明 + 示例。
"""
from __future__ import annotations

import json

from langchain.tools import tool

CAPABILITY_MESSAGE: str = """我是**九典AI助手**，可以帮您：

1. **了解产品**：查询酮洛芬凝胶贴膏、代温灸膏等产品的成分、适应症、用法用量等
2. **下载资料**：一键获取说明书、PPT、彩页、海报等推广材料
3. **生成话术**：面向医生和销售渠道的合规推广话术

试试这样问我：
- "酮洛芬的适应症是什么？"
- "发代温灸膏的说明书"
- "酮洛芬的核心卖点"
"""


@tool
def reply_capability() -> str:
    """回复能力说明。"""
    return json.dumps(
        {"status": "success", "message": CAPABILITY_MESSAGE},
        ensure_ascii=False,
    )


__all__ = ["reply_capability", "CAPABILITY_MESSAGE"]
