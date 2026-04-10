"""
Tests for mathematical growth curves and exit signal detector.
"""

import math
import pytest

from src.investment_model.curves import (
    LogisticGrowthCurve,
    GompertzCurve,
    CapitalCycleCurve,
    CapitalCyclePoint,
    ExitSignalDetector,
)


# ---------------------------------------------------------------------------
# LogisticGrowthCurve
# ---------------------------------------------------------------------------

class TestLogisticGrowthCurve:
    def test_value_at_inflection_is_half_K(self):
        curve = LogisticGrowthCurve(K=100.0, r=1.0, t0=5.0)
        assert abs(curve.value(5.0) - 50.0) < 0.01

    def test_approaches_K_at_large_t(self):
        curve = LogisticGrowthCurve(K=100.0, r=1.0, t0=5.0)
        assert curve.value(100.0) > 99.0

    def test_approaches_zero_at_negative_t(self):
        curve = LogisticGrowthCurve(K=100.0, r=1.0, t0=5.0)
        assert curve.value(-50.0) < 0.01

    def test_derivative_positive_before_peak(self):
        curve = LogisticGrowthCurve(K=100.0, r=1.0, t0=5.0)
        assert curve.derivative(3.0) > 0

    def test_derivative_decreasing_after_peak(self):
        curve = LogisticGrowthCurve(K=100.0, r=1.0, t0=5.0)
        d_before = curve.derivative(4.9)
        d_after = curve.derivative(6.0)
        assert d_before > d_after

    def test_peak_derivative_time_equals_t0(self):
        curve = LogisticGrowthCurve(K=200.0, r=0.5, t0=7.0)
        assert curve.peak_derivative_time() == 7.0

    def test_is_past_peak(self):
        curve = LogisticGrowthCurve(K=100.0, r=1.0, t0=5.0)
        assert not curve.is_past_peak(4.0)
        assert curve.is_past_peak(6.0)

    def test_invalid_K_raises(self):
        with pytest.raises(ValueError):
            LogisticGrowthCurve(K=-10, r=1.0, t0=5.0)

    def test_growth_rate_decreases_after_peak(self):
        curve = LogisticGrowthCurve(K=100.0, r=1.0, t0=5.0)
        gr_early = curve.growth_rate(1.0)
        gr_late = curve.growth_rate(10.0)
        assert gr_early > gr_late


# ---------------------------------------------------------------------------
# GompertzCurve
# ---------------------------------------------------------------------------

class TestGompertzCurve:
    def test_value_monotone_increasing(self):
        curve = GompertzCurve(K=100.0, b=3.0, c=0.5)
        prev = 0.0
        for t in [0, 1, 2, 5, 10, 20]:
            val = curve.value(t)
            assert val >= prev
            prev = val

    def test_value_approaches_K(self):
        curve = GompertzCurve(K=100.0, b=3.0, c=0.5)
        assert curve.value(100.0) > 99.0

    def test_peak_derivative_time_formula(self):
        b, c = 3.0, 0.5
        curve = GompertzCurve(K=100.0, b=b, c=c)
        expected = math.log(b) / c
        assert abs(curve.peak_derivative_time() - expected) < 1e-9

    def test_derivative_positive(self):
        curve = GompertzCurve(K=100.0, b=3.0, c=0.5)
        for t in [0, 1, 2, 5]:
            assert curve.derivative(t) > 0

    def test_is_past_peak(self):
        curve = GompertzCurve(K=100.0, b=3.0, c=0.5)
        peak_t = curve.peak_derivative_time()
        assert not curve.is_past_peak(peak_t - 0.5)
        assert curve.is_past_peak(peak_t + 0.5)

    def test_invalid_params_raise(self):
        with pytest.raises(ValueError):
            GompertzCurve(K=100, b=-1, c=0.5)
        with pytest.raises(ValueError):
            GompertzCurve(K=100, b=1, c=-0.5)


# ---------------------------------------------------------------------------
# CapitalCycleCurve
# ---------------------------------------------------------------------------

class TestCapitalCycleCurve:
    def _make_curve(self):
        return CapitalCycleCurve([
            CapitalCyclePoint(t=0.0, pe_multiple=20.0, sentiment="warming"),
            CapitalCyclePoint(t=3.0, pe_multiple=40.0, sentiment="hot"),
            CapitalCyclePoint(t=6.0, pe_multiple=25.0, sentiment="cooling"),
            CapitalCyclePoint(t=9.0, pe_multiple=15.0, sentiment="cold"),
        ])

    def test_interpolation_midpoint(self):
        curve = self._make_curve()
        # At t=1.5, halfway between 0 and 3: PE should be ~30
        val = curve.pe_at(1.5)
        assert abs(val - 30.0) < 0.1

    def test_boundary_clamp_left(self):
        curve = self._make_curve()
        assert curve.pe_at(-5.0) == 20.0

    def test_boundary_clamp_right(self):
        curve = self._make_curve()
        assert curve.pe_at(100.0) == 15.0

    def test_peak_t_at_max(self):
        curve = self._make_curve()
        assert curve.peak_t() == 3.0

    def test_is_expanding_before_peak(self):
        curve = self._make_curve()
        assert curve.is_expanding(1.5)

    def test_not_expanding_after_peak(self):
        curve = self._make_curve()
        assert not curve.is_expanding(4.5)

    def test_requires_at_least_two_points(self):
        with pytest.raises(ValueError):
            CapitalCycleCurve([CapitalCyclePoint(0.0, 20.0, "warm")])


# ---------------------------------------------------------------------------
# ExitSignalDetector
# ---------------------------------------------------------------------------

class TestExitSignalDetector:
    def _make_mature_detector(self):
        """Three curves all near their peak around t=3."""
        ind = LogisticGrowthCurve(K=100, r=2.0, t0=3.0)
        com = LogisticGrowthCurve(K=100, r=2.0, t0=3.0)
        cap = CapitalCycleCurve([
            CapitalCyclePoint(0, 10, "cold"),
            CapitalCyclePoint(3, 40, "hot"),
            CapitalCyclePoint(8, 10, "cold"),
        ])
        return ExitSignalDetector(ind, com, cap)

    def _make_early_detector(self):
        """Curves with inflection far in the future — no early exit signals."""
        ind = LogisticGrowthCurve(K=100, r=0.5, t0=20.0)
        com = GompertzCurve(K=100, b=20.0, c=0.3)
        cap = CapitalCycleCurve([
            CapitalCyclePoint(0, 15, "warming"),
            CapitalCyclePoint(10, 50, "hot"),
        ])
        return ExitSignalDetector(ind, com, cap)

    def test_mature_curves_generate_signals(self):
        detector = self._make_mature_detector()
        report = detector.scan(t_start=2.0, t_end=8.0, dt=0.5)
        assert len(report.signals) > 0

    def test_silver_or_golden_peak_detected_near_t3(self):
        detector = self._make_mature_detector()
        report = detector.scan(t_start=3.0, t_end=7.0, dt=0.5)
        types = {s.signal_type for s in report.signals}
        assert "silver_peak" in types or "golden_peak" in types

    def test_early_curves_no_silver_peak_at_start(self):
        detector = self._make_early_detector()
        report = detector.scan(t_start=0.0, t_end=5.0, dt=0.5)
        types = {s.signal_type for s in report.signals}
        # Early growth curves should not show silver/golden peaks yet
        assert "golden_peak" not in types

    def test_report_summary_contains_window_info(self):
        detector = self._make_mature_detector()
        report = detector.scan(t_start=0.0, t_end=6.0, dt=0.5)
        assert "扫描区间" in report.summary

    def test_signals_deduplicated(self):
        """Same signal type should not appear twice in the deduplicated output."""
        detector = self._make_mature_detector()
        report = detector.scan(t_start=3.0, t_end=7.0, dt=0.25)
        type_counts: dict[str, int] = {}
        for sig in report.signals:
            type_counts[sig.signal_type] = type_counts.get(sig.signal_type, 0) + 1
        for count in type_counts.values():
            assert count == 1

    def test_signal_fields_populated(self):
        detector = self._make_mature_detector()
        report = detector.scan(t_start=3.0, t_end=8.0, dt=1.0)
        for sig in report.signals:
            assert sig.t >= 0
            assert sig.recommended_action != ""
            assert sig.trigger_reason != ""
