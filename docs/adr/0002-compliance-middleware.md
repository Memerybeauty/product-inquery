# ADR-0002: 合规中间件链（6 件套焊死）

## 状态

已实现 (2026-09-03)

## 背景

V1 时代，合规规则写在 system_prompt，依赖模型自觉。**漏报率高**——LLM 有时会编造产品事实、夹带「资料依据」标签、跳过竞品拒绝。

V3 设计目标：合规规则**与模型解耦**，无论模型怎么调工具，最终响应都要走合规链。

## 决策

采用 LangChain 1.0 middleware 机制实现 6 件套合规中间件，**注册后模型无法绕过**。

### 6 件套清单

| # | 中间件 | 层级 | 功能 |
|---|---|---|---|
| 1 | `force_direct_qa_bypass` | 工具调用 | QA 命中打 `_bypass=True` 标记 |
| 2 | `validate_text_response` | 模型输出 | 越界 / 空响应 → 固定话术 |
| 3 | `strip_source_block` | 模型输出 | 剥离「资料依据」区块 |
| 4 | `forbid_model_common_sense` | 模型输出 | 禁止模型常识补全产品事实 |
| 5 | `validate_asset_response` | 工具调用 | 资产白名单 + 否定识别 + 版本对齐 |
| 6 | `append_internet_disclaimer` | 模型输出 | 联网结果附免责声明 |

### 实现层

- **工具调用层**：`@wrap_tool_call` 装饰器
- **模型输出层**：`@after_model` 装饰器

### 注册顺序

```python
middleware = [
    force_direct_qa_bypass,         # 1. 工具调用：QA 直返打标
    validate_text_response,         # 2-4. 模型输出：合规收口（合一）
    append_internet_disclaimer,     # 6. 模型输出：disclaimer
]
```

`validate_asset_response` 作为纯函数被 `fetch_file_from_minio` tool 内部调用，不在 middleware 列表。

## 后果

**正面**：
- 合规漏报 = 0（中间件必经）
- 模型改写 QA 直返内容被强制绕过
- 联网结果 100% 附 disclaimer
- 单元测试 + 集成测试可独立验证合规链

**负面**：
- 中间件调试增加一层间接性
- 需要维护 6 件套一致性

## 备选方案

- A. 全部写在 system_prompt：V1 时代做法，漏报率高
- B. 后处理链（hook on response）：与 middleware 机制等价
- C. 多 Agent 分离（合规 Agent + 业务 Agent）：复杂度高，本期不采用

## 实施

见 `src/rag_agent_v3/middleware/`，单元测试 `tests/unit/test_middleware.py`。
