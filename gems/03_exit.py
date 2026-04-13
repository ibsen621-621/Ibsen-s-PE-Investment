"""
# ============================================================
# Gemini Gems 参考文件 03 — 退出分析系统
# 来源: src/investment_model/exit.py
# 说明: 本文件为自包含参考文档，供 Gemini Gems 知识库使用
# ============================================================
"""

"""
退出分析模型
Exit Analysis Models

Implements:
- Parabola left-side exit timing (三条抛物线模型)
- Multi-channel exit evaluation
- Exit Decision Committee framework
- Dynamic liquidity discount model (credit-cycle sensitive)
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


# ---------------------------------------------------------------------------
# Exit channel types
# ---------------------------------------------------------------------------

class ExitChannel(str, Enum):
    IPO = "IPO上市"
    MA = "并购退出"
    SECONDARY = "老股转让 / S基金"
    BUYBACK = "企业回购"
    WRITE_OFF = "减值/注销"


# ---------------------------------------------------------------------------
# Parabola exit timing model
# ---------------------------------------------------------------------------

@dataclass
class ExitTimingResult:
    exit_quality: str           # "golden", "silver", "acceptable", "poor"
    recommended_action: str
    industry_curve_score: float     # 0-10
    company_curve_score: float      # 0-10
    capital_cycle_score: float      # 0-10
    composite_score: float          # weighted average 0-10
    is_optimal_window: bool
    summary: str
    warnings: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)


class ExitAnalyzer:
    """
    抛物线退出时机分析器

    Conceptual model (source: [cite 419, 420]):
    Every investment is influenced by three parabolas:
      1. 行业成长曲线 (Industry growth cycle)
      2. 企业成长曲线 (Company growth trajectory)
      3. 资本周期曲线  (Capital market cycle)

    Exit quality:
    * Golden exit: all three curves near peak simultaneously
    * Silver exit: two curves at peak, one declining
    * Exit immediately when continued holding cannot cover residual risk

    "Holding = re-buying at current price" principle (source: [cite 397, 398]):
    If expected return from current value cannot beat hurdle rate, exit now.
    """

    def analyze_timing(
        self,
        *,
        industry_growth_stage: str,      # "early", "peak", "declining", "bust"
        company_growth_stage: str,       # "early", "peak", "declining", "bust"
        capital_cycle_stage: str,        # "cold", "warming", "hot", "cooling"
        current_return_multiple: float,  # current paper gain vs cost
        hurdle_multiple: float = 3.0,    # target multiple to justify holding
        years_held: int = 3,
        years_remaining_in_fund: int = 2,
        has_liquid_secondary_market: bool = True,
    ) -> ExitTimingResult:
        """
        Analyze whether now is a good exit window.

        Parameters
        ----------
        industry_growth_stage:      Current phase of industry cycle
        company_growth_stage:       Current phase of company growth
        capital_cycle_stage:        Current phase of capital market sentiment
        current_return_multiple:    Current paper return multiple (x)
        hurdle_multiple:            Target return multiple to justify continued holding
        years_held:                 Years since initial investment
        years_remaining_in_fund:    Fund life remaining (years)
        has_liquid_secondary_market: Whether liquid exit channels exist
        """
        warnings: list[str] = []
        recommendations: list[str] = []

        # Score each curve (0=bust, 5=early, 8=peak, 3=declining)
        stage_scores = {"early": 5, "peak": 8, "declining": 3, "bust": 0}
        cap_scores = {"cold": 2, "warming": 5, "hot": 8, "cooling": 4}

        industry_score = float(stage_scores.get(industry_growth_stage, 3))
        company_score = float(stage_scores.get(company_growth_stage, 3))
        capital_score = float(cap_scores.get(capital_cycle_stage, 4))

        composite = (industry_score * 0.3 + company_score * 0.4 + capital_score * 0.3)

        # Classify exit quality
        peak_count = sum(
            1 for s in [industry_growth_stage, company_growth_stage]
            if s == "peak"
        ) + (1 if capital_cycle_stage == "hot" else 0)

        if peak_count >= 3:
            exit_quality = "golden"
        elif peak_count == 2:
            exit_quality = "silver"
        elif composite >= 5:
            exit_quality = "acceptable"
        else:
            exit_quality = "poor"

        # "Holding = re-buying" principle: if current return already ≥ hurdle, consider exiting
        already_at_hurdle = current_return_multiple >= hurdle_multiple
        urgency_signals = []

        if years_remaining_in_fund <= 1:
            urgency_signals.append(f"基金存续期仅剩 {years_remaining_in_fund} 年，须加快退出进程。")
        if not has_liquid_secondary_market:
            urgency_signals.append("二级市场流动性不足（日交易额低），IPO退出窗口受限。")
        if industry_growth_stage in ("declining", "bust"):
            urgency_signals.append("行业成长曲线已过顶，等待时间越长风险越高。")
        if capital_cycle_stage in ("cooling", "cold"):
            urgency_signals.append("资本市场情绪降温，估值倍数面临收缩压力。")

        warnings.extend(urgency_signals)

        if already_at_hurdle and exit_quality in ("golden", "silver"):
            recommended_action = "强烈建议立即止盈退出（黄金/白银退出窗口 + 已达收益目标）"
            warnings.append(
                f"当前回报 {current_return_multiple:.1f}x 已达目标 {hurdle_multiple:.1f}x，"
                "持有即等价于以当前价格重新买入，须重新评估期望收益。"
            )
        elif already_at_hurdle and exit_quality == "acceptable":
            recommended_action = "建议分批退出，锁定部分收益"
        elif exit_quality in ("golden", "silver"):
            recommended_action = "当前为优质退出窗口，即使未达目标倍数也应积极推进退出"
        elif exit_quality == "poor" and urgency_signals:
            recommended_action = "⚠️ 被动退出窗口——应放弃高定价幻想，接受折扣主动出清"
            recommendations.append(
                "建议给予接盘方10%-20%合理折扣，通过并购或老股转让尽快退出，"
                "避免继续拖延导致更大损失。"
            )
        else:
            recommended_action = "可继续持有，但需制定明确的止盈触发条件和退出时间表"

        is_optimal = exit_quality in ("golden", "silver")

        summary = (
            f"退出窗口质量：{'🥇 黄金' if exit_quality == 'golden' else '🥈 白银' if exit_quality == 'silver' else '🟡 可接受' if exit_quality == 'acceptable' else '🔴 不佳'} | "
            f"综合评分 {composite:.1f}/10 | "
            f"{'✅ 最优退出窗口' if is_optimal else '⚠️ 非最优退出窗口'}"
        )

        return ExitTimingResult(
            exit_quality=exit_quality,
            recommended_action=recommended_action,
            industry_curve_score=industry_score,
            company_curve_score=company_score,
            capital_cycle_score=capital_score,
            composite_score=round(composite, 2),
            is_optimal_window=is_optimal,
            summary=summary,
            warnings=warnings,
            recommendations=recommendations,
        )

    def evaluate_liquidity(
        self,
        *,
        exchange: str,                    # "A股", "港股", "美股", "新三板", "北交所"
        daily_trading_volume_usd: float,  # USD
        stake_value_rmb: float,           # Total value of stake to exit (亿元)
        target_exit_days: int = 90,       # Days available for exit
    ) -> dict:
        """
        Evaluate exit liquidity for secondary market sales.

        Rule of thumb (source: [cite 310, 311]):
        Small-cap HK/US stocks with daily volume < $1M USD means
        selling just 1% stake could take months.
        """
        daily_volume_rmb = daily_trading_volume_usd * 7.2 / 1e8  # convert to 亿元
        # Typically can sell ~5-10% of daily volume without moving price
        safe_daily_sell_rmb = daily_volume_rmb * 0.05
        days_to_exit = (
            stake_value_rmb / safe_daily_sell_rmb if safe_daily_sell_rmb > 0 else float("inf")
        )

        is_liquid = days_to_exit <= target_exit_days
        liquidity_crisis = daily_trading_volume_usd < 1_000_000

        result = {
            "exchange": exchange,
            "daily_trading_volume_usd": daily_trading_volume_usd,
            "daily_trading_volume_rmb_yi": round(daily_volume_rmb, 4),
            "stake_value_rmb_yi": stake_value_rmb,
            "estimated_exit_days": round(days_to_exit, 0) if days_to_exit != float("inf") else "∞",
            "target_exit_days": target_exit_days,
            "is_liquid": is_liquid,
            "liquidity_crisis": liquidity_crisis,
            "warning": (
                f"⚠️ 日交易额不足100万美元，出售 {stake_value_rmb:.1f}亿元股份"
                f"预计需约 {days_to_exit:.0f} 天，IPO≠变现！"
                if liquidity_crisis else None
            ),
        }
        return result


# ---------------------------------------------------------------------------
# Multi-channel Exit Evaluator
# ---------------------------------------------------------------------------

@dataclass
class ExitChannelResult:
    channel: ExitChannel
    feasibility_score: float    # 0-100
    estimated_valuation_rmb: float
    discount_pct: float         # discount vs peak paper value
    timeline_months: int
    pros: list[str]
    cons: list[str]
    recommendation: str


class ExitDecisionCommittee:
    """
    退出决策委员会框架

    Systematically evaluates multiple exit channels and generates
    a committee-ready decision memo.

    Source: [cite 433, 434, 436, 443, 446]
    """

    def evaluate_all_channels(
        self,
        *,
        peak_paper_valuation_rmb: float,
        company_sector: str,
        years_to_fund_end: int,
        ipo_readiness_score: float,         # 0-10
        ma_buyer_interest_score: float,     # 0-10
        secondary_market_liquidity: float,  # 0-10
        lp_cash_urgency: str,               # "low", "medium", "high"
        macro_capital_sentiment: str,       # "bullish", "neutral", "bearish"
    ) -> list[ExitChannelResult]:
        """
        Evaluate feasibility and attractiveness of all exit channels.

        Parameters
        ----------
        peak_paper_valuation_rmb:   Peak unrealised valuation of position (亿元)
        company_sector:             Sector/industry label
        years_to_fund_end:          Years until fund must be wound down
        ipo_readiness_score:        Company IPO-readiness (0-10)
        ma_buyer_interest_score:    Buyer interest for M&A (0-10)
        secondary_market_liquidity: Secondary/S-fund market liquidity (0-10)
        lp_cash_urgency:            How urgently LPs need cash distributions
        macro_capital_sentiment:    Current capital markets sentiment
        """
        results = []
        sentiment_multiplier = {"bullish": 1.1, "neutral": 1.0, "bearish": 0.85}
        sm = sentiment_multiplier.get(macro_capital_sentiment, 1.0)
        urgency_weight = {"low": 0, "medium": 0.15, "high": 0.30}.get(lp_cash_urgency, 0)

        # --- IPO ---
        ipo_val = peak_paper_valuation_rmb * sm
        ipo_discount = max(0.0, (peak_paper_valuation_rmb - ipo_val) / peak_paper_valuation_rmb)
        ipo_score = max(0, min(100, ipo_readiness_score * 10 - urgency_weight * 50))
        ipo_timeline = 18 if macro_capital_sentiment == "bearish" else 12
        results.append(ExitChannelResult(
            channel=ExitChannel.IPO,
            feasibility_score=round(ipo_score, 1),
            estimated_valuation_rmb=round(ipo_val, 2),
            discount_pct=round(ipo_discount * 100, 1),
            timeline_months=ipo_timeline,
            pros=["理论最高估值", "品牌背书", "未来减持灵活"],
            cons=[
                "流程长（12-24月）",
                "小盘股可能面临流动性枯竭",
                "上市≠变现，锁定期后仍需减持",
                "依赖市场窗口，不确定性高",
            ],
            recommendation=(
                "优先考虑IPO" if ipo_score >= 60
                else "IPO路径可行性低，建议同步推进其他退出渠道"
            ),
        ))

        # --- M&A ---
        ma_discount = 0.10 if macro_capital_sentiment != "bearish" else 0.20
        ma_val = peak_paper_valuation_rmb * (1 - ma_discount)
        ma_score = max(0, min(100, ma_buyer_interest_score * 10))
        results.append(ExitChannelResult(
            channel=ExitChannel.MA,
            feasibility_score=round(ma_score, 1),
            estimated_valuation_rmb=round(ma_val, 2),
            discount_pct=round(ma_discount * 100, 1),
            timeline_months=6,
            pros=["变现速度快（3-9月）", "一次性锁定现金", "规避二级市场流动性风险"],
            cons=[
                "须给予10%-20%折扣（source: [cite 443, 446]）",
                "可选买家有限",
                "整合风险可能影响企业价值",
            ],
            recommendation=(
                "强烈推荐" if ma_score >= 60 and years_to_fund_end <= 2
                else "可作为备选，积极接触潜在买家"
            ),
        ))

        # --- Secondary / S-fund ---
        sec_discount = 0.15 + urgency_weight
        sec_val = peak_paper_valuation_rmb * (1 - sec_discount)
        sec_score = max(0, min(100, secondary_market_liquidity * 10 - urgency_weight * 20))
        results.append(ExitChannelResult(
            channel=ExitChannel.SECONDARY,
            feasibility_score=round(sec_score, 1),
            estimated_valuation_rmb=round(sec_val, 2),
            discount_pct=round(sec_discount * 100, 1),
            timeline_months=3,
            pros=["速度最快（1-3月）", "S基金需求旺盛", "可部分退出灵活调节"],
            cons=[
                f"折扣较大（约{sec_discount * 100:.0f}%）",
                "需放弃一级市场'市梦率'定价",
                "信息不对称，谈判耗时",
            ],
            recommendation=(
                "强烈推荐（资金紧迫且流动性充足）" if lp_cash_urgency == "high"
                else "作为多元化退出组合的一部分"
            ),
        ))

        return results

    def generate_decision_memo(
        self,
        channel_results: list[ExitChannelResult],
        *,
        holding_cost_rmb: float,
        recommended_channel: Optional[ExitChannel] = None,
    ) -> str:
        """
        Generate a committee decision memo summarising all channels.
        """
        lines = [
            "=" * 60,
            "退出决策委员会报告 (Exit Decision Committee Memo)",
            "=" * 60,
            f"持仓成本: {holding_cost_rmb:.2f}亿元",
            "",
            "各退出渠道评估:",
        ]
        for r in channel_results:
            roi = (r.estimated_valuation_rmb - holding_cost_rmb) / holding_cost_rmb * 100
            lines.append(
                f"  [{r.channel.value}] 可行性={r.feasibility_score:.0f}/100 | "
                f"预期估值={r.estimated_valuation_rmb:.2f}亿 | "
                f"折价={r.discount_pct:.0f}% | "
                f"预计变现周期={r.timeline_months}月 | "
                f"相对成本回报={roi:.0f}%"
            )
        lines.append("")

        best = max(
            channel_results,
            key=lambda r: r.feasibility_score * r.estimated_valuation_rmb,
        )
        final = recommended_channel or best.channel
        lines.append(f"委员会建议退出渠道: 【{final.value}】")
        lines.append("")
        lines.append(
            "核心原则提示: 须放弃一级市场虚高'市梦率'定价，"
            "给予接盘方10%-20%合理折扣，实现有效变现。"
        )
        lines.append("=" * 60)

        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Dynamic Liquidity Discount Model
# ---------------------------------------------------------------------------

@dataclass
class LiquidityDiscountResult:
    base_discount_pct: float        # Fundamental illiquidity premium
    cycle_adjustment_pct: float     # Credit / rate cycle adjustment
    sfund_adjustment_pct: float     # S-fund market freeze adjustment
    total_discount_pct: float       # Total recommended discount to apply
    macro_regime: str               # Label for current macro regime
    s_fund_market: str              # Label for S-fund market state
    summary: str
    warnings: list[str] = field(default_factory=list)


class LiquidityDiscountModel:
    """
    动态流动性折价模型

    Replaces the fixed 10-20% discount assumption with a cycle-aware function.
    Discount is composed of:

    1. Base illiquidity premium  — structural premium for private-market assets
       (calibrated to S-fund transaction data: ~15% for VC, ~10% for PE)

    2. Credit / rate cycle adjustment — in rate-hiking cycles, discount rates
       rise and private-asset valuations compress further:
       * Rate-cut cycle:  −5% adjustment (buyer leverage cheap → lower discount)
       * Neutral:          0% adjustment
       * Rate-hike cycle: +5% to +10% depending on pace

    3. S-fund market activity adjustment — during S-fund market freezes
       (fundraising ice age 募资冰河期), bid-ask spreads widen significantly:
       * Active:    0%
       * Cooling:  +5%
       * Frozen:  +15%

    Total discount = base + credit_adj + sfund_adj, clipped to [5%, 50%].

    This ensures the committee model always uses a realistic market-clearing
    price rather than optimistic "market dream rate" (市梦率) pricing.
    """

    # Base discounts by asset class / stage
    BASE_DISCOUNTS = {
        "angel": 0.30,   # highest illiquidity
        "vc": 0.20,
        "pe": 0.12,
        "bse": 0.18,
        "default": 0.15,
    }

    CREDIT_ADJUSTMENTS = {
        "rate_cut": -0.05,
        "neutral": 0.00,
        "rate_hike_mild": 0.05,
        "rate_hike_aggressive": 0.10,
    }

    SFUND_ADJUSTMENTS = {
        "active": 0.00,
        "cooling": 0.05,
        "frozen": 0.15,
    }

    def calculate(
        self,
        *,
        asset_stage: str = "default",       # "angel", "vc", "pe", "bse", "default"
        credit_cycle: str = "neutral",       # "rate_cut", "neutral", "rate_hike_mild", "rate_hike_aggressive"
        s_fund_market: str = "active",       # "active", "cooling", "frozen"
        asset_quality: str = "average",      # "high", "average", "low" — quality premium/discount
        years_to_fund_end: int = 3,          # Urgency factor
    ) -> LiquidityDiscountResult:
        """
        Compute the dynamic liquidity discount for a private-market asset.

        Parameters
        ----------
        asset_stage:         Investment stage of the underlying asset
        credit_cycle:        Current macro credit / interest rate regime
        s_fund_market:       State of the S-fund secondary market
        asset_quality:       Subjective quality tier of the asset
        years_to_fund_end:   Years until fund must wind down (urgency)
        """
        warnings: list[str] = []

        base = self.BASE_DISCOUNTS.get(asset_stage, self.BASE_DISCOUNTS["default"])
        credit_adj = self.CREDIT_ADJUSTMENTS.get(credit_cycle, 0.0)
        sfund_adj = self.SFUND_ADJUSTMENTS.get(s_fund_market, 0.0)

        # Quality adjustment: high-quality assets command narrower bid-ask spreads
        quality_adj = {"high": -0.03, "average": 0.0, "low": 0.05}.get(asset_quality, 0.0)

        # Urgency adjustment: fund nearing end increases seller desperation
        urgency_adj = 0.0
        if years_to_fund_end <= 1:
            urgency_adj = 0.08
            warnings.append("基金存续期仅剩1年以内，卖方被动性显著提高折价幅度。")
        elif years_to_fund_end <= 2:
            urgency_adj = 0.04
            warnings.append("基金存续期仅剩2年，建议尽快启动退出谈判以控制折价区间。")

        total = base + credit_adj + sfund_adj + quality_adj + urgency_adj
        total = max(0.05, min(0.50, total))  # clip to [5%, 50%]

        if s_fund_market == "frozen":
            warnings.append(
                "S基金市场处于冰河期，流动性极度匮乏，"
                "建议优先考虑并购退出而非二级转让。"
            )
        if credit_cycle in ("rate_hike_mild", "rate_hike_aggressive"):
            warnings.append(
                f"加息周期（{credit_cycle}）下，买方融资成本上升，"
                "私募资产折价幅度系统性扩大。"
            )

        regime_labels = {
            "rate_cut": "降息/宽松周期",
            "neutral": "中性利率环境",
            "rate_hike_mild": "温和加息周期",
            "rate_hike_aggressive": "激进加息周期",
        }
        sfund_labels = {
            "active": "S基金市场活跃",
            "cooling": "S基金市场降温",
            "frozen": "S基金市场冰河期",
        }

        summary = (
            f"动态流动性折价 = {total * 100:.1f}% | "
            f"基础折价 {base * 100:.0f}% + "
            f"信用周期调整 {credit_adj * 100:+.0f}% + "
            f"S基金市场调整 {sfund_adj * 100:+.0f}% + "
            f"资产质量调整 {quality_adj * 100:+.0f}% + "
            f"紧迫度调整 {urgency_adj * 100:+.0f}%\n"
            f"宏观环境: {regime_labels.get(credit_cycle, credit_cycle)} | "
            f"{sfund_labels.get(s_fund_market, s_fund_market)}"
        )

        return LiquidityDiscountResult(
            base_discount_pct=round(base * 100, 2),
            cycle_adjustment_pct=round(credit_adj * 100, 2),
            sfund_adjustment_pct=round(sfund_adj * 100, 2),
            total_discount_pct=round(total * 100, 2),
            macro_regime=regime_labels.get(credit_cycle, credit_cycle),
            s_fund_market=sfund_labels.get(s_fund_market, s_fund_market),
            summary=summary,
            warnings=warnings,
        )
