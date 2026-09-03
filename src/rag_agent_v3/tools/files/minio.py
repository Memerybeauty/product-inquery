"""
MinIO / 产品资产 tools（v3 · 2 个 tool · 暂 stub）
=================================================

list_file_catalog:     查询产品资产清单（filter: 产品 / 类型 / 版本）
fetch_file_from_minio: 取文件原始字节（不改写，描述可改）

v3 阶段 stub 实现：返回符合 schema 的 mock 数据，保留接口。
等用户给查询条件后接真实 MinIO。
"""
from __future__ import annotations

import json
import logging
import os
from typing import Any

from langchain.tools import tool

from rag_agent_v3.middleware.asset_compliance import validate_asset_response

logger = logging.getLogger(__name__)

# 资产类型字典（中文显示用）
ASSET_TYPE_MAP: dict[str, str] = {
    "product_introduction": "产品介绍",
    "product_image": "产品图片",
    "instructions": "药品说明书",
    "product_advantage": "产品优势",
    "core_selling_point": "核心卖点",
    "economic_advantage": "经济优势",
    "promotional_image": "宣传图片",
    "promotional_presentation": "PPT介绍",
    "promotional_leaflet": "彩页/宣传卡",
    "pdr": "PDR介绍",
    "poster": "海报",
    "display_stand": "展架",
}

# Stub 数据（v3 阶段）
_STUB_CATALOG: dict[str, list[dict]] = {
    "酮洛芬": [
        {
            "asset_id": "stub_tlf_instructions_v1",
            "file_name": "酮洛芬凝胶贴膏说明书.pdf",
            "asset_type": "instructions",
            "product_id": "酮洛芬",
            "version": "v1.0",
            "file_size": "2.3MB",
            "file_type": "pdf",
        },
        {
            "asset_id": "stub_tlf_ppt_v1",
            "file_name": "酮洛芬产品介绍.pptx",
            "asset_type": "promotional_presentation",
            "product_id": "酮洛芬",
            "version": "v1.0",
            "file_size": "8.5MB",
            "file_type": "pptx",
        },
    ],
    "代温灸膏": [
        {
            "asset_id": "stub_dw_instructions_v1",
            "file_name": "代温灸膏说明书.pdf",
            "asset_type": "instructions",
            "product_id": "代温灸膏",
            "version": "v1.0",
            "file_size": "1.8MB",
            "file_type": "pdf",
        },
    ],
}


@tool
def list_file_catalog(
    product_id: str,
    asset_type: str = "",
    version: str = "",
) -> str:
    """查询产品资产清单。

    Args:
        product_id: 产品标识（酮洛芬 / 代温灸膏）
        asset_type: 资产类型（可选，见 ASSET_TYPE_MAP）
        version: 版本号（可选，默认最新）

    Returns:
        JSON: {status, assets: [...]}
    """
    # 真实接入 MinIO / release manifest（等用户给查询条件）
    # 当前 stub
    assets = _STUB_CATALOG.get(product_id, [])
    if asset_type:
        assets = [a for a in assets if a["asset_type"] == asset_type]
    if version:
        assets = [a for a in assets if a["version"] == version]

    if not assets:
        return json.dumps(
            {
                "status": "no_match",
                "message": f"暂未找到「{product_id}」的{ASSET_TYPE_MAP.get(asset_type, asset_type) or '相关'}材料",
                "assets": [],
            },
            ensure_ascii=False,
        )

    return json.dumps(
        {
            "status": "success",
            "product_id": product_id,
            "total": len(assets),
            "assets": [
                {**a, "download_url": f"stub://{a['asset_id']}", "thumbnail_url": f"stub://{a['asset_id']}.thumb"}
                for a in assets
            ],
        },
        ensure_ascii=False,
        indent=2,
    )


@tool
def fetch_file_from_minio(
    asset_id: str,
    product_id: str,
    asset_type: str,
    version: str = "",
) -> str:
    """取文件原始字节（不改写）。

    关键设计：返回的 bytes 不经过 LLM，描述文字可改写。
    必经 validate_asset_response 中间件。

    Args:
        asset_id: 资产 ID
        product_id: 产品标识
        asset_type: 资产类型
        version: 版本号

    Returns:
        JSON: {status, asset_id, bytes_b64, description, mime}
    """
    # 1. 合规验证
    is_valid, reason = validate_asset_response(asset_id, asset_type, product_id, version)
    if not is_valid:
        return json.dumps(
            {"status": "rejected", "message": f"资产合规失败: {reason}"},
            ensure_ascii=False,
        )

    # 2. stub：从 _STUB_CATALOG 找
    catalog = _STUB_CATALOG.get(product_id, [])
    asset = next((a for a in catalog if a["asset_id"] == asset_id), None)
    if not asset:
        return json.dumps(
            {"status": "not_found", "message": f"未找到 asset_id={asset_id}"},
            ensure_ascii=False,
        )

    # 3. stub 返回 mock 字节（真实接入 MinIO 后用 boto3 流式取）
    mock_bytes = f"[STUB] {asset['file_name']} (asset_id={asset_id})".encode("utf-8")
    import base64
    return json.dumps(
        {
            "status": "success",
            "asset_id": asset_id,
            "file_name": asset["file_name"],
            "mime": "application/octet-stream",
            "bytes_b64": base64.b64encode(mock_bytes).decode("ascii"),
            "description": f"已为您找到「{product_id}」的{ASSET_TYPE_MAP.get(asset_type, asset_type)}（{asset['version']}）",
            "size": len(mock_bytes),
        },
        ensure_ascii=False,
        indent=2,
    )


__all__ = ["list_file_catalog", "fetch_file_from_minio", "ASSET_TYPE_MAP"]
