"""
路由测试集
==========

加载 tests/fixtures/route_test_set.jsonl，验证三路径分类规则（关键字）。

注：实际路由由 LLM 自主判断，本测试只验证"基础规则层"（用作系统提示的预期参考）。
完整 LLM 路由准确率需要 e2e 测试。
"""
import json
from pathlib import Path

import pytest

FIXTURE_PATH = Path(__file__).parent.parent / "fixtures" / "route_test_set.jsonl"


def _load_cases() -> list[dict]:
    cases: list[dict] = []
    with open(FIXTURE_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                cases.append(json.loads(line))
    return cases


@pytest.fixture(scope="module")
def cases() -> list[dict]:
    return _load_cases()


def test_dataset_size(cases):
    """测试集至少 50 条"""
    assert len(cases) >= 50, f"仅 {len(cases)} 条，需 ≥ 50 条"


def test_dataset_path_coverage(cases):
    """三路径全覆盖"""
    paths = {c["expected_path"] for c in cases}
    assert "question" in paths
    assert "file" in paths
    assert "other" in paths


def test_dataset_required_fields(cases):
    """每条 case 都有 text + expected_path"""
    for c in cases:
        assert "text" in c
        assert "expected_path" in c
        assert c["expected_path"] in ("question", "file", "other")


def test_question_path_minimum(cases):
    """查问题路径 ≥ 15 条"""
    n = sum(1 for c in cases if c["expected_path"] == "question")
    assert n >= 15, f"仅 {n} 条，建议 ≥ 15 条"


def test_file_path_minimum(cases):
    """查资料路径 ≥ 10 条"""
    n = sum(1 for c in cases if c["expected_path"] == "file")
    assert n >= 10, f"仅 {n} 条，建议 ≥ 10 条"


def test_other_path_minimum(cases):
    """其他路径 ≥ 10 条"""
    n = sum(1 for c in cases if c["expected_path"] == "other")
    assert n >= 10, f"仅 {n} 条，建议 ≥ 10 条"


def test_reject_cases_have_reason(cases):
    """reject 类型的 case 必须带 reason"""
    for c in cases:
        if c["expected_path"] == "other" and c.get("intent") == "reject":
            assert "reason" in c
            assert c["reason"] in (
                "individual_treatment", "competitor", "system_info", "out_of_scope",
            )
