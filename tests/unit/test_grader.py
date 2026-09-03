"""
评分器单元测试
===============
"""
import json

import pytest

from rag_agent_v3.tools.grader import (
    _score_doc,
    _score_internet,
    grade_answer_confidence,
    CONFIDENCE_THRESHOLD_DOC,
    CONFIDENCE_THRESHOLD_INTERNET,
)


# ============== _score_doc ==============

class TestScoreDoc:
    """Doc 证据评分"""

    def test_empty_evidence(self):
        assert _score_doc([]) == 0.0

    def test_single_chunk_high_similarity(self):
        evidence = [{"similarity": 0.85, "content": "..."}]
        assert _score_doc(evidence) == 0.85

    def test_three_chunks_bonus(self):
        evidence = [{"similarity": 0.5}] * 3
        assert _score_doc(evidence) == 0.55  # 0.5 + 0.05

    def test_five_chunks_bonus(self):
        evidence = [{"similarity": 0.5}] * 5
        assert _score_doc(evidence) == 0.6  # 0.5 + 0.1

    def test_score_capped_at_one(self):
        evidence = [{"similarity": 1.0}] * 10
        assert _score_doc(evidence) == 1.0


# ============== _score_internet ==============

class TestScoreInternet:
    """联网证据评分"""

    def test_empty_evidence(self):
        assert _score_internet([]) == 0.0

    def test_three_results(self):
        evidence = [{"url": "https://example.com"}] * 3
        assert _score_internet(evidence) == 0.55

    def test_five_results(self):
        evidence = [{"url": "https://example.com"}] * 5
        assert _score_internet(evidence) == 0.7

    def test_authoritative_source_bonus(self):
        evidence = [{"url": "https://nhc.gov.cn/something"}] * 3
        # 0.55 + 0.1 = 0.65
        assert _score_internet(evidence) == 0.65

    def test_who_source(self):
        evidence = [{"url": "https://who.int/news"}] * 5
        # 0.7 + 0.1 = 0.8 (浮点精度容差)
        assert _score_internet(evidence) == pytest.approx(0.8)


# ============== grade_answer_confidence tool ==============

class TestGradeTool:
    """评分器 tool 接口"""

    def test_doc_above_threshold(self):
        chunks = json.dumps([{"similarity": 0.85, "content": "..."}], ensure_ascii=False)
        result = json.loads(grade_answer_confidence.invoke({"evidence_type": "doc", "evidence": chunks}))
        assert result["sufficient"] is True
        assert result["recommendation"] == "directly_answer"

    def test_doc_below_threshold_triggers_internet(self):
        chunks = json.dumps([{"similarity": 0.3, "content": "..."}], ensure_ascii=False)
        result = json.loads(grade_answer_confidence.invoke({"evidence_type": "doc", "evidence": chunks}))
        assert result["sufficient"] is False
        assert result["recommendation"] == "trigger_internet_search"

    def test_internet_above_threshold(self):
        results = json.dumps([{"url": "https://example.com", "title": "t", "snippet": "s"}] * 5, ensure_ascii=False)
        result = json.loads(grade_answer_confidence.invoke({"evidence_type": "internet", "evidence": results}))
        assert result["sufficient"] is True
        assert result["recommendation"] == "answer_with_disclaimer"

    def test_internet_below_threshold(self):
        results = json.dumps([{"url": "https://example.com"}], ensure_ascii=False)
        result = json.loads(grade_answer_confidence.invoke({"evidence_type": "internet", "evidence": results}))
        assert result["sufficient"] is False
        assert result["recommendation"] == "fallback_decline"

    def test_invalid_evidence_type(self):
        result = json.loads(grade_answer_confidence.invoke({"evidence_type": "xxx", "evidence": "[]"}))
        assert result["status"] == "error"

    def test_invalid_json(self):
        result = json.loads(grade_answer_confidence.invoke({"evidence_type": "doc", "evidence": "not json"}))
        assert result["status"] == "error"
        assert result["score"] == 0.0


# ============== 阈值常量 ==============

def test_thresholds():
    """v3 拍板的阈值"""
    assert CONFIDENCE_THRESHOLD_DOC == 0.7
    assert CONFIDENCE_THRESHOLD_INTERNET == 0.6
