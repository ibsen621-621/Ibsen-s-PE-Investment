"""
Tests for LP evaluation: GP Scorecard and Asset Allocation Advisor.
"""

import pytest
from src.investment_model.lp_evaluation import GPScorecard, AssetAllocationAdvisor


# ---------------------------------------------------------------------------
# GPScorecard
# ---------------------------------------------------------------------------

class TestGPScorecard:
    def setup_method(self):
        self.scorecard = GPScorecard()

    def _base_kwargs(self, **overrides):
        kwargs = dict(
            historical_dpi=1.5,
            reported_moc=3.0,
            unrealised_pct=30.0,
            lp_reinvestment_rate_pct=80.0,
            fund_size_rmb=30.0,
            team_managed_assets_rmb=35.0,
            target_stage="pe",
            top3_investment_pct=50.0,
            gov_fund_pct=20.0,
        )
        kwargs.update(overrides)
        return kwargs

    def test_excellent_gp_grade_a(self):
        result = self.scorecard.evaluate(**self._base_kwargs())
        assert result.grade == "A"
        assert result.is_investable is True
        assert result.total_score >= 80

    def test_poor_dpi_red_flag(self):
        result = self.scorecard.evaluate(**self._base_kwargs(historical_dpi=0.5))
        assert any("极低" in f for f in result.red_flags)
        assert result.total_score < 80

    def test_high_unrealised_moc_red_flag(self):
        result = self.scorecard.evaluate(
            **self._base_kwargs(reported_moc=4.0, unrealised_pct=80.0)
        )
        # Adjusted MOC = 4 * (1 - 0.8) = 0.8x → very low; check red flag exists
        assert any("账面浮盈" in f or "水分" in f for f in result.red_flags) or result.indicator_scores["moc_quality"] == 0

    def test_low_lp_reinvest_rate(self):
        result = self.scorecard.evaluate(**self._base_kwargs(lp_reinvestment_rate_pct=20.0))
        assert any("极低" in f for f in result.red_flags)

    def test_oversized_fund_red_flag(self):
        result = self.scorecard.evaluate(**self._base_kwargs(fund_size_rmb=500.0))
        assert any("超出团队能力" in f for f in result.red_flags)

    def test_high_gov_fund_red_flag(self):
        result = self.scorecard.evaluate(**self._base_kwargs(gov_fund_pct=60.0))
        assert any("返投压力" in f for f in result.red_flags)

    def test_low_concentration_recommendation(self):
        result = self.scorecard.evaluate(**self._base_kwargs(top3_investment_pct=15.0))
        assert len(result.recommendations) > 0

    def test_not_investable_grade_d(self):
        result = self.scorecard.evaluate(
            historical_dpi=0.3,
            reported_moc=1.5,
            unrealised_pct=70.0,
            lp_reinvestment_rate_pct=15.0,
            fund_size_rmb=200.0,
            team_managed_assets_rmb=20.0,
            target_stage="angel",
            top3_investment_pct=10.0,
            gov_fund_pct=70.0,
        )
        assert result.grade in ("C", "D")
        assert result.is_investable is False

    def test_scores_sum_correctly(self):
        result = self.scorecard.evaluate(**self._base_kwargs())
        calculated_total = sum(result.indicator_scores.values())
        assert abs(calculated_total - result.total_score) < 0.01

    def test_grade_boundaries(self):
        """A≥80, B≥65, C≥45, D<45"""
        result = self.scorecard.evaluate(**self._base_kwargs())
        if result.total_score >= 80:
            assert result.grade == "A"
        elif result.total_score >= 65:
            assert result.grade == "B"
        elif result.total_score >= 45:
            assert result.grade == "C"
        else:
            assert result.grade == "D"


# ---------------------------------------------------------------------------
# AssetAllocationAdvisor
# ---------------------------------------------------------------------------

class TestAssetAllocationAdvisor:
    def setup_method(self):
        self.advisor = AssetAllocationAdvisor()

    def _base_kwargs(self, **overrides):
        kwargs = dict(
            total_investable_assets_rmb=5.0,
            risk_tolerance="moderate",
            pe_budget_pct=25.0,
            gp_coinvestment_rate_pct=5.0,
            is_market_rate_fof=False,
            years_of_observation=3,
        )
        kwargs.update(overrides)
        return kwargs

    def test_zero_allocation_for_market_fof(self):
        result = self.advisor.advise(**self._base_kwargs(is_market_rate_fof=True))
        assert result.blind_pool_pct == 0
        assert result.special_fund_pct == 0
        assert result.fund_of_funds_pct == 0
        assert "❌" in result.summary

    def test_fund_of_funds_always_zero(self):
        result = self.advisor.advise(**self._base_kwargs())
        assert result.fund_of_funds_pct == 0.0

    def test_blind_pool_is_fraction_of_pe_budget(self):
        result = self.advisor.advise(**self._base_kwargs())
        total = result.blind_pool_pct + result.special_fund_pct
        assert abs(total - result.total_pe_allocation_pct) < 0.1

    def test_conservative_caps_allocation(self):
        """Conservative risk tolerance caps PE at 15%"""
        result = self.advisor.advise(**self._base_kwargs(
            risk_tolerance="conservative",
            pe_budget_pct=30.0,
        ))
        assert result.total_pe_allocation_pct <= 15.0

    def test_low_gp_coinvestment_warning(self):
        result = self.advisor.advise(**self._base_kwargs(gp_coinvestment_rate_pct=1.0))
        assert any("跟投" in w for w in result.warnings)

    def test_new_lp_observation_preference(self):
        """New LP (0 years observation) should have higher blind pool allocation"""
        result_new = self.advisor.advise(**self._base_kwargs(years_of_observation=0))
        result_experienced = self.advisor.advise(**self._base_kwargs(years_of_observation=5))
        # New LP gets higher blind pool % to observe GP
        assert result_new.blind_pool_pct >= result_experienced.blind_pool_pct

    def test_over_budget_warning(self):
        """When requested PE budget exceeds risk-tolerance cap"""
        result = self.advisor.advise(**self._base_kwargs(
            risk_tolerance="conservative",
            pe_budget_pct=40.0,
        ))
        assert any("超过" in w for w in result.warnings)

    def test_aggressive_allows_higher_allocation(self):
        result = self.advisor.advise(**self._base_kwargs(
            risk_tolerance="aggressive",
            pe_budget_pct=35.0,
        ))
        assert result.total_pe_allocation_pct == pytest.approx(35.0, abs=0.1)
