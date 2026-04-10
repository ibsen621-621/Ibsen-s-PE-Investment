"""
Tests for:
- FundCashflowModel (J-curve, capital calls, management fees, waterfall)
- LiquidityDiscountModel (dynamic discount)
- CompsValuationAnchor (external comps interface)
- UnrealisedValueStripper (GP MOC auto-adjustment)
"""

import math
import pytest

from src.investment_model.fund_cashflow import FundCashflowModel
from src.investment_model.exit import LiquidityDiscountModel
from src.investment_model.metrics import (
    CompsValuationAnchor,
    CompanyComp,
    UnrealisedValueStripper,
)


# ---------------------------------------------------------------------------
# FundCashflowModel
# ---------------------------------------------------------------------------

class TestFundCashflowModel:
    def setup_method(self):
        self.model = FundCashflowModel()

    def _standard_fund(self, nav_growth_rate: float = 0.25):
        """A standard 8-year PE fund."""
        return self.model.model(
            fund_name="测试基金",
            fund_size_rmb=10.0,
            capital_call_schedule=[0.30, 0.30, 0.25, 0.15],
            exit_schedule=[0, 0, 0, 0, 0.20, 0.30, 0.40, 0.10],
            nav_growth_rate=nav_growth_rate,
        )

    def test_annual_flows_length_matches_schedule(self):
        result = self._standard_fund()
        assert len(result.annual_flows) == 8

    def test_cumulative_distributed_monotone(self):
        result = self._standard_fund()
        prev = 0.0
        for flow in result.annual_flows:
            assert flow.cumulative_distributed_rmb >= prev - 1e-9
            prev = flow.cumulative_distributed_rmb

    def test_dpi_non_negative(self):
        result = self._standard_fund()
        for flow in result.annual_flows:
            assert flow.dpi >= 0

    def test_tvpi_ge_dpi(self):
        result = self._standard_fund()
        for flow in result.annual_flows:
            assert flow.tvpi >= flow.dpi - 1e-9

    def test_final_dpi_positive_for_good_fund(self):
        result = self._standard_fund(nav_growth_rate=0.30)
        assert result.final_dpi > 0

    def test_summary_contains_irr(self):
        result = self._standard_fund()
        assert "IRR" in result.summary

    def test_j_curve_trough_in_early_years(self):
        result = self._standard_fund()
        # Trough should be in the investment period (years 1-4)
        if result.j_curve_trough_year is not None:
            assert result.j_curve_trough_year <= 6

    def test_breakeven_year_after_start(self):
        result = self._standard_fund(nav_growth_rate=0.40)
        # With strong growth, fund should eventually hit DPI ≥ 1.0
        if result.j_curve_breakeven_year is not None:
            assert result.j_curve_breakeven_year >= 1

    def test_gp_carry_non_negative(self):
        result = self._standard_fund()
        assert result.gp_carry_rmb >= 0

    def test_management_fee_deducted_from_net_invested(self):
        result = self._standard_fund()
        for flow in result.annual_flows:
            # net_invested = call - management_fee (clamped to 0)
            assert flow.net_invested_rmb >= 0
            assert flow.net_invested_rmb <= flow.capital_call_rmb + 1e-9

    def test_zero_nav_growth_still_runs(self):
        result = self._standard_fund(nav_growth_rate=0.0)
        assert result.final_dpi >= 0

    def test_fund_with_only_calls_no_exits(self):
        result = self.model.model(
            fund_name="无退出基金",
            fund_size_rmb=5.0,
            capital_call_schedule=[0.5, 0.5],
            exit_schedule=[0, 0],
            nav_growth_rate=0.20,
        )
        assert result.final_dpi == 0.0

    def test_irr_improves_with_higher_nav_growth(self):
        r_low = self._standard_fund(nav_growth_rate=0.10)
        r_high = self._standard_fund(nav_growth_rate=0.40)
        if r_low.final_irr_pct is not None and r_high.final_irr_pct is not None:
            assert r_high.final_irr_pct > r_low.final_irr_pct


# ---------------------------------------------------------------------------
# LiquidityDiscountModel
# ---------------------------------------------------------------------------

class TestLiquidityDiscountModel:
    def setup_method(self):
        self.model = LiquidityDiscountModel()

    def test_neutral_environment_vc(self):
        result = self.model.calculate(
            asset_stage="vc",
            credit_cycle="neutral",
            s_fund_market="active",
        )
        assert 5 <= result.total_discount_pct <= 50

    def test_rate_hike_increases_discount(self):
        neutral = self.model.calculate(
            asset_stage="pe",
            credit_cycle="neutral",
            s_fund_market="active",
        )
        hike = self.model.calculate(
            asset_stage="pe",
            credit_cycle="rate_hike_aggressive",
            s_fund_market="active",
        )
        assert hike.total_discount_pct > neutral.total_discount_pct

    def test_frozen_sfund_increases_discount(self):
        active = self.model.calculate(
            asset_stage="pe",
            credit_cycle="neutral",
            s_fund_market="active",
        )
        frozen = self.model.calculate(
            asset_stage="pe",
            credit_cycle="neutral",
            s_fund_market="frozen",
        )
        assert frozen.total_discount_pct > active.total_discount_pct

    def test_rate_cut_reduces_discount(self):
        neutral = self.model.calculate(
            asset_stage="vc",
            credit_cycle="neutral",
            s_fund_market="active",
        )
        cut = self.model.calculate(
            asset_stage="vc",
            credit_cycle="rate_cut",
            s_fund_market="active",
        )
        assert cut.total_discount_pct < neutral.total_discount_pct

    def test_discount_clamped_to_valid_range(self):
        # Worst case: angel + aggressive hike + frozen + low quality + 1yr
        result = self.model.calculate(
            asset_stage="angel",
            credit_cycle="rate_hike_aggressive",
            s_fund_market="frozen",
            asset_quality="low",
            years_to_fund_end=1,
        )
        assert 5 <= result.total_discount_pct <= 50

    def test_high_quality_reduces_discount(self):
        avg = self.model.calculate(
            asset_stage="pe",
            credit_cycle="neutral",
            s_fund_market="active",
            asset_quality="average",
        )
        high = self.model.calculate(
            asset_stage="pe",
            credit_cycle="neutral",
            s_fund_market="active",
            asset_quality="high",
        )
        assert high.total_discount_pct < avg.total_discount_pct

    def test_urgency_increases_discount(self):
        no_urgency = self.model.calculate(
            asset_stage="pe",
            credit_cycle="neutral",
            s_fund_market="active",
            years_to_fund_end=5,
        )
        urgent = self.model.calculate(
            asset_stage="pe",
            credit_cycle="neutral",
            s_fund_market="active",
            years_to_fund_end=1,
        )
        assert urgent.total_discount_pct >= no_urgency.total_discount_pct

    def test_warnings_for_hike_and_frozen(self):
        result = self.model.calculate(
            asset_stage="vc",
            credit_cycle="rate_hike_mild",
            s_fund_market="frozen",
        )
        assert len(result.warnings) >= 2

    def test_summary_contains_components(self):
        result = self.model.calculate(asset_stage="vc")
        assert "基础折价" in result.summary
        assert "S基金" in result.summary


# ---------------------------------------------------------------------------
# CompsValuationAnchor
# ---------------------------------------------------------------------------

class TestCompsValuationAnchor:
    def setup_method(self):
        self.anchor = CompsValuationAnchor(safety_factor=0.70)
        self.anchor.add_comps([
            CompanyComp("商汤", "AI", pe_multiple=80.0, ev_ebitda=40.0, ps_multiple=15.0),
            CompanyComp("旷视", "AI", pe_multiple=70.0, ev_ebitda=35.0, ps_multiple=12.0),
            CompanyComp("第四范式", "AI", pe_multiple=90.0, ev_ebitda=45.0, ps_multiple=18.0),
            CompanyComp("云从科技", "AI", pe_multiple=60.0, ev_ebitda=30.0, ps_multiple=10.0),
        ])

    def test_median_pe_in_range(self):
        result = self.anchor.analyze("AI")
        # Median of [60, 70, 80, 90] = 75
        assert result.median_pe == 75.0

    def test_conservative_entry_pe_below_median(self):
        result = self.anchor.analyze("AI")
        assert result.conservative_entry_pe < result.median_pe

    def test_safety_factor_applied(self):
        result = self.anchor.analyze("AI")
        expected = round(result.median_pe * 0.70, 2)
        assert result.conservative_entry_pe == expected

    def test_ev_ebitda_stats(self):
        result = self.anchor.analyze("AI")
        assert result.median_ev_ebitda is not None
        assert result.median_ev_ebitda > 0

    def test_ps_stats(self):
        result = self.anchor.analyze("AI")
        assert result.median_ps is not None

    def test_filter_by_sector(self):
        self.anchor.add_comp(CompanyComp("消费A", "Consumer", pe_multiple=20.0))
        ai_result = self.anchor.analyze("AI")
        assert ai_result.n_comps == 4  # only AI comps

    def test_no_comps_raises(self):
        anchor = CompsValuationAnchor()
        with pytest.raises(ValueError):
            anchor.analyze("NonExistentSector")

    def test_small_sample_warning(self):
        anchor = CompsValuationAnchor()
        anchor.add_comp(CompanyComp("X", "Tech", pe_multiple=30.0))
        anchor.add_comp(CompanyComp("Y", "Tech", pe_multiple=40.0))
        result = anchor.analyze("Tech")
        assert len(result.warnings) > 0

    def test_summary_mentions_safety_factor(self):
        result = self.anchor.analyze("AI")
        assert "70%" in result.summary or "安全系数" in result.summary

    def test_custom_safety_factor(self):
        anchor = CompsValuationAnchor(safety_factor=0.50)
        for comp in [
            CompanyComp("A", "PE", pe_multiple=40.0),
            CompanyComp("B", "PE", pe_multiple=50.0),
            CompanyComp("C", "PE", pe_multiple=60.0),
        ]:
            anchor.add_comp(comp)
        result = anchor.analyze("PE")
        # Median PE = 50; conservative = 50 × 0.5 = 25
        assert result.conservative_entry_pe == 25.0

    def test_invalid_safety_factor_raises(self):
        with pytest.raises(ValueError):
            CompsValuationAnchor(safety_factor=0.0)
        with pytest.raises(ValueError):
            CompsValuationAnchor(safety_factor=1.5)


# ---------------------------------------------------------------------------
# UnrealisedValueStripper
# ---------------------------------------------------------------------------

class TestUnrealisedValueStripper:
    def setup_method(self):
        self.stripper = UnrealisedValueStripper()

    def test_zero_discount_no_change_to_rvpi(self):
        result = self.stripper.strip(
            reported_moc=3.0,
            reported_tvpi=3.0,
            total_invested_rmb=10.0,
            total_distributed_rmb=5.0,
            unrealised_holdings=[
                {"name": "A", "book_value": 25.0, "follow_on_discount_pct": 0.0},
            ],
        )
        # No discount → adjustment factor = 1 → adjusted MOC ≈ reported MOC
        assert abs(result.adjusted_moc - result.reported_moc) < 0.01

    def test_discount_reduces_moc(self):
        result = self.stripper.strip(
            reported_moc=3.5,
            reported_tvpi=3.5,
            total_invested_rmb=10.0,
            total_distributed_rmb=5.0,
            unrealised_holdings=[
                {"name": "B", "book_value": 20.0, "follow_on_discount_pct": 50.0},
            ],
        )
        assert result.adjusted_moc < result.reported_moc

    def test_water_content_pct_positive_with_discount(self):
        result = self.stripper.strip(
            reported_moc=4.0,
            reported_tvpi=4.0,
            total_invested_rmb=10.0,
            total_distributed_rmb=5.0,
            unrealised_holdings=[
                {"name": "C", "book_value": 30.0, "follow_on_discount_pct": 40.0},
            ],
        )
        assert result.water_content_pct > 0

    def test_100pct_discount_wipes_unrealised(self):
        result = self.stripper.strip(
            reported_moc=3.0,
            reported_tvpi=3.0,
            total_invested_rmb=10.0,
            total_distributed_rmb=5.0,
            unrealised_holdings=[
                {"name": "D", "book_value": 20.0, "follow_on_discount_pct": 100.0},
            ],
        )
        # All unrealised wiped → adjusted value = 0
        assert result.total_adjusted_value == 0.0

    def test_high_discount_triggers_warning(self):
        result = self.stripper.strip(
            reported_moc=5.0,
            reported_tvpi=5.0,
            total_invested_rmb=10.0,
            total_distributed_rmb=2.0,
            unrealised_holdings=[
                {"name": "E", "book_value": 40.0, "follow_on_discount_pct": 60.0},
            ],
        )
        assert len(result.warnings) > 0

    def test_multiple_holdings(self):
        result = self.stripper.strip(
            reported_moc=3.0,
            reported_tvpi=3.0,
            total_invested_rmb=10.0,
            total_distributed_rmb=5.0,
            unrealised_holdings=[
                {"name": "F", "book_value": 10.0, "follow_on_discount_pct": 20.0},
                {"name": "G", "book_value": 10.0, "follow_on_discount_pct": 0.0},
            ],
        )
        # Average discount = 10% → adjustment factor = 0.9
        expected_adj_factor = (8.0 + 10.0) / (10.0 + 10.0)  # = 0.9
        assert abs(result.adjustment_factor - expected_adj_factor) < 1e-9

    def test_adjusted_tvpi_formula(self):
        result = self.stripper.strip(
            reported_moc=3.0,
            reported_tvpi=3.0,
            total_invested_rmb=10.0,
            total_distributed_rmb=5.0,
            unrealised_holdings=[
                {"name": "H", "book_value": 20.0, "follow_on_discount_pct": 25.0},
            ],
        )
        # adjusted_tvpi = (5 + 20 * 0.75) / 10 = (5 + 15) / 10 = 2.0
        assert abs(result.adjusted_tvpi - 2.0) < 1e-9

    def test_summary_contains_water_content(self):
        result = self.stripper.strip(
            reported_moc=3.0,
            reported_tvpi=3.0,
            total_invested_rmb=10.0,
            total_distributed_rmb=5.0,
            unrealised_holdings=[
                {"name": "I", "book_value": 20.0, "follow_on_discount_pct": 30.0},
            ],
        )
        assert "水分" in result.summary
