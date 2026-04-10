"""
Tests for exit analysis models.
"""

import pytest
from src.investment_model.exit import ExitAnalyzer, ExitDecisionCommittee, ExitChannel


# ---------------------------------------------------------------------------
# ExitAnalyzer — Parabola timing model
# ---------------------------------------------------------------------------

class TestExitAnalyzer:
    def setup_method(self):
        self.analyzer = ExitAnalyzer()

    def _base_kwargs(self, **overrides):
        kwargs = dict(
            industry_growth_stage="peak",
            company_growth_stage="peak",
            capital_cycle_stage="hot",
            current_return_multiple=4.5,
            hurdle_multiple=3.0,
            years_held=4,
            years_remaining_in_fund=2,
            has_liquid_secondary_market=True,
        )
        kwargs.update(overrides)
        return kwargs

    def test_golden_exit_all_peaks(self):
        result = self.analyzer.analyze_timing(**self._base_kwargs())
        assert result.exit_quality == "golden"
        assert result.is_optimal_window is True

    def test_silver_exit_two_peaks(self):
        result = self.analyzer.analyze_timing(
            **self._base_kwargs(capital_cycle_stage="warming")
        )
        # 2 peaks (industry + company), capital warming
        assert result.exit_quality in ("silver", "golden")

    def test_poor_exit_all_declining(self):
        result = self.analyzer.analyze_timing(
            industry_growth_stage="declining",
            company_growth_stage="declining",
            capital_cycle_stage="cold",
            current_return_multiple=1.2,
            hurdle_multiple=3.0,
            years_held=6,
            years_remaining_in_fund=1,
            has_liquid_secondary_market=False,
        )
        assert result.exit_quality == "poor"
        assert result.is_optimal_window is False

    def test_holding_equals_rebuying_warning(self):
        """When return multiple ≥ hurdle, holding = re-buying — should warn"""
        result = self.analyzer.analyze_timing(**self._base_kwargs())
        assert any("重新买入" in w for w in result.warnings)

    def test_fund_end_urgency(self):
        result = self.analyzer.analyze_timing(
            **self._base_kwargs(years_remaining_in_fund=1)
        )
        assert any("存续期" in w for w in result.warnings)

    def test_illiquid_secondary_market_warning(self):
        result = self.analyzer.analyze_timing(
            **self._base_kwargs(has_liquid_secondary_market=False)
        )
        assert any("流动性" in w for w in result.warnings)

    def test_liquidity_crisis_detection(self):
        """Small-cap HK/US stocks with daily volume < $1M"""
        result = self.analyzer.evaluate_liquidity(
            exchange="港股",
            daily_trading_volume_usd=500_000,
            stake_value_rmb=2.0,
            target_exit_days=90,
        )
        assert result["liquidity_crisis"] is True
        assert result["is_liquid"] is False

    def test_liquid_large_cap(self):
        result = self.analyzer.evaluate_liquidity(
            exchange="A股",
            daily_trading_volume_usd=50_000_000,
            stake_value_rmb=1.0,
            target_exit_days=90,
        )
        assert result["liquidity_crisis"] is False
        assert result["is_liquid"] is True

    def test_composite_score_range(self):
        result = self.analyzer.analyze_timing(**self._base_kwargs())
        assert 0 <= result.composite_score <= 10


# ---------------------------------------------------------------------------
# ExitDecisionCommittee
# ---------------------------------------------------------------------------

class TestExitDecisionCommittee:
    def setup_method(self):
        self.committee = ExitDecisionCommittee()

    def _eval_channels(self, **overrides):
        kwargs = dict(
            peak_paper_valuation_rmb=20.0,
            company_sector="消费科技",
            years_to_fund_end=2,
            ipo_readiness_score=6.0,
            ma_buyer_interest_score=7.0,
            secondary_market_liquidity=8.0,
            lp_cash_urgency="high",
            macro_capital_sentiment="neutral",
        )
        kwargs.update(overrides)
        return self.committee.evaluate_all_channels(**kwargs)

    def test_returns_three_channels(self):
        channels = self._eval_channels()
        assert len(channels) == 3
        channel_names = {c.channel for c in channels}
        assert ExitChannel.IPO in channel_names
        assert ExitChannel.MA in channel_names
        assert ExitChannel.SECONDARY in channel_names

    def test_ipo_channel_highest_valuation(self):
        channels = self._eval_channels(macro_capital_sentiment="bullish")
        ipo = next(c for c in channels if c.channel == ExitChannel.IPO)
        # IPO should have the highest or near-highest valuation in bullish market
        assert ipo.estimated_valuation_rmb >= 20.0

    def test_secondary_fastest_channel(self):
        channels = self._eval_channels()
        secondary = next(c for c in channels if c.channel == ExitChannel.SECONDARY)
        ipo = next(c for c in channels if c.channel == ExitChannel.IPO)
        assert secondary.timeline_months < ipo.timeline_months

    def test_high_urgency_ma_recommendation(self):
        channels = self._eval_channels(lp_cash_urgency="high", years_to_fund_end=1)
        ma = next(c for c in channels if c.channel == ExitChannel.MA)
        assert "强烈推荐" in ma.recommendation

    def test_bearish_market_higher_discount(self):
        channels_bear = self._eval_channels(macro_capital_sentiment="bearish")
        channels_bull = self._eval_channels(macro_capital_sentiment="bullish")
        # bearish market → lower valuations
        bear_ipo = next(c for c in channels_bear if c.channel == ExitChannel.IPO)
        bull_ipo = next(c for c in channels_bull if c.channel == ExitChannel.IPO)
        assert bear_ipo.estimated_valuation_rmb < bull_ipo.estimated_valuation_rmb

    def test_memo_generation(self):
        channels = self._eval_channels()
        memo = self.committee.generate_decision_memo(channels, holding_cost_rmb=8.0)
        assert "退出决策委员会" in memo
        assert "10%-20%" in memo
        assert "折扣" in memo

    def test_feasibility_scores_in_range(self):
        channels = self._eval_channels()
        for c in channels:
            assert 0 <= c.feasibility_score <= 100
