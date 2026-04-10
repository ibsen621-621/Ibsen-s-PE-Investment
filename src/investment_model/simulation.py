"""
蒙特卡洛模拟引擎 & 投资组合幂律模型
Monte Carlo Simulation Engine & Portfolio Power-Law Model

Replaces static single-point inputs with probability distributions so that
every model can produce a *distribution* of outcomes rather than one number.

Distribution choices (justified):
- Future market cap / exit valuation  →  LogNormal  (multiplicative growth,
  always positive, fat right tail matching venture outcomes)
- Annual profit growth rate            →  Normal     (bounded by business economics)
- Exit event occurrence per year       →  Poisson    (rare discrete events)
- Holding period                       →  LogNormal  (skewed — deals often take longer)

The PortfolioSimulator adds the fund-level power-law view: given survival rates
and return-multiple distributions across N investments, it checks whether the
portfolio as a whole can hit the fund's 50-50-1 / 100-10-10 macro targets.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# Helpers — seed-safe deterministic PRNG wrappers
# ---------------------------------------------------------------------------

def _lognormal(mean: float, std: float, rng: random.Random) -> float:
    """Sample from a log-normal distribution with the given arithmetic mean and std."""
    if std <= 0:
        return mean
    # Convert arithmetic mean/std to log-space parameters
    variance = std ** 2
    mu = math.log(mean ** 2 / math.sqrt(variance + mean ** 2))
    sigma = math.sqrt(math.log(1 + variance / mean ** 2))
    z = rng.gauss(0, 1)
    return math.exp(mu + sigma * z)


def _normal_clipped(mean: float, std: float, lo: float, hi: float, rng: random.Random) -> float:
    """Sample from a Normal distribution clipped to [lo, hi]."""
    if std <= 0:
        return mean
    val = rng.gauss(mean, std)
    return max(lo, min(hi, val))


def _poisson(lam: float, rng: random.Random) -> int:
    """Simple Knuth Poisson sampler."""
    if lam <= 0:
        return 0
    L = math.exp(-lam)
    k, p = 0, 1.0
    while True:
        k += 1
        p *= rng.random()
        if p <= L:
            return k - 1


# ---------------------------------------------------------------------------
# Distribution parameter containers
# ---------------------------------------------------------------------------

@dataclass
class LognormalParam:
    """Arithmetic mean and std for a log-normal variable (e.g. market cap 亿元)."""
    mean: float
    std: float

    def sample(self, rng: random.Random) -> float:
        return _lognormal(self.mean, self.std, rng)


@dataclass
class NormalParam:
    """Mean and std for a normally distributed variable (e.g. profit growth rate)."""
    mean: float
    std: float
    lo: float = -1.0
    hi: float = 10.0

    def sample(self, rng: random.Random) -> float:
        return _normal_clipped(self.mean, self.std, self.lo, self.hi, rng)


@dataclass
class PoissonParam:
    """Rate parameter for a Poisson variable (e.g. exit events per year)."""
    lam: float  # expected number of events per period

    def sample(self, rng: random.Random) -> int:
        return _poisson(self.lam, rng)


# ---------------------------------------------------------------------------
# Monte Carlo result
# ---------------------------------------------------------------------------

@dataclass
class MonteCarloResult:
    """Summary statistics from N simulations."""
    n_simulations: int
    p10: float          # 10th percentile (downside scenario)
    p25: float
    p50: float          # median
    p75: float
    p90: float          # 90th percentile (upside scenario)
    mean: float
    std: float
    prob_above_hurdle: float    # fraction of runs that beat the hurdle
    hurdle_value: float
    raw_samples: list[float] = field(default_factory=list, repr=False)

    @property
    def summary(self) -> str:
        return (
            f"Monte Carlo ({self.n_simulations:,} runs) | "
            f"P10={self.p10:.2f} | P50={self.p50:.2f} | P90={self.p90:.2f} | "
            f"均值={self.mean:.2f} | σ={self.std:.2f} | "
            f"超越基准概率={self.prob_above_hurdle * 100:.1f}%"
        )

    @classmethod
    def from_samples(
        cls,
        samples: list[float],
        hurdle: float,
        store_raw: bool = False,
    ) -> "MonteCarloResult":
        n = len(samples)
        sorted_s = sorted(samples)

        def pct(p: float) -> float:
            idx = max(0, min(n - 1, int(p * n)))
            return sorted_s[idx]

        mean = sum(samples) / n
        variance = sum((x - mean) ** 2 for x in samples) / n
        std = math.sqrt(variance)
        prob = sum(1 for s in samples if s >= hurdle) / n

        return cls(
            n_simulations=n,
            p10=round(pct(0.10), 4),
            p25=round(pct(0.25), 4),
            p50=round(pct(0.50), 4),
            p75=round(pct(0.75), 4),
            p90=round(pct(0.90), 4),
            mean=round(mean, 4),
            std=round(std, 4),
            prob_above_hurdle=round(prob, 4),
            hurdle_value=hurdle,
            raw_samples=samples if store_raw else [],
        )


# ---------------------------------------------------------------------------
# Monte Carlo Engine — wraps any stage model computation
# ---------------------------------------------------------------------------

class MonteCarloEngine:
    """
    蒙特卡洛模拟引擎

    Converts static stage-model inputs into probability distributions and
    runs N simulations to produce return-multiple and IRR distributions.

    Example usage (VC model with probabilistic market cap):

        engine = MonteCarloEngine(n_simulations=10_000, seed=42)
        result = engine.simulate_vc_return(
            entry_valuation_rmb=6.0,
            investment_amount_rmb=1.0,
            market_cap_dist=LognormalParam(mean=120.0, std=60.0),
            dilution_rate_dist=NormalParam(mean=0.40, std=0.05, lo=0.10, hi=0.80),
            hurdle_multiple=10.0,
        )
        print(result.summary)
    """

    def __init__(self, n_simulations: int = 10_000, seed: Optional[int] = None):
        self.n_simulations = n_simulations
        self._rng = random.Random(seed)

    # ------------------------------------------------------------------
    # Angel model simulation
    # ------------------------------------------------------------------

    def simulate_angel_return(
        self,
        *,
        entry_valuation_rmb: float,
        investment_amount_rmb: float,
        market_cap_dist: LognormalParam,
        dilution_rate_dist: NormalParam,
        hurdle_multiple: float = 50.0,
        store_raw: bool = False,
    ) -> MonteCarloResult:
        """
        Monte Carlo simulation for angel-stage return multiple.

        Parameters
        ----------
        entry_valuation_rmb:   Fixed pre-money valuation (亿元)
        investment_amount_rmb: Fixed investment amount (亿元)
        market_cap_dist:       Lognormal distribution for exit market cap (亿元)
        dilution_rate_dist:    Normal distribution for cumulative dilution ratio
        hurdle_multiple:       Return multiple hurdle (default 50x for angel)
        store_raw:             Whether to store all simulation values
        """
        samples: list[float] = []
        entry_stake = investment_amount_rmb / (entry_valuation_rmb + investment_amount_rmb)

        for _ in range(self.n_simulations):
            market_cap = market_cap_dist.sample(self._rng)
            dilution = dilution_rate_dist.sample(self._rng)
            diluted_stake = entry_stake * (1 - dilution)
            gross_return = diluted_stake * market_cap
            multiple = gross_return / investment_amount_rmb if investment_amount_rmb > 0 else 0
            samples.append(multiple)

        return MonteCarloResult.from_samples(samples, hurdle_multiple, store_raw)

    # ------------------------------------------------------------------
    # VC model simulation
    # ------------------------------------------------------------------

    def simulate_vc_return(
        self,
        *,
        entry_valuation_rmb: float,
        investment_amount_rmb: float,
        market_cap_dist: LognormalParam,
        dilution_rate_dist: NormalParam,
        hurdle_multiple: float = 10.0,
        store_raw: bool = False,
    ) -> MonteCarloResult:
        """Monte Carlo simulation for VC-stage return multiple."""
        samples: list[float] = []
        post_money = entry_valuation_rmb + investment_amount_rmb

        for _ in range(self.n_simulations):
            market_cap = market_cap_dist.sample(self._rng)
            dilution = dilution_rate_dist.sample(self._rng)
            stake = (investment_amount_rmb / post_money) * (1 - dilution)
            multiple = stake * market_cap / investment_amount_rmb
            samples.append(multiple)

        return MonteCarloResult.from_samples(samples, hurdle_multiple, store_raw)

    # ------------------------------------------------------------------
    # PE model simulation
    # ------------------------------------------------------------------

    def simulate_pe_return(
        self,
        *,
        entry_pe: float,
        current_profit_rmb: float,
        investment_amount_rmb: float,
        profit_growth_dist: NormalParam,
        exit_pe_dist: NormalParam,
        holding_years: int = 3,
        hurdle_multiple: float = 3.0,
        store_raw: bool = False,
    ) -> MonteCarloResult:
        """
        Monte Carlo simulation for PE-stage return multiple.

        Parameters
        ----------
        entry_pe:              Fixed PE at investment time
        current_profit_rmb:    Current annual net profit (亿元)
        investment_amount_rmb: Fixed investment amount (亿元)
        profit_growth_dist:    Normal distribution for annual profit CAGR
        exit_pe_dist:          Normal distribution for exit/IPO PE multiple
        holding_years:         Fixed holding period (years)
        hurdle_multiple:       Return multiple hurdle
        store_raw:             Whether to store all simulation values
        """
        samples: list[float] = []
        entry_market_cap = current_profit_rmb * entry_pe
        stake = investment_amount_rmb / entry_market_cap if entry_market_cap > 0 else 0

        for _ in range(self.n_simulations):
            growth = profit_growth_dist.sample(self._rng)
            pe_exit = exit_pe_dist.sample(self._rng)
            exit_profit = current_profit_rmb * ((1 + growth) ** holding_years)
            exit_market_cap = exit_profit * pe_exit
            multiple = stake * exit_market_cap / investment_amount_rmb
            samples.append(multiple)

        return MonteCarloResult.from_samples(samples, hurdle_multiple, store_raw)

    # ------------------------------------------------------------------
    # Exit event simulation (Poisson arrival of exit opportunities)
    # ------------------------------------------------------------------

    def simulate_exit_events(
        self,
        *,
        exit_rate_per_year: PoissonParam,
        fund_life_years: int = 7,
        n_portfolio_companies: int = 20,
        store_raw: bool = False,
    ) -> MonteCarloResult:
        """
        Simulate the number of successful exits from a portfolio using Poisson arrivals.

        Each company generates exit opportunities at the given Poisson rate per year.
        The total exits over fund life is the sum across all companies and years.

        Parameters
        ----------
        exit_rate_per_year:        Poisson rate of exit events per company per year
        fund_life_years:           Total fund life
        n_portfolio_companies:     Number of portfolio companies
        store_raw:                 Whether to store all simulation values
        """
        samples: list[float] = []

        for _ in range(self.n_simulations):
            total_exits = 0
            for _ in range(n_portfolio_companies):
                exits_this_company = sum(
                    min(exit_rate_per_year.sample(self._rng), 1)
                    for _ in range(fund_life_years)
                )
                total_exits += min(exits_this_company, 1)  # each company exits at most once
            samples.append(float(total_exits))

        # hurdle: target exit count
        hurdle = n_portfolio_companies * 0.25  # 25% exit rate (PE benchmark)
        return MonteCarloResult.from_samples(samples, hurdle, store_raw)


# ---------------------------------------------------------------------------
# Portfolio Power-Law Model
# ---------------------------------------------------------------------------

@dataclass
class PortfolioSimResult:
    """Fund-level portfolio simulation result."""
    n_investments: int
    fund_size_rmb: float
    avg_investment_rmb: float
    # Distribution of fund-level return multiples across MC runs
    fund_multiple_dist: MonteCarloResult
    # Probability that the portfolio meets the stage-specific macro target
    prob_meets_macro_target: float
    macro_target_label: str
    # Expected number of "winners" (investments returning ≥ threshold)
    expected_winners: float
    winner_threshold_multiple: float
    summary: str
    power_law_concentration: float  # fraction of total return from top 20% positions


class PortfolioSimulator:
    """
    投资组合幂律模型

    A primary-market portfolio strictly follows the power-law distribution:
    a tiny minority of investments generate the overwhelming majority of returns.
    This class back-calculates whether the current single-investment sizing and
    return expectations are consistent with the fund's macro target (50-50-1 or
    100-10-10) once power-law distribution is applied across the whole portfolio.

    Usage:
        sim = PortfolioSimulator(n_simulations=5_000, seed=42)
        result = sim.simulate_vc_portfolio(
            fund_size_rmb=20.0,
            n_investments=20,
            survival_rate=0.40,
            winner_multiple_dist=LognormalParam(mean=15.0, std=20.0),
            loser_multiple_dist=LognormalParam(mean=0.3, std=0.2),
            winner_threshold_multiple=10.0,
        )
        print(result.summary)
    """

    def __init__(self, n_simulations: int = 5_000, seed: Optional[int] = None):
        self.n_simulations = n_simulations
        self._rng = random.Random(seed)

    def simulate_vc_portfolio(
        self,
        *,
        fund_size_rmb: float,
        n_investments: int,
        survival_rate: float,          # probability that a company returns > 1x
        winner_multiple_dist: LognormalParam,   # multiples for winners
        loser_multiple_dist: LognormalParam,    # multiples for losers (often < 1)
        winner_threshold_multiple: float = 10.0,
        macro_target_label: str = "100-10-10",
        macro_target_fund_multiple: float = 3.0,   # fund-level TVPI target
        store_raw: bool = False,
    ) -> PortfolioSimResult:
        """
        Simulate a VC portfolio under power-law return distribution.

        Parameters
        ----------
        fund_size_rmb:             Total fund size (亿元)
        n_investments:             Number of portfolio companies
        survival_rate:             Probability a given company returns > cost
        winner_multiple_dist:      Lognormal distribution for winning investments
        loser_multiple_dist:       Lognormal distribution for losing investments
        winner_threshold_multiple: Multiple that makes an investment a "winner"
        macro_target_label:        Label for the macro target (e.g. "100-10-10")
        macro_target_fund_multiple: Required fund-level TVPI to declare macro success
        store_raw:                 Store raw fund-multiple samples
        """
        avg_investment_rmb = fund_size_rmb / n_investments
        fund_multiples: list[float] = []
        total_winner_fraction: list[float] = []

        for _ in range(self.n_simulations):
            returns: list[float] = []
            for _ in range(n_investments):
                is_winner = self._rng.random() < survival_rate
                multiple = (
                    winner_multiple_dist.sample(self._rng)
                    if is_winner
                    else loser_multiple_dist.sample(self._rng)
                )
                multiple = max(0.0, multiple)
                returns.append(multiple)

            gross_return_rmb = sum(r * avg_investment_rmb for r in returns)
            fund_multiple = gross_return_rmb / fund_size_rmb
            fund_multiples.append(fund_multiple)

            # Power-law concentration: top 20% of positions by return
            sorted_returns = sorted(returns, reverse=True)
            top20_count = max(1, int(n_investments * 0.20))
            top20_return = sum(r * avg_investment_rmb for r in sorted_returns[:top20_count])
            total_return = sum(r * avg_investment_rmb for r in returns)
            top20_fraction = top20_return / total_return if total_return > 0 else 0
            total_winner_fraction.append(top20_fraction)

        dist = MonteCarloResult.from_samples(
            fund_multiples, macro_target_fund_multiple, store_raw
        )

        expected_winners = (
            sum(
                1 for _ in range(self.n_simulations)
                for _ in range(n_investments)
                if self._rng.random() < survival_rate
            ) / self.n_simulations
        )

        avg_concentration = sum(total_winner_fraction) / len(total_winner_fraction)

        summary = (
            f"组合模拟 ({n_investments}个项目, 基金规模{fund_size_rmb:.0f}亿) | "
            f"基金TVPI: P50={dist.p50:.2f}x | P90={dist.p90:.2f}x | "
            f"达到{macro_target_label}概率={dist.prob_above_hurdle * 100:.1f}% | "
            f"前20%项目贡献回报={avg_concentration * 100:.0f}%（幂律集中度）"
        )

        return PortfolioSimResult(
            n_investments=n_investments,
            fund_size_rmb=fund_size_rmb,
            avg_investment_rmb=avg_investment_rmb,
            fund_multiple_dist=dist,
            prob_meets_macro_target=dist.prob_above_hurdle,
            macro_target_label=macro_target_label,
            expected_winners=round(expected_winners, 1),
            winner_threshold_multiple=winner_threshold_multiple,
            summary=summary,
            power_law_concentration=round(avg_concentration, 4),
        )
