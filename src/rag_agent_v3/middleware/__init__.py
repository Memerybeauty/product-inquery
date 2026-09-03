"""v3 合规中间件链（6 件套 · 焊死）"""
from rag_agent_v3.middleware.text_compliance import (
    validate_text_response,
    force_direct_qa_bypass,
)
from rag_agent_v3.middleware.asset_compliance import (
    validate_asset_response,
    ASSET_TYPE_WHITELIST,
    ALLOWED_PRODUCTS,
)
from rag_agent_v3.middleware.disclaimer import (
    append_internet_disclaimer,
    INTERNET_DISCLAIMER,
)
from rag_agent_v3.middleware.short_circuit import short_circuit_tool_result

# 装饰器包装后的中间件用 __wrapped__ 拿原函数名
_MIDDLEWARE_NAMES = {
    "force_direct_qa_bypass": "QA 直返通道",
    "validate_text_response": "文本合规验证",
    "append_internet_disclaimer": "联网免责声明",
    "short_circuit_tool_result": "短路 tool → final answer",
}


def get_compliance_middleware_list() -> list:
    """返回合规中间件注册列表。

    顺序很关键：
    - 工具调用层先执行（force_direct_qa_bypass）
    - 模型输出层后执行（validate_text_response + append_internet_disclaimer + short_circuit）
    """
    return [
        force_direct_qa_bypass,
        short_circuit_tool_result,
        validate_text_response,
        append_internet_disclaimer,
    ]


def get_middleware_names() -> list[str]:
    """返回中间件名（用于日志/调试）"""
    return [getattr(m, "__name__", str(m)) for m in get_compliance_middleware_list()]


__all__ = [
    "validate_text_response",
    "force_direct_qa_bypass",
    "validate_asset_response",
    "ASSET_TYPE_WHITELIST",
    "ALLOWED_PRODUCTS",
    "append_internet_disclaimer",
    "INTERNET_DISCLAIMER",
    "short_circuit_tool_result",
    "get_compliance_middleware_list",
    "get_middleware_names",
]
