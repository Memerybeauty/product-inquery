"""
上下文增强器单元测试（v3 · 多轮对话）
"""
import pytest

from rag_agent_v3.context import (
    augment_query,
    get_last_product,
    PRODUCT_KEYWORDS,
)


class TestExtractProduct:
    """产品提取"""

    def test_jiuduan_product(self):
        history = [{"role": "user", "content": "酮洛芬的副作用"}]
        assert get_last_product(history) == "酮洛芬"

    def test_competitor_product(self):
        history = [{"role": "user", "content": "扶他林是什么"}]
        assert get_last_product(history) == "扶他林"

    def test_last_product(self):
        """多个产品时取最后一个"""
        history = [
            {"role": "user", "content": "酮洛芬是什么"},
            {"role": "user", "content": "代温灸膏呢"},
        ]
        assert get_last_product(history) == "代温灸膏"

    def test_no_product(self):
        assert get_last_product([{"role": "user", "content": "你好"}]) is None

    def test_lookback_limit(self):
        """只看最近 N 条"""
        history = [
            {"role": "user", "content": "酮洛芬"},
        ] * 20  # 20 条提到酮洛芬
        # lookback=5 → 5 条都提到酮洛芬
        assert get_last_product(history, lookback=5) == "酮洛芬"

    def test_longer_keyword_priority(self):
        """长关键词优先匹配（避免短词先匹配）"""
        history = [{"role": "user", "content": "酮洛芬凝胶贴膏怎么样"}]
        result = get_last_product(history)
        # 应该匹配到"酮洛芬凝胶贴膏"或"酮洛芬"
        assert result in ("酮洛芬凝胶贴膏", "酮洛芬")


class TestAugmentQuery:
    """query 增强"""

    def test_no_augment_when_product_in_query(self):
        """当前 query 含产品 → 不增强"""
        result = augment_query(
            [{"role": "user", "content": "代温灸膏"}],
            "酮洛芬的副作用",
        )
        assert result == "酮洛芬的副作用"

    def test_augment_with_context_product(self):
        """当前 query 无产品 + 上下文有 → 增强"""
        history = [
            {"role": "user", "content": "代温灸膏呢"},
        ]
        result = augment_query(history, "它有什么副作用")
        assert "代温灸膏" in result
        assert "它有什么副作用" in result
        assert result.startswith("关于")

    def test_no_augment_no_context_product(self):
        """当前 query 无产品 + 上下文无产品 → 不增强"""
        result = augment_query(
            [{"role": "user", "content": "你好"}],
            "今天天气怎么样",
        )
        assert result == "今天天气怎么样"

    def test_competitor_product_works(self):
        """竞品也能被识别为产品"""
        history = [{"role": "user", "content": "扶他林是什么"}]
        result = augment_query(history, "它能治什么")
        assert "扶他林" in result

    def test_empty_history(self):
        """空历史 → 不增强"""
        result = augment_query([], "酮洛芬")
        assert result == "酮洛芬"

    def test_custom_template(self):
        """支持自定义模板"""
        history = [{"role": "user", "content": "代温灸膏"}]
        result = augment_query(
            history,
            "它呢",
            template="[{product}] {query}",
        )
        assert result == "[代温灸膏] 它呢"

    def test_lookback_respected(self):
        """lookback 限制生效"""
        # 20 条提到酮洛芬，然后最后 1 条提到代温灸膏
        history = [{"role": "user", "content": "酮洛芬"}] * 20
        history.append({"role": "user", "content": "代温灸膏"})
        # lookback=5 → 应该看不到酮洛芬（前面 20 条），看到代温灸膏
        result = get_last_product(history, lookback=5)
        assert result == "代温灸膏"


class TestIntegration:
    """集成场景"""

    def test_realistic_conversation(self):
        """真实多轮对话场景"""
        history = [
            {"role": "user", "content": "酮洛芬的适应症是什么"},
            {"role": "assistant", "content": "适用于骨关节炎..."},
            {"role": "user", "content": "代温灸膏呢"},
            {"role": "assistant", "content": "代温灸膏用于..."},
            {"role": "user", "content": "它能长期用吗"},
        ]
        result = augment_query(history[:-1], "它能长期用吗")
        # 当前 query 在 history 里时，应去掉，避免污染
        assert "代温灸膏" in result

    def test_topic_switch_resets(self):
        """话题切换：上一个产品 + 当前新问题不含产品 → 用上一个产品补全"""
        history = [
            {"role": "user", "content": "布洛芬怎么样"},
        ]
        result = augment_query(history, "那安全性呢")
        assert "布洛芬" in result
