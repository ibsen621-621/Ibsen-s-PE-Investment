"""
投资哲学检查器
Investment Philosophy Checker

Validates an investment thesis against the core philosophies:
1. Value speculation vs value investing
2. Political economy lens (hard tech / autonomous control)
3. Exit rate reality check
"""

from __future__ import annotations

from dataclasses import dataclass, field


EXIT_RATE_BENCHMARKS = {
    "top_pe": (0.25, 0.28),      # 25-28% (source: [cite 203, 205])
    "top_vc": (0.12, 0.16),      # ~16% (source: [cite 207])
    "top_angel": (0.03, 0.05),   # < 5% (source: [cite 208])
}


@dataclass
class PhilosophyCheckResult:
    is_value_speculative: bool
    political_economy_score: float  # 0-10
    exit_rate_realistic: bool
    overall_alignment: bool
    summary: str
    warnings: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)


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
    """

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
    ) -> PhilosophyCheckResult:
        """
        Check if an investment decision aligns with the three core philosophy tenets.

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
        """
        warnings: list[str] = []
        recommendations: list[str] = []

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
        )
