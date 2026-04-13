"""
Tests for LP behavioral bias corrector.
"""

import pytest
from src.investment_model.lp_evaluation import LPBehaviorChecker


class TestLPBehaviorChecker:
    def setup_method(self):
        self.checker = LPBehaviorChecker()

    def _base_kwargs(self, **overrides):
        kwargs = dict(
            attracted_by_narrative=False,
            has_concrete_evidence=True,
            following_famous_fund=False,
            has_independent_analysis=True,
            estimated_win_probability_pct=25.0,
            expected_return_multiple=8.0,
            expected_loss_multiple=0.2,
        )
        kwargs.update(overrides)
        return kwargs

    def test_rational_lp_no_biases(self):
        result = self.checker.check(**self._base_kwargs())
        assert result.narrative_trap_detected is False
        assert result.fomo_detected is False
        assert result.is_rational_decision is True

    def test_narrative_trap_detected(self):
        result = self.checker.check(
            **self._base_kwargs(
                attracted_by_narrative=True,
                has_concrete_evidence=False,
            )
        )
        assert result.narrative_trap_detected is True
        assert any("宏大叙事" in w for w in result.warnings)

    def test_narrative_with_evidence_not_trap(self):
        result = self.checker.check(
            **self._base_kwargs(
                attracted_by_narrative=True,
                has_concrete_evidence=True,
            )
        )
        assert result.narrative_trap_detected is False

    def test_fomo_detected(self):
        result = self.checker.check(
            **self._base_kwargs(
                following_famous_fund=True,
                has_independent_analysis=False,
            )
        )
        assert result.fomo_detected is True
        assert any("FOMO" in w for w in result.warnings)

    def test_fomo_with_independent_analysis_not_triggered(self):
        result = self.checker.check(
            **self._base_kwargs(
                following_famous_fund=True,
                has_independent_analysis=True,
            )
        )
        assert result.fomo_detected is False

    def test_expected_value_calculation(self):
        """EV = win_prob * return_multiple + (1-win_prob) * loss_multiple"""
        result = self.checker.check(
            **self._base_kwargs(
                estimated_win_probability_pct=30.0,
                expected_return_multiple=5.0,
                expected_loss_multiple=0.2,
            )
        )
        expected = 0.30 * 5.0 + 0.70 * 0.2
        assert abs(result.expected_value - expected) < 0.01

    def test_negative_expected_value_warning(self):
        result = self.checker.check(
            **self._base_kwargs(
                estimated_win_probability_pct=10.0,
                expected_return_multiple=3.0,
                expected_loss_multiple=0.0,
            )
        )
        # EV = 0.1 * 3.0 + 0.9 * 0.0 = 0.3 < 1.0
        assert result.expected_value < 1.0
        assert any("期望" in w or "数学" in w for w in result.warnings)

    def test_positive_expected_value_rational(self):
        result = self.checker.check(
            **self._base_kwargs(
                estimated_win_probability_pct=30.0,
                expected_return_multiple=10.0,
                expected_loss_multiple=0.1,
            )
        )
        # EV = 0.3 * 10 + 0.7 * 0.1 = 3.07 > 1.0
        assert result.expected_value > 1.0

    def test_multiple_biases_irrational(self):
        result = self.checker.check(
            attracted_by_narrative=True,
            has_concrete_evidence=False,
            following_famous_fund=True,
            has_independent_analysis=False,
            estimated_win_probability_pct=15.0,
            expected_return_multiple=3.0,
            expected_loss_multiple=0.1,
        )
        assert result.narrative_trap_detected is True
        assert result.fomo_detected is True
        assert result.is_rational_decision is False

    def test_soul_questions_not_empty(self):
        result = self.checker.check(**self._base_kwargs())
        assert len(result.soul_questions) > 0

    def test_narrative_trap_generates_soul_question(self):
        result = self.checker.check(
            **self._base_kwargs(
                attracted_by_narrative=True,
                has_concrete_evidence=False,
            )
        )
        assert any("灵魂拷问" in q or "具体" in q for q in result.soul_questions)

    def test_fomo_generates_soul_question(self):
        result = self.checker.check(
            **self._base_kwargs(
                following_famous_fund=True,
                has_independent_analysis=False,
            )
        )
        assert any("知名机构" in q or "独立" in q for q in result.soul_questions)

    def test_summary_contains_ev(self):
        result = self.checker.check(**self._base_kwargs())
        assert "期望值" in result.summary

    def test_is_rational_false_when_ev_negative(self):
        result = self.checker.check(
            **self._base_kwargs(
                estimated_win_probability_pct=5.0,
                expected_return_multiple=2.0,
                expected_loss_multiple=0.0,
            )
        )
        # EV = 0.05 * 2.0 + 0.95 * 0.0 = 0.1 < 1.0
        assert result.is_rational_decision is False
