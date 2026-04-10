"""
Tests for investment philosophy checker.
"""

import pytest
from src.investment_model.philosophy import InvestmentPhilosophyChecker


class TestInvestmentPhilosophyChecker:
    def setup_method(self):
        self.checker = InvestmentPhilosophyChecker()

    def _base_kwargs(self, **overrides):
        kwargs = dict(
            investment_thesis="国产PLC/SCADA软件，替代西门子，政策强催化",
            has_exit_plan=True,
            has_profit_taking_triggers=True,
            sector="工业软件",
            is_hard_tech=True,
            is_domestic_substitution=True,
            is_autonomous_controllable=True,
            is_internet_traffic_model=False,
            fund_stage="vc",
            assumed_exit_rate_pct=15.0,
            valuation_vs_intrinsic_pct=30.0,
        )
        kwargs.update(overrides)
        return kwargs

    def test_fully_aligned_investment(self):
        result = self.checker.check(**self._base_kwargs())
        assert result.overall_alignment is True
        assert result.is_value_speculative is True
        assert result.political_economy_score >= 8.0

    def test_no_exit_plan_fails_philosophy(self):
        result = self.checker.check(**self._base_kwargs(has_exit_plan=False))
        assert result.is_value_speculative is False
        assert any("退出计划" in w for w in result.warnings)

    def test_no_profit_taking_fails(self):
        result = self.checker.check(**self._base_kwargs(has_profit_taking_triggers=False))
        assert result.is_value_speculative is False
        assert any("止盈" in w for w in result.warnings)

    def test_severe_overvaluation_warning(self):
        result = self.checker.check(**self._base_kwargs(valuation_vs_intrinsic_pct=120.0))
        assert any("透支" in w for w in result.warnings)

    def test_internet_model_penalizes_score(self):
        base_result = self.checker.check(**self._base_kwargs())
        internet_result = self.checker.check(
            **self._base_kwargs(is_internet_traffic_model=True)
        )
        assert internet_result.political_economy_score <= base_result.political_economy_score

    def test_no_hard_tech_attributes(self):
        result = self.checker.check(
            **self._base_kwargs(
                is_hard_tech=False,
                is_domestic_substitution=False,
                is_autonomous_controllable=False,
                is_internet_traffic_model=False,
            )
        )
        assert result.political_economy_score < 5.0

    def test_unrealistic_exit_rate_angel(self):
        result = self.checker.check(
            **self._base_kwargs(fund_stage="angel", assumed_exit_rate_pct=30.0)
        )
        # Angel top exit rate is ~5%; 30% is wildly optimistic
        assert result.exit_rate_realistic is False
        assert any("退出率" in w for w in result.warnings)

    def test_realistic_exit_rate_vc(self):
        result = self.checker.check(
            **self._base_kwargs(fund_stage="vc", assumed_exit_rate_pct=12.0)
        )
        # VC benchmark is ~16%; 12% is conservative — realistic
        assert result.exit_rate_realistic is True

    def test_summary_contains_all_three_checks(self):
        result = self.checker.check(**self._base_kwargs())
        assert "价值投机" in result.summary
        assert "政治经济" in result.summary
        assert "退出率" in result.summary
