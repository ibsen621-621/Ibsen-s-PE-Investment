"""
叙事驱动分类加总DCF估值模块
Narrative-Driven SOTP-DCF Valuation Module

对应达莫达兰工具一：叙事 → TAM → 市占率 → 稳态利润率的自上而下框架
一级市场融合点：用叙事锚定终局、Sales-to-Capital倒推烧钱率、SOTP加总避免单一折现率失灵

哲学原则：
"不要因为难，就放弃第一性原理；你100%会犯错，但这正是风险的本质。" —— Aswath Damodaran

模块说明：
- BusinessSegment：描述一个业务板块的叙事假设（TAM、市占率、利润率、烧钱率）
- NarrativeDCFValuer：对每个板块执行逐年FCF折现 + Gordon Growth终值计算
- SOTP（Sum-of-the-Parts）加总：对复合业务公司，每板块用匹配其特征的折现率，
  规避"单一WACC掩盖高增长子业务"的结构性谬误
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# 行业Sales-to-Capital基准参考表
# Industry Sales-to-Capital Benchmarks
# ---------------------------------------------------------------------------

INDUSTRY_S2C_BENCHMARKS: Dict[str, float] = {
    "SaaS": 1.5,
    "半导体": 0.8,
    "生物医药": 2.0,
    "新能源制造": 1.2,
    "互联网平台": 1.8,
    "AI大模型": 1.3,
    "电动汽车": 0.9,
    "航天发射": 0.6,
    "宽带卫星": 1.1,
    "消费品": 1.4,
}


# ---------------------------------------------------------------------------
# 输入数据类 — 业务板块假设
# Input — Business Segment Assumptions
# ---------------------------------------------------------------------------

@dataclass
class BusinessSegment:
    """
    单一业务板块的叙事假设集合
    Narrative assumptions for a single business segment.

    Fields
    ------
    name                         板块名称
    tam_rmb                      潜在市场规模（亿元）
    terminal_market_share_pct    第N年终局市占率（0-100）
    terminal_operating_margin_pct 终局EBIT利润率（0-100）
    sales_to_capital_ratio       销售资本比（每单位资本能支撑多少单位收入增量）
    years_to_terminal            达到终局的年数
    discount_rate                折现率（0-1，例如 0.12 代表 12%）
    industry_type                行业类型（用于与 INDUSTRY_S2C_BENCHMARKS 对比）
    tax_rate                     税率（默认 25%）
    """

    name: str
    tam_rmb: float                        # 潜在市场规模（亿元）
    terminal_market_share_pct: float      # 终局市占率（0-100）
    terminal_operating_margin_pct: float  # 终局EBIT利润率（0-100）
    sales_to_capital_ratio: float         # 销售资本比
    years_to_terminal: int                # 达到终局年数
    discount_rate: float                  # 折现率（0-1）
    industry_type: str = ""               # 行业类型（用于基准对比）
    tax_rate: float = 0.25                # 税率


# ---------------------------------------------------------------------------
# 输出数据类 — 板块估值明细
# Output — Segment Valuation Detail
# ---------------------------------------------------------------------------

@dataclass
class SegmentValuationDetail:
    """
    单一板块的DCF估值明细
    DCF valuation detail for one business segment.
    """

    name: str
    terminal_revenue_rmb: float           # 终局收入（亿元）
    terminal_ebit_rmb: float              # 终局EBIT（亿元）
    terminal_fcf_rmb: float               # 终局自由现金流（亿元）
    terminal_value_rmb: float             # Gordon Growth终值（亿元）
    pv_of_terminal_value_rmb: float       # 终值现值（亿元）
    pv_of_fcf_rmb: float                  # 过渡期FCF现值之和（亿元）
    total_pv_rmb: float                   # 总估值现值（亿元）
    cumulative_burn_rmb: float            # 累计负FCF（烧钱总量，亿元）
    annual_fcf_list: list[float]          # 逐年FCF序列（亿元）
    s2c_benchmark_deviation_pct: float    # 与行业S2C基准的偏差（%）


# ---------------------------------------------------------------------------
# 输出数据类 — SOTP估值汇总
# Output — SOTP Valuation Summary
# ---------------------------------------------------------------------------

@dataclass
class NarrativeDCFResult:
    """
    叙事驱动SOTP-DCF估值汇总结果
    Summary result of the Narrative-Driven SOTP-DCF valuation.
    """

    segment_details: list[SegmentValuationDetail]  # 各板块估值明细
    sotp_ev_rmb: float                              # SOTP企业价值（亿元）
    total_burn_rmb: float                           # 全项目累计烧钱金额（亿元）
    summary: str
    warnings: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    details: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# 核心估值引擎
# Core Valuation Engine
# ---------------------------------------------------------------------------

class NarrativeDCFValuer:
    """
    叙事驱动分类加总DCF估值引擎
    Narrative-Driven SOTP-DCF Valuation Engine

    算法原理
    --------
    对每个业务板块执行以下步骤：

    1. 收入路径（线性插值）：
       - 第0年收入=0（假设叙事起点），第N年=TAM × 市占率
       - 中间年份线性插值

    2. 再投资：
       - reinvestment_t = ΔRevenue_t / Sales-to-Capital

    3. EBIT路径（线性爬升）：
       - 利润率从0线性爬升至终局利润率

    4. FCF = EBIT × (1 - 税率) - reinvestment

    5. 终值（Gordon Growth）：
       - Terminal FCF = 终局Revenue × 终局Margin × (1-税率)
                      - 终局Revenue × g / S2C
       - TV = Terminal FCF × (1+g) / (r - g)

    6. 折现汇总：
       - PV = Σ FCF_t/(1+r)^t + TV/(1+r)^N

    7. S2C偏差检验：
       - 若偏离行业基准>50%，发出警告
    """

    def value(
        self,
        segments: list[BusinessSegment],
        terminal_growth_rate: float = 0.03,
    ) -> NarrativeDCFResult:
        """
        对多个业务板块执行叙事DCF并加总（SOTP）。

        Parameters
        ----------
        segments             业务板块列表
        terminal_growth_rate 终局永续增长率（默认 3%）

        Returns
        -------
        NarrativeDCFResult   包含各板块明细及SOTP汇总
        """
        warnings: list[str] = []
        recommendations: list[str] = []
        segment_details: list[SegmentValuationDetail] = []
        sotp_ev_rmb = 0.0
        total_burn_rmb = 0.0

        for seg in segments:
            detail = self._value_segment(seg, terminal_growth_rate, warnings)
            segment_details.append(detail)
            sotp_ev_rmb += detail.total_pv_rmb
            total_burn_rmb += detail.cumulative_burn_rmb

        # 整体推荐逻辑
        if total_burn_rmb > sotp_ev_rmb * 0.3:
            warnings.append(
                f"累计烧钱量 {total_burn_rmb:.1f}亿元 超过SOTP估值 {sotp_ev_rmb:.1f}亿元的30%，"
                "融资路径风险较高，需确保资本统筹覆盖至终局。"
            )
            recommendations.append(
                "建议在Term Sheet中约定里程碑触发式融资条款，分批释放估值，"
                "降低烧钱路径上的稀释风险。"
            )

        if len(segments) > 1:
            recommendations.append(
                f"SOTP方法将{len(segments)}个板块分别折现，"
                "有效规避了单一WACC掩盖高增长子业务的估值偏差，这是一级市场估值的正确姿势。"
            )

        summary = (
            f"SOTP-DCF企业价值: {sotp_ev_rmb:.2f}亿元 | "
            f"覆盖{len(segments)}个业务板块 | "
            f"累计烧钱: {total_burn_rmb:.2f}亿元 | "
            f"终局永续增长率: {terminal_growth_rate:.1%}"
        )

        return NarrativeDCFResult(
            segment_details=segment_details,
            sotp_ev_rmb=round(sotp_ev_rmb, 4),
            total_burn_rmb=round(total_burn_rmb, 4),
            summary=summary,
            warnings=warnings,
            recommendations=recommendations,
            details={
                "n_segments": len(segments),
                "terminal_growth_rate": terminal_growth_rate,
                "segment_names": [s.name for s in segments],
            },
        )

    # ------------------------------------------------------------------
    # 私有方法：单板块估值
    # Private: value a single segment
    # ------------------------------------------------------------------

    def _value_segment(
        self,
        seg: BusinessSegment,
        g: float,
        warnings: list[str],
    ) -> SegmentValuationDetail:
        """
        对单一业务板块执行逐年DCF估值。

        Parameters
        ----------
        seg       业务板块假设
        g         终局永续增长率
        warnings  共享警告列表（就地追加）
        """
        r = seg.discount_rate
        n = seg.years_to_terminal
        s2c = seg.sales_to_capital_ratio
        tax = seg.tax_rate

        terminal_revenue = seg.tam_rmb * (seg.terminal_market_share_pct / 100.0)
        terminal_margin = seg.terminal_operating_margin_pct / 100.0

        # 逐年收入序列（线性插值，第1年至第N年）
        revenues: list[float] = []
        for t in range(1, n + 1):
            revenues.append(terminal_revenue * t / n)

        # 逐年EBIT利润率序列（线性爬升）
        margins: list[float] = []
        for t in range(1, n + 1):
            margins.append(terminal_margin * t / n)

        # 逐年FCF及折现
        annual_fcf_list: list[float] = []
        pv_of_fcf = 0.0
        cumulative_burn = 0.0
        prev_revenue = 0.0

        for t in range(1, n + 1):
            rev = revenues[t - 1]
            margin = margins[t - 1]
            delta_rev = rev - prev_revenue
            reinvestment = delta_rev / s2c if s2c > 0 else 0.0
            ebit = rev * margin
            fcf = ebit * (1 - tax) - reinvestment

            discount_factor = (1 + r) ** t
            pv_of_fcf += fcf / discount_factor
            annual_fcf_list.append(round(fcf, 4))

            if fcf < 0:
                cumulative_burn += abs(fcf)

            prev_revenue = rev

        # 终值计算（Gordon Growth Model）
        terminal_ebit = terminal_revenue * terminal_margin
        terminal_fcf = (
            terminal_ebit * (1 - tax)
            - terminal_revenue * g / s2c
        )
        if r <= g:
            # 折现率不能低于增长率，否则Gordon Growth失效
            warnings.append(
                f"[{seg.name}] 折现率 {r:.1%} ≤ 永续增长率 {g:.1%}，"
                "Gordon Growth模型无法计算有效终值，终值设为0。"
            )
            terminal_value = 0.0
        else:
            terminal_value = terminal_fcf * (1 + g) / (r - g)

        pv_of_terminal_value = terminal_value / ((1 + r) ** n)
        total_pv = pv_of_fcf + pv_of_terminal_value

        # S2C基准偏差检验
        s2c_benchmark_deviation_pct = 0.0
        if seg.industry_type and seg.industry_type in INDUSTRY_S2C_BENCHMARKS:
            benchmark = INDUSTRY_S2C_BENCHMARKS[seg.industry_type]
            deviation = abs(s2c - benchmark) / benchmark
            s2c_benchmark_deviation_pct = round(deviation * 100, 2)
            if deviation > 0.5:
                warnings.append(
                    f"[{seg.name}] Sales-to-Capital {s2c:.2f} 与行业基准 "
                    f"({seg.industry_type}: {benchmark:.2f}) 偏差达 "
                    f"{deviation:.0%}，超过50%警戒线。"
                    "请核实烧钱效率假设是否与行业实证数据匹配。"
                )

        return SegmentValuationDetail(
            name=seg.name,
            terminal_revenue_rmb=round(terminal_revenue, 4),
            terminal_ebit_rmb=round(terminal_ebit, 4),
            terminal_fcf_rmb=round(terminal_fcf, 4),
            terminal_value_rmb=round(terminal_value, 4),
            pv_of_terminal_value_rmb=round(pv_of_terminal_value, 4),
            pv_of_fcf_rmb=round(pv_of_fcf, 4),
            total_pv_rmb=round(total_pv, 4),
            cumulative_burn_rmb=round(cumulative_burn, 4),
            annual_fcf_list=annual_fcf_list,
            s2c_benchmark_deviation_pct=s2c_benchmark_deviation_pct,
        )
