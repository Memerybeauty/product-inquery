"""
路由决策（v3 · 1 个 tool）
=========================

route_user_intent: DeepAgent 内部自主决策三路径（查问题 / 查资料 / 其他）

不写死规则——由 LLM 在 system_prompt 引导下自主选择。
本文件只暴露 tool 描述和元信息。
"""
from langchain.tools import tool


@tool
def route_user_intent(text: str) -> str:
    """分析用户消息意图，决定走哪条路径。

    三路径：
    - 查问题：用户询问产品用法、适应症、介绍、卖点等
    - 查资料：用户索要说明书、海报、PPT、彩页等文件
    - 其他：问候、越界、能力询问

    Args:
        text: 用户消息文本

    Returns:
        路径名（question / file / other）
    """
    # 实际由 LLM 自主判断，此处仅暴露 tool schema
    return "question"


__all__ = ["route_user_intent"]
