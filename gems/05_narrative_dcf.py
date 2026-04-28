# ==== GEMS FILE: 05_narrative_dcf.py ====
# Merged from: narrative_dcf.py, cyclical_normalization.py
# For Gemini Gems knowledge base — v4.0
# NOTE: This is a knowledge reference file, not executable production code.
#       Cross-module imports have been annotated for clarity.

from __future__ import annotations
import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional


# ==== ORIGIN: narrative_dcf.py ====
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


# ==== ORIGIN: cyclical_normalization.py ====
"""
周期股常态化模块
Cyclical Stock Normalization Module

对应达莫达兰工具七：宏观剥离常态化
一级市场融合点：避免用周期高点利润做DCF、大宗商品回归方程提炼常态基准

核心洞见：
- 周期性行业（资源、化工、航运、钢铁、新能源制造）的利润具有强烈的宏观周期性
- 在行业景气高点时做DCF，会系统性高估终值（"在超级周期顶部买矿"的错误）
- 正确做法：用历史7年的常态化平均利润率替代当前利润率做DCF
- 大宗商品价格敏感型行业（锂电、铜、油气）需额外做价格回归分析
- 去头去尾的修剪平均值（Trimmed Mean）比简单均值对周期性数据更稳健

模块组成：
- NormalizationResult：利润率常态化结果
- RegressionResult：大宗商品价格与利润率回归结果
- CyclicalNormalizer：历史平均常态化 + 商品价格回归常态化
"""




# ---------------------------------------------------------------------------
# 常态化结果
# Normalization Result
# ---------------------------------------------------------------------------

@dataclass
class NormalizationResult:
    """
    周期性利润率常态化结果
    Cyclical margin normalization result.

    Fields
    ------
    normalized_margin            建议用于DCF的常态化利润率（0-1）
    raw_average_margin           历史期间简单平均利润率
    trimmed_average_margin       修剪均值（去掉最高和最低各一个数据点后的均值）
    current_margin               当前实际利润率
    current_vs_normalized_pct    当前利润率相对常态化值的偏差（%）
    commodity_regression_margin  大宗商品价格回归得出的常态化利润率（可选）
    margin_history               历史利润率序列
    """

    normalized_margin: float               # 建议用于DCF的常态化利润率
    raw_average_margin: float              # 简单历史均值
    trimmed_average_margin: float          # 修剪均值
    current_margin: float                  # 当前利润率
    current_vs_normalized_pct: float       # 偏差（%）
    commodity_regression_margin: Optional[float]  # 回归常态化值（可选）
    margin_history: list[float]
    summary: str
    warnings: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    details: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# 大宗商品回归结果
# Commodity Regression Result
# ---------------------------------------------------------------------------

@dataclass
class RegressionResult:
    """
    大宗商品价格与利润率OLS回归结果
    OLS regression result: commodity price → operating margin.

    Fields
    ------
    slope                        回归斜率（Δ利润率/Δ商品价格）
    intercept                    截距
    r_squared                    拟合优度R²（0-1）
    at_current_commodity_price   当前商品价格对应的预测利润率
    commodity_price_percentile   当前商品价格在历史分布中的百分位（0-100）
    """

    slope: float
    intercept: float
    r_squared: float
    at_current_commodity_price: float     # 当前商品价格下的预测利润率
    commodity_price_percentile: float     # 当前价格的历史百分位（0-100）
    summary: str
    details: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# 周期性利润率常态化引擎
# Cyclical Normalizer
# ---------------------------------------------------------------------------

class CyclicalNormalizer:
    """
    周期股利润率常态化引擎
    Cyclical Stock Margin Normalization Engine

    方法一：历史平均常态化
    - 取最近 lookback_years 年的利润率历史
    - 计算简单均值和修剪均值（去头去尾）
    - 若当前利润率 > 常态化值 × 1.5 → 警告（可能处于周期高点）

    方法二：大宗商品价格回归常态化
    - OLS回归：利润率 = a + b × 商品价格
    - 将当前商品价格代入预测常态化利润率
    - 用商品价格百分位判断当前处于周期的哪个位置
    """

    def normalize_by_historical_average(
        self,
        *,
        margins_history: list[float],
        lookback_years: int = 7,
        current_margin: Optional[float] = None,
    ) -> NormalizationResult:
        """
        用历史平均法常态化利润率。

        Parameters
        ----------
        margins_history   历史利润率序列（0-1，从早到晚排列）
        lookback_years    回溯年数（默认7年）
        current_margin    当前利润率（若不提供则使用最新历史值）

        Returns
        -------
        NormalizationResult
        """
        warnings: list[str] = []
        recommendations: list[str] = []

        if not margins_history:
            return NormalizationResult(
                normalized_margin=0.0,
                raw_average_margin=0.0,
                trimmed_average_margin=0.0,
                current_margin=0.0,
                current_vs_normalized_pct=0.0,
                commodity_regression_margin=None,
                margin_history=[],
                summary="历史数据为空，无法执行常态化。",
                warnings=["margins_history 为空列表，无法执行常态化计算。"],
            )

        # 取最近 lookback_years 年
        effective_history = margins_history[-lookback_years:]
        n = len(effective_history)

        # 简单均值
        raw_avg = sum(effective_history) / n

        # 修剪均值（去掉最高和最低各一个，至少需要3个数据点）
        if n >= 3:
            sorted_h = sorted(effective_history)
            trimmed = sorted_h[1:-1]
            trimmed_avg = sum(trimmed) / len(trimmed)
        else:
            trimmed_avg = raw_avg

        # 当前利润率
        curr = current_margin if current_margin is not None else effective_history[-1]

        # 计算与常态化值的偏差
        normalized = trimmed_avg
        if normalized != 0:
            deviation_pct = (curr - normalized) / abs(normalized) * 100
        else:
            deviation_pct = 0.0

        # 警告：当前利润率远高于常态化值（周期高点信号）
        if curr > normalized * 1.5 and normalized > 0:
            warnings.append(
                f"⚠️ 当前利润率 {curr:.1%} 是常态化均值 {normalized:.1%} 的 "
                f"{curr/normalized:.1f} 倍（>1.5倍），"
                "高度疑似周期高点！若用当前利润率做DCF将严重高估终值。"
            )
            recommendations.append(
                f"建议用常态化利润率 {normalized:.1%} 替代当前利润率 {curr:.1%} 做DCF，"
                f"可避免 {(curr - normalized)/normalized:.0%} 的终值高估偏差。"
                "参考Damodaran对资源/化工/新能源制造行业的常态化处理原则。"
            )
        elif curr < normalized * 0.5 and normalized > 0:
            warnings.append(
                f"当前利润率 {curr:.1%} 仅为常态化均值 {normalized:.1%} 的 "
                f"{curr/normalized:.1f} 倍（<0.5倍），"
                "可能处于周期低谷，若为周期低点投资则具备较好的安全边际。"
            )
            recommendations.append(
                f"若处于周期底部布局，建议用常态化利润率 {normalized:.1%} 做DCF，"
                "当前低利润率是暂时性的，不代表企业真实盈利能力。"
            )

        # 数据完整性检验
        if n < lookback_years:
            warnings.append(
                f"历史数据仅有{n}年（要求{lookback_years}年），"
                "常态化结果的统计显著性可能不足，建议补充更长历史数据。"
            )

        summary = (
            f"常态化利润率: {normalized:.2%} | "
            f"当前利润率: {curr:.2%} | "
            f"偏差: {deviation_pct:+.1f}% | "
            f"简单均值: {raw_avg:.2%} | "
            f"修剪均值: {trimmed_avg:.2%} | "
            f"基于{n}年历史"
        )

        return NormalizationResult(
            normalized_margin=round(normalized, 6),
            raw_average_margin=round(raw_avg, 6),
            trimmed_average_margin=round(trimmed_avg, 6),
            current_margin=round(curr, 6),
            current_vs_normalized_pct=round(deviation_pct, 2),
            commodity_regression_margin=None,
            margin_history=list(effective_history),
            summary=summary,
            warnings=warnings,
            recommendations=recommendations,
            details={
                "lookback_years": lookback_years,
                "n_data_points": n,
                "sorted_history": sorted(effective_history),
                "min_margin": min(effective_history),
                "max_margin": max(effective_history),
            },
        )

    def regress_margin_to_commodity(
        self,
        *,
        margins: list[float],
        commodity_prices: list[float],
        current_commodity_price: float,
    ) -> RegressionResult:
        """
        用OLS回归分析商品价格与利润率的关系，预测常态化利润率。

        Parameters
        ----------
        margins                   历史利润率序列（0-1）
        commodity_prices          对应的历史商品价格序列（同等长度）
        current_commodity_price   当前商品价格

        Returns
        -------
        RegressionResult

        算法（OLS）
        -----------
        β = Σ(x-x̄)(y-ȳ) / Σ(x-x̄)²
        α = ȳ - β×x̄
        R² = 1 - SS_res / SS_tot
        预测: ŷ = α + β × current_commodity_price
        百分位: percentile = (当前价格 < 历史价格的比例) × 100
        """
        if len(margins) != len(commodity_prices) or len(margins) < 2:
            default_margin = sum(margins) / len(margins) if len(margins) > 0 else 0.0
            return RegressionResult(
                slope=0.0,
                intercept=default_margin,
                r_squared=0.0,
                at_current_commodity_price=default_margin,
                commodity_price_percentile=50.0,
                summary="数据不足，无法执行OLS回归（需要至少2个配对数据点且长度相同）。",
            )

        n = len(margins)
        x_bar = sum(commodity_prices) / n
        y_bar = sum(margins) / n

        # OLS 斜率
        numerator = sum((commodity_prices[i] - x_bar) * (margins[i] - y_bar) for i in range(n))
        denominator = sum((commodity_prices[i] - x_bar) ** 2 for i in range(n))

        if abs(denominator) < 1e-12:
            slope = 0.0
            intercept = y_bar
        else:
            slope = numerator / denominator
            intercept = y_bar - slope * x_bar

        # 拟合优度 R²
        y_pred = [intercept + slope * x for x in commodity_prices]
        ss_res = sum((margins[i] - y_pred[i]) ** 2 for i in range(n))
        ss_tot = sum((margins[i] - y_bar) ** 2 for i in range(n))
        r_squared = 1.0 - ss_res / ss_tot if ss_tot > 1e-12 else 0.0

        # 当前商品价格下的预测利润率
        at_current = intercept + slope * current_commodity_price

        # 当前价格百分位（直接计数法）
        below_count = sum(1 for p in commodity_prices if p < current_commodity_price)
        commodity_price_percentile = below_count / n * 100

        # 结果分析
        if commodity_price_percentile > 80:
            price_position = "历史高位（>P80），利润率可能受益于高商品价格，需常态化"
        elif commodity_price_percentile < 20:
            price_position = "历史低位（<P20），当前利润率可能被压制，长期可能改善"
        else:
            price_position = f"历史中等位置（P{commodity_price_percentile:.0f}）"

        summary = (
            f"OLS回归: 利润率 = {intercept:.4f} + {slope:.6f} × 商品价格 | "
            f"R²={r_squared:.3f} | "
            f"当前商品价格({current_commodity_price:.2f})对应利润率预测={at_current:.2%} | "
            f"当前价格处于历史{price_position}"
        )

        return RegressionResult(
            slope=round(slope, 8),
            intercept=round(intercept, 6),
            r_squared=round(r_squared, 4),
            at_current_commodity_price=round(at_current, 6),
            commodity_price_percentile=round(commodity_price_percentile, 1),
            summary=summary,
            details={
                "n_data_points": n,
                "x_bar": round(x_bar, 4),
                "y_bar": round(y_bar, 4),
                "ss_tot": round(ss_tot, 6),
                "ss_res": round(ss_res, 6),
                "price_position_label": price_position,
            },
        )
