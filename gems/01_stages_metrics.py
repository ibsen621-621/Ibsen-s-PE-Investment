# ==== GEMS FILE: 01_stages_metrics.py ====
# Merged from: stages.py, metrics.py
# For Gemini Gems knowledge base — v4.0
# NOTE: This is a knowledge reference file, not executable production code.
#       Cross-module imports have been annotated for clarity.

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
import math


# ==== ORIGIN: stages.py ====
"""
投资阶段量化模型
Investment Stage Quantitative Models

Implements the three core stage models:
- Angel / 天使轮: 50-50-1 model
- VC / 成长期:   100-10-10 model
- PE / 中后期:   3-year-3x / 4-year-4x model
- BSE / 北交所:  Safety-margin valuation model
"""




# ---------------------------------------------------------------------------
# Shared result types
# ---------------------------------------------------------------------------

@dataclass
class StageResult:
    """Unified result object returned by every stage model."""
    stage: str
    is_viable: bool
    score: float                    # 0-100 composite score
    max_valuation_rmb: float        # Maximum acceptable pre-money valuation (RMB 亿元)
    expected_return_multiple: float # Expected investment multiple (x)
    summary: str
    details: dict = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Angel Model — 50-50-1
# ---------------------------------------------------------------------------

class AngelModel:
    """
    天使轮 50-50-1 模型

    Rules (source: [cite 38, 39, 43]):
    * Target company future market cap ≥ 50亿 RMB
    * Single investment must achieve ≥ 50x return
    * A single winning project must recoup the entire fund
    * Entry valuation should not exceed 5000万 (0.5亿) RMB to maintain 50x potential
    """

    REQUIRED_MARKET_CAP_RMB = 50.0      # 亿元
    REQUIRED_RETURN_MULTIPLE = 50.0     # 倍
    MAX_ENTRY_VALUATION_RMB = 0.5       # 亿元 (5000万)

    def evaluate(
        self,
        *,
        entry_valuation_rmb: float,         # 亿元
        fund_size_rmb: float,               # 亿元
        investment_amount_rmb: float,       # 亿元
        expected_market_cap_rmb: float,     # 亿元
        dilution_rate: float = 0.60,        # cumulative dilution across future rounds
        holding_years: int = 7,
    ) -> StageResult:
        """
        Evaluate an angel-stage investment opportunity.

        Parameters
        ----------
        entry_valuation_rmb:     Pre-money valuation at entry (亿元)
        fund_size_rmb:           Total fund size (亿元)
        investment_amount_rmb:   Amount to invest (亿元)
        expected_market_cap_rmb: Projected exit market cap (亿元)
        dilution_rate:           Cumulative dilution ratio across all future rounds (default 60%)
        holding_years:           Expected holding period in years
        """
        warnings: list[str] = []
        recommendations: list[str] = []
        checks_passed = 0
        total_checks = 4

        # 1. Market cap threshold
        cap_ok = expected_market_cap_rmb >= self.REQUIRED_MARKET_CAP_RMB
        if cap_ok:
            checks_passed += 1
        else:
            warnings.append(
                f"预期市值 {expected_market_cap_rmb:.1f}亿 低于50亿门槛，"
                "难以支撑50倍回报要求。"
            )

        # 2. Valuation ceiling
        valuation_ok = entry_valuation_rmb <= self.MAX_ENTRY_VALUATION_RMB
        if valuation_ok:
            checks_passed += 1
        else:
            warnings.append(
                f"进入估值 {entry_valuation_rmb:.2f}亿 超过5000万上限，"
                "经多轮稀释后难以实现50倍回报。"
            )
            recommendations.append("建议压低估值至5000万以内，或降低单笔投入。")

        # 3. Effective return multiple
        entry_stake = investment_amount_rmb / (entry_valuation_rmb + investment_amount_rmb)
        diluted_stake = entry_stake * (1 - dilution_rate)
        gross_return = diluted_stake * expected_market_cap_rmb
        return_multiple = gross_return / investment_amount_rmb if investment_amount_rmb > 0 else 0

        multiple_ok = return_multiple >= self.REQUIRED_RETURN_MULTIPLE
        if multiple_ok:
            checks_passed += 1
        else:
            warnings.append(
                f"测算回报倍数 {return_multiple:.1f}x 低于50倍要求。"
            )
            recommendations.append(
                "考虑增加持股比例、降低进入估值或聚焦更高潜在市值赛道。"
            )

        # 4. Fund-recovery potential (single project covers entire fund)
        net_return_rmb = gross_return - investment_amount_rmb
        fund_recovery_ok = net_return_rmb >= fund_size_rmb
        if fund_recovery_ok:
            checks_passed += 1
        else:
            warnings.append(
                f"单项目净回报 {net_return_rmb:.1f}亿 无法覆盖基金规模 {fund_size_rmb:.1f}亿。"
            )
            recommendations.append("天使策略要求单笔成功项目能回收整支基金，建议重估赛道天花板。")

        score = (checks_passed / total_checks) * 100
        is_viable = checks_passed >= 3  # need at least 3 of 4 checks

        if is_viable:
            summary = (
                f"✅ 天使投资可行性通过 ({checks_passed}/{total_checks} 项指标达标)。"
                f"预测回报 {return_multiple:.1f}x，"
                f"估值 {entry_valuation_rmb:.2f}亿。"
            )
        else:
            summary = (
                f"❌ 天使投资可行性不足 ({checks_passed}/{total_checks} 项指标达标)。"
                "建议重新审视估值或赛道天花板。"
            )

        return StageResult(
            stage="天使轮 (Angel)",
            is_viable=is_viable,
            score=score,
            max_valuation_rmb=self.MAX_ENTRY_VALUATION_RMB,
            expected_return_multiple=return_multiple,
            summary=summary,
            details={
                "entry_valuation_rmb": entry_valuation_rmb,
                "investment_amount_rmb": investment_amount_rmb,
                "expected_market_cap_rmb": expected_market_cap_rmb,
                "entry_stake_pct": round(entry_stake * 100, 2),
                "diluted_stake_pct": round(diluted_stake * 100, 2),
                "gross_return_rmb": round(gross_return, 2),
                "net_return_rmb": round(net_return_rmb, 2),
                "return_multiple": round(return_multiple, 1),
                "fund_recovery_ok": fund_recovery_ok,
                "holding_years": holding_years,
            },
            warnings=warnings,
            recommendations=recommendations,
        )


# ---------------------------------------------------------------------------
# VC Model — 100-10-10
# ---------------------------------------------------------------------------

class VCModel:
    """
    成长期 VC 100-10-10 模型

    Rules (source: [cite 38]):
    * Company must have ≥ 100亿 market cap potential
    * Single investment expected to return ≥ 10x
    * Net profit per project ≥ 10亿 RMB
    * Entry valuation strictly capped at 5-8亿 RMB, stake > 13%
    """

    REQUIRED_MARKET_CAP_RMB = 100.0
    REQUIRED_RETURN_MULTIPLE = 10.0
    REQUIRED_NET_PROFIT_RMB = 10.0
    MAX_ENTRY_VALUATION_RMB = 8.0
    MIN_ENTRY_VALUATION_RMB = 5.0
    MIN_STAKE_PCT = 13.0

    def evaluate(
        self,
        *,
        entry_valuation_rmb: float,
        investment_amount_rmb: float,
        expected_market_cap_rmb: float,
        fund_size_rmb: float,
        dilution_rate: float = 0.40,
        holding_years: int = 5,
    ) -> StageResult:
        """
        Evaluate a VC-stage growth investment opportunity.

        Parameters
        ----------
        entry_valuation_rmb:     Pre-money valuation at entry (亿元)
        investment_amount_rmb:   Amount to invest (亿元)
        expected_market_cap_rmb: Projected exit market cap (亿元)
        fund_size_rmb:           Total fund size (亿元)
        dilution_rate:           Cumulative dilution ratio (default 40%)
        holding_years:           Expected holding period in years
        """
        warnings: list[str] = []
        recommendations: list[str] = []
        checks_passed = 0
        total_checks = 5

        # 1. Market cap potential
        cap_ok = expected_market_cap_rmb >= self.REQUIRED_MARKET_CAP_RMB
        if cap_ok:
            checks_passed += 1
        else:
            warnings.append(
                f"预期市值 {expected_market_cap_rmb:.0f}亿 未达百亿门槛。"
            )

        # 2. Valuation ceiling
        valuation_ok = (
            self.MIN_ENTRY_VALUATION_RMB <= entry_valuation_rmb <= self.MAX_ENTRY_VALUATION_RMB
        )
        if valuation_ok:
            checks_passed += 1
        else:
            if entry_valuation_rmb > self.MAX_ENTRY_VALUATION_RMB:
                warnings.append(
                    f"进入估值 {entry_valuation_rmb:.1f}亿 超过VC上限8亿，"
                    "将难以实现10倍回报。"
                )
                recommendations.append("建议将投资时点提前至估值更低的轮次。")
            else:
                warnings.append(
                    f"进入估值 {entry_valuation_rmb:.1f}亿 低于5亿参考值，"
                    "请确认企业已具备足够成长验证。"
                )

        # 3. Stake > 13%
        post_money = entry_valuation_rmb + investment_amount_rmb
        stake_pct = (investment_amount_rmb / post_money) * 100
        stake_ok = stake_pct >= self.MIN_STAKE_PCT
        if stake_ok:
            checks_passed += 1
        else:
            warnings.append(
                f"持股比例 {stake_pct:.1f}% 低于13%最低要求，"
                "无法形成有效话语权和退出博弈能力。"
            )
            recommendations.append("增加投资金额或压低估值以提升持股比例至13%以上。")

        # 4. Return multiple
        diluted_stake = (investment_amount_rmb / post_money) * (1 - dilution_rate)
        gross_return = diluted_stake * expected_market_cap_rmb
        return_multiple = gross_return / investment_amount_rmb if investment_amount_rmb > 0 else 0
        multiple_ok = return_multiple >= self.REQUIRED_RETURN_MULTIPLE
        if multiple_ok:
            checks_passed += 1
        else:
            warnings.append(
                f"预测回报倍数 {return_multiple:.1f}x 低于10倍要求。"
            )

        # 5. Net profit per project
        net_return_rmb = gross_return - investment_amount_rmb
        profit_ok = net_return_rmb >= self.REQUIRED_NET_PROFIT_RMB
        if profit_ok:
            checks_passed += 1
        else:
            warnings.append(
                f"单项目净回报 {net_return_rmb:.1f}亿 低于10亿要求。"
            )

        score = (checks_passed / total_checks) * 100
        is_viable = checks_passed >= 4

        summary = (
            f"{'✅' if is_viable else '❌'} VC投资可行性"
            f"{'通过' if is_viable else '不足'} "
            f"({checks_passed}/{total_checks} 项指标达标)。"
            f"预测回报 {return_multiple:.1f}x，持股 {stake_pct:.1f}%。"
        )

        return StageResult(
            stage="成长期 VC (100-10-10)",
            is_viable=is_viable,
            score=score,
            max_valuation_rmb=self.MAX_ENTRY_VALUATION_RMB,
            expected_return_multiple=return_multiple,
            summary=summary,
            details={
                "entry_valuation_rmb": entry_valuation_rmb,
                "post_money_rmb": round(post_money, 2),
                "investment_amount_rmb": investment_amount_rmb,
                "expected_market_cap_rmb": expected_market_cap_rmb,
                "stake_pct": round(stake_pct, 2),
                "diluted_stake_pct": round(diluted_stake * 100, 2),
                "gross_return_rmb": round(gross_return, 2),
                "net_return_rmb": round(net_return_rmb, 2),
                "return_multiple": round(return_multiple, 1),
                "holding_years": holding_years,
            },
            warnings=warnings,
            recommendations=recommendations,
        )


# ---------------------------------------------------------------------------
# PE Model — 3-year-3x / 4-year-4x
# ---------------------------------------------------------------------------

class PEModel:
    """
    中后期 PE 三年三倍 / 四年四倍 模型

    Rules (source: [cite 30, 31]):
    * Annual profit growth rate ≥ 30%
    * Expected PE multiple at exit > current entry PE by ≥ 1x
    * Holding period 3 years → 3x return; 4 years → 4x return
    """

    MIN_PROFIT_GROWTH_RATE = 0.30       # 30% per year
    MIN_PE_EXPANSION = 1.0              # at least 1x PE expansion post-IPO

    def evaluate(
        self,
        *,
        entry_pe: float,                    # PE multiple at investment
        current_profit_rmb: float,          # Current annual profit (亿元)
        annual_profit_growth_rate: float,   # Expected annual profit growth rate
        target_exit_pe: float,              # Expected PE multiple at exit/IPO
        investment_amount_rmb: float,       # Amount to invest (亿元)
        holding_years: int = 3,             # 3 or 4 year holding
        fund_size_rmb: Optional[float] = None,
    ) -> StageResult:
        """
        Evaluate a PE-stage late-growth investment.

        Parameters
        ----------
        entry_pe:                    Price/earnings multiple at investment
        current_profit_rmb:          Current annual profit (亿元)
        annual_profit_growth_rate:   Expected CAGR for profit
        target_exit_pe:              Expected PE at exit/IPO
        investment_amount_rmb:       Capital to invest (亿元)
        holding_years:               Holding period (typically 3 or 4)
        fund_size_rmb:               Fund size for context (optional)
        """
        warnings: list[str] = []
        recommendations: list[str] = []
        checks_passed = 0
        total_checks = 4

        # 1. Profit growth requirement
        growth_ok = annual_profit_growth_rate >= self.MIN_PROFIT_GROWTH_RATE
        if growth_ok:
            checks_passed += 1
        else:
            warnings.append(
                f"年利润增速 {annual_profit_growth_rate * 100:.1f}% 低于30%最低要求，"
                "无法支撑三年三倍回报目标。"
            )
            recommendations.append("建议选择利润年增速≥30%的企业，或重新评估退出倍数。")

        # 2. PE expansion headroom
        pe_expansion = target_exit_pe - entry_pe
        pe_ok = pe_expansion >= self.MIN_PE_EXPANSION
        if pe_ok:
            checks_passed += 1
        else:
            warnings.append(
                f"退出PE {target_exit_pe:.1f}x 较进入PE {entry_pe:.1f}x "
                f"扩张仅 {pe_expansion:.1f}x，未达最低1倍扩张要求。"
            )
            recommendations.append(
                "确认当前进入估值是否已透支未来IPO市盈率，"
                "避免上市后出现一二级估值倒挂。"
            )

        # 3. Projected return multiple
        exit_profit_rmb = current_profit_rmb * ((1 + annual_profit_growth_rate) ** holding_years)
        exit_market_cap_rmb = exit_profit_rmb * target_exit_pe
        entry_market_cap_rmb = current_profit_rmb * entry_pe

        # Rough stake assumption: investment / entry market cap
        stake = investment_amount_rmb / entry_market_cap_rmb if entry_market_cap_rmb > 0 else 0
        gross_return = stake * exit_market_cap_rmb
        return_multiple = gross_return / investment_amount_rmb if investment_amount_rmb > 0 else 0

        target_multiple = float(holding_years)  # 3 years → 3x, 4 years → 4x
        multiple_ok = return_multiple >= target_multiple
        if multiple_ok:
            checks_passed += 1
        else:
            warnings.append(
                f"预测 {holding_years} 年回报 {return_multiple:.1f}x，"
                f"低于 {holding_years}年{int(target_multiple)}倍目标。"
            )

        # 4. Implied IRR check (≥ 15%)
        irr_approx = return_multiple ** (1 / holding_years) - 1
        irr_ok = irr_approx >= 0.15
        if irr_ok:
            checks_passed += 1
        else:
            warnings.append(
                f"隐含IRR约 {irr_approx * 100:.1f}% 低于基金最低IRR要求15%。"
            )

        score = (checks_passed / total_checks) * 100
        is_viable = checks_passed >= 3

        summary = (
            f"{'✅' if is_viable else '❌'} PE投资可行性"
            f"{'通过' if is_viable else '不足'} "
            f"({checks_passed}/{total_checks} 项指标达标)。"
            f"预测 {holding_years}年回报 {return_multiple:.1f}x，"
            f"隐含IRR {irr_approx * 100:.1f}%。"
        )

        return StageResult(
            stage=f"中后期 PE ({holding_years}年{int(target_multiple)}倍)",
            is_viable=is_viable,
            score=score,
            max_valuation_rmb=entry_market_cap_rmb,
            expected_return_multiple=return_multiple,
            summary=summary,
            details={
                "entry_pe": entry_pe,
                "target_exit_pe": target_exit_pe,
                "pe_expansion": round(pe_expansion, 2),
                "current_profit_rmb": current_profit_rmb,
                "exit_profit_rmb": round(exit_profit_rmb, 2),
                "entry_market_cap_rmb": round(entry_market_cap_rmb, 2),
                "exit_market_cap_rmb": round(exit_market_cap_rmb, 2),
                "annual_profit_growth_rate": annual_profit_growth_rate,
                "implied_stake_pct": round(stake * 100, 2),
                "return_multiple": round(return_multiple, 2),
                "implied_irr_pct": round(irr_approx * 100, 2),
                "holding_years": holding_years,
            },
            warnings=warnings,
            recommendations=recommendations,
        )


# ---------------------------------------------------------------------------
# BSE Model — 北交所估值模型
# ---------------------------------------------------------------------------

class BSEModel:
    """
    北交所 (Beijing Stock Exchange) 估值安全垫模型

    Rules (source: [cite 65, 66, 72, 73]):
    * BSE listed companies typically have market cap ≤ 20亿 and PE 15-20x
    * Entry PE must be ≤ 10x (provides ≥50% safety margin to exit PE)
    * Target company profit growth rate ≥ 20% per year
    """

    BSE_TYPICAL_PE_LOW = 15.0
    BSE_TYPICAL_PE_HIGH = 20.0
    MAX_ENTRY_PE = 10.0
    MIN_PROFIT_GROWTH_RATE = 0.20

    def evaluate(
        self,
        *,
        entry_pe: float,
        current_profit_rmb: float,          # 亿元
        annual_profit_growth_rate: float,
        expected_listing_pe: float,
        investment_amount_rmb: float,
        holding_years: int = 3,
    ) -> StageResult:
        """
        Evaluate an investment targeting BSE listing.

        Parameters
        ----------
        entry_pe:                    PE multiple at investment
        current_profit_rmb:          Current annual net profit (亿元)
        annual_profit_growth_rate:   Expected annual profit growth rate
        expected_listing_pe:         Anticipated PE at BSE listing
        investment_amount_rmb:       Capital to invest (亿元)
        holding_years:               Years until BSE listing
        """
        warnings: list[str] = []
        recommendations: list[str] = []
        checks_passed = 0
        total_checks = 4

        # 1. Entry PE ≤ 10x
        pe_ok = entry_pe <= self.MAX_ENTRY_PE
        if pe_ok:
            checks_passed += 1
        else:
            warnings.append(
                f"进入PE {entry_pe:.1f}x 超过北交所安全垫上限10倍。"
            )
            recommendations.append(
                "北交所二级流动性有限，进入PE须控制在10倍以内，"
                "以确保相对上市PE有至少50%的安全垫。"
            )

        # 2. Safety margin from entry to listing PE
        safety_margin = (expected_listing_pe - entry_pe) / expected_listing_pe if expected_listing_pe > 0 else 0
        margin_ok = safety_margin >= 0.50
        if margin_ok:
            checks_passed += 1
        else:
            warnings.append(
                f"PE安全垫 {safety_margin * 100:.1f}% 低于50%要求。"
            )
            recommendations.append("需要更低的进入估值或更高的预期上市PE。")

        # 3. Profit growth ≥ 20%
        growth_ok = annual_profit_growth_rate >= self.MIN_PROFIT_GROWTH_RATE
        if growth_ok:
            checks_passed += 1
        else:
            warnings.append(
                f"年利润增速 {annual_profit_growth_rate * 100:.1f}% 低于北交所20%最低要求。"
            )

        # 4. Projected return
        entry_market_cap = current_profit_rmb * entry_pe
        stake = investment_amount_rmb / entry_market_cap if entry_market_cap > 0 else 0
        exit_profit = current_profit_rmb * ((1 + annual_profit_growth_rate) ** holding_years)
        exit_market_cap = exit_profit * expected_listing_pe
        gross_return = stake * exit_market_cap
        return_multiple = gross_return / investment_amount_rmb if investment_amount_rmb > 0 else 0
        return_ok = return_multiple >= 2.0  # at least 2x for BSE
        if return_ok:
            checks_passed += 1
        else:
            warnings.append(
                f"预测回报 {return_multiple:.1f}x，北交所策略建议至少2倍回报。"
            )

        score = (checks_passed / total_checks) * 100
        is_viable = checks_passed >= 3

        summary = (
            f"{'✅' if is_viable else '❌'} 北交所投资可行性"
            f"{'通过' if is_viable else '不足'} "
            f"({checks_passed}/{total_checks} 项指标达标)。"
            f"PE安全垫 {safety_margin * 100:.1f}%，"
            f"预测回报 {return_multiple:.1f}x。"
        )

        return StageResult(
            stage="北交所 (BSE)",
            is_viable=is_viable,
            score=score,
            max_valuation_rmb=current_profit_rmb * self.MAX_ENTRY_PE,
            expected_return_multiple=return_multiple,
            summary=summary,
            details={
                "entry_pe": entry_pe,
                "expected_listing_pe": expected_listing_pe,
                "safety_margin_pct": round(safety_margin * 100, 2),
                "current_profit_rmb": current_profit_rmb,
                "entry_market_cap_rmb": round(entry_market_cap, 2),
                "exit_market_cap_rmb": round(exit_market_cap, 2),
                "annual_profit_growth_rate_pct": annual_profit_growth_rate * 100,
                "return_multiple": round(return_multiple, 2),
                "holding_years": holding_years,
            },
            warnings=warnings,
            recommendations=recommendations,
        )


# ==== ORIGIN: metrics.py ====
"""
核心财务指标计算器
Core Financial Metrics Calculators

Includes:
- IRR (Internal Rate of Return) calculator
- DPI / TVPI metrics (cash conversion analysis)
- Valuation analysis (Davis double-kill detection)
- CompsValuationAnchor — external comparable company data interface
- UnrealisedValueStripper — GP MOC auto-adjustment using market pricing
"""




# ---------------------------------------------------------------------------
# IRR Calculator
# ---------------------------------------------------------------------------

@dataclass
class IRRResult:
    irr_pct: float
    meets_hurdle: bool
    hurdle_rate_pct: float
    summary: str


class IRRCalculator:
    """
    IRR (内部收益率) 计算器

    Uses Newton-Raphson iteration to compute IRR from cash flows.
    Minimum hurdle rate for fund-level viability is 15% (source: [cite 30]).
    """

    DEFAULT_HURDLE_RATE = 0.15  # 15%

    def calculate(
        self,
        cash_flows: list[float],
        hurdle_rate: float = DEFAULT_HURDLE_RATE,
        max_iterations: int = 1000,
        tolerance: float = 1e-7,
    ) -> IRRResult:
        """
        Calculate IRR from a list of cash flows.

        Parameters
        ----------
        cash_flows:  List of cash flows ordered by period.
                     First element is typically a negative investment.
                     e.g. [-100, 0, 0, 350] for 3-year 3.5x investment.
        hurdle_rate: Minimum acceptable IRR (default 15%).

        Returns
        -------
        IRRResult with computed IRR percentage and hurdle comparison.
        """
        irr = self._compute_irr(cash_flows, max_iterations, tolerance)
        if irr is None:
            return IRRResult(
                irr_pct=float("nan"),
                meets_hurdle=False,
                hurdle_rate_pct=hurdle_rate * 100,
                summary="❌ 无法收敛计算IRR，请检查现金流序列。",
            )

        meets = irr >= hurdle_rate
        summary = (
            f"{'✅' if meets else '❌'} IRR = {irr * 100:.2f}%，"
            f"基准回报率 {hurdle_rate * 100:.0f}%，"
            f"{'达标' if meets else '未达标'}。"
        )
        return IRRResult(
            irr_pct=round(irr * 100, 4),
            meets_hurdle=meets,
            hurdle_rate_pct=hurdle_rate * 100,
            summary=summary,
        )

    def from_multiple(
        self,
        investment_rmb: float,
        return_rmb: float,
        holding_years: int,
        hurdle_rate: float = DEFAULT_HURDLE_RATE,
    ) -> IRRResult:
        """
        Convenience: compute IRR from a simple lump-sum investment and exit.

        Parameters
        ----------
        investment_rmb:  Initial investment amount (positive value).
        return_rmb:      Total exit proceeds.
        holding_years:   Number of years held.
        hurdle_rate:     Minimum acceptable IRR.
        """
        cash_flows = [-investment_rmb] + [0.0] * (holding_years - 1) + [return_rmb]
        return self.calculate(cash_flows, hurdle_rate)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _npv(rate: float, cash_flows: list[float]) -> float:
        return sum(cf / ((1 + rate) ** t) for t, cf in enumerate(cash_flows))

    @staticmethod
    def _npv_derivative(rate: float, cash_flows: list[float]) -> float:
        return sum(
            -t * cf / ((1 + rate) ** (t + 1)) for t, cf in enumerate(cash_flows)
        )

    def _compute_irr(
        self,
        cash_flows: list[float],
        max_iterations: int,
        tolerance: float,
    ) -> Optional[float]:
        rate = 0.1  # initial guess
        for _ in range(max_iterations):
            npv = self._npv(rate, cash_flows)
            derivative = self._npv_derivative(rate, cash_flows)
            if abs(derivative) < 1e-12:
                break
            new_rate = rate - npv / derivative
            if abs(new_rate - rate) < tolerance:
                return new_rate
            rate = new_rate
        return None


# ---------------------------------------------------------------------------
# DPI / TVPI Calculator
# ---------------------------------------------------------------------------

@dataclass
class DPITVPIResult:
    dpi: float          # Distributed to Paid-In
    tvpi: float         # Total Value to Paid-In (DPI + RVPI)
    rvpi: float         # Residual Value to Paid-In
    conversion_rate: float  # DPI / TVPI
    benchmark_conversion: float
    is_healthy: bool
    summary: str
    warnings: list[str] = field(default_factory=list)


class DPITVPICalculator:
    """
    DPI / TVPI 分析器

    Benchmarks (source: [cite 501, 502]):
    * Top global funds convert 88% of TVPI to DPI by end of fund life.
    * Chinese RMB blind-pool funds: DPI/TVPI ratio typically ~36%.

    DPI = cash actually distributed / capital invested
    TVPI = (cash distributed + remaining fair value) / capital invested
    """

    GLOBAL_TOP_CONVERSION = 0.88    # 88% — top global funds
    CHINA_AVG_CONVERSION = 0.36     # 36% — typical Chinese RMB fund

    def calculate(
        self,
        total_invested_rmb: float,
        total_distributed_rmb: float,
        remaining_fair_value_rmb: float,
        benchmark: str = "global",  # "global" or "china"
    ) -> DPITVPIResult:
        """
        Compute DPI, TVPI, RVPI and DPI/TVPI conversion rate.

        Parameters
        ----------
        total_invested_rmb:        Total capital called / invested (亿元)
        total_distributed_rmb:     Total cash actually returned to LPs (亿元)
        remaining_fair_value_rmb:  Current fair market value of unrealised portfolio (亿元)
        benchmark:                 Comparison benchmark ("global" or "china")
        """
        if total_invested_rmb <= 0:
            raise ValueError("total_invested_rmb must be positive")

        dpi = total_distributed_rmb / total_invested_rmb
        rvpi = remaining_fair_value_rmb / total_invested_rmb
        tvpi = dpi + rvpi
        conversion_rate = dpi / tvpi if tvpi > 0 else 0

        benchmark_conversion = (
            self.GLOBAL_TOP_CONVERSION if benchmark == "global"
            else self.CHINA_AVG_CONVERSION
        )
        bench_label = "全球顶尖基金" if benchmark == "global" else "国内人民币基金均值"

        warnings: list[str] = []
        if tvpi < 1.5:
            warnings.append(
                f"TVPI {tvpi:.2f}x 较低，基金整体回报可能不理想。"
            )
        if dpi < 1.0:
            warnings.append(
                f"DPI {dpi:.2f}x 尚未回本，LP尚未收回本金。"
                "账面浮盈存在无法变现的风险。"
            )
        if conversion_rate < self.CHINA_AVG_CONVERSION:
            warnings.append(
                f"DPI/TVPI转化率 {conversion_rate * 100:.1f}% "
                f"低于国内均值 {self.CHINA_AVG_CONVERSION * 100:.0f}%，"
                "账面回报的可信度存疑。"
            )

        is_healthy = dpi >= 1.0 and conversion_rate >= benchmark_conversion * 0.8

        summary = (
            f"DPI={dpi:.2f}x | TVPI={tvpi:.2f}x | 转化率={conversion_rate * 100:.1f}%\n"
            f"对标{bench_label}转化率 {benchmark_conversion * 100:.0f}%："
            f"{'✅ 健康' if is_healthy else '⚠️ 偏低，账面价值含水分较多'}。"
        )

        return DPITVPIResult(
            dpi=round(dpi, 4),
            tvpi=round(tvpi, 4),
            rvpi=round(rvpi, 4),
            conversion_rate=round(conversion_rate, 4),
            benchmark_conversion=benchmark_conversion,
            is_healthy=is_healthy,
            summary=summary,
            warnings=warnings,
        )


# ---------------------------------------------------------------------------
# Valuation Analyzer — Davis Double-Kill Detection
# ---------------------------------------------------------------------------

@dataclass
class DavisAnalysisResult:
    risk_level: str         # "low", "medium", "high", "critical"
    davis_double_kill_risk: bool
    pe_premium_pct: float   # how much current PE exceeds fair PE
    earnings_growth_gap: float  # expected growth vs required growth
    summary: str
    warnings: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)


class ValuationAnalyzer:
    """
    估值分析器 —— 戴维斯双杀风险检测

    Detects "Davis single-click" (PE expansion without earnings growth) and
    "Davis double-kill" risk (both PE contraction and earnings miss).

    Source: [cite 58, 59]
    """

    def analyze(
        self,
        current_pe: float,
        sector_median_pe: float,
        current_earnings_growth_pct: float,
        consensus_earnings_growth_pct: float,
        market_phase: str = "neutral",  # "boom", "neutral", "bust"
    ) -> DavisAnalysisResult:
        """
        Analyze valuation risk and Davis double-kill probability.

        Parameters
        ----------
        current_pe:                    Current/proposed PE multiple
        sector_median_pe:              Median PE for comparable sector peers
        current_earnings_growth_pct:   LTM actual earnings growth (%)
        consensus_earnings_growth_pct: Market consensus forecast earnings growth (%)
        market_phase:                  Current market sentiment phase
        """
        warnings: list[str] = []
        recommendations: list[str] = []

        pe_premium_pct = ((current_pe - sector_median_pe) / sector_median_pe * 100
                          if sector_median_pe > 0 else 0)
        earnings_growth_gap = consensus_earnings_growth_pct - current_earnings_growth_pct

        # Davis single-click: PE expanded much faster than earnings
        single_click = pe_premium_pct > 30 and current_earnings_growth_pct < consensus_earnings_growth_pct * 0.8

        # Davis double-kill: overvalued AND earnings outlook deteriorating
        double_kill_risk = (
            pe_premium_pct > 50
            and earnings_growth_gap > 20
            and market_phase in ("neutral", "bust")
        )

        if double_kill_risk:
            risk_level = "critical"
            warnings.append(
                "🚨 高危：检测到戴维斯双杀风险！"
                f"估值溢价 {pe_premium_pct:.0f}%，业绩预期差 {earnings_growth_gap:.0f}ppts。"
                "一旦风口退去将面临估值倍数与业绩双重暴跌。"
            )
            recommendations.append("建议立即止盈，避免持有至估值与业绩双杀时段。")
        elif single_click:
            risk_level = "high"
            warnings.append(
                f"⚠️ 戴维斯单击：估值溢价 {pe_premium_pct:.0f}%，"
                "但企业业绩增长尚未跟上估值扩张速度，存在后续双杀风险。"
            )
            recommendations.append("可继续持有，但需设立明确止盈触发点。")
        elif pe_premium_pct > 20:
            risk_level = "medium"
            warnings.append(
                f"估值较行业中位数溢价 {pe_premium_pct:.0f}%，"
                "需密切跟踪业绩兑现情况。"
            )
        else:
            risk_level = "low"

        if market_phase == "boom":
            warnings.append('当前处于市场狂热期，警惕"市梦率"透支未来，建议提前布局止盈预案。')

        summary = (
            f"{'🚨 极高' if risk_level == 'critical' else '⚠️ 偏高' if risk_level == 'high' else '🟡 中等' if risk_level == 'medium' else '✅ 低'} "
            f"估值风险 | PE溢价 {pe_premium_pct:.0f}% | "
            f"业绩增速差 {earnings_growth_gap:.0f}ppts | "
            f"戴维斯双杀风险：{'是' if double_kill_risk else '否'}"
        )

        return DavisAnalysisResult(
            risk_level=risk_level,
            davis_double_kill_risk=double_kill_risk,
            pe_premium_pct=round(pe_premium_pct, 2),
            earnings_growth_gap=round(earnings_growth_gap, 2),
            summary=summary,
            warnings=warnings,
            recommendations=recommendations,
        )


# ---------------------------------------------------------------------------
# Comparable Company Valuation Anchor
# ---------------------------------------------------------------------------

@dataclass
class CompanyComp:
    """A single comparable company's valuation data."""
    name: str
    sector: str
    pe_multiple: Optional[float] = None     # Price / Earnings
    ev_ebitda: Optional[float] = None       # Enterprise Value / EBITDA
    ps_multiple: Optional[float] = None     # Price / Sales
    growth_rate_pct: Optional[float] = None # Revenue / earnings growth rate


@dataclass
class CompsAnalysisResult:
    sector: str
    n_comps: int
    # PE statistics
    median_pe: Optional[float]
    mean_pe: Optional[float]
    percentile_25_pe: Optional[float]
    percentile_75_pe: Optional[float]
    # EV/EBITDA statistics
    median_ev_ebitda: Optional[float]
    mean_ev_ebitda: Optional[float]
    # P/S statistics
    median_ps: Optional[float]
    # Safety margin thresholds
    conservative_entry_pe: Optional[float]  # 25th pct × safety factor
    aggressive_entry_pe: Optional[float]    # 50th pct × safety factor
    safety_factor: float
    summary: str
    warnings: list[str] = field(default_factory=list)


class CompsValuationAnchor:
    """
    可比公司估值锚 — 外部数据接口

    Prevents valuation models from drifting away from the secondary market by
    establishing a dynamic safety-margin baseline anchored to real comparable
    company multiples.

    The Davis double-kill risk deepens when the primary-market target trades at
    a large premium to its secondary-market peers. This class:
    1. Accepts a list of CompanyComp objects (can be populated from any external
       data feed, database, or manual entry)
    2. Computes sector median / percentile statistics across PE, EV/EBITDA, P/S
    3. Derives conservative and aggressive entry PE thresholds by applying a
       configurable safety factor to the sector median
    4. Feeds updated sector statistics back into ValuationAnalyzer so that
       sector_median_pe is always market-current rather than static

    Usage:
        anchor = CompsValuationAnchor(safety_factor=0.70)
        anchor.add_comp(CompanyComp("商汤", "AI", pe_multiple=80.0, ev_ebitda=40.0))
        anchor.add_comp(CompanyComp("旷视", "AI", pe_multiple=70.0, ev_ebitda=35.0))
        result = anchor.analyze("AI")
        print(result.median_pe)   # → 75.0
    """

    def __init__(self, safety_factor: float = 0.70):
        """
        Parameters
        ----------
        safety_factor: Fraction of sector median PE to use as conservative entry.
                       E.g. 0.70 means entry PE ≤ 70% of sector median.
        """
        if not 0 < safety_factor <= 1:
            raise ValueError("safety_factor must be between 0 and 1")
        self.safety_factor = safety_factor
        self._comps: list[CompanyComp] = []

    def add_comp(self, comp: CompanyComp) -> None:
        self._comps.append(comp)

    def add_comps(self, comps: list[CompanyComp]) -> None:
        self._comps.extend(comps)

    def clear(self) -> None:
        self._comps.clear()

    def analyze(self, sector: Optional[str] = None) -> CompsAnalysisResult:
        """
        Compute sector statistics from loaded comps.

        Parameters
        ----------
        sector: If provided, filter comps to this sector only.
                If None, use all loaded comps.
        """
        comps = [c for c in self._comps if sector is None or c.sector == sector]
        if not comps:
            raise ValueError(
                f"No comps found for sector={sector!r}. "
                "Add comps via add_comp() before calling analyze()."
            )

        target_sector = sector or "全行业"
        warnings: list[str] = []

        def _stats(values: list[float]) -> tuple[Optional[float], Optional[float], Optional[float], Optional[float]]:
            """Return (median, mean, p25, p75) or all None if empty."""
            if not values:
                return None, None, None, None
            vs = sorted(values)
            n = len(vs)
            median = vs[n // 2] if n % 2 == 1 else (vs[n // 2 - 1] + vs[n // 2]) / 2
            mean = sum(vs) / n
            p25 = vs[max(0, int(0.25 * n))]
            p75 = vs[min(n - 1, int(0.75 * n))]
            return (
                round(median, 2),
                round(mean, 2),
                round(p25, 2),
                round(p75, 2),
            )

        pe_vals = [c.pe_multiple for c in comps if c.pe_multiple is not None]
        ev_vals = [c.ev_ebitda for c in comps if c.ev_ebitda is not None]
        ps_vals = [c.ps_multiple for c in comps if c.ps_multiple is not None]

        med_pe, mean_pe, p25_pe, p75_pe = _stats(pe_vals)
        med_ev, mean_ev, _, _ = _stats(ev_vals)
        med_ps, _, _, _ = _stats(ps_vals)

        # Derive entry thresholds
        conservative_entry = round(med_pe * self.safety_factor, 2) if med_pe else None
        aggressive_entry = round(med_pe, 2) if med_pe else None

        if len(comps) < 3:
            warnings.append(
                f"仅 {len(comps)} 家可比公司，样本量不足，"
                "统计结果可信度较低，建议补充更多同行数据。"
            )

        summary = (
            f"可比公司分析 ({target_sector}, N={len(comps)}) | "
            f"PE中位数={med_pe} | EV/EBITDA中位数={med_ev} | P/S中位数={med_ps}\n"
            f"建议进场PE上限: 保守={conservative_entry} | 积极={aggressive_entry} "
            f"（安全系数={self.safety_factor:.0%}）"
        )

        return CompsAnalysisResult(
            sector=target_sector,
            n_comps=len(comps),
            median_pe=med_pe,
            mean_pe=mean_pe,
            percentile_25_pe=p25_pe,
            percentile_75_pe=p75_pe,
            median_ev_ebitda=med_ev,
            mean_ev_ebitda=mean_ev,
            median_ps=med_ps,
            conservative_entry_pe=conservative_entry,
            aggressive_entry_pe=aggressive_entry,
            safety_factor=self.safety_factor,
            summary=summary,
            warnings=warnings,
        )


# ---------------------------------------------------------------------------
# Unrealised Value Stripper — GP MOC Auto-Adjustment
# ---------------------------------------------------------------------------

@dataclass
class UnrealisedStripResult:
    reported_moc: float
    reported_tvpi: float
    # Inputs
    unrealised_holdings: list[dict]   # each: {name, book_value, follow_on_discount_pct}
    total_book_value: float
    total_adjusted_value: float
    adjustment_factor: float          # adjusted / reported ratio
    # Adjusted metrics
    adjusted_moc: float
    adjusted_tvpi: float
    water_content_pct: float          # (1 - adjustment_factor) × 100
    summary: str
    warnings: list[str] = field(default_factory=list)


class UnrealisedValueStripper:
    """
    未变现价值水分剔除工具 — GP MOC自动校正

    The GP scorecard currently accepts self-reported MOC/TVPI, which can
    include large "unrealised" paper gains that may never be realised.

    A more rigorous approach uses the *follow-on funding discount rate*:
    when a portfolio company raises a new round from external investors,
    the new round price reveals what sophisticated third parties are willing
    to pay. If the GP still marks the position at a higher internal valuation,
    the gap is "water" (水分).

    This class:
    1. Accepts a list of unrealised holdings with their latest book value
       and the discount (or premium) implied by the most recent external
       follow-on financing
    2. Adjusts each holding's fair value downward by the follow-on discount
    3. Recomputes a water-stripped MOC and TVPI

    The corrected MOC feeds directly into GPScorecard for a more objective
    real-asset-management-capability score.

    Usage:
        stripper = UnrealisedValueStripper()
        result = stripper.strip(
            reported_moc=3.5,
            reported_tvpi=3.5,
            total_invested_rmb=10.0,
            total_distributed_rmb=5.0,
            unrealised_holdings=[
                {"name": "A公司", "book_value": 20.0, "follow_on_discount_pct": 30.0},
                {"name": "B公司", "book_value": 10.0, "follow_on_discount_pct": 0.0},
            ],
        )
        print(result.adjusted_moc)  # → lower than 3.5
    """

    def strip(
        self,
        *,
        reported_moc: float,
        reported_tvpi: float,
        total_invested_rmb: float,
        total_distributed_rmb: float,
        unrealised_holdings: list[dict],
    ) -> UnrealisedStripResult:
        """
        Strip unrealised water from GP-reported MOC/TVPI.

        Parameters
        ----------
        reported_moc:          GP's self-reported Multiple on Invested Capital
        reported_tvpi:         GP's self-reported Total Value to Paid-In
        total_invested_rmb:    Total capital invested (亿元)
        total_distributed_rmb: Cash already returned to LPs (亿元)
        unrealised_holdings:   List of dicts, each with:
                               - name (str): company name
                               - book_value (float): GP's internal book value (亿元)
                               - follow_on_discount_pct (float): discount implied by
                                 latest external follow-on round vs GP book (%).
                                 0 = no discount (3rd-party confirmed GP's valuation).
                                 Positive = GP over-marks vs external market.
        """
        warnings: list[str] = []

        total_book = sum(h.get("book_value", 0.0) for h in unrealised_holdings)
        total_adjusted = 0.0
        processed: list[dict] = []

        for h in unrealised_holdings:
            bv = h.get("book_value", 0.0)
            disc = h.get("follow_on_discount_pct", 0.0)
            adj_val = bv * (1 - disc / 100)
            total_adjusted += adj_val
            processed.append({
                "name": h.get("name", "未命名"),
                "book_value": bv,
                "follow_on_discount_pct": disc,
                "adjusted_value": round(adj_val, 4),
            })
            if disc > 30:
                warnings.append(
                    f"持仓『{h.get('name', '?')}』后续融资折价达 {disc:.0f}%，"
                    "账面价值严重虚高，建议大幅下调估值。"
                )

        adj_factor = total_adjusted / total_book if total_book > 0 else 1.0

        # Recompute TVPI: (distributed + adjusted unrealised NAV) / invested
        adjusted_tvpi = (total_distributed_rmb + total_adjusted) / total_invested_rmb \
            if total_invested_rmb > 0 else 0.0

        # Recompute MOC: scale reported MOC by adjustment factor applied to the
        # unrealised portion only
        reported_rvpi = reported_tvpi - (total_distributed_rmb / total_invested_rmb
                                         if total_invested_rmb > 0 else 0.0)
        adjusted_rvpi = reported_rvpi * adj_factor
        adjusted_moc = (total_distributed_rmb / total_invested_rmb + adjusted_rvpi
                        if total_invested_rmb > 0 else reported_moc * adj_factor)

        water_pct = (1 - adj_factor) * 100

        if water_pct > 20:
            warnings.append(
                f"账面整体水分率 {water_pct:.1f}%，GP真实资管能力被显著高估，"
                f"建议在GP评分卡中使用校正后MOC {adjusted_moc:.2f}x 替代报告值。"
            )

        summary = (
            f"报告MOC={reported_moc:.2f}x → 校正MOC={adjusted_moc:.2f}x | "
            f"报告TVPI={reported_tvpi:.2f}x → 校正TVPI={adjusted_tvpi:.2f}x | "
            f"账面水分={water_pct:.1f}%"
        )

        return UnrealisedStripResult(
            reported_moc=reported_moc,
            reported_tvpi=reported_tvpi,
            unrealised_holdings=processed,
            total_book_value=round(total_book, 4),
            total_adjusted_value=round(total_adjusted, 4),
            adjustment_factor=round(adj_factor, 4),
            adjusted_moc=round(adjusted_moc, 4),
            adjusted_tvpi=round(adjusted_tvpi, 4),
            water_content_pct=round(water_pct, 2),
            summary=summary,
            warnings=warnings,
        )
