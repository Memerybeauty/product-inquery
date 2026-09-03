"""v3 全部 tool 入口（11 个）"""
from rag_agent_v3.tools.route import route_user_intent
from rag_agent_v3.tools.knowledge import search_qa_kb, search_rag_kb
from rag_agent_v3.tools.files import list_file_catalog, fetch_file_from_minio
from rag_agent_v3.tools.search import internet_search
from rag_agent_v3.tools.grader import grade_answer_confidence
from rag_agent_v3.tools.clarify import clarify_user
from rag_agent_v3.tools.reject import reject_request
from rag_agent_v3.tools.capability import reply_capability

ALL_TOOLS: list = [
    # 路由
    route_user_intent,
    # 查问题路径
    search_qa_kb,
    search_rag_kb,
    grade_answer_confidence,
    internet_search,
    # 查资料路径
    list_file_catalog,
    fetch_file_from_minio,
    # 其他路径
    clarify_user,
    reject_request,
    reply_capability,
]

__all__ = [
    "route_user_intent",
    "search_qa_kb",
    "search_rag_kb",
    "grade_answer_confidence",
    "internet_search",
    "list_file_catalog",
    "fetch_file_from_minio",
    "clarify_user",
    "reject_request",
    "reply_capability",
    "ALL_TOOLS",
]
