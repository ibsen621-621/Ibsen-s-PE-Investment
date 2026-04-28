"""
概率估值与扩张期权模块
Probabilistic Valuation & Expansion Options Module

对应达莫达兰工具二：拥抱不确定性的概率估值法
一级市场融合点：用蒙特卡洛替代Bull/Base/Bear三情景，用期权定价"想象空间"

核心洞见：
- 传统三情景分析（悲观/基准/乐观）本质是在骗自己：三个点不构成分布
- 真正的不确定性需要用概率分布描述，蒙特卡洛才是正确工具
- 早期项目的"想象空间"是一个实值期权，而非CFO Excel里多乘的一个倍数
- Black-Scholes用于扩张期权时，底层资产=新业务NPV，行权价=进入新市场的资本支出

模块组成：
- ExpansionOptionValuer：Black-Scholes扩张期权估值（stdlib math实现N(x)近似）
- ValuationDistribution：蒙特卡洛DCF估值分布（10,000次模拟，可重现）
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Optional

from .simulation import LognormalParam, NormalParam


# ---------------------------------------------------------------------------
# 扩张期权估值 — Black-Scholes Call
# Expansion Option Valuation — Black-Scholes Call
# ---------------------------------------------------------------------------

@dataclass
class ExpansionOptionResult:
    """
    扩张期权估值结果
    Expansion option valuation result using Black-Scholes.

    Fields
    ------
    option_value_rmb    期权价值（亿元，已按存活概率调整）
    intrinsic_value_rmb 内在价值（当前价值超出行权价部分）
    time_value_rmb      时间价值（= option_value - intrinsic_value）
    d1, d2              Black-Scholes d1/d2 参数
    """

    option_value_rmb: float       # 期权价值（亿元）
    intrinsic_value_rmb: float    # 内在价值（亿元）
    time_value_rmb: float         # 时间价值（亿元）
    d1: float
    d2: float
    summary: str
    warnings: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    details: dict = field(default_factory=dict)


class ExpansionOptionValuer:
    """
    扩张期权定价引擎（Black-Scholes调用期权）
    Expansion Option Pricing Engine using Black-Scholes Call Formula

    应用场景：
    - 企业已有核心业务（底层资产），未来有机会扩张至新市场（行权）
    - 底层资产价值 = 新业务/新市场在当前时点的NPV估计
    - 行权价格 = 进入新市场所需的资本支出（工厂/研发/牌照等）
    - 有效期 = 可以延迟决策的最长时间窗口（竞争格局变化前）
    - 波动率 = 底层资产NPV的年化波动率

    方法：
    使用 math.erfc 近似正态分布 CDF N(x) ≈ erfc(-x/√2)/2
    这是 stdlib-only 的精确近似，误差约 1e-7。
    """

    @staticmethod
    def _norm_cdf(x: float) -> float:
        """标准正态分布累积分布函数近似 N(x)，使用 erfc。"""
        return math.erfc(-x / math.sqrt(2)) / 2

    def value(
        self,
        underlying_value_rmb: float,
        exercise_cost_rmb: float,
        time_to_expiry_years: float,
        volatility: float,
        risk_free_rate: float,
        probability_of_viability: float = 1.0,
    ) -> ExpansionOptionResult:
        """
        计算扩张期权价值。

        Parameters
        ----------
        underlying_value_rmb      底层资产当前价值（亿元），即新业务NPV
        exercise_cost_rmb         行权成本（亿元），即进入新市场的资本支出
        time_to_expiry_years      期权有效期（年）
        volatility                底层资产年化波动率（0-1，例如 0.40 代表 40%）
        risk_free_rate            无风险利率（0-1，例如 0.03 代表 3%）
        probability_of_viability  业务存活/可行概率（0-1，用于调整期权价值）

        Returns
        -------
        ExpansionOptionResult
        """
        warnings: list[str] = []
        recommendations: list[str] = []

        S = underlying_value_rmb
        K = exercise_cost_rmb
        T = time_to_expiry_years
        sigma = volatility
        r = risk_free_rate

        # 参数合理性检验
        if T <= 0:
            warnings.append("期权有效期 ≤ 0，期权价值为0。")
            return ExpansionOptionResult(
                option_value_rmb=0.0,
                intrinsic_value_rmb=max(0.0, S - K),
                time_value_rmb=0.0,
                d1=0.0, d2=0.0,
                summary="有效期为零，期权无价值。",
                warnings=warnings,
            )

        # 计算 d1/d2 及 bs_call
        if sigma > 0 and S > 0 and K > 0:
            sqrt_T = math.sqrt(T)
            d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * sqrt_T)
            d2 = d1 - sigma * sqrt_T
            bs_call = S * self._norm_cdf(d1) - K * math.exp(-r * T) * self._norm_cdf(d2)
        else:
            warnings.append("波动率 ≤ 0 或底层参数无效，退化为确定性情形。")
            d1, d2 = 0.0, 0.0
            bs_call = max(0.0, S - K * math.exp(-r * T))

        bs_call = max(0.0, bs_call)

        # 按存活概率调整
        option_value = probability_of_viability * bs_call
        intrinsic_value = max(0.0, S - K)
        time_value = option_value - intrinsic_value

        if probability_of_viability < 0.5:
            warnings.append(
                f"存活概率仅 {probability_of_viability:.0%}，"
                "期权价值已大幅折减，建议优先提升核心业务存活率而非依赖期权想象空间。"
            )

        if volatility > 0.8:
            warnings.append(
                f"波动率 {volatility:.0%} 极高，期权定价对波动率假设高度敏感，"
                "请对 ±20% 波动率区间做敏感性分析。"
            )

        if intrinsic_value > 0:
            recommendations.append(
                f"期权已处于实值状态（内在价值 {intrinsic_value:.2f}亿），"
                "建议评估是否提前行权锁定收益，并对冲底层资产波动风险。"
            )

        summary = (
            f"扩张期权价值: {option_value:.2f}亿元 | "
            f"内在价值: {intrinsic_value:.2f}亿 | "
            f"时间价值: {time_value:.2f}亿 | "
            f"d1={d1:.4f} d2={d2:.4f} | "
            f"存活概率调整: {probability_of_viability:.0%}"
        )

        return ExpansionOptionResult(
            option_value_rmb=round(option_value, 4),
            intrinsic_value_rmb=round(intrinsic_value, 4),
            time_value_rmb=round(time_value, 4),
            d1=round(d1, 6),
            d2=round(d2, 6),
            summary=summary,
            warnings=warnings,
            recommendations=recommendations,
            details={
                "S": S, "K": K, "T": T, "sigma": sigma,
                "r": r, "bs_call_raw": round(bs_call, 4),
                "probability_of_viability": probability_of_viability,
            },
        )


# ---------------------------------------------------------------------------
# 蒙特卡洛估值分布
# Monte Carlo Valuation Distribution
# ---------------------------------------------------------------------------

@dataclass
class ValuationDistributionResult:
    """
    蒙特卡洛估值分布结果
    Monte Carlo valuation distribution result.

    Fields
    ------
    p10, p25, median, p75, p90   分位数估值（亿元）
    mean                         均值估值（亿元）
    std_dev                      标准差（亿元）
    is_overpriced_at_p90         若当前要价 > P90估值 → True（即使最乐观情景也贵）
    given_price_percentile       当前要价所处分位数（0-100）
    histogram_ascii              ASCII直方图（10个桶）
    n_simulations                模拟次数
    """

    p10: float
    p25: float
    median: float
    p75: float
    p90: float
    mean: float
    std_dev: float
    is_overpriced_at_p90: bool
    given_price_percentile: float
    histogram_ascii: str
    n_simulations: int
    summary: str
    warnings: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    details: dict = field(default_factory=dict)


class ValuationDistribution:
    """
    蒙特卡洛DCF估值分布模拟器
    Monte Carlo DCF Valuation Distribution Simulator

    核心逻辑
    --------
    每次模拟从TAM、利润率、S2C、存活概率四个维度分别采样，
    用Gordon Growth模型快速估算单点DCF终值，然后折现至当前时点，
    最终形成10,000次估值的完整分布。

    与三情景分析的本质区别：
    - 三情景：3个点，给人"悲观/基准/乐观"的假精确感
    - 蒙特卡洛：完整分布，诚实描述不确定性，P10-P90才是真正的"估值区间"
    """

    def simulate(
        self,
        *,
        tam_param: LognormalParam,
        margin_param: NormalParam,
        sales_to_capital_param: NormalParam,
        survival_prob: float,
        years_to_terminal: int,
        discount_rate: float,
        terminal_growth_rate: float = 0.03,
        n_simulations: int = 10_000,
        given_price_rmb: Optional[float] = None,
        seed: int = 42,
    ) -> ValuationDistributionResult:
        """
        运行蒙特卡洛估值分布模拟。

        Parameters
        ----------
        tam_param              TAM（亿元）的对数正态分布参数
        margin_param           终局EBIT利润率的正态分布参数（0-1）
        sales_to_capital_param S2C比率的正态分布参数
        survival_prob          公司存活概率（0-1），以此概率权重决定是否计入终值
        years_to_terminal      达到终局的年数
        discount_rate          折现率（0-1）
        terminal_growth_rate   永续增长率（默认 3%）
        n_simulations          模拟次数（默认 10,000）
        given_price_rmb        当前要价（亿元），用于计算所处分位（可选）
        seed                   随机种子（保证可重现）
        """
        warnings: list[str] = []
        recommendations: list[str] = []
        rng = random.Random(seed)
        r = discount_rate
        g = terminal_growth_rate
        n = years_to_terminal

        results: list[float] = []
        for _ in range(n_simulations):
            # 采样
            tam = tam_param.sample(rng)
            margin = margin_param.sample(rng)
            s2c = max(0.1, sales_to_capital_param.sample(rng))

            # 存活概率决定是否归零
            survived = rng.random() < survival_prob

            if not survived:
                results.append(0.0)
                continue

            # 简化DCF：假设市占率15%（可通过参数化扩展）
            terminal_revenue = tam * 0.15
            terminal_ebit = terminal_revenue * max(0.0, margin)
            tax_rate = 0.25
            terminal_fcf = terminal_ebit * (1 - tax_rate) - terminal_revenue * g / s2c

            if r <= g or terminal_fcf <= 0:
                results.append(0.0)
                continue

            terminal_value = terminal_fcf * (1 + g) / (r - g)
            pv = terminal_value / ((1 + r) ** n)
            results.append(max(0.0, pv))

        # 统计
        sorted_r = sorted(results)
        n_total = len(sorted_r)

        def pct(p: float) -> float:
            idx = max(0, min(n_total - 1, int(p * n_total)))
            return sorted_r[idx]

        p10 = pct(0.10)
        p25 = pct(0.25)
        median = pct(0.50)
        p75 = pct(0.75)
        p90 = pct(0.90)
        mean_val = sum(results) / n_total
        variance = sum((x - mean_val) ** 2 for x in results) / n_total
        std_dev = math.sqrt(variance)

        # 当前要价分位
        given_price_percentile = 0.0
        is_overpriced_at_p90 = False
        if given_price_rmb is not None:
            below_count = sum(1 for x in sorted_r if x < given_price_rmb)
            given_price_percentile = below_count / n_total * 100
            is_overpriced_at_p90 = given_price_rmb > p90

            if is_overpriced_at_p90:
                warnings.append(
                    f"⚠️ 要价 {given_price_rmb:.1f}亿元 高于P90估值 {p90:.1f}亿元，"
                    "即使最乐观情景（前10%）也无法支撑当前定价，存在严重高估风险。"
                )
            elif given_price_rmb > p75:
                warnings.append(
                    f"要价 {given_price_rmb:.1f}亿元 高于P75估值 {p75:.1f}亿元，"
                    "处于偏乐观区间，安全边际有限，建议谈判压价或要求更强的条款保护。"
                )

        if survival_prob < 0.5:
            warnings.append(
                f"存活概率 {survival_prob:.0%} 较低，超过一半模拟路径估值为零，"
                "分布严重左偏，均值被少数高价值路径拉高，中位数更具参考价值。"
            )
            recommendations.append(
                "建议以P25-P50区间作为估值基准，而非均值；"
                "高风险项目的均值估值在统计意义上具有欺骗性。"
            )

        # ASCII直方图（10桶）
        histogram_ascii = self._build_histogram(sorted_r)

        summary = (
            f"蒙特卡洛估值分布 ({n_simulations:,}次) | "
            f"P10={p10:.1f} P25={p25:.1f} 中位={median:.1f} "
            f"P75={p75:.1f} P90={p90:.1f}（亿元）| "
            f"均值={mean_val:.1f} σ={std_dev:.1f}"
        )
        if given_price_rmb is not None:
            summary += f" | 要价分位: {given_price_percentile:.1f}%"

        return ValuationDistributionResult(
            p10=round(p10, 2),
            p25=round(p25, 2),
            median=round(median, 2),
            p75=round(p75, 2),
            p90=round(p90, 2),
            mean=round(mean_val, 2),
            std_dev=round(std_dev, 2),
            is_overpriced_at_p90=is_overpriced_at_p90,
            given_price_percentile=round(given_price_percentile, 2),
            histogram_ascii=histogram_ascii,
            n_simulations=n_simulations,
            summary=summary,
            warnings=warnings,
            recommendations=recommendations,
            details={
                "seed": seed,
                "survival_prob": survival_prob,
                "discount_rate": discount_rate,
                "terminal_growth_rate": terminal_growth_rate,
                "years_to_terminal": years_to_terminal,
            },
        )

    @staticmethod
    def _build_histogram(sorted_values: list[float], n_buckets: int = 10, max_bar_width: int = 20) -> str:
        """
        生成ASCII直方图（10个桶，█字符）。
        Build ASCII histogram with █ characters.
        """
        if not sorted_values:
            return "(无数据)"

        min_v = sorted_values[0]
        max_v = sorted_values[-1]
        if max_v <= min_v:
            return f"所有值均为 {min_v:.2f}（无分布）"

        bucket_width = (max_v - min_v) / n_buckets
        counts = [0] * n_buckets
        for v in sorted_values:
            idx = min(int((v - min_v) / bucket_width), n_buckets - 1)
            counts[idx] += 1

        max_count = max(counts) if counts else 1
        lines = ["估值分布直方图（亿元）:", "─" * 40]
        for i, count in enumerate(counts):
            lo = min_v + i * bucket_width
            hi = lo + bucket_width
            bar_len = int(count / max_count * max_bar_width)
            bar = "█" * bar_len
            pct_str = f"{count / len(sorted_values) * 100:4.1f}%"
            lines.append(f"[{lo:6.1f}-{hi:6.1f}] {bar:<{max_bar_width}} {pct_str}")
        lines.append("─" * 40)
        return "\n".join(lines)
