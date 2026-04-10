"""
核心财务指标计算器
Core Financial Metrics Calculators

Includes:
- IRR (Internal Rate of Return) calculator
- DPI / TVPI metrics (cash conversion analysis)
- Valuation analysis (Davis double-kill detection)
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional


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
