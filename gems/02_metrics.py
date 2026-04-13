"""
# ============================================================
# Gemini Gems 参考文件 02 — 核心财务指标计算器
# 来源: src/investment_model/metrics.py
# 说明: 本文件为自包含参考文档，供 Gemini Gems 知识库使用
# ============================================================
"""

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
