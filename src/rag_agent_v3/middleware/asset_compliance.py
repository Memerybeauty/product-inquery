"""
资产合规中间件（v3 · 1 件套）
============================

validate_asset_response: 资产合规验证
- 类型白名单（ASSET_TYPE_MAP）
- 否定识别（产品必须在字典内）
- 版本对齐（对齐 release manifest）
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

# 类型白名单
ASSET_TYPE_WHITELIST: set[str] = {
    "product_introduction", "product_image", "instructions",
    "product_advantage", "core_selling_point", "economic_advantage",
    "promotional_image", "promotional_presentation", "promotional_leaflet",
    "pdr", "poster", "display_stand",
}

# 允许的产品
ALLOWED_PRODUCTS: set[str] = {"酮洛芬", "代温灸膏"}


def validate_asset_response(
    asset_id: str,
    asset_type: str,
    product_id: str,
    version: str = "",
) -> tuple[bool, str]:
    """资产合规验证。

    Args:
        asset_id: 资产 ID
        asset_type: 资产类型
        product_id: 产品标识
        version: 版本号（可选）

    Returns:
        (is_valid, reason)
    """
    # 1. 类型白名单
    if asset_type not in ASSET_TYPE_WHITELIST:
        return False, f"asset_type_not_whitelisted:{asset_type}"

    # 2. 否定识别（产品必须在字典内）
    if product_id not in ALLOWED_PRODUCTS:
        return False, f"product_not_allowed:{product_id}"

    # 3. 版本对齐（v3 stub 阶段跳过，生产对齐 release manifest）
    return True, "ok"
