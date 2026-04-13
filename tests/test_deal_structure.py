"""
Tests for deal structure: anti-dilution checker and buyback feasibility checker.
"""

import pytest
from src.investment_model.deal_structure import AntiDilutionChecker, BuybackFeasibilityChecker


class TestAntiDilutionChecker:
    def setup_method(self):
        self.checker = AntiDilutionChecker()

    def _base_kwargs(self, **overrides):
        kwargs = dict(
            founder_selling_pct=5.0,
            selling_discount_pct=20.0,
            latest_round_valuation_rmb=20.0,
            has_anti_dilution_clause=True,
            anti_dilution_type="weighted_average",
        )
        kwargs.update(overrides)
        return kwargs

    def test_normal_transfer_low_risk(self):
        result = self.checker.check(**self._base_kwargs())
        assert result.risk_level == "low"
        assert result.founder_red_flag is False

    def test_deep_discount_triggers_red_flag(self):
        result = self.checker.check(**self._base_kwargs(selling_discount_pct=70.0))
        assert result.founder_red_flag is True
        assert any("红旗" in w or "套现" in w for w in result.warnings)

    def test_high_selling_pct_triggers_red_flag(self):
        result = self.checker.check(**self._base_kwargs(founder_selling_pct=25.0))
        assert result.founder_red_flag is True
        assert any("20%" in w or "比例" in w for w in result.warnings)

    def test_full_ratchet_anti_dilution_triggered(self):
        result = self.checker.check(
            **self._base_kwargs(
                selling_discount_pct=50.0,
                anti_dilution_type="full_ratchet",
            )
        )
        assert result.anti_dilution_triggered is True
        assert any("Full Ratchet" in w or "棘轮" in w for w in result.warnings)

    def test_weighted_average_anti_dilution_triggered(self):
        result = self.checker.check(
            **self._base_kwargs(
                selling_discount_pct=40.0,
                anti_dilution_type="weighted_average",
            )
        )
        assert result.anti_dilution_triggered is True
        assert any("加权平均" in w for w in result.warnings)

    def test_no_anti_dilution_clause_recommendation(self):
        result = self.checker.check(
            **self._base_kwargs(has_anti_dilution_clause=False, anti_dilution_type="none")
        )
        assert any("反稀释" in r for r in result.recommendations)

    def test_critical_risk_both_flags(self):
        result = self.checker.check(
            founder_selling_pct=30.0,
            selling_discount_pct=70.0,
            latest_round_valuation_rmb=10.0,
            has_anti_dilution_clause=True,
            anti_dilution_type="full_ratchet",
        )
        assert result.risk_level == "critical"

    def test_valuation_anchor_impact_reported(self):
        result = self.checker.check(**self._base_kwargs(selling_discount_pct=60.0))
        assert len(result.valuation_anchor_impact) > 0

    def test_summary_contains_risk_level(self):
        result = self.checker.check(**self._base_kwargs())
        assert "风险" in result.summary


class TestBuybackFeasibilityChecker:
    def setup_method(self):
        self.checker = BuybackFeasibilityChecker()

    def _base_kwargs(self, **overrides):
        kwargs = dict(
            buyback_trigger_metric="profit",
            buyback_trigger_value=1.0,
            actual_value=0.8,
            founder_personal_assets_rmb=3.0,
            has_joint_liability=True,
            company_cash_reserve_rmb=2.0,
            buyback_amount_rmb=2.5,
        )
        kwargs.update(overrides)
        return kwargs

    def test_feasible_buyback_high_score(self):
        result = self.checker.check(**self._base_kwargs())
        assert result.feasibility_score >= 60
        assert result.is_buyback_executable is True

    def test_no_joint_liability_warning(self):
        result = self.checker.check(**self._base_kwargs(has_joint_liability=False))
        assert any("连带" in w for w in result.warnings)

    def test_excessive_revenue_growth_target(self):
        result = self.checker.check(
            **self._base_kwargs(
                buyback_trigger_metric="revenue",
                buyback_trigger_value=10.0,     # 400% growth from actual 2.0
                actual_value=2.0,
            )
        )
        assert result.is_trigger_metric_reasonable is False
        assert any("增速" in w for w in result.warnings)

    def test_ipo_timeline_warning(self):
        result = self.checker.check(
            **self._base_kwargs(buyback_trigger_metric="ipo_timeline")
        )
        assert any("IPO" in w or "时间线" in w for w in result.warnings)

    def test_insufficient_assets_warning(self):
        result = self.checker.check(
            founder_personal_assets_rmb=0.5,
            has_joint_liability=True,
            company_cash_reserve_rmb=0.8,
            buyback_amount_rmb=5.0,           # Way more than available assets
            buyback_trigger_metric="profit",
            buyback_trigger_value=1.0,
            actual_value=0.8,
        )
        assert result.is_buyback_executable is False
        assert any("不足" in w for w in result.warnings)

    def test_trigger_fired_generates_warning(self):
        result = self.checker.check(
            **self._base_kwargs(
                buyback_trigger_value=2.0,
                actual_value=1.0,  # Below trigger
            )
        )
        assert any("触发" in w for w in result.warnings)

    def test_feasibility_score_range(self):
        result = self.checker.check(**self._base_kwargs())
        assert 0 <= result.feasibility_score <= 100

    def test_meaningful_guarantee_requires_joint_liability(self):
        result_no_liability = self.checker.check(
            **self._base_kwargs(has_joint_liability=False)
        )
        assert result_no_liability.has_meaningful_guarantee is False

    def test_low_feasibility_score_no_liability(self):
        result = self.checker.check(
            founder_personal_assets_rmb=0.1,
            has_joint_liability=False,
            company_cash_reserve_rmb=0.2,
            buyback_amount_rmb=3.0,
            buyback_trigger_metric="revenue",
            buyback_trigger_value=10.0,
            actual_value=2.0,
        )
        assert result.feasibility_score < 50

    def test_summary_contains_key_metrics(self):
        result = self.checker.check(**self._base_kwargs())
        assert "回购" in result.summary or "可行性" in result.summary
