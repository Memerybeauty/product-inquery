# 合规中间件说明

v3 架构的核心设计：**6 件套合规中间件焊死，模型无法绕过**。

## 6 件套一览

| # | 名称 | 层级 | 触发条件 | 行为 |
|---|---|---|---|---|
| 1 | `force_direct_qa_bypass` | 工具调用 | `search_qa_kb` 返回 `_bypass=True` | 打标，bypass 通道直返 |
| 2 | `validate_text_response` | 模型输出 | 每次模型输出 | 越界 / 空响应 → 固定话术 |
| 3 | `strip_source_block` | 模型输出 | 同上 | 剥离「资料依据」区块 |
| 4 | `forbid_model_common_sense` | 模型输出 | 同上 | 剥离模型常识补全 |
| 5 | `validate_asset_response` | 工具调用 | `fetch_file_from_minio` 每次调用 | 白名单 + 否定识别 + 版本对齐 |
| 6 | `append_internet_disclaimer` | 模型输出 | `used_internet_search=True` | 附联网免责声明 |

## 中间件 vs system_prompt

| 维度 | system_prompt | 中间件 |
|---|---|---|
| 能否被模型绕过 | ✅ 可以 | ❌ 不行 |
| 单元测试覆盖 | 难 | 易 |
| 性能开销 | 无 | 微小 |
| 调试可见性 | 隐藏在 prompt | 显式函数调用 |

## 关键设计：QA 直返通道

```python
# search_qa_kb 返回
{"status": "success", "qa": {"serving_answer": "..."}, "_bypass": True}

# force_direct_qa_bypass 中间件检测到 _bypass=True
# 打标 response_metadata["direct_qa_bypass"] = True

# validate_text_response 检查到 bypass 标记
# → 跳过所有改写，直接返回
```

这样**模型无论如何都改不了 serving_answer**，保证产品官方话术的准确性。

## 关键设计：联网 disclaimer 必附

```python
# internet_search 返回
{"_meta": {"used_internet_search": True}}

# append_internet_disclaimer 中间件检测到
# → 自动追加：
"\n\n---\n📌 **以上内容来自互联网，仅供参考，不构成医疗建议。**"
```

## 测试覆盖

见 `tests/unit/test_middleware.py`：
- `TestTextCompliance` — 文本合规 5 个测试
- `TestAssetCompliance` — 资产合规 13 个测试（含参数化白名单）
- `TestDisclaimer` — 固定模板 2 个测试

## 调试

中间件执行日志前缀：
- `[bypass]` — QA 直返通道
- `[validate]` — 文本合规
- `[disclaimer]` — 联网 disclaimer

设置 `LOG_LEVEL=DEBUG` 可看每次工具调用的中间件触发情况。
