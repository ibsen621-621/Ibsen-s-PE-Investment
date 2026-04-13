"""
Tests for fundamental due diligence: DuPont analyzer and growth quality checker.
"""

import pytest
from src.investment_model.due_diligence import DuPontAnalyzer, GrowthQualityChecker


class TestDuPontAnalyzer:
    def setup_method(self):
        self.analyzer = DuPontAnalyzer()

    def _base_kwargs(self, **overrides):
        kwargs = dict(
            net_profit_rmb=3.0,
            revenue_rmb=15.0,
            total_assets_rmb=20.0,
            total_equity_rmb=15.0,
        )
        kwargs.update(overrides)
        return kwargs

    def test_roe_decomposition_identity(self):
        """ROE = net_margin * asset_turnover * equity_multiplier"""
        result = self.analyzer.analyze(**self._base_kwargs())
        expected_roe = result.net_profit_margin * result.asset_turnover * result.equity_multiplier
        assert abs(result.roe - expected_roe) < 1e-4

    def test_high_margin_model(self):
        """Net margin > 15% → high_margin or high_margin_turnover"""
        result = self.analyzer.analyze(
            net_profit_rmb=3.0,
            revenue_rmb=15.0,     # 20% net margin
            total_assets_rmb=20.0,
            total_equity_rmb=15.0,
        )
        assert "high_margin" in result.business_model

    def test_high_turnover_model(self):
        """Asset turnover > 2.0 → high_turnover"""
        result = self.analyzer.analyze(
            net_profit_rmb=0.5,
            revenue_rmb=30.0,     # asset_turnover = 3.0 (>2.0)
            total_assets_rmb=10.0,
            total_equity_rmb=6.0,
        )
        assert "high_turnover" in result.business_model

    def test_high_leverage_model_and_warning(self):
        """Equity multiplier > 3.0 → high_leverage with warning"""
        result = self.analyzer.analyze(
            net_profit_rmb=2.0,
            revenue_rmb=20.0,
            total_assets_rmb=80.0,
            total_equity_rmb=16.0,  # multiplier = 5.0
        )
        assert result.business_model == "high_leverage"
        assert len(result.warnings) > 0

    def test_balanced_model(self):
        """No single dominant factor → balanced"""
        result = self.analyzer.analyze(
            net_profit_rmb=1.0,
            revenue_rmb=20.0,   # 5% margin — not high
            total_assets_rmb=15.0,  # turnover = 1.33 — not high
            total_equity_rmb=8.0,   # multiplier = 1.875 — not high
        )
        assert result.business_model == "balanced"

    def test_low_roe_warning(self):
        result = self.analyzer.analyze(
            net_profit_rmb=0.1,
            revenue_rmb=10.0,
            total_assets_rmb=20.0,
            total_equity_rmb=15.0,
        )
        # ROE = 0.01 / 0.15 = very low
        assert any("ROE" in w for w in result.warnings)

    def test_net_profit_margin_formula(self):
        result = self.analyzer.analyze(**self._base_kwargs())
        assert abs(result.net_profit_margin - 3.0 / 15.0) < 1e-6

    def test_asset_turnover_formula(self):
        result = self.analyzer.analyze(**self._base_kwargs())
        assert abs(result.asset_turnover - 15.0 / 20.0) < 1e-6

    def test_equity_multiplier_formula(self):
        result = self.analyzer.analyze(**self._base_kwargs())
        assert abs(result.equity_multiplier - 20.0 / 15.0) < 1e-4

    def test_invalid_revenue_raises(self):
        with pytest.raises(ValueError):
            self.analyzer.analyze(
                net_profit_rmb=1.0,
                revenue_rmb=0.0,
                total_assets_rmb=10.0,
                total_equity_rmb=8.0,
            )

    def test_summary_contains_roe(self):
        result = self.analyzer.analyze(**self._base_kwargs())
        assert "ROE" in result.summary


class TestGrowthQualityChecker:
    def setup_method(self):
        self.checker = GrowthQualityChecker()

    def _base_kwargs(self, **overrides):
        kwargs = dict(
            gmv_rmb=5.0,
            revenue_rmb=5.0,
            user_retention_rate_pct=92.0,
            nps_score=55,
            customer_acquisition_cost_rmb=0.05,
            lifetime_value_rmb=0.30,
            revenue_from_subsidies_pct=5.0,
            business_model="saas",
            net_dollar_retention_pct=115.0,
        )
        kwargs.update(overrides)
        return kwargs

    def test_genuine_growth_saas(self):
        result = self.checker.check(**self._base_kwargs())
        assert result.is_genuine_growth is True
        assert result.quality_score >= 60

    def test_low_ltv_cac_flags_pseudo_growth(self):
        result = self.checker.check(
            **self._base_kwargs(
                customer_acquisition_cost_rmb=0.20,
                lifetime_value_rmb=0.30,  # LTV/CAC = 1.5 < 3.0
            )
        )
        assert any("LTV" in f for f in result.pseudo_growth_flags)
        assert any("LTV/CAC" in w for w in result.warnings)

    def test_low_retention_flags_pseudo_growth_toc(self):
        result = self.checker.check(
            **self._base_kwargs(
                user_retention_rate_pct=15.0,
                business_model="to_c",
            )
        )
        assert any("留存" in f for f in result.pseudo_growth_flags)

    def test_negative_nps_flags_pseudo_growth(self):
        result = self.checker.check(**self._base_kwargs(nps_score=-20))
        assert any("NPS" in f for f in result.pseudo_growth_flags)
        assert any("口碑" in w or "NPS" in w for w in result.warnings)

    def test_high_subsidy_flags_pseudo_growth(self):
        result = self.checker.check(**self._base_kwargs(revenue_from_subsidies_pct=45.0))
        assert any("补贴" in f for f in result.pseudo_growth_flags)

    def test_low_saas_ndr_flags_pseudo_growth(self):
        result = self.checker.check(
            **self._base_kwargs(
                business_model="saas",
                net_dollar_retention_pct=85.0,  # < 100%
            )
        )
        assert any("NDR" in f for f in result.pseudo_growth_flags)
        assert any("NDR" in w or "净收入留存" in w for w in result.warnings)

    def test_multiple_flags_not_genuine_growth(self):
        result = self.checker.check(
            gmv_rmb=50.0,
            revenue_rmb=5.0,
            user_retention_rate_pct=15.0,
            nps_score=-20,
            customer_acquisition_cost_rmb=0.25,
            lifetime_value_rmb=0.30,
            revenue_from_subsidies_pct=50.0,
            business_model="to_c",
        )
        assert result.is_genuine_growth is False
        assert len(result.pseudo_growth_flags) >= 3

    def test_quality_score_range(self):
        result = self.checker.check(**self._base_kwargs())
        assert 0 <= result.quality_score <= 100

    def test_high_gmv_revenue_ratio_warning(self):
        result = self.checker.check(
            **self._base_kwargs(gmv_rmb=200.0, revenue_rmb=5.0)  # GMV/revenue = 40x
        )
        assert any("GMV" in w for w in result.warnings)

    def test_tob_retention_uses_higher_threshold(self):
        """ToB model uses 70% annual retention threshold, not 30%"""
        result = self.checker.check(
            **self._base_kwargs(
                user_retention_rate_pct=55.0,  # OK for ToC but fails ToB 70% threshold
                business_model="to_b",
            )
        )
        assert any("留存" in f for f in result.pseudo_growth_flags)

    def test_summary_contains_quality_score(self):
        result = self.checker.check(**self._base_kwargs())
        assert "100" in result.summary or str(int(result.quality_score)) in result.summary
