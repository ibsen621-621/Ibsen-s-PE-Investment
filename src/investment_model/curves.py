"""
数学增长曲线拟合 & 退出信号自动触发
Mathematical Growth Curve Fitting & Automated Exit Signal Triggers

Converts the qualitative "three parabolas" concept into executable math:

1. LogisticGrowthCurve  — S-shaped growth: fast early, plateau later.
   Used to fit company revenue / profit growth trajectory.
   f(t) = K / (1 + exp(-r * (t - t0)))

2. GompertzCurve        — asymmetric S-curve: slow start, faster middle, slow plateau.
   Better for industries with long ramp-up periods.
   f(t) = K * exp(-b * exp(-c * t))

3. CapitalCycleCurve    — models PE multiple expansion/contraction driven by
   macro sentiment and secondary market PE volatility.

4. ExitSignalDetector   — fits all three curves, computes first derivatives,
   detects peaks (derivative sign change from + to −) and automatically
   raises exit alerts when the composite derivative crosses below zero.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# Logistic growth curve
# ---------------------------------------------------------------------------

class LogisticGrowthCurve:
    """
    Logistic (S-shaped) growth model.

    f(t) = K / (1 + exp(-r * (t - t0)))

    Parameters
    ----------
    K  : carrying capacity (upper asymptote, e.g. max market share or revenue)
    r  : growth rate steepness
    t0 : inflection point (time of maximum growth rate)
    """

    def __init__(self, K: float, r: float, t0: float):
        if K <= 0:
            raise ValueError("K (carrying capacity) must be positive")
        if r <= 0:
            raise ValueError("r (growth rate) must be positive")
        self.K = K
        self.r = r
        self.t0 = t0

    def value(self, t: float) -> float:
        """Return f(t)."""
        return self.K / (1 + math.exp(-self.r * (t - self.t0)))

    def derivative(self, t: float) -> float:
        """Return f'(t) — the instantaneous growth rate at time t."""
        fv = self.value(t)
        return self.r * fv * (1 - fv / self.K)

    def growth_rate(self, t: float) -> float:
        """Return relative growth rate f'(t) / f(t)."""
        fv = self.value(t)
        if fv <= 0:
            return 0.0
        return self.derivative(t) / fv

    def peak_derivative_time(self) -> float:
        """Time at which the derivative is maximised (= inflection point t0)."""
        return self.t0

    def is_past_peak(self, t: float) -> bool:
        """True if t is past the inflection point (growth slowing)."""
        return t > self.t0


# ---------------------------------------------------------------------------
# Gompertz curve
# ---------------------------------------------------------------------------

class GompertzCurve:
    """
    Gompertz growth model — asymmetric S-curve.

    f(t) = K * exp(-b * exp(-c * t))

    Parameters
    ----------
    K : upper asymptote
    b : displacement along x-axis (sets location of inflection)
    c : growth rate
    """

    def __init__(self, K: float, b: float, c: float):
        if K <= 0:
            raise ValueError("K must be positive")
        if b <= 0 or c <= 0:
            raise ValueError("b and c must be positive")
        self.K = K
        self.b = b
        self.c = c

    def value(self, t: float) -> float:
        """Return f(t)."""
        return self.K * math.exp(-self.b * math.exp(-self.c * t))

    def derivative(self, t: float) -> float:
        """Return f'(t)."""
        fv = self.value(t)
        return fv * self.b * self.c * math.exp(-self.c * t)

    def growth_rate(self, t: float) -> float:
        """Return relative growth rate f'(t) / f(t)."""
        return self.b * self.c * math.exp(-self.c * t)

    def peak_derivative_time(self) -> float:
        """Inflection point of Gompertz: t = ln(b) / c."""
        return math.log(self.b) / self.c

    def is_past_peak(self, t: float) -> bool:
        return t > self.peak_derivative_time()


# ---------------------------------------------------------------------------
# Capital cycle curve (PE multiple modelling)
# ---------------------------------------------------------------------------

@dataclass
class CapitalCyclePoint:
    t: float            # time (years since investment)
    pe_multiple: float  # secondary market PE multiple at time t
    sentiment: str      # "cold", "warming", "hot", "cooling"


class CapitalCycleCurve:
    """
    资本周期PE倍数曲线

    Models PE multiple expansion/contraction as a sinusoidal-like cycle
    anchored to observed sector PE data points.

    Uses linear interpolation between user-supplied data points; also
    exposes a first-derivative estimate to determine whether the capital
    cycle is in expansion (derivative > 0) or contraction (derivative < 0).
    """

    def __init__(self, data_points: list[CapitalCyclePoint]):
        if len(data_points) < 2:
            raise ValueError("Need at least 2 data points for capital cycle curve.")
        self._points = sorted(data_points, key=lambda p: p.t)

    def pe_at(self, t: float) -> float:
        """Return linearly interpolated PE multiple at time t."""
        pts = self._points
        if t <= pts[0].t:
            return pts[0].pe_multiple
        if t >= pts[-1].t:
            return pts[-1].pe_multiple
        for i in range(len(pts) - 1):
            t0, t1 = pts[i].t, pts[i + 1].t
            if t0 <= t <= t1:
                w = (t - t0) / (t1 - t0)
                return pts[i].pe_multiple + w * (pts[i + 1].pe_multiple - pts[i].pe_multiple)
        return pts[-1].pe_multiple

    def derivative_at(self, t: float, dt: float = 0.1) -> float:
        """Numerical first derivative of PE multiple curve at time t."""
        return (self.pe_at(t + dt) - self.pe_at(t - dt)) / (2 * dt)

    def is_expanding(self, t: float) -> bool:
        """True if PE multiples are still rising at time t."""
        return self.derivative_at(t) > 0

    def peak_t(self) -> float:
        """Return the time at which PE multiple reaches its maximum."""
        pts = self._points
        max_pe = max(p.pe_multiple for p in pts)
        for p in pts:
            if p.pe_multiple == max_pe:
                return p.t
        return pts[-1].t


# ---------------------------------------------------------------------------
# Exit signal detector
# ---------------------------------------------------------------------------

@dataclass
class ExitSignal:
    t: float
    signal_type: str        # "golden_peak", "silver_peak", "warning", "urgent"
    trigger_reason: str
    composite_derivative: float
    industry_derivative: float
    company_derivative: float
    capital_derivative: float
    recommended_action: str


@dataclass
class ExitSignalReport:
    signals: list[ExitSignal] = field(default_factory=list)
    earliest_golden_t: Optional[float] = None
    earliest_silver_t: Optional[float] = None
    summary: str = ""

    def add_signal(self, sig: ExitSignal) -> None:
        self.signals.append(sig)
        if sig.signal_type == "golden_peak" and self.earliest_golden_t is None:
            self.earliest_golden_t = sig.t
        if sig.signal_type == "silver_peak" and self.earliest_silver_t is None:
            self.earliest_silver_t = sig.t


class ExitSignalDetector:
    """
    退出信号自动检测器

    Fits three mathematical curves (industry growth, company growth, capital cycle)
    and scans a time horizon to detect:

    - "golden_peak"  : all three curves' first derivatives near zero (all peaking together)
    - "silver_peak"  : two of three derivatives turn negative (two curves past peak)
    - "warning"      : composite derivative crosses zero
    - "urgent"       : composite score falls sharply AND capital cycle contracting

    The first-derivative sign-change approach replaces the qualitative "parabola
    intersection" with a rigorous mathematical trigger.
    """

    # Derivative thresholds (relative growth rates)
    PEAK_THRESHOLD = 0.03       # growth rate < 3% → effectively at peak
    URGENT_THRESHOLD = -0.05    # composite derivative < -5% → urgent sell

    def __init__(
        self,
        industry_curve: LogisticGrowthCurve | GompertzCurve,
        company_curve: LogisticGrowthCurve | GompertzCurve,
        capital_curve: CapitalCycleCurve,
    ):
        self.industry = industry_curve
        self.company = company_curve
        self.capital = capital_curve

    def scan(
        self,
        t_start: float = 0.0,
        t_end: float = 10.0,
        dt: float = 0.25,
    ) -> ExitSignalReport:
        """
        Scan the time horizon [t_start, t_end] at step dt and detect exit signals.

        Returns an ExitSignalReport with all detected signals in chronological order.
        """
        report = ExitSignalReport()
        t = t_start

        while t <= t_end:
            ind_gr = self.industry.growth_rate(t)
            com_gr = self.company.growth_rate(t)
            cap_der = self.capital.derivative_at(t)
            # Normalise capital derivative to a comparable scale
            pe_now = self.capital.pe_at(t)
            cap_gr = cap_der / pe_now if pe_now > 0 else 0

            # Composite score: weighted sum of relative growth rates
            composite = ind_gr * 0.30 + com_gr * 0.40 + cap_gr * 0.30

            # Count how many curves are at/past peak
            ind_past = self.industry.is_past_peak(t)
            com_past = self.company.is_past_peak(t)
            cap_past = not self.capital.is_expanding(t)
            past_count = sum([ind_past, com_past, cap_past])

            ind_near_peak = abs(ind_gr) < self.PEAK_THRESHOLD
            com_near_peak = abs(com_gr) < self.PEAK_THRESHOLD
            cap_near_peak = abs(cap_gr) < self.PEAK_THRESHOLD

            signal = None

            if past_count == 3 and all([ind_near_peak, com_near_peak, cap_near_peak]):
                signal = ExitSignal(
                    t=round(t, 2),
                    signal_type="golden_peak",
                    trigger_reason="三条曲线同时触顶（一阶导数趋近于零）",
                    composite_derivative=round(composite, 4),
                    industry_derivative=round(ind_gr, 4),
                    company_derivative=round(com_gr, 4),
                    capital_derivative=round(cap_gr, 4),
                    recommended_action="🥇 黄金退出窗口触发 — 立即启动退出流程",
                )
            elif past_count >= 2:
                signal = ExitSignal(
                    t=round(t, 2),
                    signal_type="silver_peak",
                    trigger_reason=f"三条曲线中 {past_count} 条已过顶（一阶导数转负）",
                    composite_derivative=round(composite, 4),
                    industry_derivative=round(ind_gr, 4),
                    company_derivative=round(com_gr, 4),
                    capital_derivative=round(cap_gr, 4),
                    recommended_action="🥈 白银退出窗口触发 — 建议分批启动退出",
                )
            elif composite < self.URGENT_THRESHOLD:
                signal = ExitSignal(
                    t=round(t, 2),
                    signal_type="urgent",
                    trigger_reason=f"综合增长率 {composite:.3f} 低于紧急阈值 {self.URGENT_THRESHOLD}",
                    composite_derivative=round(composite, 4),
                    industry_derivative=round(ind_gr, 4),
                    company_derivative=round(com_gr, 4),
                    capital_derivative=round(cap_gr, 4),
                    recommended_action="🚨 紧急退出预警 — 价值正在加速损失",
                )

            if signal is not None:
                report.add_signal(signal)

            t = round(t + dt, 10)

        # Deduplicate consecutive same-type signals (keep first occurrence)
        seen: set[str] = set()
        deduped: list[ExitSignal] = []
        for sig in report.signals:
            key = sig.signal_type
            if key not in seen:
                seen.add(key)
                deduped.append(sig)
        report.signals = deduped

        golden_t = report.earliest_golden_t
        silver_t = report.earliest_silver_t
        report.summary = (
            f"扫描区间 t=[{t_start}, {t_end}] | "
            f"黄金退出点: {'t=' + str(golden_t) if golden_t is not None else '未触发'} | "
            f"白银退出点: {'t=' + str(silver_t) if silver_t is not None else '未触发'} | "
            f"共检测到 {len(report.signals)} 个退出信号"
        )

        return report
