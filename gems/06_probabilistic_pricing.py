# ==== GEMS FILE: 06_probabilistic_pricing.py ====
# Merged from: probabilistic_valuation.py, pricing_deconstructor.py
# For Gemini Gems knowledge base — v4.0
# NOTE: This is a knowledge reference file, not executable production code.
#       Cross-module imports have been annotated for clarity.

from __future__ import annotations
import math
import random
from dataclasses import dataclass, field
from typing import Optional
from typing import Dict, List, Optional


# ==== ORIGIN: probabilistic_valuation.py ====
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



# NOTE: LognormalParam and NormalParam are defined in gems/03_simulation_curves_cashflow.py (from simulation.py)
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


# ==== ORIGIN: pricing_deconstructor.py ====
"""
定价体操拆解模块
Pricing Gymnastics Deconstructor Module

对应达莫达兰工具三：识破投行相对定价的防身术
一级市场融合点：FA话术解码、对标池完整性检验、乘数跨期操纵识别

核心洞见：
- 相对定价（乘数法）本身不是估值，是"定价"——本质上是跟同类资产比较谁贵谁便宜
- 投行FA最擅长的五种"定价体操"：
  1. 用未来年份收入（E）锚定低乘数，忽视当前高乘数的畸形
  2. 对标池只选高增长标杆，剔除行业中位数
  3. 不同年份乘数混搭（TTM vs 2026E），制造伪对比
  4. 以未实现的"协同效应"单独估值
  5. 用DAU/GMV等非盈利指标绕开盈利能力检验
- 本模块量化检测上述操纵，提供反向尽调清单

模块组成：
- Comp：可比公司数据类
- PricingGymnasticsDetector：检测定价操纵的五种模式，生成FA话术解码表
"""




# ---------------------------------------------------------------------------
# 可比公司数据类
# Comparable Company Data Class
# ---------------------------------------------------------------------------

@dataclass
class Comp:
    """
    可比公司数据
    Comparable company data point.

    Fields
    ------
    name               公司名称
    ev_sales_multiple  EV/Sales 乘数
    reference_year     乘数对应年份（"TTM" / "2024E" / "2025E" 等）
    sector             所属行业/子赛道
    is_growth_stock    是否为高增长股票（若非，则不宜与高增长标的对比）
    """

    name: str
    ev_sales_multiple: float
    reference_year: str               # "TTM" / "2024E" / "2025E" etc.
    sector: str = ""
    is_growth_stock: bool = True


# ---------------------------------------------------------------------------
# 输出数据类
# Output Data Class
# ---------------------------------------------------------------------------

@dataclass
class PricingDeconstructionResult:
    """
    定价体操拆解结果
    Pricing gymnastics deconstruction result.

    Fields
    ------
    red_flags                    检测到的红旗列表
    fa_decoder_table             FA话术 → 真实含义 → 反制动作 对照表
    implied_current_multiple     基于当前收入的隐含乘数（EV/当前Revenue）
    comp_pool_std_over_mean      对标池乘数离散度（标准差/均值）
    cherry_pick_detected         是否检测到樱桃采摘（对标池选择性偏差）
    cross_period_mismatch        是否存在跨期乘数混搭（TTM vs Forward混用）
    multiple_compression_detected 是否检测到乘数压缩操纵（当前高乘数被未来低乘数掩盖）
    missing_anchor_count         对标池中缺少的低估值锚数量
    """

    red_flags: list[str]
    fa_decoder_table: list[dict]         # FA话术解码表
    implied_current_multiple: float      # 当前隐含EV/Sales
    comp_pool_std_over_mean: float       # 对标池离散度
    cherry_pick_detected: bool
    cross_period_mismatch: bool
    multiple_compression_detected: bool
    missing_anchor_count: int
    summary: str
    warnings: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    details: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# 定价体操检测引擎
# Pricing Gymnastics Detection Engine
# ---------------------------------------------------------------------------

class PricingGymnasticsDetector:
    """
    定价体操检测引擎
    Pricing Gymnastics Detection Engine

    检测逻辑概述：
    1. 跨期混搭（Cross-Period Mismatch）：
       - 若目标公司用 Forward Revenue 计算乘数，但可比公司用 TTM → 系统性低估目标乘数
    2. 樱桃采摘（Cherry-Picking）：
       - 对标池乘数标准差/均值 > 0.5 → 分散度过高，说明对标不同质
       - 对标池中 < claimed_multiple/2 的公司数量 → 缺失的低估值锚
    3. 乘数压缩操纵（Multiple Compression）：
       - 当前隐含乘数 > 30 但宣称乘数 < 5 → 用远期乘数掩盖当前畸形估值
    4. 生成 FA 话术解码表（至少5条），覆盖一级市场常见套路
    """

    # 常见FA话术解码表（固定知识库）
    FA_DECODER_KNOWLEDGE_BASE: list[dict] = [
        {
            "fa_claim": "参照可比公司2025E EV/Sales 3x，本项目估值合理",
            "real_meaning": "2025E乘数掩盖了当前可能高达20-30x的TTM乘数；"
                            "Forward估值依赖未来Revenue兑现，一旦增速低于预期，乘数立即回归高位",
            "counter_action": "要求同时披露基于当前TTM Revenue的EV/Sales，并做乘数压缩敏感性分析",
        },
        {
            "fa_claim": "对标Palantir/Snowflake等头部SaaS，给予高溢价",
            "real_meaning": "选取了行业top 5%的公司作为对标，忽略了90%的中位数公司；"
                            "头部溢价不适用于尚未穿越PMF的早期项目",
            "counter_action": "要求FA提供完整的行业可比公司池（含中位数），剔除市值>100亿美元的头部公司",
        },
        {
            "fa_claim": "本项目年增速200%，享受增长溢价",
            "real_meaning": "高增速从极低基数出发，Rule of 40测试（增速+利润率）往往不达标；"
                            "早期高增速持续性存疑，需要验证同期对标公司是否有类似增速",
            "counter_action": "要求提供Rule of 40评分、NRR（净收入留存率）以及增速衰减曲线",
        },
        {
            "fa_claim": "并购协同效应另行估值，不计入基础估值",
            "real_meaning": "协同效应高度不确定，研究表明超过70%的并购未能实现预期协同；"
                            "单独为不确定性付溢价是对买方不利的定价",
            "counter_action": "拒绝为协同效应单独付费，要求将协同效应纳入DCF敏感性分析而非单独乘数",
        },
        {
            "fa_claim": "参照GMV/DAU/MAU等运营指标估值，EV/GMV仅0.3x",
            "real_meaning": "非盈利指标估值绕开了Profitability检验；"
                            "GMV变现率和货币化路径的不确定性被定价忽视",
            "counter_action": "坚持使用Revenue-based乘数，要求提供从GMV到Revenue的变现率路径及时间表",
        },
        {
            "fa_claim": "本轮由知名机构领投，估值已经过市场验证",
            "real_meaning": "机构领投不等于估值合理——机构也会追风口犯错；"
                            "需独立核查机构是否做了真正的基本面分析，还是仅在跟风",
            "counter_action": "要求查阅领投机构的投资备忘录摘要，或直接与其GP沟通投资逻辑",
        },
        {
            "fa_claim": "海外同类公司估值是我们的5倍，中国折价后仍有3倍空间",
            "real_meaning": "中外市场结构差异巨大（监管/货币/退出渠道），"
                            "直接套用海外乘数是错误的跨市场比较；A股/港股估值体系与纳斯达克存在结构性差异",
            "counter_action": "要求使用同一市场（A股/港股）的可比公司，对海外对标打30-50%市场折扣",
        },
    ]

    def detect(
        self,
        *,
        comp_pool: list[Comp],
        current_revenue_rmb: float,
        forward_revenue_rmb: float,
        forward_year: str,
        claimed_multiple: float,
        current_ev_rmb: float,
    ) -> PricingDeconstructionResult:
        """
        检测定价体操并生成完整分析报告。

        Parameters
        ----------
        comp_pool             可比公司池
        current_revenue_rmb   目标公司当前收入（亿元，TTM）
        forward_revenue_rmb   目标公司Forward收入（亿元）
        forward_year          Forward收入对应年份（例如 "2025E"）
        claimed_multiple      FA/投行宣称的EV/Sales乘数
        current_ev_rmb        当前企业价值（亿元）

        Returns
        -------
        PricingDeconstructionResult
        """
        warnings: list[str] = []
        recommendations: list[str] = []
        red_flags: list[str] = []

        # --- 1. 计算当前隐含乘数 ---
        if current_revenue_rmb > 0:
            implied_current_multiple = current_ev_rmb / current_revenue_rmb
        else:
            implied_current_multiple = 0.0
            warnings.append("当前收入为零，无法计算TTM EV/Sales乘数。")

        # --- 2. 检测跨期乘数混搭 ---
        comp_reference_years = {c.reference_year for c in comp_pool}
        target_uses_forward = bool(forward_year) and forward_year.upper() != "TTM"
        comps_use_ttm = "TTM" in comp_reference_years
        cross_period_mismatch = target_uses_forward and comps_use_ttm and len(comp_pool) > 0

        if cross_period_mismatch:
            red_flags.append(
                f"⚠️ 跨期乘数混搭：目标公司使用 {forward_year} Forward Revenue，"
                "但部分可比公司使用 TTM，造成系统性低估目标公司乘数的假象。"
            )
            recommendations.append(
                "要求FA统一使用TTM Revenue计算所有可比公司和目标公司的乘数，"
                "消除跨期比较的偏差。"
            )

        # --- 3. 对标池离散度检验（樱桃采摘）---
        multiples = [c.ev_sales_multiple for c in comp_pool]
        if len(multiples) >= 2:
            mean_m = sum(multiples) / len(multiples)
            variance_m = sum((m - mean_m) ** 2 for m in multiples) / len(multiples)
            std_m = math.sqrt(variance_m)
            comp_pool_std_over_mean = std_m / mean_m if mean_m > 0 else 0.0
        else:
            mean_m = multiples[0] if multiples else 0.0
            comp_pool_std_over_mean = 0.0

        cherry_pick_detected = comp_pool_std_over_mean > 0.5
        if cherry_pick_detected:
            red_flags.append(
                f"⚠️ 对标池离散度过高（标准差/均值={comp_pool_std_over_mean:.2f} > 0.5）："
                "可比公司之间估值分散度大，说明对标公司不同质，存在选择性偏差。"
            )
            recommendations.append(
                "要求FA缩小对标池范围，仅保留商业模式、收入规模（±50%）和增速高度相似的公司，"
                "确保对标池同质性。"
            )

        # 缺失低估值锚数量
        low_threshold = claimed_multiple / 2.0
        missing_anchor_count = sum(
            1 for c in comp_pool if c.ev_sales_multiple < low_threshold
        )
        total_below_claimed = sum(
            1 for c in comp_pool if c.ev_sales_multiple < claimed_multiple
        )
        if total_below_claimed == 0 and len(comp_pool) > 0:
            red_flags.append(
                f"⚠️ 所有可比公司乘数均高于宣称乘数 {claimed_multiple:.1f}x，"
                "对标池只选了估值更高的公司，形成向上偏差。"
            )

        # --- 4. 乘数压缩操纵检测 ---
        multiple_compression_detected = (
            implied_current_multiple > 30 and claimed_multiple < 5
        )
        if multiple_compression_detected:
            red_flags.append(
                f"🚨 乘数压缩操纵：当前TTM EV/Sales={implied_current_multiple:.1f}x，"
                f"但宣称乘数仅 {claimed_multiple:.1f}x（基于远期收入）。"
                "用远期乘数掩盖当前高估，若增速未达预期将面临剧烈估值回调。"
            )
            recommendations.append(
                f"当前TTM乘数达 {implied_current_multiple:.1f}x，"
                "要求建立Revenue Bridge（当前→Forward年份），逐季验证增速可实现性，"
                "并在Term Sheet中加入估值重置条款（如未完成里程碑则触发反稀释）。"
            )

        # --- 5. 非成长股混入检测 ---
        non_growth_comps = [c.name for c in comp_pool if not c.is_growth_stock]
        if non_growth_comps:
            names_str = ", ".join(non_growth_comps)
            red_flags.append(
                f"⚠️ 对标池混入非成长股：{names_str}。"
                "非成长股的低乘数用于拉低对标池均值，制造'相对低估'假象。"
            )

        # --- 6. 生成FA话术解码表（从知识库中选取相关条目）---
        fa_decoder_table = self.FA_DECODER_KNOWLEDGE_BASE[:5]  # 展示前5条核心话术

        # --- 整合评估 ---
        n_red_flags = len(red_flags)
        if n_red_flags >= 3:
            warnings.append(
                f"检测到 {n_red_flags} 个定价操纵信号，建议拒绝当前估值框架，"
                "要求FA从头以内在价值DCF方法重新定价。"
            )
        elif n_red_flags >= 1:
            warnings.append(
                f"检测到 {n_red_flags} 个定价操纵信号，在接受当前乘数估值前，"
                "逐一核查并要求FA提供书面解释。"
            )
        else:
            recommendations.append(
                "未检测到明显定价体操信号，可比公司池质量尚可，"
                "但仍建议进行独立DCF验证以锚定内在价值地板价。"
            )

        summary = (
            f"定价体操检测: {n_red_flags}个红旗 | "
            f"当前TTM乘数={implied_current_multiple:.1f}x vs 宣称{claimed_multiple:.1f}x | "
            f"对标池离散度={comp_pool_std_over_mean:.2f} | "
            f"跨期混搭={'是' if cross_period_mismatch else '否'} | "
            f"樱桃采摘={'检测到' if cherry_pick_detected else '未检测到'}"
        )

        return PricingDeconstructionResult(
            red_flags=red_flags,
            fa_decoder_table=fa_decoder_table,
            implied_current_multiple=round(implied_current_multiple, 2),
            comp_pool_std_over_mean=round(comp_pool_std_over_mean, 4),
            cherry_pick_detected=cherry_pick_detected,
            cross_period_mismatch=cross_period_mismatch,
            multiple_compression_detected=multiple_compression_detected,
            missing_anchor_count=missing_anchor_count,
            summary=summary,
            warnings=warnings,
            recommendations=recommendations,
            details={
                "n_comps": len(comp_pool),
                "comp_multiples": multiples,
                "mean_comp_multiple": round(mean_m, 2) if multiples else 0.0,
                "implied_current_multiple": round(implied_current_multiple, 2),
                "claimed_multiple": claimed_multiple,
                "forward_year": forward_year,
                "current_revenue_rmb": current_revenue_rmb,
                "forward_revenue_rmb": forward_revenue_rmb,
            },
        )
