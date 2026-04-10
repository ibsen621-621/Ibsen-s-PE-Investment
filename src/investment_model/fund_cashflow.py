"""
基金J曲线与现金流时间序列模型
Fund J-Curve & Cash Flow Time-Series Model

Upgrades IRR from a static snapshot to a full fund-lifecycle cash flow model:

- Capital calls: staggered over investment period (years 1-4 typically)
- Management fees: charged on committed capital during investment period,
  then on invested/NAV during harvest period
- Portfolio distributions: governed by exit path and waterfall mechanics
- DPI evolution: tracks cumulative distribution / paid-in over every year
- J-curve visualization data: the characteristic dip-then-recovery pattern

The model is parameterised per standard PE/VC fund conventions:
- 2% annual management fee on committed capital (investment period)
- 1.5% annual management fee on NAV / invested capital (harvest period)
- 20% carried interest over 8% preferred return hurdle (LP first)
- GP catch-up to 20% of total profits
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class AnnualCashFlow:
    year: int
    capital_call_rmb: float          # LP capital drawn down this year
    management_fee_rmb: float        # Management fee paid this year
    net_invested_rmb: float          # capital_call - management_fee
    distribution_rmb: float          # Cash returned to LPs this year
    nav_rmb: float                   # Estimated portfolio NAV at year-end
    cumulative_invested_rmb: float   # Total capital called to date
    cumulative_distributed_rmb: float
    dpi: float                       # Cumulative DPI at year-end
    tvpi: float                      # DPI + RVPI (NAV / cumulative invested)
    rvpi: float
    net_cash_flow_to_lp: float       # distribution - capital_call - management_fee


@dataclass
class FundCashflowResult:
    fund_name: str
    fund_size_rmb: float
    management_fee_rate_invest_pct: float
    management_fee_rate_harvest_pct: float
    carried_interest_pct: float
    preferred_return_pct: float
    annual_flows: list[AnnualCashFlow]
    final_irr_pct: Optional[float]
    final_dpi: float
    final_tvpi: float
    lp_net_return_rmb: float         # After carry and fees
    gp_carry_rmb: float
    summary: str
    j_curve_trough_year: Optional[int]      # Year with most negative cumulative cash flow
    j_curve_breakeven_year: Optional[int]   # Year DPI first crosses 1.0x


# ---------------------------------------------------------------------------
# J-curve model
# ---------------------------------------------------------------------------

class FundCashflowModel:
    """
    基金J曲线与资金时间价值模型

    Models the full lifecycle cash flows of a PE/VC fund including:
    - Capital calls: drawn down over the investment period following a
      user-specified annual call schedule (sums to fund_size)
    - Management fees: 2% on committed capital during investment period,
      1.5% on remaining NAV during harvest period
    - Portfolio distributions: modelled as a lump-sum exit in each year,
      scaled by the exit_schedule (list of fractions of NAV to distribute)
    - Carried interest: 20% of profits above 8% preferred return
    - DPI/TVPI path: computed annually so the J-curve shape is visible
    - IRR: computed from LP net cash flows (calls out, distributions in)

    All amounts in 亿元 RMB.
    """

    DEFAULT_MGMT_FEE_INVEST_PCT = 2.0    # % on committed during investment period
    DEFAULT_MGMT_FEE_HARVEST_PCT = 1.5   # % on NAV during harvest period
    DEFAULT_CARRY_PCT = 20.0             # % carried interest
    DEFAULT_PREFERRED_RETURN_PCT = 8.0   # % hurdle rate for LP preferred return

    def model(
        self,
        *,
        fund_name: str = "未命名基金",
        fund_size_rmb: float,
        # Capital call schedule: list of fractions per year (must sum to ≈ 1.0)
        # e.g. [0.30, 0.30, 0.25, 0.15] for a 4-year investment period
        capital_call_schedule: list[float],
        # Exit / distribution schedule: fraction of remaining NAV distributed per year
        # Indexed from year 0; zeroes during investment period are common
        # e.g. [0, 0, 0, 0, 0.20, 0.30, 0.40, 0.10] for 8-year fund
        exit_schedule: list[float],
        # NAV growth rate per year (before distributions) — rough proxy for portfolio growth
        nav_growth_rate: float = 0.20,
        management_fee_rate_invest_pct: float = DEFAULT_MGMT_FEE_INVEST_PCT,
        management_fee_rate_harvest_pct: float = DEFAULT_MGMT_FEE_HARVEST_PCT,
        carried_interest_pct: float = DEFAULT_CARRY_PCT,
        preferred_return_pct: float = DEFAULT_PREFERRED_RETURN_PCT,
    ) -> FundCashflowResult:
        """
        Model fund cash flows and compute the J-curve.

        Parameters
        ----------
        fund_size_rmb:                 Total committed capital (亿元)
        capital_call_schedule:         Fraction of fund called each year (list, sums to 1)
        exit_schedule:                 Fraction of NAV distributed each year (list)
        nav_growth_rate:               Annual NAV growth rate before distributions
        management_fee_rate_invest_pct: Management fee % during investment period
        management_fee_rate_harvest_pct: Management fee % during harvest period
        carried_interest_pct:          Carried interest % (e.g. 20)
        preferred_return_pct:          Preferred return hurdle % (e.g. 8)
        """
        n_years = max(len(capital_call_schedule), len(exit_schedule))
        invest_years = len(capital_call_schedule)

        annual_flows: list[AnnualCashFlow] = []
        nav = 0.0
        cumulative_invested = 0.0
        cumulative_distributed = 0.0
        lp_net_cfs: list[float] = []  # LP perspective: calls are negative, distributions positive

        for yr in range(n_years):
            # Capital call
            call_fraction = capital_call_schedule[yr] if yr < len(capital_call_schedule) else 0.0
            call_rmb = fund_size_rmb * call_fraction

            # Management fee
            in_investment_period = yr < invest_years
            if in_investment_period:
                mgmt_fee = fund_size_rmb * management_fee_rate_invest_pct / 100
            else:
                mgmt_fee = nav * management_fee_rate_harvest_pct / 100

            net_invested = max(0.0, call_rmb - mgmt_fee)

            # Grow NAV before distribution
            nav = (nav + net_invested) * (1 + nav_growth_rate)

            # Distribution
            exit_fraction = exit_schedule[yr] if yr < len(exit_schedule) else 0.0
            distribution = nav * exit_fraction
            nav = max(0.0, nav - distribution)

            cumulative_invested += call_rmb + mgmt_fee
            cumulative_distributed += distribution

            dpi = cumulative_distributed / cumulative_invested if cumulative_invested > 0 else 0.0
            rvpi = nav / cumulative_invested if cumulative_invested > 0 else 0.0
            tvpi = dpi + rvpi

            net_cf = distribution - call_rmb - mgmt_fee
            lp_net_cfs.append(net_cf)

            annual_flows.append(AnnualCashFlow(
                year=yr + 1,
                capital_call_rmb=round(call_rmb, 4),
                management_fee_rmb=round(mgmt_fee, 4),
                net_invested_rmb=round(net_invested, 4),
                distribution_rmb=round(distribution, 4),
                nav_rmb=round(nav, 4),
                cumulative_invested_rmb=round(cumulative_invested, 4),
                cumulative_distributed_rmb=round(cumulative_distributed, 4),
                dpi=round(dpi, 4),
                tvpi=round(tvpi, 4),
                rvpi=round(rvpi, 4),
                net_cash_flow_to_lp=round(net_cf, 4),
            ))

        # Waterfall: LP preferred return + carry
        total_invested = cumulative_invested
        total_gross_return = cumulative_distributed + nav  # remaining NAV as terminal value

        # LP preferred return (compound)
        pref_rate = preferred_return_pct / 100
        # Simple hurdle: LP needs back cost × (1 + pref)^years
        lp_preferred = total_invested * ((1 + pref_rate) ** n_years)
        carry_base = max(0.0, total_gross_return - lp_preferred)
        gp_carry = carry_base * carried_interest_pct / 100
        lp_net_return = total_gross_return - gp_carry

        # IRR from LP cash flows
        final_irr = self._compute_irr(lp_net_cfs, max_iter=1000, tol=1e-7)

        # J-curve metrics
        cumulative_cf = 0.0
        trough_cf = 0.0
        trough_year = None
        breakeven_year = None
        for flow in annual_flows:
            cumulative_cf += flow.net_cash_flow_to_lp
            if cumulative_cf < trough_cf:
                trough_cf = cumulative_cf
                trough_year = flow.year
            if breakeven_year is None and flow.dpi >= 1.0:
                breakeven_year = flow.year

        final_dpi = annual_flows[-1].dpi if annual_flows else 0.0
        final_tvpi = annual_flows[-1].tvpi if annual_flows else 0.0

        irr_str = f"{final_irr * 100:.2f}%" if final_irr is not None else "N/A"
        summary = (
            f"基金: {fund_name} | 规模: {fund_size_rmb:.0f}亿 | "
            f"最终IRR: {irr_str} | DPI: {final_dpi:.2f}x | TVPI: {final_tvpi:.2f}x\n"
            f"J曲线谷底: 第{trough_year}年 | DPI回本年份: 第{breakeven_year if breakeven_year else 'N/A'}年 | "
            f"GP Carry: {gp_carry:.2f}亿 | LP净回报: {lp_net_return:.2f}亿"
        )

        return FundCashflowResult(
            fund_name=fund_name,
            fund_size_rmb=fund_size_rmb,
            management_fee_rate_invest_pct=management_fee_rate_invest_pct,
            management_fee_rate_harvest_pct=management_fee_rate_harvest_pct,
            carried_interest_pct=carried_interest_pct,
            preferred_return_pct=preferred_return_pct,
            annual_flows=annual_flows,
            final_irr_pct=round(final_irr * 100, 4) if final_irr is not None else None,
            final_dpi=round(final_dpi, 4),
            final_tvpi=round(final_tvpi, 4),
            lp_net_return_rmb=round(lp_net_return, 4),
            gp_carry_rmb=round(gp_carry, 4),
            summary=summary,
            j_curve_trough_year=trough_year,
            j_curve_breakeven_year=breakeven_year,
        )

    # ------------------------------------------------------------------
    # IRR helper (Newton-Raphson, same algorithm as metrics.py)
    # ------------------------------------------------------------------

    @staticmethod
    def _npv(rate: float, cfs: list[float]) -> float:
        return sum(cf / ((1 + rate) ** t) for t, cf in enumerate(cfs))

    @staticmethod
    def _npv_d(rate: float, cfs: list[float]) -> float:
        return sum(-t * cf / ((1 + rate) ** (t + 1)) for t, cf in enumerate(cfs))

    def _compute_irr(
        self,
        cfs: list[float],
        max_iter: int,
        tol: float,
    ) -> Optional[float]:
        rate = 0.1
        for _ in range(max_iter):
            npv = self._npv(rate, cfs)
            d = self._npv_d(rate, cfs)
            if abs(d) < 1e-12:
                break
            new_rate = rate - npv / d
            if abs(new_rate - rate) < tol:
                return new_rate
            rate = new_rate
        return None
