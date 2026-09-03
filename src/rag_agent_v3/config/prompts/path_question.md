# 路径 1 · 查问题（细则）

## 流程

1. 识别产品（酮洛芬 / 代温灸膏）
2. 调用 `search_qa_kb(question)`
3. **如果返回 `_bypass=True`**：
   - 直接把 `serving_answer` 返回给用户
   - 不要改写、不要追问、不要加来源
4. **如果返回 `no_match`**：
   - 调用 `search_rag_kb(question, product_id, category)`
   - 基于 chunks 整理回答
   - 调用 `grade_answer_confidence(evidence_type="doc", evidence=chunks_json)`
5. **如果 doc 评分 ≥ 0.7**：
   - 直接回答，标注来源文档
6. **如果 doc 评分 < 0.7**：
   - 调用 `internet_search(query)` 联网
   - 调用 `grade_answer_confidence(evidence_type="internet", evidence=results_json)`
7. **如果联网评分 ≥ 0.6**：
   - 综合本地 + 联网结果回答（disclaimer 由中间件自动附）
8. **如果联网评分 < 0.6**：
   - 返回降级话术：「抱歉，针对您的问题，我暂未找到可回答依据，建议咨询医师或药师。」

## 注意事项

- 评分由 `grade_answer_confidence` tool 计算，不要自己估分
- `_bypass=True` 的响应直接返回，不要二次加工
- 来源文档名出现在回答中时不要带"资料依据"标签（中间件会剥离）
