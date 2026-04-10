"""
Tests for investment stage models (Angel, VC, PE, BSE).
"""

import pytest
from src.investment_model.stages import AngelModel, VCModel, PEModel, BSEModel


# ---------------------------------------------------------------------------
# AngelModel — 50-50-1
# ---------------------------------------------------------------------------

class TestAngelModel:
    def setup_method(self):
        self.model = AngelModel()

    def _base_kwargs(self, **overrides):
        kwargs = dict(
            entry_valuation_rmb=0.4,
            fund_size_rmb=2.0,
            investment_amount_rmb=0.1,
            expected_market_cap_rmb=60.0,
            dilution_rate=0.60,
            holding_years=7,
        )
        kwargs.update(overrides)
        return kwargs

    def test_viable_investment(self):
        result = self.model.evaluate(**self._base_kwargs())
        assert result.is_viable is True
        assert result.score > 50
        # With 60% dilution, entry at 0.4亿, market cap 60亿: return ≈ 48x (close to 50x target)
        assert result.expected_return_multiple >= 45

    def test_overvalued_entry_reduces_score(self):
        result = self.model.evaluate(**self._base_kwargs(entry_valuation_rmb=2.0))
        # Entry valuation 2亿 >> 0.5亿 max: should warn and reduce score
        assert any("超过5000万" in w for w in result.warnings)
        assert result.score < 100

    def test_insufficient_market_cap(self):
        result = self.model.evaluate(**self._base_kwargs(expected_market_cap_rmb=10.0))
        # Market cap 10亿 < 50亿 threshold
        assert any("50亿门槛" in w for w in result.warnings)

    def test_fund_recovery_check(self):
        result = self.model.evaluate(
            **self._base_kwargs(
                investment_amount_rmb=0.01,  # tiny investment
                fund_size_rmb=100.0,         # giant fund — can't recover it
            )
        )
        assert any("基金规模" in w for w in result.warnings)

    def test_stage_label(self):
        result = self.model.evaluate(**self._base_kwargs())
        assert "Angel" in result.stage

    def test_details_keys(self):
        result = self.model.evaluate(**self._base_kwargs())
        expected_keys = {
            "entry_valuation_rmb", "investment_amount_rmb",
            "expected_market_cap_rmb", "return_multiple",
        }
        assert expected_keys.issubset(result.details.keys())


# ---------------------------------------------------------------------------
# VCModel — 100-10-10
# ---------------------------------------------------------------------------

class TestVCModel:
    def setup_method(self):
        self.model = VCModel()

    def _base_kwargs(self, **overrides):
        kwargs = dict(
            entry_valuation_rmb=6.0,
            investment_amount_rmb=1.0,
            expected_market_cap_rmb=120.0,
            fund_size_rmb=20.0,
            dilution_rate=0.40,
            holding_years=5,
        )
        kwargs.update(overrides)
        return kwargs

    def test_viable_investment(self):
        result = self.model.evaluate(**self._base_kwargs())
        assert result.is_viable is True

    def test_overvalued_entry(self):
        result = self.model.evaluate(**self._base_kwargs(entry_valuation_rmb=12.0))
        assert any("VC上限8亿" in w for w in result.warnings)
        assert result.is_viable is False

    def test_stake_below_13pct(self):
        # stake = 1 / (20 + 1) = ~4.8% — way below 13%
        result = self.model.evaluate(**self._base_kwargs(entry_valuation_rmb=20.0, investment_amount_rmb=1.0))
        assert any("13%" in w for w in result.warnings)

    def test_market_cap_below_100yi(self):
        result = self.model.evaluate(**self._base_kwargs(expected_market_cap_rmb=50.0))
        assert any("百亿门槛" in w for w in result.warnings)

    def test_details_contain_stake(self):
        result = self.model.evaluate(**self._base_kwargs())
        assert "stake_pct" in result.details
        assert result.details["stake_pct"] > 0


# ---------------------------------------------------------------------------
# PEModel — 3-year-3x / 4-year-4x
# ---------------------------------------------------------------------------

class TestPEModel:
    def setup_method(self):
        self.model = PEModel()

    def _base_kwargs(self, **overrides):
        kwargs = dict(
            entry_pe=15.0,
            current_profit_rmb=2.0,
            annual_profit_growth_rate=0.35,
            target_exit_pe=25.0,
            investment_amount_rmb=5.0,
            holding_years=3,
        )
        kwargs.update(overrides)
        return kwargs

    def test_viable_3yr_investment(self):
        result = self.model.evaluate(**self._base_kwargs())
        assert result.is_viable is True

    def test_low_profit_growth_fails(self):
        result = self.model.evaluate(**self._base_kwargs(annual_profit_growth_rate=0.10))
        assert any("30%" in w for w in result.warnings)

    def test_no_pe_expansion_fails(self):
        # entry PE == exit PE → no expansion
        result = self.model.evaluate(**self._base_kwargs(target_exit_pe=15.0, entry_pe=15.0))
        assert any("1倍扩张" in w for w in result.warnings)

    def test_4year_4x_target(self):
        result = self.model.evaluate(**self._base_kwargs(holding_years=4))
        assert "4年4倍" in result.stage

    def test_irr_check(self):
        result = self.model.evaluate(**self._base_kwargs())
        assert "implied_irr_pct" in result.details
        assert result.details["implied_irr_pct"] > 15

    def test_3year_label(self):
        result = self.model.evaluate(**self._base_kwargs(holding_years=3))
        assert "3年3倍" in result.stage


# ---------------------------------------------------------------------------
# BSEModel
# ---------------------------------------------------------------------------

class TestBSEModel:
    def setup_method(self):
        self.model = BSEModel()

    def _base_kwargs(self, **overrides):
        kwargs = dict(
            entry_pe=8.0,
            current_profit_rmb=0.3,
            annual_profit_growth_rate=0.25,
            expected_listing_pe=18.0,
            investment_amount_rmb=0.5,
            holding_years=3,
        )
        kwargs.update(overrides)
        return kwargs

    def test_viable_bse_investment(self):
        result = self.model.evaluate(**self._base_kwargs())
        assert result.is_viable is True

    def test_entry_pe_too_high(self):
        result = self.model.evaluate(**self._base_kwargs(entry_pe=12.0))
        assert any("安全垫上限" in w for w in result.warnings)

    def test_50pct_safety_margin(self):
        result = self.model.evaluate(**self._base_kwargs())
        # entry_pe=8, listing_pe=18 → safety = (18-8)/18 = 55.6% ≥ 50%
        assert result.details["safety_margin_pct"] >= 50.0

    def test_low_growth_fails(self):
        result = self.model.evaluate(**self._base_kwargs(annual_profit_growth_rate=0.10))
        assert any("20%最低要求" in w for w in result.warnings)

    def test_stage_label(self):
        result = self.model.evaluate(**self._base_kwargs())
        assert "北交所" in result.stage
