# ADR-0001: v3 三路径架构

## 状态

提议中 (2026-09-03)

## 背景

RAG_agent 历史版本：

- **V1**（已归档）：6 路意图识别，12 工具，单次检索
- **V2**（已归档）：13 工具，CRAG 回环，自主增强
- **V3**（本 ADR）：11 工具，三路径路由，联网兜底，文件不改写，合规中间件焊死

V1/V2 的痛点：

1. 6 路路由写死在 system_prompt，新增意图需要改 prompt + 工具列表
2. 合规规则依赖模型自觉，漏报率高
3. 文件下发经过 LLM 改写，可能污染原文件
4. 无联网兜底，知识库无答案时只能拒答

## 决策

采用 **v3 三路径架构**：

1. **单层 DeepAgent 编排**：所有能力都是 tool，所有规则写在 system_prompt + middleware
2. **三路径路由**：DeepAgent 自主判断 `查问题 / 查资料 / 其他`，不写死
3. **查问题路径**：QA 知识库 → RAG 知识库 → 置信度不足 → 联网搜索 → 合规验证 → 改写 → 输出
4. **查资料路径**：查文件清单 → MinIO 取文件 → **不改写**（原始字节直附响应）
5. **合规收口 = 后处理中间件链**：模型无法绕过

## 工具清单（11 个）

| Tool | 路径 | 自主权 |
|---|---|---|
| route_user_intent | 路由 | DeepAgent 内部 |
| search_qa_kb | 查问题 | DeepAgent 自主 |
| search_rag_kb | 查问题 | DeepAgent 自主 |
| grade_answer_confidence | 查问题 | 评分器 |
| internet_search | 查问题 | DeepAgent 兜底 |
| list_file_catalog | 查资料 | DeepAgent 自主 |
| fetch_file_from_minio | 查资料 | DeepAgent 自主 |
| clarify_user | 其他 | DeepAgent 自主 |
| reject_request | 其他 | DeepAgent 自主 |
| reply_capability | 其他 | DeepAgent 自主 |
| memory_recall | 记忆 | DeepAgent 自主 |

## 合规中间件链（6 件套，焊死）

1. `validate_text_response` — 文本合规验证
2. `validate_asset_response` — 资产合规验证
3. `strip_source_block` — 剥离「资料依据」区块
4. `forbid_model_common_sense` — 禁止常识补全产品事实
5. `force_direct_qa_bypass` — serving_answer 直返通道
6. `append_internet_disclaimer` — 联网免责声明

## 阈值

- Doc 置信度阈值 = 0.7
- 联网置信度阈值 = 0.6

## 后果

- 模型无法绕过合规链，漏报 = 0
- 文件下发原文件 100% 一致
- 联网兜底扩展知识库覆盖
- 路由决策由 LLM 承担，需配套测试集

## 备选方案

- A. 沿用 V2 13 工具 + CRAG 回环：已验证，扩展性差
- B. v3 三路径（已选）：单层编排 + 焊死中间件
- C. 多 Agent 协作：复杂度高，本期不采用

## 实施计划

见 [开发计划](../../README.md)
