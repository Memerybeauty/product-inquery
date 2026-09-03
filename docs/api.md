# API 文档

## 入口

```python
from rag_agent_v3 import build_agent

agent = build_agent()
result = agent.invoke(
    {"messages": [{"role": "user", "content": "酮洛芬的适应症"}]},
    config={"configurable": {"thread_id": "user-123"}},
)
```

## 11 个 Tool

### 1. route_user_intent
分析用户消息意图，决定走哪条路径。

### 2. search_qa_kb(question)
检索历史 QA 知识库。**命中时返回 `_bypass=True` 触发直返通道**。

### 3. search_rag_kb(question, product_id="", category="")
检索 RAG 知识库（Doc Dataset）。

### 4. grade_answer_confidence(evidence_type, evidence)
对证据做置信度评分。
- `evidence_type`: `doc`（QA+RAG） / `internet`（联网）
- `evidence`: JSON 字符串
- 返回：`{score, threshold, sufficient, recommendation}`

### 5. internet_search(query, max_results=5)
联网搜索兜底（duckduckgo）。返回的 `_meta.used_internet_search=True` 触发 disclaimer。

### 6. list_file_catalog(product_id, asset_type="", version="")
查询产品资产清单。

### 7. fetch_file_from_minio(asset_id, product_id, asset_type, version="")
取文件原始字节（不改写）。必经 `validate_asset_response` 合规验证。

### 8. clarify_user(text, original_request="")
引导用户澄清意图，返回 Pending 标记。

### 9. reject_request(reason)
拒绝越界请求。`reason` 可选值：
- `individual_treatment` — 个体化诊疗
- `competitor` — 竞品
- `system_info` — 系统信息
- `out_of_scope` — 其他越界

### 10. reply_capability()
回复能力说明。

### 11. memory_recall（v2 阶段补，本期未实现）
跨会话记忆。

## 中间件（焊死）

| 中间件 | 触发层级 |
|---|---|
| `force_direct_qa_bypass` | 工具调用 |
| `validate_text_response` | 模型输出 |
| `append_internet_disclaimer` | 模型输出 |

`validate_asset_response` 作为纯函数被 `fetch_file_from_minio` 内部调用。

## 环境变量

| 变量 | 默认值 | 说明 |
|---|---|---|
| `OPENAI_API_KEY` | — | LLM API key（必填） |
| `OPENAI_BASE_URL` | — | LLM base URL |
| `LLM_MODEL` | `qwen-3-5-plus-260215` | 模型名 |
| `CHECKPOINTER_BACKEND` | `memory` | `memory` / `sqlite` / `postgres` |
| `CONFIDENCE_THRESHOLD_DOC` | `0.7` | Doc 置信度阈值 |
| `CONFIDENCE_THRESHOLD_INTERNET` | `0.6` | 联网置信度阈值 |
| `INTERNET_SEARCH_ENABLED` | `true` | 是否启用联网 |
| `MCP_CONFIG_PATH` | `./config/mcp.json` | MCP 配置文件路径 |
| `RAGFLOW_BASE_URL` | `http://localhost:8081` | RAGFlow 兜底地址 |
| `RAGFLOW_API_KEY` | — | RAGFlow API key |
| `RAGFLOW_DATASET_TLF` | — | 酮洛芬 Dataset ID |
| `RAGFLOW_DATASET_DW` | — | 代温灸膏 Dataset ID |
| `RAGFLOW_QA_DATASET_ID` | — | QA Dataset ID |
| `MINIO_ENDPOINT` | `localhost:9100` | MinIO 地址（生产） |
| `MINIO_BUCKET` | `airag-files` | MinIO bucket |

## CLI

```bash
# 单轮 demo
uv run python -m rag_agent_v3 --query "酮洛芬的适应症"

# 交互模式
uv run python -m rag_agent_v3 --interactive

# 默认跑 3 个预设 case
uv run python -m rag_agent_v3
```
