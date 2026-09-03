# rag-agent-v3 · 九典制药 · AI 助手

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)
[![Type checked: mypy](https://img.shields.io/badge/type%20checked-mypy-blue.svg)](http://mypy-lang.org/)

九典制药 AI 助手 v3 三路径架构（查问题 / 查资料 / 其他），基于 LangChain 1.0 + LangGraph 编排，合规中间件焊死。

## 快速开始

```bash
# 安装依赖
uv sync

# 运行本地 demo
uv run python -m rag_agent_v3

# 跑测试
uv run pytest
```

## 架构

v3 三路径：

```
用户消息
   │
   ▼
┌─────────────────────────────────────┐
│  DeepAgent（大脑，自主路由）           │
└─────────────────────────────────────┘
   │
   ├── 查问题路径：QA → RAG → 联网兜底
   ├── 查资料路径：清单 → MinIO 字节
   └── 其他路径：澄清 / 拒绝 / 能力
   │
   ▼
┌─────────────────────────────────────┐
│  6 件套合规中间件链（焊死）            │
└─────────────────────────────────────┘
```

详见 [docs/architecture.md](docs/architecture.md)

## 目录结构

```
src/rag_agent_v3/
├── agent.py                # DeepAgent 编排入口
├── middleware/             # 6 件套合规中间件
├── tools/                  # 11 个 tool
│   ├── knowledge/          # search_qa_kb / search_rag_kb
│   ├── files/              # list_file_catalog / fetch_file_from_minio
│   ├── search.py           # internet_search
│   ├── grader.py           # grade_answer_confidence
│   ├── clarify.py
│   ├── reject.py
│   └── capability.py
├── config/                 # LLM 配置 + system_prompt
└── storage/                # checkpointer
```

## 文档

- [架构说明](docs/architecture.md)
- [合规中间件](docs/compliance.md)
- [API 文档](docs/api.md)
- [ADR 决策记录](docs/adr/)

## 许可

MIT © 九典制药 AI 实验室
