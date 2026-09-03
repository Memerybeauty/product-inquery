"""产品资产 tools（MinIO · stub）"""
from rag_agent_v3.tools.files.minio import (
    list_file_catalog,
    fetch_file_from_minio,
    ASSET_TYPE_MAP,
)

__all__ = ["list_file_catalog", "fetch_file_from_minio", "ASSET_TYPE_MAP"]
