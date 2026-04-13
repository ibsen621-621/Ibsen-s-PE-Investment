"""
Tests for GP post-investment evaluator and double-down decision model.
"""

import pytest
from src.investment_model.post_investment import (
    GPPostInvestmentEvaluator,
    DoubleDownDecisionModel,
)


class TestGPPostInvestmentEvaluator:
    def setup_method(self):
        self.evaluator = GPPostInvestmentEvaluator()

    def _base_kwargs(self, **overrides):
        kwargs = dict(
            has_financial_monitoring=True,
            has_3r_services=True,
            has_strategic_empowerment=True,
            has_exit_oriented_management=True,
            portfolio_company_survival_rate=0.70,
            avg_time_to_next_round_months=15.0,
        )
        kwargs.update(overrides)
        return kwargs

    def test_level_4_full_capabilities(self):
        result = self.evaluator.evaluate(**self._base_kwargs())
        assert result.level == 4
        assert result.score == 40

    def test_level_3_no_exit_oriented(self):
        result = self.evaluator.evaluate(
            **self._base_kwargs(has_exit_oriented_management=False)
        )
        assert result.level == 3
        assert result.score == 30

    def test_level_2_only_3r(self):
        result = self.evaluator.evaluate(
            **self._base_kwargs(
                has_strategic_empowerment=False,
                has_exit_oriented_management=False,
            )
        )
        assert result.level == 2
        assert result.score == 20

    def test_level_1_only_financial_monitoring(self):
        result = self.evaluator.evaluate(
            **self._base_kwargs(
                has_3r_services=False,
                has_strategic_empowerment=False,
                has_exit_oriented_management=False,
            )
        )
        assert result.level == 1
        assert result.score == 10

    def test_level_0_no_capabilities(self):
        result = self.evaluator.evaluate(
            has_financial_monitoring=False,
            has_3r_services=False,
            has_strategic_empowerment=False,
            has_exit_oriented_management=False,
            portfolio_company_survival_rate=0.3,
            avg_time_to_next_round_months=30.0,
        )
        assert result.level == 0
        assert result.score == 0

    def test_low_survival_rate_warning(self):
        result = self.evaluator.evaluate(**self._base_kwargs(portfolio_company_survival_rate=0.3))
        assert any("存活率" in w for w in result.warnings)

    def test_long_next_round_time_warning(self):
        result = self.evaluator.evaluate(
            **self._base_kwargs(avg_time_to_next_round_months=30.0)
        )
        assert any("下一轮" in w for w in result.warnings)

    def test_level_below_3_triggers_warning(self):
        result = self.evaluator.evaluate(
            **self._base_kwargs(
                has_strategic_empowerment=False,
                has_exit_oriented_management=False,
            )
        )
        assert len(result.warnings) > 0

    def test_level_4_includes_recommendation(self):
        result = self.evaluator.evaluate(**self._base_kwargs())
        assert len(result.recommendations) > 0

    def test_summary_contains_level_info(self):
        result = self.evaluator.evaluate(**self._base_kwargs())
        assert "40" in result.summary  # score in summary


class TestDoubleDownDecisionModel:
    def setup_method(self):
        self.model = DoubleDownDecisionModel()

    def _base_kwargs(self, **overrides):
        kwargs = dict(
            initial_investment_rmb=1.0,
            current_valuation_rmb=8.0,
            initial_valuation_rmb=2.0,
            tech_milestone_achieved=True,
            benchmark_customer_secured=True,
            revenue_inflection=True,
            competitive_moat_strengthened=True,
            follow_on_round_quality="top_tier",
            fund_remaining_capacity_rmb=10.0,
        )
        kwargs.update(overrides)
        return kwargs

    def test_strong_signal_recommends_follow_on(self):
        result = self.model.decide(**self._base_kwargs())
        assert result.recommended_action == "strong_follow_on"
        assert result.signal_strength >= 70

    def test_no_signal_no_follow_on(self):
        result = self.model.decide(
            **self._base_kwargs(
                tech_milestone_achieved=False,
                benchmark_customer_secured=False,
                revenue_inflection=False,
                competitive_moat_strengthened=False,
                follow_on_round_quality="weak",
            )
        )
        assert result.recommended_action == "no_follow_on"
        assert result.suggested_amount_rmb == 0.0

    def test_high_valuation_increase_triggers_caution(self):
        # Signal strength >= 70 but valuation > 5x initial
        result = self.model.decide(
            **self._base_kwargs(
                current_valuation_rmb=15.0,  # 7.5x from initial 2.0
                initial_valuation_rmb=2.0,
            )
        )
        assert result.recommended_action == "cautious_follow_on"
        assert any("估值" in w for w in result.warnings)

    def test_signal_strength_max_100(self):
        result = self.model.decide(**self._base_kwargs())
        assert result.signal_strength <= 100.0

    def test_signal_strength_minimum_zero(self):
        result = self.model.decide(
            **self._base_kwargs(
                tech_milestone_achieved=False,
                benchmark_customer_secured=False,
                revenue_inflection=False,
                competitive_moat_strengthened=False,
                follow_on_round_quality="weak",
            )
        )
        assert result.signal_strength >= 0.0

    def test_suggested_amount_respects_fund_capacity(self):
        result = self.model.decide(
            **self._base_kwargs(fund_remaining_capacity_rmb=2.0)
        )
        assert result.suggested_amount_rmb <= 2.0

    def test_weak_follow_on_quality_warning(self):
        result = self.model.decide(
            **self._base_kwargs(follow_on_round_quality="weak")
        )
        assert any("跟投方" in w for w in result.warnings)

    def test_partial_signal_mid_tier_follow_on(self):
        # Only 2 signals triggered, mid-tier quality
        result = self.model.decide(
            **self._base_kwargs(
                tech_milestone_achieved=True,
                benchmark_customer_secured=True,
                revenue_inflection=False,
                competitive_moat_strengthened=False,
                follow_on_round_quality="mid_tier",
                current_valuation_rmb=4.0,  # < 5x increase
                initial_valuation_rmb=2.0,
            )
        )
        # 30 (tech) + 25 (benchmark) + 5 (mid_tier) = 60 pts — cautious or strong
        assert result.recommended_action in ("strong_follow_on", "cautious_follow_on")

    def test_summary_contains_signal_strength(self):
        result = self.model.decide(**self._base_kwargs())
        assert "信号" in result.summary
