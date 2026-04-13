"""
# ============================================================
# Gemini Gems 参考文件 01 — 投资阶段量化模型
# 来源: src/investment_model/stages.py
# 说明: 本文件为自包含参考文档，供 Gemini Gems 知识库使用
# ============================================================
"""

"""
投资阶段量化模型
Investment Stage Quantitative Models

Implements the three core stage models:
- Angel / 天使轮: 50-50-1 model
- VC / 成长期:   100-10-10 model
- PE / 中后期:   3-year-3x / 4-year-4x model
- BSE / 北交所:  Safety-margin valuation model
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


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
