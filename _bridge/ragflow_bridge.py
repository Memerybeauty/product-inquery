"""
RAGFlow 语义检索 MCP 桥接工具
供 WorkBuddy 在九典生图流水线 brief 阶段查询外部知识库产品信息与文案素材
"""
import os
import requests
from fastmcp import FastMCP

# ====== 从环境变量读取配置（不在代码中硬编码密钥） ======
BASE_URL = os.getenv("RAGFLOW_BASE_URL", "http://192.168.1.235:8081")
API_KEY = os.getenv("RAGFLOW_API_KEY", "")
# 知识库 ID 列表，逗号分隔；可覆盖默认值
DATASET_IDS_STR = os.getenv("RAGFLOW_DATASET_IDS", "54ebd702f1f211f0be81463b2845add5")
DATASET_IDS = [did.strip() for did in DATASET_IDS_STR.split(",") if did.strip()]
DEFAULT_TOP_K = int(os.getenv("RAGFLOW_DEFAULT_TOP_K", "15"))
MAX_TOP_K = int(os.getenv("RAGFLOW_MAX_TOP_K", "50"))
TIMEOUT = int(os.getenv("RAGFLOW_TIMEOUT_SECONDS", "15"))

mcp = FastMCP("ragflow-knowledge")


@mcp.tool()
def search_knowledge(query: str, top_k: int = DEFAULT_TOP_K) -> str:
    """在 RAGFlow 知识库中语义搜索产品信息、文案素材等资料。

    参数说明:
        query: 自然语言查询文本，如"钙维生素D片的适用人群和用法用量"
        top_k: 返回结果数量，默认 15，最大 50

    返回: 格式化的检索结果文本，包含内容片段、相似度分数和来源文档名
    """
    # 校验查询文本非空
    query = (query or "").strip()
    if not query:
        return "错误：查询内容不能为空，请提供要检索的问题。"

    # 限制 top_k 范围
    top_k = max(1, min(top_k, MAX_TOP_K))

    # ====== 构造 RAGFlow 检索请求体 ======
    # top_k 映射为 RAGFlow 的 page_size 字段
    payload = {
        "question": query,
        "dataset_ids": DATASET_IDS,
        "page_size": top_k,
        "highlight": False,
        "similarity_threshold": 0.2,
        "vector_similarity_weight": 0.7,
        "cross_languages": ["Chinese"],
    }

    # 拼接完整 URL（处理用户可能多写或漏写 http:// 的情况）
    base = BASE_URL.rstrip("/")
    if not base.startswith("http"):
        base = "http://" + base
    url = f"{base}/api/v1/retrieval"

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }

    # ====== 发送请求 & 错误处理 ======
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=TIMEOUT)
        resp.raise_for_status()
        result = resp.json()
    except requests.exceptions.Timeout:
        return f"错误：知识库检索超时（{TIMEOUT} 秒），请稍后重试。"
    except requests.exceptions.ConnectionError:
        return f"错误：无法连接到知识库服务（{url}），请检查网络和 RAGFlow 服务状态。"
    except requests.exceptions.HTTPError as e:
        return f"错误：知识库服务返回 HTTP {e.response.status_code}，请检查 API Key 是否有效。"
    except Exception as e:
        return f"错误：知识库检索异常 —— {e}"

    # ====== 解析返回结果 ======
    # 成功判断：code 为数字 0、字符串 "0" 或缺失
    code = result.get("code", 0)
    if str(code) != "0":
        msg = result.get("message", "未知错误")
        return f"知识库返回错误 (code={code}): {msg}"

    chunks = result.get("data", {}).get("chunks", [])
    if not chunks:
        return "知识库中未找到相关内容，请尝试更换查询词或确认知识库中已有相关资料。"

    # ====== 格式化为可读文本 ======
    lines = []
    for i, chunk in enumerate(chunks, 1):
        # 内容：优先 content 字段，其次 content_ltks
        content = chunk.get("content") or chunk.get("content_ltks", "")
        # 相似度分数：优先 similarity，其次 vector_similarity，兜底 0.0
        score = chunk.get("similarity") or chunk.get("vector_similarity", 0.0)
        # 文档名称
        doc_name = chunk.get("document_keyword") or chunk.get("document_name", "未知文档")

        lines.append(f"【{i}】相似度 {score:.2f} | 来源：{doc_name}")
        lines.append(content.strip())
        lines.append("---")

    return "\n".join(lines)


if __name__ == "__main__":
    mcp.run()
