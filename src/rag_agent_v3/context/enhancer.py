"""
上下文增强器（v3 · 多轮对话）
==============================

解决"用户省略主语"问题（如"它有什么副作用"中的"它"指代什么）。

== 流程 ==

```
用户当前消息 + 最近 10 条历史
        ↓
[1] 提取当前消息里的产品（关键词匹配）
        ↓ 命中
[2] 直接用原消息（无需增强）
        ↓ 未命中
[3] 从最近 10 条历史里找最后提到的产品
        ↓ 找到
[4] 重写："关于{产品}：{当前消息}"
        ↓ 没找到
[5] 直接用原消息（不增强）
```

== 用法 ==

```python
from rag_agent_v3.context import augment_query

history = [
    {"role": "user", "content": "酮洛芬的适应症是什么"},
    {"role": "assistant", "content": "酮洛芬适用于..."},
    {"role": "user", "content": "它有什么副作用"},  # 省略主语
]
current = "它有什么副作用"
enhanced = augment_query(history, current)
# → "关于酮洛芬：它有什么副作用"
```
"""
from __future__ import annotations

import re
from typing import Any

# 已知产品关键词（含九典 + 竞品/外部药品）
# 顺序很重要：从长到短，避免"酮洛芬凝胶贴膏"匹配到"酮洛芬"先
PRODUCT_KEYWORDS: list[str] = [
    # 九典产品（最优先）
    "酮洛芬凝胶贴膏",
    "酮洛芬",
    "代温灸膏",
    # 常见竞品 / 外部药品
    "洛索洛芬",
    "洛索",
    "扶他林",
    "双氯芬酸",
    "西乐葆",
    "塞来昔布",
    "芬太尼",
    "布洛芬",
    "对乙酰氨基酚",
    "阿司匹林",
    "美洛昔康",
    "尼美舒利",
    "塞来考昔",
]

# 整合模板
AUGMENT_TEMPLATE: str = "关于{product}：{query}"


def _get_text(message: Any) -> str:
    """从 message dict 或对象提取文本"""
    if isinstance(message, dict):
        return message.get("content", "") or ""
    return getattr(message, "content", "") or ""


def _get_role(message: Any) -> str:
    """从 message dict 或对象提取 role"""
    if isinstance(message, dict):
        return message.get("role", "")
    return getattr(message, "type", "")  # HumanMessage/AIMessage → 不直接有 role


def _has_product_in_text(text: str) -> str | None:
    """检查文本里是否含产品关键词，返回匹配的产品名"""
    for kw in PRODUCT_KEYWORDS:
        if kw in text:
            return kw
    return None


def _extract_product_from_history(messages: list, lookback: int = 10) -> str | None:
    """从最近 N 条消息中提取最后提到的产品（按时间倒序）"""
    recent = messages[-lookback:] if len(messages) > lookback else messages
    for msg in reversed(recent):
        text = _get_text(msg)
        if not text:
            continue
        product = _has_product_in_text(text)
        if product:
            return product
    return None


def augment_query(
    messages: list[Any],
    current_query: str,
    template: str = AUGMENT_TEMPLATE,
    lookback: int = 10,
) -> str:
    """根据上下文增强当前 query

    Args:
        messages: 历史消息列表（不含当前 query）
        current_query: 用户当前问题
        template: 整合模板，默认 "关于{product}：{query}"
        lookback: 看多少条历史，默认 10

    Returns:
        增强后的 query（如果无需增强，返回原 query）
    """
    # 1. 当前问题含产品 → 不增强
    if _has_product_in_text(current_query):
        return current_query

    # 2. 从历史里提取产品
    product = _extract_product_from_history(messages, lookback=lookback)

    # 3. 没找到 → 不增强
    if not product:
        return current_query

    # 4. 整合
    return template.format(product=product, query=current_query)


def get_last_product(messages: list[Any], lookback: int = 10) -> str | None:
    """公开 API：获取最近 N 条消息里最后提到的产品"""
    return _extract_product_from_history(messages, lookback=lookback)


__all__ = ["augment_query", "get_last_product", "PRODUCT_KEYWORDS"]
