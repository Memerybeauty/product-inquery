# ADR-0003: Stub 接口先行（保留 MinIO 真实接入位置）

## 状态

已实现 (2026-09-03)

## 背景

v3 三路径架构中，**查资料路径**依赖 MinIO / 产品资产服务。本地开发阶段：
- 没有真实 MinIO
- 没有 release manifest
- 没有产品资产测试集

如果不做任何 stub，P0 阶段跑不通三路径 demo；如果等所有资源就绪再开发，又会拖慢节奏。

## 决策

**接口先行，stub 实现**：定义符合 v3 规范的 tool schema，先用 mock 数据填充，等真实资源就绪后替换实现。

### Stub 范围

| Tool | Stub 行为 | 真实接入点 |
|---|---|---|
| `list_file_catalog` | 返回 `_STUB_CATALOG` 静态数据 | MinIO manifest 查询 |
| `fetch_file_from_minio` | 返回 mock bytes（base64 编码） | boto3 流式取字节 |
| `search_qa_kb` | 无 MCP 时 fall back RAGFlow HTTP | MCP 客户端 |
| `search_rag_kb` | 直接 HTTP 调 RAGFlow（无 stub） | — |

### Stub 设计原则

1. **schema 不变**：返回的 JSON 结构与生产一致
2. **可替换**：实现细节集中在一个文件（`tools/files/minio.py`）
3. **可观测**：stub 标识（如 `bytes_b64` 前缀 `[STUB]`）便于调试
4. **合规先行**：`validate_asset_response` 中间件已实现，stub 也必经

## 后果

**正面**：
- P0 阶段可跑通三路径 demo
- 接口规范先定，避免后期重构
- 真实接入只需替换 `_STUB_CATALOG` 变量和 boto3 调用

**负面**：
- 测试可能通过 stub 通过，真实环境不一定通过
- 需要在 P2 阶段做"stub → 真实"切换的集成测试

## 真实接入触发条件

用户提供：
- MinIO endpoint / access key / secret key
- 产品资产 manifest（产品/类型/版本映射）
- 测试样本

## 实施

见 `src/rag_agent_v3/tools/files/minio.py`。
