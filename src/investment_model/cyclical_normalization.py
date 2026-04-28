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

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional


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
