# ==== GEMS FILE: 02_exit_lp_gp.py ====
# Merged from: exit.py, lp_evaluation.py, philosophy.py
# For Gemini Gems knowledge base — v4.0
# NOTE: This is a knowledge reference file, not executable production code.
#       Cross-module imports have been annotated for clarity.

from __future__ import annotations
import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


# ==== ORIGIN: exit.py ====
"""
退出分析模型
Exit Analysis Models

Implements:
- Parabola left-side exit timing (三条抛物线模型)
- Multi-channel exit evaluation
- Exit Decision Committee framework
- Dynamic liquidity discount model (credit-cycle sensitive)
"""




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


# ==== ORIGIN: lp_evaluation.py ====
"""
LP / GP 评估框架
LP Evaluation & GP Scorecard

Implements:
- GP Scorecard with 6 core indicators (source: [cite 496, 497, 498])
- Asset Allocation Advisor (三不与三要 / Three-no Three-yes framework)
- LP Behavior Checker (个人LP行为学纠偏)
"""




# ---------------------------------------------------------------------------
# GP Scorecard — 6 Core Indicators
# ---------------------------------------------------------------------------

@dataclass
class GPScorecardResult:
    total_score: float              # 0-100
    grade: str                      # "A", "B", "C", "D"
    is_investable: bool
    indicator_scores: dict[str, float]
    summary: str
    red_flags: list[str] = field(default_factory=list)
    green_flags: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)


class GPScorecard:
    """
    GP综合评分卡 — 六大核心指标

    DO NOT rely on star deals or inflated IRR. Instead evaluate:
    1. Historical real DPI data
    2. MOC with paper gains stripped out (fair value adjusted)
    3. Old LP re-investment rate
    4. Fund size vs GP stage/capability match
    5. Concentration in core winners (conviction)
    6. Government-guidance fund proportion (返投压力)

    Source: [cite 496, 497, 498]
    """

    WEIGHTS = {
        "dpi": 0.30,
        "moc_quality": 0.20,
        "lp_reinvest_rate": 0.15,
        "fund_stage_match": 0.15,
        "concentration": 0.10,
        "gov_fund_ratio": 0.10,
    }

    def evaluate(
        self,
        *,
        # 1. DPI — actual cash returned to LPs / total capital called
        historical_dpi: float,

        # 2. MOC quality — adjusted MOC after removing unrealised paper gains
        reported_moc: float,
        unrealised_pct: float,          # % of MOC that is paper / unrealised

        # 3. Old LP re-investment rate
        lp_reinvestment_rate_pct: float,  # % of existing LPs who re-invested

        # 4. Fund size vs team capability match
        fund_size_rmb: float,           # 亿元
        team_managed_assets_rmb: float, # 亿元 — historically managed by this team
        target_stage: str,              # "angel", "vc", "pe"

        # 5. Core portfolio concentration
        top3_investment_pct: float,     # % of fund capital in top 3 positions

        # 6. Government guidance fund proportion
        gov_fund_pct: float,            # % of total LP base that is gov guidance funds
    ) -> GPScorecardResult:
        """
        Score a GP across 6 core indicators.

        Returns a 0-100 composite score with grade and detailed breakdown.
        """
        red_flags: list[str] = []
        green_flags: list[str] = []
        recommendations: list[str] = []
        indicator_scores: dict[str, float] = {}

        # 1. DPI (max score: 30)
        # ≥ 1.5x = excellent (88 global conversion), 1.0-1.5 = good, < 1.0 = poor
        if historical_dpi >= 1.5:
            dpi_score = 30
            green_flags.append(f"DPI {historical_dpi:.2f}x — 实质性现金回报优秀。")
        elif historical_dpi >= 1.0:
            dpi_score = 18
        elif historical_dpi >= 0.7:
            dpi_score = 8
            red_flags.append(
                f"DPI {historical_dpi:.2f}x — 现金回款不足，账面浮盈转化能力存疑。"
            )
        else:
            dpi_score = 0
            red_flags.append(
                f"DPI {historical_dpi:.2f}x — 极低！LP本金尚未收回，存在重大风险。"
            )
        indicator_scores["dpi"] = dpi_score

        # 2. MOC quality (max score: 20)
        adjusted_moc = reported_moc * (1 - unrealised_pct / 100)
        if adjusted_moc >= 2.5:
            moc_score = 20
            green_flags.append(f"剔除未变现水分后MOC {adjusted_moc:.2f}x — 实质回报丰厚。")
        elif adjusted_moc >= 1.5:
            moc_score = 12
        elif adjusted_moc >= 1.0:
            moc_score = 6
            red_flags.append(
                f"调整后MOC {adjusted_moc:.2f}x (剔除{unrealised_pct:.0f}%未变现)，"
                "实质回报平庸。"
            )
        else:
            moc_score = 0
            red_flags.append(
                f"调整后MOC {adjusted_moc:.2f}x — 账面浮盈占比过高，"
                "真实回报严重低于宣传数据。"
            )
        indicator_scores["moc_quality"] = moc_score

        # 3. LP re-investment rate (max score: 15)
        if lp_reinvestment_rate_pct >= 80:
            lp_score = 15
            green_flags.append(f"老LP复投率 {lp_reinvestment_rate_pct:.0f}% — 历史满意度极高。")
        elif lp_reinvestment_rate_pct >= 60:
            lp_score = 10
        elif lp_reinvestment_rate_pct >= 40:
            lp_score = 5
            red_flags.append(
                f"老LP复投率 {lp_reinvestment_rate_pct:.0f}% — 历史LP认可度不足，"
                "需深入了解原因。"
            )
        else:
            lp_score = 0
            red_flags.append(
                f"老LP复投率 {lp_reinvestment_rate_pct:.0f}% — 极低！"
                "历史表现未获LP信任，高度警惕。"
            )
        indicator_scores["lp_reinvest_rate"] = lp_score

        # 4. Fund size vs stage match (max score: 15)
        # Rough benchmarks: Angel<5亿, VC 5-30亿, PE 30-200亿
        stage_limits = {"angel": 5, "vc": 30, "pe": 200}
        stage_limit = stage_limits.get(target_stage, 50)
        size_ratio = fund_size_rmb / stage_limit

        if size_ratio <= 1.0 and fund_size_rmb <= team_managed_assets_rmb * 1.5:
            match_score = 15
            green_flags.append(
                f"基金规模 {fund_size_rmb:.0f}亿与团队历史管理规模匹配。"
            )
        elif size_ratio <= 1.5:
            match_score = 10
        elif size_ratio <= 2.5:
            match_score = 5
            red_flags.append(
                f"基金规模 {fund_size_rmb:.0f}亿 相对{target_stage}阶段偏大，"
                "可能超出团队能力圈，导致投资动作变形。"
            )
        else:
            match_score = 0
            red_flags.append(
                f"基金规模严重超出团队能力边界，"
                "大概率导致投资策略偏离、回报摊薄。"
            )
        indicator_scores["fund_stage_match"] = match_score

        # 5. Concentration / conviction (max score: 10)
        # High concentration (top 3 > 40%) shows conviction
        if top3_investment_pct >= 50:
            conc_score = 10
            green_flags.append(
                f"核心项目集中度 {top3_investment_pct:.0f}% — 重仓赢家策略，体现投资魄力。"
            )
        elif top3_investment_pct >= 30:
            conc_score = 6
        else:
            conc_score = 3
            recommendations.append(
                "核心项目持仓分散，可能存在'撒胡椒面'投资风格，"
                "建议了解是否具备重仓优质资产的决策机制。"
            )
        indicator_scores["concentration"] = conc_score

        # 6. Government fund proportion (max score: 10)
        # Too high (> 40%) creates 返投压力 (re-investment location pressure)
        if gov_fund_pct <= 20:
            gov_score = 10
            green_flags.append(
                f"政府引导基金占比 {gov_fund_pct:.0f}% — 低政策依赖，"
                "投资决策相对独立自主。"
            )
        elif gov_fund_pct <= 40:
            gov_score = 6
        else:
            gov_score = 2
            red_flags.append(
                f"政府引导基金占比 {gov_fund_pct:.0f}% — 返投压力过大，"
                "可能导致强迫投资本地企业，投资决策系统性变形。"
            )
        indicator_scores["gov_fund_ratio"] = gov_score

        # Total score
        total = sum(indicator_scores.values())
        if total >= 80:
            grade = "A"
        elif total >= 65:
            grade = "B"
        elif total >= 45:
            grade = "C"
        else:
            grade = "D"

        is_investable = grade in ("A", "B")

        summary = (
            f"GP综合评分: {total:.0f}/100 | 等级: {grade} | "
            f"{'✅ 建议投资' if is_investable else '❌ 建议暂缓'}\n"
            f"红旗数量: {len(red_flags)} | 绿旗数量: {len(green_flags)}"
        )

        if not is_investable:
            recommendations.append(
                "综合评分不达标，建议暂缓投资。如坚持投入，"
                "须将承诺金额控制在资产配置盲池仓位的20%-30%以内，"
                "重点作为观察GP真实能力的低成本窗口。"
            )

        return GPScorecardResult(
            total_score=round(total, 1),
            grade=grade,
            is_investable=is_investable,
            indicator_scores=indicator_scores,
            summary=summary,
            red_flags=red_flags,
            green_flags=green_flags,
            recommendations=recommendations,
        )


# ---------------------------------------------------------------------------
# Asset Allocation Advisor — 三不与三要
# ---------------------------------------------------------------------------

@dataclass
class AllocationAdvice:
    blind_pool_pct: float       # recommended blind-pool fund allocation %
    special_fund_pct: float     # recommended special/co-investment allocation %
    fund_of_funds_pct: float    # recommended FoF allocation (likely 0)
    total_pe_allocation_pct: float
    summary: str
    warnings: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)


class AssetAllocationAdvisor:
    """
    LP资产配置顾问 — 三不与三要框架

    Three-NO rules (source: [cite 475, 476, 478]):
    1. 不碰市场化母基金 (No market-rate FoF — double-fee structure kills DPI)
    2. 不重仓盲池基金   (No over-concentration in blind-pool funds)
    3. 不投GP自有资金占比低的基金 (No GP if no meaningful co-investment)

    Three-YES rules:
    1. 控制盲池仓位 20%-30%  (Blind pools: observation & deal-flow access)
    2. 重仓精选专项基金       (Concentrate in carefully selected special funds)
    3. 要求GP大比例跟投       (Require GP to have meaningful skin in the game)
    """

    def advise(
        self,
        *,
        total_investable_assets_rmb: float,     # 亿元
        risk_tolerance: str,                    # "conservative", "moderate", "aggressive"
        pe_budget_pct: float,                   # % of total to allocate to PE/VC
        gp_coinvestment_rate_pct: float,        # GP's own co-investment %
        is_market_rate_fof: bool,               # Is this a market-rate FoF?
        years_of_observation: int = 0,          # Years the LP has observed this GP
    ) -> AllocationAdvice:
        """
        Provide LP asset allocation guidance.

        Parameters
        ----------
        total_investable_assets_rmb:  Total liquid investable capital (亿元)
        risk_tolerance:               Risk appetite
        pe_budget_pct:                % of total capital earmarked for PE/VC
        gp_coinvestment_rate_pct:     GP's own money as % of fund size
        is_market_rate_fof:           Whether the vehicle is a market-rate FoF
        years_of_observation:         How long LP has watched this GP
        """
        warnings: list[str] = []
        recommendations: list[str] = []

        # Hard rule: never invest in market-rate FoF
        if is_market_rate_fof:
            return AllocationAdvice(
                blind_pool_pct=0,
                special_fund_pct=0,
                fund_of_funds_pct=0,
                total_pe_allocation_pct=0,
                summary=(
                    "❌ 市场化母基金: 建议零配置。"
                    "双重收费结构（管理费+carry叠加）导致DPI极难回本，"
                    "实质上是把高净值LP变成接盘侠。"
                ),
                warnings=[
                    "市场化母基金的双重收费结构是天然的回报杀手，"
                    "务必坚决规避。"
                ],
            )

        # Warn if GP co-investment is too low
        if gp_coinvestment_rate_pct < 3:
            warnings.append(
                f"GP跟投比例仅 {gp_coinvestment_rate_pct:.1f}%，"
                "利益绑定不足，难以确保GP与LP目标一致。建议要求GP提高跟投比例至5%以上。"
            )

        # Base allocation by risk tolerance
        base_pe_pct = pe_budget_pct
        risk_caps = {"conservative": 15.0, "moderate": 25.0, "aggressive": 40.0}
        max_pe_pct = risk_caps.get(risk_tolerance, 20.0)
        actual_pe_pct = min(base_pe_pct, max_pe_pct)

        if base_pe_pct > max_pe_pct:
            warnings.append(
                f"目标PE配置比例 {base_pe_pct:.0f}% 超过"
                f"{risk_tolerance}风险偏好的上限 {max_pe_pct:.0f}%，"
                "建议降低配置。"
            )

        # Blind pool: 20-30% of PE allocation
        if years_of_observation < 2:
            blind_pool_pct = min(actual_pe_pct * 0.30, actual_pe_pct)
            recommendations.append(
                "观察期少于2年，建议以盲池基金为主要接触方式，"
                "重点考察GP的真实投资能力和退出能力。"
            )
        else:
            blind_pool_pct = actual_pe_pct * 0.25

        special_fund_pct = actual_pe_pct - blind_pool_pct

        summary_lines = [
            f"总可投资产: {total_investable_assets_rmb:.1f}亿元",
            f"建议PE/VC总配置: {actual_pe_pct:.1f}%（{total_investable_assets_rmb * actual_pe_pct / 100:.2f}亿元）",
            f"  其中 盲池基金: {blind_pool_pct:.1f}%（用于观察GP实力，获取项目流）",
            f"  其中 精选专项: {special_fund_pct:.1f}%（GP须大比例跟投，深度利益绑定）",
            f"  其中 市场化母基金: 0%（坚决规避双重收费结构）",
        ]

        return AllocationAdvice(
            blind_pool_pct=round(blind_pool_pct, 2),
            special_fund_pct=round(special_fund_pct, 2),
            fund_of_funds_pct=0.0,
            total_pe_allocation_pct=round(actual_pe_pct, 2),
            summary="\n".join(summary_lines),
            warnings=warnings,
            recommendations=recommendations,
        )


# ---------------------------------------------------------------------------
# LP Behavior Checker / 个人LP行为学纠偏
# ---------------------------------------------------------------------------

@dataclass
class LPBehaviorResult:
    """个人LP行为学纠偏结果 / LP behavioral bias check result."""
    narrative_trap_detected: bool       # 宏大叙事陷阱检测
    fomo_detected: bool                 # FOMO跟风效应检测
    expected_value: float               # 期望收益值（倍数）
    is_rational_decision: bool          # 综合判断：是否为理性决策
    soul_questions: list[str]           # 给LP的灵魂拷问清单
    summary: str
    warnings: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)


class LPBehaviorChecker:
    """
    个人LP行为学纠偏器
    LP Behavioral Bias Corrector

    Individual LPs often lose money not because they can't calculate returns,
    but because of fundamental human biases. This checker performs a "soul
    interrogation" (灵魂拷问) on the LP's own decision-making process.

    Three core checks:
    1. Grand Narrative Trap (宏大叙事陷阱): Attracted by "trillion-dollar market,
       led by renowned academics" without concrete evidence
    2. FOMO Effect (跟风效应): Following famous funds without independent analysis
    3. Cold Math: Expected value calculation from win probability and return/loss multiples
    """

    def check(
        self,
        *,
        # 1. Narrative trap / 宏大叙事陷阱
        attracted_by_narrative: bool,       # 是否被宏大叙事（万亿赛道/院士领衔）吸引
        has_concrete_evidence: bool,        # 是否看到具体的订单/良率/财务数据
        # 2. FOMO effect / 跟风效应
        following_famous_fund: bool,        # 是否因知名机构投了才跟投
        has_independent_analysis: bool,     # 是否做了独立分析
        # 3. Expected value / 期望值计算
        estimated_win_probability_pct: float,   # 预估胜率（%，0-100）
        expected_return_multiple: float,        # 胜出时的预期回报倍数
        expected_loss_multiple: float,          # 失败时的亏损倍数（通常0.0-1.0，0=全亏）
    ) -> LPBehaviorResult:
        """
        Perform a behavioral bias check on the LP's investment decision.

        Parameters
        ----------
        attracted_by_narrative:          LP was attracted by grand narrative claims
        has_concrete_evidence:           LP has reviewed concrete orders, yields, financials
        following_famous_fund:           LP is following because a famous fund invested
        has_independent_analysis:        LP has done own independent due diligence
        estimated_win_probability_pct:   LP's estimated probability of success (0-100)
        expected_return_multiple:        Expected return multiple on success (e.g., 5.0 = 5x)
        expected_loss_multiple:          Expected value of loss on failure (0.0 = total loss,
                                         0.5 = recover 50% of capital)
        """
        warnings: list[str] = []
        recommendations: list[str] = []
        soul_questions: list[str] = []

        # --- Check 1: Grand narrative trap ---
        narrative_trap_detected = attracted_by_narrative and not has_concrete_evidence

        if narrative_trap_detected:
            warnings.append(
                "⚠️ 宏大叙事陷阱警告：您被'万亿赛道、院士领衔'等宏大叙事所吸引，"
                "但尚未看到具体的订单数据、技术良率或财务验证。"
                "宏大叙事是吸引注意力的工具，不是投资的依据。"
            )
            soul_questions.append(
                "【灵魂拷问1】您能说出该公司最近一个季度的具体营收数字、"
                "主要客户名称和产品良率吗？如果不能，您投的是叙事而非企业。"
            )
        elif attracted_by_narrative and has_concrete_evidence:
            recommendations.append(
                "叙事+数据双重验证：您既被赛道叙事吸引，也验证了具体数据，"
                "这是正确的投资路径——叙事给方向，数据定价值。"
            )
            soul_questions.append(
                "【建议】持续追踪核心数据指标（良率/订单/营收），"
                "当数据与叙事出现偏差时及时复盘。"
            )
        else:
            soul_questions.append(
                "【灵魂拷问1】您决策的核心依据是什么？请确保有具体数据支撑，"
                "而非仅基于行业趋势判断。"
            )

        # --- Check 2: FOMO effect ---
        fomo_detected = following_famous_fund and not has_independent_analysis

        if fomo_detected:
            warnings.append(
                "⚠️ FOMO跟风效应警告：您因某知名机构（如知名VC）投了而选择跟投，"
                "但并未做独立分析。知名机构也会犯错，且其投资逻辑和您的风险偏好可能完全不同。"
                "跟风是情绪驱动，不是投资逻辑。"
            )
            soul_questions.append(
                "【灵魂拷问2】如果该知名机构从未投过这家公司，"
                "您还会投吗？如果答案是'不会'，您投的是机构背书而非企业本身。"
            )
        elif following_famous_fund and has_independent_analysis:
            recommendations.append(
                "知名机构背书+独立分析：您在验证了知名机构的投资逻辑后形成了独立判断，"
                "这是成熟LP的正确做法。"
            )

        # --- Check 3: Expected value calculation ---
        win_prob = estimated_win_probability_pct / 100.0
        loss_prob = 1.0 - win_prob

        # EV = win_prob * return_multiple + loss_prob * loss_multiple
        # Note: loss_multiple should be ≤ 1.0 (0 = total loss, 1 = full return of capital)
        # We interpret expected_loss_multiple as what fraction of capital is returned on loss
        expected_value = win_prob * expected_return_multiple + loss_prob * expected_loss_multiple

        if expected_value < 1.0:
            warnings.append(
                f"❄️ 冷酷数学警告：期望值 = {win_prob:.0%} × {expected_return_multiple:.1f}x + "
                f"{loss_prob:.0%} × {expected_loss_multiple:.2f}x = {expected_value:.2f}x < 1.0x。"
                "从概率论角度，这笔投资的期望收益为负。"
                "除非您有充分理由认为胜率/回报倍数被低估，否则在数学上不应投资。"
            )
            soul_questions.append(
                f"【灵魂拷问3】您的期望值仅为 {expected_value:.2f}x，"
                "数学告诉您这不是一笔好投资。您是否有额外的信息不对称优势，"
                "使实际胜率远高于您的估算？"
            )
        elif expected_value >= 2.0:
            recommendations.append(
                f"期望值 {expected_value:.2f}x ≥ 2.0x，从赔率角度值得投资。"
                "核心风险是胜率估算是否准确——请务必验证您的胜率假设。"
            )
            soul_questions.append(
                f"【确认问题】您的期望值为 {expected_value:.2f}x，赔率合理。"
                f"请再次确认：您的胜率估算 {estimated_win_probability_pct:.0f}% 是基于什么证据？"
            )
        else:
            soul_questions.append(
                f"【灵魂拷问3】期望值 {expected_value:.2f}x，勉强达标。"
                "请量化您的核心风险：最可能让这笔投资失败的因素是什么？"
            )

        # --- Overall rationality assessment ---
        rationality_issues = sum([narrative_trap_detected, fomo_detected, expected_value < 1.0])
        is_rational_decision = rationality_issues == 0

        if rationality_issues >= 2:
            warnings.append(
                f"检测到 {rationality_issues} 个行为偏差，当前决策受情绪和认知偏差影响显著，"
                "建议暂缓投资决策，给自己48小时冷静期后重新评估。"
            )
        elif rationality_issues == 1:
            recommendations.append(
                "存在1个行为偏差需要关注，建议在消除该偏差后再做最终决策。"
            )

        soul_questions.append(
            "【终极问题】如果这笔投资亏损一半，您的生活质量会受到显著影响吗？"
            "一级市场投资的平均退出周期为7-9年，在此期间该资金不可动用，"
            "请确认您的资金期限与投资期限匹配。"
        )

        rationality_labels = {True: "✅ 决策路径基本理性", False: "⚠️ 存在显著行为偏差"}
        summary = (
            f"{rationality_labels[is_rational_decision]} | "
            f"宏大叙事陷阱: {'⚠️ 是' if narrative_trap_detected else '✅ 否'} | "
            f"FOMO跟风: {'⚠️ 是' if fomo_detected else '✅ 否'} | "
            f"期望值: {expected_value:.2f}x | "
            f"灵魂拷问: {len(soul_questions)}题"
        )

        return LPBehaviorResult(
            narrative_trap_detected=narrative_trap_detected,
            fomo_detected=fomo_detected,
            expected_value=round(expected_value, 3),
            is_rational_decision=is_rational_decision,
            soul_questions=soul_questions,
            summary=summary,
            warnings=warnings,
            recommendations=recommendations,
        )



# ==== ORIGIN: philosophy.py ====
"""
投资哲学检查器
Investment Philosophy Checker

Validates an investment thesis against the core philosophies:
1. Value speculation vs value investing
2. Political economy lens (hard tech / autonomous control)
3. Exit rate reality check
4. Hard-tech strategy evaluator (P/Strategic dimension)
"""




EXIT_RATE_BENCHMARKS = {
    "top_pe": (0.25, 0.28),      # 25-28% (source: [cite 203, 205])
    "top_vc": (0.12, 0.16),      # ~16% (source: [cite 207])
    "top_angel": (0.03, 0.05),   # < 5% (source: [cite 208])
}

# Technology path types / 技术路径类型
TECH_PATH_CORE_PLUGIN = "core_plugin_replacement"        # 核心插件替换（高容错）
TECH_PATH_SYSTEM_REBUILD = "system_infrastructure_rebuild"  # 系统性基础设施重构（极高风险）
TECH_PATH_INCREMENTAL = "incremental_improvement"        # 渐进式改良（中等）


@dataclass
class HardTechStrategyResult:
    """硬科技战略评估结果 / Hard-tech strategy evaluation result."""
    tech_path_type: str             # 技术路径类型
    tech_path_score: float          # 技术路径得分 0-10
    is_chokepoint_tech: bool        # 是否卡脖子技术
    trl_level: int                  # 技术成熟度等级 1-9 (NASA TRL)
    strategic_premium_coefficient: float  # 战略价值系数/含权量 1.0-3.0
    strategic_score: float          # 综合战略得分 0-10
    strategic_valuation_multiplier: float  # 估值修正系数（可被估值模块引用）
    tech_path_assessment: str       # 技术路径评估描述
    warnings: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)


@dataclass
class PhilosophyCheckResult:
    is_value_speculative: bool
    political_economy_score: float  # 0-10
    exit_rate_realistic: bool
    overall_alignment: bool
    summary: str
    warnings: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    # New hard-tech strategy fields / 新增硬科技战略字段
    strategic_score: float = 0.0
    strategic_valuation_multiplier: float = 1.0
    tech_path_assessment: str = ""


class HardTechStrategyEvaluator:
    """
    硬科技战略评估器 — P/Strategic维度
    Hard-Tech Strategy Evaluator — P/Strategic Dimension

    Evaluates hard-tech investments from a strategic (non-purely-financial) lens.
    Introduces the concept of strategic_valuation_multiplier to adjust valuations
    for chokepoint technologies beyond simple PE/PS ratios.

    Key dimensions:
    - Technology landing path (技术落地路径)
    - Forced PMF check via "national urgency" (强制PMF — 国家急需属性)
    - P/Strategic strategic tolerance as correction coefficient (战略容错率)
    """

    # TRL (Technology Readiness Level) thresholds
    TRL_EARLY = 3         # Basic proof-of-concept / 基础概念验证
    TRL_MID = 6           # System prototype demo / 系统原型演示
    TRL_COMMERCIAL = 8    # System qualified for operations / 系统量产就绪

    def evaluate(
        self,
        *,
        tech_path_type: str,                    # TECH_PATH_* constant
        is_chokepoint_tech: bool,               # 是否卡脖子技术
        has_gov_procurement: bool,              # 是否有政府/国企采购
        tech_readiness_level: int,              # TRL 1-9 (NASA standard)
        is_domestic_substitution: bool = False,
        is_hard_tech: bool = True,
    ) -> HardTechStrategyResult:
        """
        Evaluate the strategic dimension of a hard-tech investment.

        Parameters
        ----------
        tech_path_type:          Type of technology landing path (see TECH_PATH_* constants)
        is_chokepoint_tech:      Is this a chokepoint/bottleneck technology (卡脖子)?
        has_gov_procurement:     Has the project secured government or SOE procurement?
        tech_readiness_level:    NASA TRL scale 1-9; 1=basic research, 9=proven in operations
        is_domestic_substitution: Is it replacing foreign technology?
        is_hard_tech:            Is the project a hard-tech company?
        """
        warnings: list[str] = []
        recommendations: list[str] = []

        # --- Tech path scoring / 技术路径评分 ---
        if tech_path_type == TECH_PATH_CORE_PLUGIN:
            tech_path_score = 8.0
            tech_path_assessment = (
                "核心插件替换型：容错率高，替代速度快（如固态电池替换液态、国产GPU替换英伟达）。"
                "系统阻力小，客户迁移成本低，技术演进路径清晰。"
            )
        elif tech_path_type == TECH_PATH_SYSTEM_REBUILD:
            tech_path_score = 3.0
            tech_path_assessment = (
                "系统性基础设施重构型：存在极高系统性阻力（如氢能大规模民用）。"
                "需要多方协同、基础设施配套、政策强力支撑，落地周期极长。"
            )
            warnings.append(
                "系统性基础设施重构类项目：系统性阻力极大，落地时间窗口难以预判，"
                "商业化进程通常比预期慢5-10年，建议大幅提高安全边际。"
            )
        else:  # TECH_PATH_INCREMENTAL or unknown
            tech_path_score = 5.5
            tech_path_assessment = (
                "渐进式改良型：在现有系统上进行量变式优化，风险适中，"
                "市场接受度相对平稳，但护城河可能较浅。"
            )

        # --- Strategic premium coefficient / 战略价值系数 ---
        # Base coefficient for non-chokepoint hard tech
        strategic_premium = 1.0

        if is_chokepoint_tech:
            strategic_premium = 2.0  # Base chokepoint premium
            warnings.append(
                "卡脖子技术赛道：估值锚不应单纯使用财务PE/PS，"
                "国资兜底可能性使其具备超额战略溢价（含权量）。"
            )
            recommendations.append(
                "建议引入战略价值系数（strategic_valuation_multiplier）对财务估值进行修正，"
                "该系数已自动计算并可被其他估值模块引用。"
            )
            if has_gov_procurement:
                strategic_premium = min(3.0, strategic_premium + 0.5)
        elif is_domestic_substitution:
            strategic_premium = 1.4

        if has_gov_procurement and not is_chokepoint_tech:
            strategic_premium = min(3.0, strategic_premium + 0.3)

        # Clamp to [1.0, 3.0]
        strategic_premium = max(1.0, min(3.0, strategic_premium))

        # --- TRL adjustment / 技术成熟度调整 ---
        if tech_readiness_level < self.TRL_EARLY:
            warnings.append(
                f"技术成熟度仅TRL {tech_readiness_level}（基础研究阶段），"
                "距商用落地还有巨大不确定性，建议在技术验证期限制投资规模。"
            )
            trl_adj = -1.5
        elif tech_readiness_level < self.TRL_MID:
            trl_adj = 0.0
        elif tech_readiness_level < self.TRL_COMMERCIAL:
            trl_adj = 1.0
            recommendations.append(
                f"TRL {tech_readiness_level} — 系统原型验证阶段，关注良率和成本是否达到商用阈值。"
            )
        else:
            trl_adj = 2.0  # TRL 8-9: near or at commercial readiness

        # --- Composite strategic score / 综合战略得分 ---
        strategic_score = min(10.0, max(0.0, tech_path_score + trl_adj))
        if is_chokepoint_tech:
            strategic_score = min(10.0, strategic_score + 1.0)
        if has_gov_procurement:
            strategic_score = min(10.0, strategic_score + 0.5)

        # Strategic valuation multiplier (for use by other valuation modules)
        # Combines strategic premium with TRL readiness
        trl_readiness_factor = tech_readiness_level / 9.0
        strategic_valuation_multiplier = (
            1.0 + (strategic_premium - 1.0) * trl_readiness_factor
        )
        strategic_valuation_multiplier = round(
            max(1.0, min(3.0, strategic_valuation_multiplier)), 2
        )

        if strategic_score >= 8.0:
            recommendations.append(
                "战略评分极高：项目具备强国家战略属性，即使短期财务亏损，"
                "也可能获得持续国资采购或政策补贴支撑。建议适当放宽IRR要求，"
                f"应用战略估值修正系数 {strategic_valuation_multiplier:.2f}x。"
            )
        elif strategic_score < 4.0:
            warnings.append(
                "战略评分偏低：项目在当前政治经济逻辑下战略属性不突出，"
                "需更依赖纯商业逻辑支撑估值，建议回归财务PE/PS锚定。"
            )

        return HardTechStrategyResult(
            tech_path_type=tech_path_type,
            tech_path_score=round(tech_path_score, 1),
            is_chokepoint_tech=is_chokepoint_tech,
            trl_level=tech_readiness_level,
            strategic_premium_coefficient=round(strategic_premium, 2),
            strategic_score=round(strategic_score, 1),
            strategic_valuation_multiplier=strategic_valuation_multiplier,
            tech_path_assessment=tech_path_assessment,
            warnings=warnings,
            recommendations=recommendations,
        )


class InvestmentPhilosophyChecker:
    """
    投资哲学一致性检验器

    Source framework: 《投的好，更要退的好（2024版）》by 李刚强

    Key principles:
    1. Value Speculation (价值投机): Use company growth as foundation, but take
       profit decisively when capital fever causes valuations to diverge severely
       from intrinsic value. (source: [cite 21, 22, 23])

    2. Political Economy Lens: PE has shifted from "internet economy" (traffic/scale)
       to "political economy" (autonomous control / domestic substitution / hard tech).
       Scarcity and "chokehold" attributes command huge premiums. (source: [cite 289, 290])

    3. Exit Reality: Be realistic about exit rates — even top PE funds only exit 25-28%
       of portfolio companies. Plan for the distribution, not the outlier. (source: [cite 203-208])

    4. P/Strategic (硬科技战略容错率): Beyond pure PE/PS valuation, evaluate the
       strategic tolerance and national urgency attributes of hard-tech investments.
    """

    def __init__(self) -> None:
        self._hardtech_evaluator = HardTechStrategyEvaluator()

    def check(
        self,
        *,
        investment_thesis: str,
        has_exit_plan: bool,
        has_profit_taking_triggers: bool,
        sector: str,
        is_hard_tech: bool,
        is_domestic_substitution: bool,
        is_autonomous_controllable: bool,
        is_internet_traffic_model: bool,
        fund_stage: str,                  # "angel", "vc", "pe"
        assumed_exit_rate_pct: float,     # The exit rate the fund is assuming
        valuation_vs_intrinsic_pct: float, # How far current valuation is above intrinsic value
        # New hard-tech strategy parameters / 新增硬科技战略参数
        tech_path_type: str = TECH_PATH_INCREMENTAL,
        is_chokepoint_tech: bool = False,
        has_gov_procurement: bool = False,
        tech_readiness_level: int = 5,    # NASA TRL 1-9
    ) -> PhilosophyCheckResult:
        """
        Check if an investment decision aligns with the three core philosophy tenets,
        now extended with the P/Strategic hard-tech dimension.

        Parameters
        ----------
        investment_thesis:           One-line description of investment rationale
        has_exit_plan:               Does the investment memo include a concrete exit plan?
        has_profit_taking_triggers:  Are stop-profit triggers defined?
        sector:                      Sector/industry
        is_hard_tech:                Is this a hard-tech company?
        is_domestic_substitution:    Does the company replace foreign tech/products?
        is_autonomous_controllable:  Is it in the autonomous-control/security space?
        is_internet_traffic_model:   Is the business model driven by internet traffic/scale?
        fund_stage:                  Stage of fund
        assumed_exit_rate_pct:       What exit rate is the fund planning around?
        valuation_vs_intrinsic_pct:  Valuation premium over estimated intrinsic value (%)
        tech_path_type:              Technology landing path type (TECH_PATH_* constants)
        is_chokepoint_tech:          Is this a chokepoint/bottleneck technology (卡脖子)?
        has_gov_procurement:         Has the project secured government or SOE procurement?
        tech_readiness_level:        NASA TRL 1-9 (1=basic research, 9=proven in operations)
        """
        warnings: list[str] = []
        recommendations: list[str] = []

        # --- Hard-tech strategy evaluation (new P/Strategic dimension) ---
        hardtech_result = self._hardtech_evaluator.evaluate(
            tech_path_type=tech_path_type,
            is_chokepoint_tech=is_chokepoint_tech,
            has_gov_procurement=has_gov_procurement,
            tech_readiness_level=tech_readiness_level,
            is_domestic_substitution=is_domestic_substitution,
            is_hard_tech=is_hard_tech,
        )
        # Merge warnings/recommendations from hard-tech evaluation
        warnings.extend(hardtech_result.warnings)
        recommendations.extend(hardtech_result.recommendations)

        # --- Check 1: Value speculation vs long-hold value investing ---
        if not has_exit_plan:
            warnings.append(
                "投资备忘录缺乏明确退出计划。中国一级市场基金存续期7-9年，"
                "不应依赖长线持有等待价值实现。"
            )
            recommendations.append("在投前即制定清晰的退出路径（IPO/并购/老股转让）和时间窗口。")

        if not has_profit_taking_triggers:
            warnings.append("未定义止盈触发条件，可能在资本狂热期错失最佳退出窗口（戴维斯双杀风险）。")
            recommendations.append("设立估值溢价触发点（如超出行业PE中位数50%时启动退出评估）。")

        if valuation_vs_intrinsic_pct > 100:
            warnings.append(
                f"当前估值较内在价值溢价 {valuation_vs_intrinsic_pct:.0f}%，"
                "已严重透支未来成长，符合'价值投机'止盈信号。"
            )
            recommendations.append("根据价值投机原则，建议启动分批退出程序。")

        is_value_speculative = has_exit_plan and has_profit_taking_triggers

        # --- Check 2: Political economy lens ---
        pe_signals = sum([is_hard_tech, is_domestic_substitution, is_autonomous_controllable])
        political_economy_score = float(pe_signals) / 3.0 * 10.0

        if is_internet_traffic_model:
            warnings.append(
                "互联网流量/规模驱动型商业模式在当前政治经济逻辑下溢价有限，"
                "需重新评估未来估值扩张空间。"
            )
            political_economy_score = max(0, political_economy_score - 3)

        if pe_signals == 0 and not is_internet_traffic_model:
            warnings.append(
                "项目既不符合硬科技/国产替代属性，也不是成熟互联网模式，"
                "需明确其在当前投资逻辑下的稀缺性所在。"
            )

        if pe_signals >= 2:
            pass  # no warning needed — strong political economy alignment

        # --- Check 3: Exit rate reality ---
        stage_key = {"angel": "top_angel", "vc": "top_vc", "pe": "top_pe"}.get(
            fund_stage, "top_vc"
        )
        lo, hi = EXIT_RATE_BENCHMARKS[stage_key]
        benchmark_center = (lo + hi) / 2 * 100  # as percentage

        assumed_pct = assumed_exit_rate_pct
        exit_rate_realistic = assumed_pct <= hi * 100 * 1.5  # allow 50% over benchmark

        if assumed_exit_rate_pct > hi * 100:
            warnings.append(
                f"计划退出率 {assumed_exit_rate_pct:.0f}% 超过顶级{fund_stage.upper()}基金"
                f"实际退出率基准 {hi * 100:.0f}%。"
                "过度乐观的退出假设将导致基金业绩测算严重失真。"
            )
            recommendations.append(
                f"建议将退出率假设调整至 {benchmark_center:.0f}% 附近，"
                "并为无法退出的项目制定减值预案。"
            )

        overall_alignment = (
            is_value_speculative
            and political_economy_score >= 4
            and exit_rate_realistic
        )

        summary_parts = [
            f"价值投机就绪: {'✅' if is_value_speculative else '❌'}",
            f"政治经济视角得分: {political_economy_score:.1f}/10",
            f"退出率假设合理性: {'✅' if exit_rate_realistic else '❌'}",
            f"战略评分: {hardtech_result.strategic_score:.1f}/10",
            f"综合哲学对齐度: {'✅ 对齐' if overall_alignment else '⚠️ 存在偏差'}",
        ]

        return PhilosophyCheckResult(
            is_value_speculative=is_value_speculative,
            political_economy_score=round(political_economy_score, 1),
            exit_rate_realistic=exit_rate_realistic,
            overall_alignment=overall_alignment,
            summary=" | ".join(summary_parts),
            warnings=warnings,
            recommendations=recommendations,
            strategic_score=hardtech_result.strategic_score,
            strategic_valuation_multiplier=hardtech_result.strategic_valuation_multiplier,
            tech_path_assessment=hardtech_result.tech_path_assessment,
        )
