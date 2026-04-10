"""
Tests for Monte Carlo simulation engine and Portfolio power-law model.
"""

import math
import pytest

from src.investment_model.simulation import (
    LognormalParam,
    NormalParam,
    PoissonParam,
    MonteCarloEngine,
    MonteCarloResult,
    PortfolioSimulator,
)


# ---------------------------------------------------------------------------
# Distribution parameter helpers
# ---------------------------------------------------------------------------

class TestLognormalParam:
    def test_deterministic_when_zero_std(self):
        p = LognormalParam(mean=100.0, std=0.0)
        rng = __import__("random").Random(42)
        assert p.sample(rng) == 100.0

    def test_positive_samples(self):
        p = LognormalParam(mean=50.0, std=20.0)
        rng = __import__("random").Random(7)
        for _ in range(100):
            assert p.sample(rng) > 0


class TestNormalParam:
    def test_clipping_to_bounds(self):
        p = NormalParam(mean=5.0, std=100.0, lo=0.0, hi=1.0)
        rng = __import__("random").Random(1)
        for _ in range(200):
            val = p.sample(rng)
            assert 0.0 <= val <= 1.0

    def test_deterministic_zero_std(self):
        p = NormalParam(mean=0.30, std=0.0)
        rng = __import__("random").Random(1)
        assert p.sample(rng) == 0.30


class TestPoissonParam:
    def test_non_negative_output(self):
        p = PoissonParam(lam=2.0)
        rng = __import__("random").Random(99)
        for _ in range(200):
            assert p.sample(rng) >= 0

    def test_zero_rate(self):
        p = PoissonParam(lam=0)
        rng = __import__("random").Random(1)
        assert p.sample(rng) == 0


# ---------------------------------------------------------------------------
# MonteCarloResult
# ---------------------------------------------------------------------------

class TestMonteCarloResult:
    def test_percentiles_ordered(self):
        samples = list(range(1, 101))  # 1..100
        result = MonteCarloResult.from_samples(samples, hurdle=50.0)
        assert result.p10 <= result.p25 <= result.p50 <= result.p75 <= result.p90

    def test_prob_above_hurdle(self):
        # All samples are 100 → prob above 50 should be 1.0
        result = MonteCarloResult.from_samples([100.0] * 1000, hurdle=50.0)
        assert result.prob_above_hurdle == 1.0

    def test_prob_below_hurdle(self):
        # All samples are 10 → prob above 50 should be 0.0
        result = MonteCarloResult.from_samples([10.0] * 1000, hurdle=50.0)
        assert result.prob_above_hurdle == 0.0

    def test_summary_string(self):
        result = MonteCarloResult.from_samples([1.0, 2.0, 3.0], hurdle=2.0)
        assert "P50" in result.summary
        assert "%" in result.summary

    def test_store_raw(self):
        result = MonteCarloResult.from_samples([1.0, 2.0], hurdle=1.5, store_raw=True)
        assert len(result.raw_samples) == 2

    def test_no_raw_by_default(self):
        result = MonteCarloResult.from_samples([1.0, 2.0], hurdle=1.5)
        assert result.raw_samples == []


# ---------------------------------------------------------------------------
# MonteCarloEngine — Angel simulation
# ---------------------------------------------------------------------------

class TestMonteCarloEngineAngel:
    def setup_method(self):
        self.engine = MonteCarloEngine(n_simulations=2000, seed=42)

    def test_angel_p50_positive(self):
        result = self.engine.simulate_angel_return(
            entry_valuation_rmb=0.4,
            investment_amount_rmb=0.1,
            market_cap_dist=LognormalParam(mean=60.0, std=30.0),
            dilution_rate_dist=NormalParam(mean=0.60, std=0.10, lo=0.10, hi=0.90),
            hurdle_multiple=50.0,
        )
        assert result.p50 > 0

    def test_angel_hurdle_probability_range(self):
        result = self.engine.simulate_angel_return(
            entry_valuation_rmb=0.4,
            investment_amount_rmb=0.1,
            market_cap_dist=LognormalParam(mean=60.0, std=30.0),
            dilution_rate_dist=NormalParam(mean=0.60, std=0.10, lo=0.10, hi=0.90),
            hurdle_multiple=50.0,
        )
        assert 0.0 <= result.prob_above_hurdle <= 1.0

    def test_higher_mean_cap_raises_p50(self):
        low = self.engine.simulate_angel_return(
            entry_valuation_rmb=0.5,
            investment_amount_rmb=0.1,
            market_cap_dist=LognormalParam(mean=20.0, std=5.0),
            dilution_rate_dist=NormalParam(mean=0.5, std=0.05, lo=0.0, hi=0.9),
            hurdle_multiple=10.0,
        )
        engine2 = MonteCarloEngine(n_simulations=2000, seed=42)
        high = engine2.simulate_angel_return(
            entry_valuation_rmb=0.5,
            investment_amount_rmb=0.1,
            market_cap_dist=LognormalParam(mean=200.0, std=50.0),
            dilution_rate_dist=NormalParam(mean=0.5, std=0.05, lo=0.0, hi=0.9),
            hurdle_multiple=10.0,
        )
        assert high.p50 > low.p50


# ---------------------------------------------------------------------------
# MonteCarloEngine — VC simulation
# ---------------------------------------------------------------------------

class TestMonteCarloEngineVC:
    def setup_method(self):
        self.engine = MonteCarloEngine(n_simulations=2000, seed=7)

    def test_vc_result_has_correct_n(self):
        result = self.engine.simulate_vc_return(
            entry_valuation_rmb=6.0,
            investment_amount_rmb=1.0,
            market_cap_dist=LognormalParam(mean=120.0, std=60.0),
            dilution_rate_dist=NormalParam(mean=0.40, std=0.05, lo=0.10, hi=0.80),
            hurdle_multiple=10.0,
        )
        assert result.n_simulations == 2000

    def test_vc_p90_greater_than_p10(self):
        result = self.engine.simulate_vc_return(
            entry_valuation_rmb=6.0,
            investment_amount_rmb=1.0,
            market_cap_dist=LognormalParam(mean=120.0, std=60.0),
            dilution_rate_dist=NormalParam(mean=0.40, std=0.05, lo=0.10, hi=0.80),
            hurdle_multiple=10.0,
        )
        assert result.p90 > result.p10


# ---------------------------------------------------------------------------
# MonteCarloEngine — PE simulation
# ---------------------------------------------------------------------------

class TestMonteCarloEnginePE:
    def setup_method(self):
        self.engine = MonteCarloEngine(n_simulations=2000, seed=13)

    def test_pe_result_positive_p50(self):
        result = self.engine.simulate_pe_return(
            entry_pe=15.0,
            current_profit_rmb=2.0,
            investment_amount_rmb=5.0,
            profit_growth_dist=NormalParam(mean=0.35, std=0.05, lo=0.0, hi=1.0),
            exit_pe_dist=NormalParam(mean=25.0, std=5.0, lo=10.0, hi=60.0),
            holding_years=3,
            hurdle_multiple=3.0,
        )
        assert result.p50 > 0

    def test_pe_hurdle_prob_reasonable(self):
        result = self.engine.simulate_pe_return(
            entry_pe=15.0,
            current_profit_rmb=2.0,
            investment_amount_rmb=5.0,
            profit_growth_dist=NormalParam(mean=0.35, std=0.05, lo=0.0, hi=1.0),
            exit_pe_dist=NormalParam(mean=25.0, std=5.0, lo=10.0, hi=60.0),
            holding_years=3,
            hurdle_multiple=3.0,
        )
        # With good fundamentals, most sims should beat 3x
        assert result.prob_above_hurdle > 0.5


# ---------------------------------------------------------------------------
# MonteCarloEngine — Exit event (Poisson)
# ---------------------------------------------------------------------------

class TestMonteCarloExitEvents:
    def test_exit_events_within_range(self):
        engine = MonteCarloEngine(n_simulations=1000, seed=99)
        result = engine.simulate_exit_events(
            exit_rate_per_year=PoissonParam(lam=0.2),
            fund_life_years=7,
            n_portfolio_companies=20,
        )
        # Exits must be between 0 and 20
        assert 0 <= result.p10 <= 20
        assert 0 <= result.p90 <= 20


# ---------------------------------------------------------------------------
# PortfolioSimulator
# ---------------------------------------------------------------------------

class TestPortfolioSimulator:
    def setup_method(self):
        self.sim = PortfolioSimulator(n_simulations=1000, seed=42)

    def test_fund_multiple_positive(self):
        result = self.sim.simulate_vc_portfolio(
            fund_size_rmb=20.0,
            n_investments=20,
            survival_rate=0.40,
            winner_multiple_dist=LognormalParam(mean=15.0, std=20.0),
            loser_multiple_dist=LognormalParam(mean=0.3, std=0.2),
            winner_threshold_multiple=10.0,
        )
        assert result.fund_multiple_dist.p50 > 0

    def test_higher_survival_rate_improves_p50(self):
        low = self.sim.simulate_vc_portfolio(
            fund_size_rmb=20.0,
            n_investments=20,
            survival_rate=0.10,
            winner_multiple_dist=LognormalParam(mean=10.0, std=5.0),
            loser_multiple_dist=LognormalParam(mean=0.1, std=0.05),
        )
        sim2 = PortfolioSimulator(n_simulations=1000, seed=42)
        high = sim2.simulate_vc_portfolio(
            fund_size_rmb=20.0,
            n_investments=20,
            survival_rate=0.70,
            winner_multiple_dist=LognormalParam(mean=10.0, std=5.0),
            loser_multiple_dist=LognormalParam(mean=0.1, std=0.05),
        )
        assert high.fund_multiple_dist.p50 > low.fund_multiple_dist.p50

    def test_power_law_concentration(self):
        result = self.sim.simulate_vc_portfolio(
            fund_size_rmb=10.0,
            n_investments=20,
            survival_rate=0.30,
            winner_multiple_dist=LognormalParam(mean=50.0, std=80.0),
            loser_multiple_dist=LognormalParam(mean=0.2, std=0.1),
        )
        # Top 20% of positions should contribute a large fraction of return
        assert result.power_law_concentration > 0.30

    def test_summary_contains_key_info(self):
        result = self.sim.simulate_vc_portfolio(
            fund_size_rmb=20.0,
            n_investments=15,
            survival_rate=0.40,
            winner_multiple_dist=LognormalParam(mean=12.0, std=10.0),
            loser_multiple_dist=LognormalParam(mean=0.3, std=0.2),
        )
        assert "15个项目" in result.summary
        assert "幂律" in result.summary
