"""
Tests for financial metrics: IRR, DPI/TVPI, Valuation (Davis double-kill).
"""

import math
import pytest
from src.investment_model.metrics import IRRCalculator, DPITVPICalculator, ValuationAnalyzer


# ---------------------------------------------------------------------------
# IRRCalculator
# ---------------------------------------------------------------------------

class TestIRRCalculator:
    def setup_method(self):
        self.calc = IRRCalculator()

    def test_simple_3x_3yr(self):
        """3x in 3 years ≈ 44.2% IRR"""
        result = self.calc.from_multiple(
            investment_rmb=10.0,
            return_rmb=30.0,
            holding_years=3,
        )
        assert result.meets_hurdle is True
        assert abs(result.irr_pct - 44.22) < 0.5

    def test_below_hurdle(self):
        """1.3x in 5 years ≈ 5.4% IRR — below 15% hurdle"""
        result = self.calc.from_multiple(
            investment_rmb=10.0,
            return_rmb=13.0,
            holding_years=5,
        )
        assert result.meets_hurdle is False
        assert result.irr_pct < 15.0

    def test_15pct_hurdle_exactly(self):
        """Investment that exactly meets 15% hurdle over 5 years"""
        # 1.15^5 ≈ 2.011
        result = self.calc.from_multiple(
            investment_rmb=10.0,
            return_rmb=20.12,
            holding_years=5,
            hurdle_rate=0.15,
        )
        assert result.meets_hurdle is True
        assert abs(result.irr_pct - 15.0) < 0.5

    def test_cash_flows_with_interim_investment(self):
        """Multi-period cash flow with interim investment"""
        # Invest 5 upfront, add 1 in year 1, receive 20 in year 4
        result = self.calc.calculate([-5.0, -1.0, 0.0, 0.0, 20.0])
        assert not math.isnan(result.irr_pct)
        assert result.irr_pct > 0

    def test_summary_contains_irr(self):
        result = self.calc.from_multiple(10.0, 30.0, 3)
        assert "IRR" in result.summary

    def test_custom_hurdle_rate(self):
        """Custom 20% hurdle rate"""
        result = self.calc.from_multiple(
            investment_rmb=10.0,
            return_rmb=15.0,
            holding_years=3,
            hurdle_rate=0.20,
        )
        # 3yr 1.5x ≈ 14.5% < 20%
        assert result.meets_hurdle is False
        assert result.hurdle_rate_pct == 20.0


# ---------------------------------------------------------------------------
# DPITVPICalculator
# ---------------------------------------------------------------------------

class TestDPITVPICalculator:
    def setup_method(self):
        self.calc = DPITVPICalculator()

    def test_healthy_global_fund(self):
        """DPI/TVPI ≥ 88% — matches global top fund benchmark"""
        result = self.calc.calculate(
            total_invested_rmb=10.0,
            total_distributed_rmb=16.0,
            remaining_fair_value_rmb=2.0,
            benchmark="global",
        )
        assert result.dpi == pytest.approx(1.6, abs=0.01)
        assert result.tvpi == pytest.approx(1.8, abs=0.01)
        # conversion = 1.6 / 1.8 ≈ 88.9%
        assert result.conversion_rate > 0.85
        assert result.is_healthy is True

    def test_typical_china_rmb_fund(self):
        """Simulates typical Chinese RMB fund with low cash conversion"""
        result = self.calc.calculate(
            total_invested_rmb=10.0,
            total_distributed_rmb=4.0,
            remaining_fair_value_rmb=8.0,
            benchmark="china",
        )
        # conversion = 4/12 ≈ 33%
        assert result.conversion_rate < 0.40
        assert len(result.warnings) > 0

    def test_dpi_below_one_warning(self):
        result = self.calc.calculate(
            total_invested_rmb=10.0,
            total_distributed_rmb=8.0,
            remaining_fair_value_rmb=4.0,
        )
        assert result.dpi < 1.0
        assert any("本金" in w for w in result.warnings)

    def test_zero_invested_raises(self):
        with pytest.raises(ValueError):
            self.calc.calculate(
                total_invested_rmb=0,
                total_distributed_rmb=5.0,
                remaining_fair_value_rmb=5.0,
            )

    def test_dpi_tvpi_rvpi_relation(self):
        """DPI + RVPI should equal TVPI"""
        result = self.calc.calculate(
            total_invested_rmb=10.0,
            total_distributed_rmb=12.0,
            remaining_fair_value_rmb=5.0,
        )
        assert result.tvpi == pytest.approx(result.dpi + result.rvpi, abs=0.001)

    def test_summary_contains_dpi(self):
        result = self.calc.calculate(10.0, 12.0, 5.0)
        assert "DPI" in result.summary


# ---------------------------------------------------------------------------
# ValuationAnalyzer — Davis double-kill
# ---------------------------------------------------------------------------

class TestValuationAnalyzer:
    def setup_method(self):
        self.analyzer = ValuationAnalyzer()

    def _base_kwargs(self, **overrides):
        kwargs = dict(
            current_pe=80.0,
            sector_median_pe=40.0,
            current_earnings_growth_pct=20.0,
            consensus_earnings_growth_pct=60.0,
            market_phase="boom",
        )
        kwargs.update(overrides)
        return kwargs

    def test_critical_davis_double_kill(self):
        result = self.analyzer.analyze(
            current_pe=100.0,
            sector_median_pe=40.0,
            current_earnings_growth_pct=10.0,
            consensus_earnings_growth_pct=60.0,
            market_phase="neutral",
        )
        assert result.davis_double_kill_risk is True
        assert result.risk_level == "critical"

    def test_low_risk_fair_valuation(self):
        result = self.analyzer.analyze(
            current_pe=20.0,
            sector_median_pe=20.0,
            current_earnings_growth_pct=30.0,
            consensus_earnings_growth_pct=30.0,
            market_phase="neutral",
        )
        assert result.risk_level == "low"
        assert result.davis_double_kill_risk is False

    def test_pe_premium_calculation(self):
        result = self.analyzer.analyze(
            current_pe=60.0,
            sector_median_pe=40.0,
            current_earnings_growth_pct=30.0,
            consensus_earnings_growth_pct=30.0,
            market_phase="neutral",
        )
        # (60-40)/40 * 100 = 50%
        assert result.pe_premium_pct == pytest.approx(50.0, abs=0.1)

    def test_boom_market_warning(self):
        result = self.analyzer.analyze(**self._base_kwargs(market_phase="boom"))
        assert any("市梦率" in w for w in result.warnings)

    def test_no_double_kill_in_boom_with_high_growth(self):
        """Boom + high actual earnings growth should not trigger double-kill"""
        result = self.analyzer.analyze(
            current_pe=60.0,
            sector_median_pe=40.0,
            current_earnings_growth_pct=80.0,
            consensus_earnings_growth_pct=80.0,
            market_phase="boom",
        )
        assert result.davis_double_kill_risk is False

    def test_summary_contains_risk_info(self):
        result = self.analyzer.analyze(**self._base_kwargs())
        assert "PE溢价" in result.summary
