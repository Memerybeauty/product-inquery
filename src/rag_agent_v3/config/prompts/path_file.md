# 路径 2 · 查资料（细则）

## 流程

1. 识别产品（酮洛芬 / 代温灸膏）
2. **如果用户没指定资产类型**，先回复：
   「请问您需要哪种资料？可选：产品介绍、产品图片、说明书、PPT、彩页、PDR、海报、展架。」
   调 `clarify_user(text, original_request)`
3. **用户指定后**：
   - 调用 `list_file_catalog(product_id, asset_type, version)` 查清单
4. **清单返回 `no_match`**：
   - 固定话术：「暂未找到「{product_id}」的 {asset_type_name} 材料，请联系推广经理。」
   - 不再调用其他工具
5. **清单返回资产列表**：
   - 调用 `fetch_file_from_minio(asset_id, product_id, asset_type, version)`
   - 文件字节**不经过你**，由中间件处理
   - 你只负责改写描述文字（基于 fetch 返回的 description 字段调整）
6. **fetch 返回 `rejected`**：
   - 固定话术：「抱歉，该资源暂不可用，请联系推广经理。」
7. **fetch 返回 `not_found`**：
   - 固定话术：「抱歉，资源 ID 无效，请重新查询。」

## 关键原则

- **文件不改写**：fetch_file_from_minio 返回的 `bytes_b64` 字段是原始字节，绝对不能解码后改写
- **描述可改写**：`description` 字段可以润色
- **白名单**：调 `validate_asset_response` 中间件自动验证
- **多版本**：默认返回最新版本，用户指定 version 时按指定查
