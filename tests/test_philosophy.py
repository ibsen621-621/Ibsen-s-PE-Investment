"""
Tests for investment philosophy checker.
"""

import pytest
from src.investment_model.philosophy import (
    InvestmentPhilosophyChecker,
    HardTechStrategyEvaluator,
    TECH_PATH_CORE_PLUGIN,
    TECH_PATH_SYSTEM_REBUILD,
    TECH_PATH_INCREMENTAL,
)


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

    # --- New tests for P/Strategic hard-tech parameters ---

    def test_new_fields_present_with_defaults(self):
        """New strategic fields are present with sensible defaults."""
        result = self.checker.check(**self._base_kwargs())
        assert hasattr(result, "strategic_score")
        assert hasattr(result, "strategic_valuation_multiplier")
        assert hasattr(result, "tech_path_assessment")
        assert result.strategic_valuation_multiplier >= 1.0

    def test_chokepoint_tech_increases_strategic_score(self):
        result_no = self.checker.check(**self._base_kwargs(is_chokepoint_tech=False))
        result_yes = self.checker.check(**self._base_kwargs(is_chokepoint_tech=True))
        assert result_yes.strategic_score >= result_no.strategic_score

    def test_chokepoint_tech_increases_valuation_multiplier(self):
        result_no = self.checker.check(**self._base_kwargs(is_chokepoint_tech=False))
        result_yes = self.checker.check(**self._base_kwargs(is_chokepoint_tech=True))
        assert result_yes.strategic_valuation_multiplier >= result_no.strategic_valuation_multiplier

    def test_core_plugin_path_high_score(self):
        result = self.checker.check(
            **self._base_kwargs(tech_path_type=TECH_PATH_CORE_PLUGIN)
        )
        assert result.strategic_score > 0

    def test_system_rebuild_path_generates_warning(self):
        result = self.checker.check(
            **self._base_kwargs(tech_path_type=TECH_PATH_SYSTEM_REBUILD)
        )
        assert any("系统性" in w or "基础设施" in w for w in result.warnings)

    def test_low_trl_generates_warning(self):
        result = self.checker.check(
            **self._base_kwargs(tech_readiness_level=2)
        )
        assert any("TRL" in w for w in result.warnings)

    def test_gov_procurement_boosts_multiplier(self):
        result_no = self.checker.check(**self._base_kwargs(has_gov_procurement=False))
        result_yes = self.checker.check(**self._base_kwargs(has_gov_procurement=True))
        assert result_yes.strategic_valuation_multiplier >= result_no.strategic_valuation_multiplier

    def test_strategic_score_in_summary(self):
        result = self.checker.check(**self._base_kwargs())
        assert "战略" in result.summary

    def test_tech_path_assessment_not_empty(self):
        result = self.checker.check(**self._base_kwargs())
        assert len(result.tech_path_assessment) > 0


class TestHardTechStrategyEvaluator:
    def setup_method(self):
        self.evaluator = HardTechStrategyEvaluator()

    def _base_kwargs(self, **overrides):
        kwargs = dict(
            tech_path_type=TECH_PATH_CORE_PLUGIN,
            is_chokepoint_tech=True,
            has_gov_procurement=True,
            tech_readiness_level=7,
            is_domestic_substitution=True,
            is_hard_tech=True,
        )
        kwargs.update(overrides)
        return kwargs

    def test_core_plugin_high_tech_path_score(self):
        result = self.evaluator.evaluate(**self._base_kwargs())
        assert result.tech_path_score >= 7.0

    def test_system_rebuild_low_score_with_warning(self):
        result = self.evaluator.evaluate(
            **self._base_kwargs(tech_path_type=TECH_PATH_SYSTEM_REBUILD)
        )
        assert result.tech_path_score <= 5.0
        assert len(result.warnings) > 0

    def test_incremental_mid_score(self):
        result = self.evaluator.evaluate(
            **self._base_kwargs(tech_path_type=TECH_PATH_INCREMENTAL)
        )
        assert 4.0 <= result.tech_path_score <= 7.0

    def test_chokepoint_premium_coefficient(self):
        result = self.evaluator.evaluate(**self._base_kwargs())
        assert result.strategic_premium_coefficient >= 1.5

    def test_non_chokepoint_lower_premium(self):
        result = self.evaluator.evaluate(**self._base_kwargs(is_chokepoint_tech=False))
        assert result.strategic_premium_coefficient < 2.0

    def test_valuation_multiplier_range(self):
        result = self.evaluator.evaluate(**self._base_kwargs())
        assert 1.0 <= result.strategic_valuation_multiplier <= 3.0

    def test_low_trl_reduces_valuation_multiplier(self):
        result_low_trl = self.evaluator.evaluate(**self._base_kwargs(tech_readiness_level=2))
        result_high_trl = self.evaluator.evaluate(**self._base_kwargs(tech_readiness_level=8))
        assert result_low_trl.strategic_valuation_multiplier <= result_high_trl.strategic_valuation_multiplier

    def test_strategic_score_0_to_10(self):
        result = self.evaluator.evaluate(**self._base_kwargs())
        assert 0.0 <= result.strategic_score <= 10.0

    def test_tech_path_assessment_not_empty(self):
        result = self.evaluator.evaluate(**self._base_kwargs())
        assert len(result.tech_path_assessment) > 0

