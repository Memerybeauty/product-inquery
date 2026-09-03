"""
中间件单元测试
===============

覆盖：
- text_compliance: validate / strip_source / strip_common_sense
- asset_compliance: 白名单 / 否定识别
- disclaimer: 联网结果附 disclaimer
"""
import json

import pytest

from rag_agent_v3.middleware.text_compliance import (
    _is_valid,
    _strip_source,
    _strip_common_sense,
)
from rag_agent_v3.middleware.asset_compliance import validate_asset_response
from rag_agent_v3.middleware.disclaimer import INTERNET_DISCLAIMER


# ============== text_compliance ==============

class TestTextCompliance:
    """文本合规验证"""

    def test_valid_text(self):
        ok, reason = _is_valid("酮洛芬的适应症是缓解疼痛")
        assert ok is True
        assert reason == "ok"

    def test_empty_text(self):
        ok, reason = _is_valid("")
        assert ok is False
        assert reason == "empty_response"

    def test_boundary_keyword(self):
        ok, reason = _is_valid("我爸爸腰疼，能贴酮洛芬吗")
        assert ok is False
        assert "boundary_keyword" in reason

    def test_competitor_not_boundary(self):
        """v3 设计：竞品/外部产品不是越界条件，应通过合规检查"""
        ok, reason = _is_valid("扶他林的副作用")
        assert ok is True
        assert reason == "ok"

    def test_external_drug_not_boundary(self):
        """v3 设计：任何产品名（含竞品）都不是越界关键词"""
        ok, reason = _is_valid("洛索洛芬凝胶的副作用")
        assert ok is True
        assert reason == "ok"

    def test_strip_source_block(self):
        text = "酮洛芬适用于缓解疼痛。\n\n资料依据：XXX 文件 2024-01-01"
        stripped = _strip_source(text)
        assert "资料依据" not in stripped
        assert "酮洛芬适用于缓解疼痛" in stripped

    def test_strip_common_sense(self):
        text = "一般来说，酮洛芬用于缓解疼痛。"
        stripped = _strip_common_sense(text)
        assert "一般来说" not in stripped


# ============== asset_compliance ==============

class TestAssetCompliance:
    """资产合规验证"""

    def test_valid_asset(self):
        ok, reason = validate_asset_response("asset_1", "instructions", "酮洛芬", "v1.0")
        assert ok is True
        assert reason == "ok"

    def test_invalid_asset_type(self):
        ok, reason = validate_asset_response("asset_1", "malware", "酮洛芬")
        assert ok is False
        assert "not_whitelisted" in reason

    def test_invalid_product(self):
        ok, reason = validate_asset_response("asset_1", "instructions", "扶他林")
        assert ok is False
        assert "not_allowed" in reason

    @pytest.mark.parametrize("asset_type", [
        "instructions", "product_image", "promotional_presentation",
        "promotional_leaflet", "pdr", "poster", "display_stand",
        "promotional_image", "product_introduction", "core_selling_point",
    ])
    def test_all_whitelisted_types(self, asset_type):
        ok, _ = validate_asset_response("a1", asset_type, "酮洛芬")
        assert ok is True


# ============== disclaimer ==============

class TestDisclaimer:
    """联网 disclaimer 固定模板"""

    def test_disclaimer_template_exists(self):
        assert "互联网" in INTERNET_DISCLAIMER
        assert "不构成医疗建议" in INTERNET_DISCLAIMER
        assert "咨询医师或药师" in INTERNET_DISCLAIMER

    def test_disclaimer_contains_formatting(self):
        # 必须有 markdown 引用块样式
        assert "📌" in INTERNET_DISCLAIMER
        assert "**" in INTERNET_DISCLAIMER
