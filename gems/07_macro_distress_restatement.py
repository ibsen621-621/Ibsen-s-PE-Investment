# ==== GEMS FILE: 07_macro_distress_restatement.py ====
# Merged from: macro_risk.py, distress_valuation.py, financial_restatement.py
# For Gemini Gems knowledge base — v4.0
# NOTE: This is a knowledge reference file, not executable production code.
#       Cross-module imports have been annotated for clarity.

from __future__ import annotations
import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional


# ==== ORIGIN: macro_risk.py ====
"""
动态宏观风险重定价引擎
Dynamic Macro Risk Re-pricing Engine

对应达莫达兰工具四：实时隐含ERP + 主权CDS国家风险溢价
一级市场融合点：投资时点系数校准、MAC触发条件、跨境估值CRP叠加

核心洞见：
- 股权风险溢价（ERP）不是常数——它是市场情绪的实时温度计
- 当市场隐含ERP高于历史均值时，用历史ERP折现会系统性高估资产价值
- 一级市场投资决策必须用"投资时点的真实ERP"校准折现率，而非教科书上的静态数字
- 跨境投资叠加国家风险溢价（CRP）= 主权CDS利差 × 股债波动率比

模块组成：
- ImpliedERPCalculator：用 Gordon Growth Model 反推当前市场隐含ERP
- SovereignCRPAdjuster：基于主权CDS利差计算国家风险溢价（CRP）
- MacroRiskEngine：综合ERP + CRP，计算宏观调整系数，判断MAC触发条件

MAC（Material Adverse Change）触发逻辑：
当宏观调整系数（current_ERP / base_ERP）> 1.10 时，
建议重新谈判估值或推迟交割，触发Term Sheet中的MAC条款。
"""




# ---------------------------------------------------------------------------
# 主权CDS参考数据（示例，非实时，仅用于离线分析基准）
# Sovereign CDS Reference Data (sample, non-real-time)
# ---------------------------------------------------------------------------

SOVEREIGN_CDS_REFERENCE: Dict[str, float] = {
    "美国": 30,
    "中国": 65,
    "阿联酋": 80,
    "沙特": 90,
    "伊拉克": 450,
    "巴西": 180,
    "印度": 120,
    "土耳其": 320,
    "德国": 20,
    "日本": 25,
}


# ---------------------------------------------------------------------------
# 隐含ERP计算
# Implied ERP Calculation
# ---------------------------------------------------------------------------

@dataclass
class ImpliedERPResult:
    """
    市场隐含股权风险溢价计算结果
    Implied Equity Risk Premium calculation result.

    Fields
    ------
    implied_irr     市场隐含IRR（股票市场要求回报率）
    implied_erp     隐含ERP = implied_irr - risk_free_rate
    risk_free_rate  无风险利率（0-1）
    """

    implied_irr: float         # 隐含IRR（0-1）
    implied_erp: float         # 隐含ERP = implied_irr - risk_free_rate
    risk_free_rate: float      # 无风险利率（0-1）
    summary: str
    warnings: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    details: dict = field(default_factory=dict)


class ImpliedERPCalculator:
    """
    市场隐含ERP计算器（Gordon Growth Model反推法）
    Implied ERP Calculator using Gordon Growth Model Inversion

    方法说明
    --------
    Gordon Growth Model（稳态永续增长）：
        Index = CF1 / (r - g)
        → r = CF1 / Index + g

    其中：
        CF1 = Index × Dividend_Yield × (1 + g)  → 下一期预期现金流
        r   = 市场隐含IRR
        g   = 预期永续增长率
        ERP = r - risk_free_rate

    局限性：
    - GGM假设永续稳态增长，对于周期或高波动市场可能低估真实ERP
    - 实际应用中Damodaran采用5年两阶段现金流模型，这里用单阶段GGM作为快速近似
    - 建议将本结果与过去10年历史ERP均值（约4-6%）做交叉验证
    """

    def calculate(
        self,
        *,
        index_level: float,
        expected_dividend_yield_pct: float,
        expected_growth_pct: float,
        risk_free_rate_pct: float,
        max_iterations: int = 100,
        tolerance: float = 1e-6,
    ) -> ImpliedERPResult:
        """
        计算当前市场隐含ERP。

        Parameters
        ----------
        index_level                  当前指数点位（或市值代理，亿元）
        expected_dividend_yield_pct  预期股息率（%，例如 2.5 代表 2.5%）
        expected_growth_pct          预期永续增长率（%，例如 5.0 代表 5%）
        risk_free_rate_pct           无风险利率（%，例如 3.0 代表 3%）
        max_iterations               Newton-Raphson最大迭代次数（备用，此处GGM为解析解）
        tolerance                    收敛容差

        Returns
        -------
        ImpliedERPResult
        """
        warnings: list[str] = []
        recommendations: list[str] = []

        g = expected_growth_pct / 100.0
        rf = risk_free_rate_pct / 100.0
        dy = expected_dividend_yield_pct / 100.0

        # GGM反推：r = CF1/P + g
        # CF1 = P × dy × (1+g)
        cf1 = index_level * dy * (1 + g)
        implied_irr = cf1 / index_level + g  # 解析解
        implied_erp = implied_irr - rf

        # 合理性检验
        if implied_erp < 0:
            warnings.append(
                f"隐含ERP为负值（{implied_erp:.2%}），"
                "说明市场当前处于极度乐观（泡沫化）状态，"
                "股票定价已无风险溢价，极大风险信号。"
            )
        elif implied_erp < 0.02:
            warnings.append(
                f"隐含ERP仅 {implied_erp:.2%}，历史上低ERP对应市场高估，"
                "建议对所有基于CAPM的折现率上调至少100-150bp。"
            )
        elif implied_erp > 0.10:
            warnings.append(
                f"隐含ERP高达 {implied_erp:.2%}，超过历史正常区间（4-7%），"
                "市场处于恐慌/危机模式，是逆周期布局的信号窗口。"
            )

        if dy < 0.005:
            warnings.append(
                f"股息率 {dy:.2%} 极低（<0.5%），GGM对低股息市场的适用性有限，"
                "建议补充FCF Yield替代股息率重新计算。"
            )

        recommendations.append(
            f"当前隐含ERP={implied_erp:.2%}，"
            "建议将此值代入CAPM重新核算被投项目的折现率，"
            "而非使用教科书中的静态ERP假设（通常4-6%）。"
        )

        summary = (
            f"隐含IRR: {implied_irr:.2%} | "
            f"隐含ERP: {implied_erp:.2%} | "
            f"无风险利率: {rf:.2%} | "
            f"(GGM反推: CF1={cf1:.2f}, Index={index_level:.2f})"
        )

        return ImpliedERPResult(
            implied_irr=round(implied_irr, 6),
            implied_erp=round(implied_erp, 6),
            risk_free_rate=round(rf, 6),
            summary=summary,
            warnings=warnings,
            recommendations=recommendations,
            details={
                "index_level": index_level,
                "dividend_yield_pct": expected_dividend_yield_pct,
                "growth_pct": expected_growth_pct,
                "cf1": round(cf1, 4),
                "method": "GGM_single_stage",
            },
        )


# ---------------------------------------------------------------------------
# 主权国家风险溢价（CRP）
# Sovereign Country Risk Premium (CRP)
# ---------------------------------------------------------------------------

@dataclass
class SovereignCRPResult:
    """
    主权国家风险溢价计算结果
    Sovereign Country Risk Premium calculation result.

    Fields
    ------
    crp                      国家风险溢价（0-1，例如 0.025 代表 2.5%）
    country_cds_spread_bps   目标国主权CDS利差（基点）
    """

    crp: float                          # 国家风险溢价（0-1）
    country_cds_spread_bps: float       # 主权CDS利差（bps）
    summary: str
    warnings: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    details: dict = field(default_factory=dict)


class SovereignCRPAdjuster:
    """
    主权国家风险溢价调整器
    Sovereign Country Risk Premium Adjuster

    计算公式（Damodaran方法）：
        CRP = (Country_CDS - Base_CDS) / 10000 × Equity_to_Bond_Vol_Ratio

    其中：
        Country_CDS     目标国主权CDS利差（基点）
        Base_CDS        基准国（通常为美国）CDS利差（基点）
        Equity_to_Bond_Vol_Ratio  股票/债券波动率比（通常 1.5）

    应用场景：
    - 跨境投资（如中东、东南亚、拉美）必须在基础ERP之上叠加CRP
    - CRP = 额外要求的股权溢价以补偿政治风险、货币风险、法律风险
    """

    def calculate(
        self,
        *,
        country_cds_bps: float,
        base_country_cds_bps: float = 30.0,
        equity_to_bond_volatility_ratio: float = 1.5,
    ) -> SovereignCRPResult:
        """
        计算国家风险溢价（CRP）。

        Parameters
        ----------
        country_cds_bps              目标国主权CDS利差（基点）
        base_country_cds_bps         基准国CDS利差（基点，默认美国30bps）
        equity_to_bond_volatility_ratio 股票/债券波动率比（默认1.5）

        Returns
        -------
        SovereignCRPResult
        """
        warnings: list[str] = []
        recommendations: list[str] = []

        crp = (country_cds_bps - base_country_cds_bps) / 10000.0 * equity_to_bond_volatility_ratio
        crp = max(0.0, crp)  # CRP不能为负（发达国家基准国已是最低风险）

        if crp > 0.05:
            warnings.append(
                f"CRP={crp:.2%} 超过5%，目标国主权风险极高，"
                "建议要求交易结构中加入外汇对冲、政治风险保险（MIGA）或分期付款安排。"
            )
        elif crp > 0.02:
            warnings.append(
                f"CRP={crp:.2%} 属于中等主权风险，"
                "需在估值折现率中明确叠加此风险溢价，不可使用纯美元ERP做跨境估值。"
            )

        if country_cds_bps < base_country_cds_bps:
            recommendations.append(
                f"目标国CDS利差 ({country_cds_bps:.0f}bps) 低于基准国 ({base_country_cds_bps:.0f}bps)，"
                "CRP按零处理，主权风险相对较低。"
            )

        recommendations.append(
            f"将CRP={crp:.2%} 叠加至基础ERP，得到跨境投资的完整折现率调整量。"
            f"例如：若基础ERP=5%，叠加CRP后折现率应额外增加 {crp:.2%}。"
        )

        summary = (
            f"国家风险溢价(CRP): {crp:.2%} | "
            f"主权CDS: {country_cds_bps:.0f}bps | "
            f"基准CDS: {base_country_cds_bps:.0f}bps | "
            f"股债波动率比: {equity_to_bond_volatility_ratio:.1f}"
        )

        return SovereignCRPResult(
            crp=round(crp, 6),
            country_cds_spread_bps=country_cds_bps,
            summary=summary,
            warnings=warnings,
            recommendations=recommendations,
            details={
                "country_cds_bps": country_cds_bps,
                "base_country_cds_bps": base_country_cds_bps,
                "equity_to_bond_volatility_ratio": equity_to_bond_volatility_ratio,
                "formula": "CRP = (Country_CDS - Base_CDS)/10000 × Vol_Ratio",
            },
        )


# ---------------------------------------------------------------------------
# 综合宏观风险评估引擎
# Macro Risk Evaluation Engine
# ---------------------------------------------------------------------------

@dataclass
class MacroRiskResult:
    """
    综合宏观风险评估结果
    Comprehensive macro risk evaluation result.

    Fields
    ------
    erp_result          隐含ERP计算结果
    crp_result          国家风险溢价结果（可选，跨境投资适用）
    adjustment_factor   当前ERP / 基准ERP（>1表示风险溢价高于历史均值）
    mac_triggered       MAC条款触发标志（adjustment_factor > 1.10 时为True）
    """

    erp_result: ImpliedERPResult
    crp_result: Optional[SovereignCRPResult]
    adjustment_factor: float          # current_erp / base_erp
    mac_triggered: bool               # True if adjustment_factor > 1.10
    summary: str
    warnings: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    details: dict = field(default_factory=dict)


class MacroRiskEngine:
    """
    动态宏观风险重定价引擎
    Dynamic Macro Risk Re-pricing Engine

    核心功能：
    1. 基于当前市场隐含ERP与历史基准ERP的比率，计算宏观调整系数
    2. 当调整系数 > 1.10（ERP比历史高10%以上）时，触发MAC条款建议
    3. 跨境投资自动叠加CRP调整

    投资实践建议：
    - 在宏观环境恶化（ERP上升）时，坚持用更高的折现率折现，宁愿少投也不要用历史ERP高估
    - MAC触发时建议在Term Sheet中加入：估值重置条款、延迟交割选项权、利率条件锁定

    MAC = Material Adverse Change（重大不利变化条款）
    """

    MAC_THRESHOLD = 1.10   # ERP超过基准10%触发MAC

    def evaluate(
        self,
        *,
        current_erp_result: ImpliedERPResult,
        base_erp_pct: float,
        crp_result: Optional[SovereignCRPResult] = None,
    ) -> MacroRiskResult:
        """
        综合评估宏观风险并输出调整建议。

        Parameters
        ----------
        current_erp_result   当前市场隐含ERP（由ImpliedERPCalculator生成）
        base_erp_pct         历史基准ERP（%，例如 5.0 代表 5%）
        crp_result           国家风险溢价（跨境投资时传入）

        Returns
        -------
        MacroRiskResult
        """
        warnings: list[str] = []
        recommendations: list[str] = []

        base_erp = base_erp_pct / 100.0
        current_erp = current_erp_result.implied_erp

        if base_erp <= 0:
            warnings.append("基准ERP ≤ 0，无法计算调整系数，请检查输入。")
            adjustment_factor = 1.0
        else:
            adjustment_factor = current_erp / base_erp

        mac_triggered = adjustment_factor > self.MAC_THRESHOLD

        # 宏观风险信号分析
        if mac_triggered:
            warnings.append(
                f"🚨 MAC触发警告：当前隐含ERP ({current_erp:.2%}) "
                f"比历史基准 ({base_erp:.2%}) 高出 {(adjustment_factor - 1) * 100:.1f}%，"
                "超过10%的触发阈值。建议暂停或重新谈判估值，"
                "所有DCF折现率应上调以反映真实市场风险水平。"
            )
            recommendations.append(
                "MAC触发时的标准操作清单：\n"
                "  1. 重新用当前ERP替换DCF中的历史ERP，重算合理估值区间\n"
                "  2. 在Term Sheet中加入'宏观条件锁定条款'：若ERP继续上升>X%则可重议价\n"
                "  3. 缩短投资决策时间窗口，避免在高ERP环境下锁定长期价格\n"
                "  4. 优先考虑分期付款结构（Tranche），第一笔以当前估值，后续笔按届时市场价"
            )
        elif adjustment_factor > 1.0:
            warnings.append(
                f"宏观风险轻度上升：当前ERP ({current_erp:.2%}) "
                f"高于历史基准 ({base_erp:.2%})，调整系数={adjustment_factor:.3f}，"
                "建议在折现率上增加50-100bp的宏观安全垫。"
            )
        else:
            recommendations.append(
                f"宏观环境相对宽松：当前ERP ({current_erp:.2%}) "
                f"接近或低于历史基准 ({base_erp:.2%})，"
                "折现率无需额外上调，但需警惕ERP均值回归风险。"
            )

        # CRP叠加分析
        if crp_result is not None:
            total_extra_premium = current_erp + crp_result.crp
            recommendations.append(
                f"跨境投资CRP叠加：基础ERP={current_erp:.2%} + CRP={crp_result.crp:.2%} "
                f"= 总超额风险溢价={total_extra_premium:.2%}。"
                "投资跨境项目的折现率应在当地无风险利率基础上加上此总溢价。"
            )

        summary = (
            f"宏观风险调整系数: {adjustment_factor:.3f} | "
            f"当前隐含ERP: {current_erp:.2%} | "
            f"历史基准ERP: {base_erp:.2%} | "
            f"MAC触发: {'✅ 是' if mac_triggered else '否'}"
        )
        if crp_result:
            summary += f" | CRP: {crp_result.crp:.2%}"

        return MacroRiskResult(
            erp_result=current_erp_result,
            crp_result=crp_result,
            adjustment_factor=round(adjustment_factor, 6),
            mac_triggered=mac_triggered,
            summary=summary,
            warnings=warnings,
            recommendations=recommendations,
            details={
                "current_erp": current_erp,
                "base_erp": base_erp,
                "adjustment_factor": round(adjustment_factor, 6),
                "mac_threshold": self.MAC_THRESHOLD,
                "crp": crp_result.crp if crp_result else 0.0,
            },
        )


# ==== ORIGIN: distress_valuation.py ====
"""
截断/破产双轨分离估值模块
Distress & Truncation Dual-Track Valuation Module

对应达莫达兰工具五：双轨期望值模型
一级市场融合点：early-stage存活权重、债券市场隐含违约概率、清算NAV

核心洞见：
- 传统DCF隐含假设"企业永续经营"——对早期项目这是一个危险的假设
- 正确的方法是：期望价值 = P(存活) × 持续经营价值 + P(破产) × 清算价值 - 重组成本
- 破产概率可从两条路获取：
  1. 债券定价路径（Hull公式）：从公开债券YTM反推隐含违约概率
  2. Altman Z-Score：从财务比率量化破产可能性
- 对于一级市场早期项目，还需叠加"下轮融资关闭概率"对存活率做二次调整

模块组成：
- AltmanZResult：Altman Z-Score计算结果
- DistressDualTrackValuer：双轨估值核心引擎（债券路径 + Altman路径）
- DistressValuationResult：完整双轨估值结果
"""




# ---------------------------------------------------------------------------
# Altman Z-Score 结果
# Altman Z-Score Result
# ---------------------------------------------------------------------------

@dataclass
class AltmanZResult:
    """
    Altman Z-Score 破产预测结果
    Altman Z-Score bankruptcy prediction result.

    Fields
    ------
    z_score                   Z-Score 数值
    zone                      风险区间：'safe' / 'grey' / 'distress'
    implied_default_probability 隐含违约概率（0-1）
    """

    z_score: float
    zone: str                           # "safe" / "grey" / "distress"
    implied_default_probability: float  # 0-1
    summary: str


# ---------------------------------------------------------------------------
# 双轨估值结果
# Dual-Track Valuation Result
# ---------------------------------------------------------------------------

@dataclass
class DistressValuationResult:
    """
    双轨分离估值结果
    Dual-track (going concern vs. liquidation) valuation result.

    Fields
    ------
    going_concern_value_rmb         持续经营价值（亿元，通常为DCF估值）
    liquidation_nav_rmb             清算净资产价值（亿元）
    p_survival                      原始存活概率（未调整）
    p_distress                      破产概率（未调整）
    restructuring_cost_rmb          重组/破产处置成本（亿元）
    expected_deal_value_rmb         期望交易价值（亿元）
    traditional_dcf_value_rmb       传统DCF估值（未做破产调整，用于对比）
    value_discount_vs_traditional_pct 双轨法 vs 传统DCF的折价幅度（%）
    distress_method                 使用的方法："bond_pricing" 或 "altman_z"
    """

    going_concern_value_rmb: float
    liquidation_nav_rmb: float
    p_survival: float
    p_distress: float
    restructuring_cost_rmb: float
    expected_deal_value_rmb: float
    traditional_dcf_value_rmb: float
    value_discount_vs_traditional_pct: float
    distress_method: str              # "bond_pricing" or "altman_z"
    summary: str
    warnings: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    details: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# 双轨分离估值引擎
# Dual-Track Distress Valuation Engine
# ---------------------------------------------------------------------------

class DistressDualTrackValuer:
    """
    破产双轨分离估值引擎
    Distress Dual-Track Valuation Engine

    提供两条路径计算破产概率：
    1. 债券定价路径（from_bond_pricing）：
       - 使用 Newton-Raphson 从市场债券价格反推YTM
       - 用 Hull 简化公式：P_default = 1 - exp(-spread × T)
    2. Altman Z-Score路径（from_altman_z）：
       - 5因子回归模型，区分安全区/灰色区/破产区
       - 每个区间对应经验违约概率

    核心估值公式：
        adjusted_p_survival = p_survival × (0.5 + 0.5 × next_round_prob)
        expected_value = going_concern × adj_p_survival
                       + liquidation × (1 - adj_p_survival)
                       - restructuring_cost
    """

    # Newton-Raphson 求 YTM 的收敛边界
    # 下界：0.1% — 防止 YTM 趋近于零时分母溢出（零利率债券在收益率模型中无意义）
    # 上界：99%  — 防止极度折价债券的迭代发散（实际垃圾债 YTM 极少超过 80%）
    _YTM_LOWER_BOUND: float = 0.001
    _YTM_UPPER_BOUND: float = 0.99

    # ------------------------------------------------------------------
    # 路径1：债券定价反推破产概率
    # Path 1: Bond Pricing → Implied Default Probability
    # ------------------------------------------------------------------

    @staticmethod
    def from_bond_pricing(
        *,
        face_value: float,
        market_price: float,
        coupon_rate: float,
        years_to_maturity: float,
        recovery_rate: float = 0.40,
    ) -> float:
        """
        从债券市场价格反推隐含破产概率（Hull简化公式）。

        Parameters
        ----------
        face_value           债券面值（亿元）
        market_price         债券市场价格（亿元）
        coupon_rate          票面利率（0-1，例如 0.06 代表 6%）
        years_to_maturity    到期年数
        recovery_rate        回收率（默认 40%，参考Moody's历史均值）

        Returns
        -------
        float  隐含P_default（0-1）

        算法
        ----
        1. Newton-Raphson 从市场价格求 YTM
        2. 隐含信用利差 = YTM - 无风险利率（用票面利率近似<5%时）
        3. P_default = 1 - exp(-spread × T)，按回收率调整
        """
        n = max(1, int(round(years_to_maturity)))
        coupon = face_value * coupon_rate

        def bond_price(ytm: float) -> float:
            """计算给定YTM下的债券价格。"""
            if abs(ytm) < 1e-10:
                return coupon * n + face_value
            return sum(coupon / (1 + ytm) ** t for t in range(1, n + 1)) + face_value / (1 + ytm) ** n

        def bond_price_deriv(ytm: float) -> float:
            """债券价格对YTM的一阶导数（用于Newton-Raphson）。"""
            if abs(ytm) < 1e-10:
                return -sum(t * coupon for t in range(1, n + 1)) - n * face_value
            return (
                sum(-t * coupon / (1 + ytm) ** (t + 1) for t in range(1, n + 1))
                - n * face_value / (1 + ytm) ** (n + 1)
            )

        # Newton-Raphson 求 YTM，初始值为票面利率
        ytm = coupon_rate
        max_iter = 100
        tol = 1e-8
        for _ in range(max_iter):
            f = bond_price(ytm) - market_price
            df = bond_price_deriv(ytm)
            if abs(df) < 1e-12:
                break
            ytm_new = ytm - f / df
            if abs(ytm_new - ytm) < tol:
                ytm = ytm_new
                break
            ytm = ytm_new
            ytm = max(DistressDualTrackValuer._YTM_LOWER_BOUND,
                      min(ytm, DistressDualTrackValuer._YTM_UPPER_BOUND))

        # 无风险利率近似：若票面利率<5%，用票面利率；否则用3%
        risk_free_approx = coupon_rate if coupon_rate < 0.05 else 0.03
        implied_spread = max(0.0, ytm - risk_free_approx)

        # Hull公式：P_default = 1 - exp(-spread * T)，调整回收率
        # 精确版本考虑回收率：spread ≈ LGD × default_intensity
        # → default_intensity = spread / (1 - recovery_rate)
        lgd = 1 - recovery_rate
        if lgd > 0:
            default_intensity = implied_spread / lgd
        else:
            default_intensity = implied_spread

        p_default = 1.0 - math.exp(-default_intensity * years_to_maturity)
        return max(0.0, min(0.999, p_default))

    # ------------------------------------------------------------------
    # 路径2：Altman Z-Score 反推违约概率
    # Path 2: Altman Z-Score → Implied Default Probability
    # ------------------------------------------------------------------

    @staticmethod
    def from_altman_z(
        *,
        working_capital: float,
        retained_earnings: float,
        ebit: float,
        market_value_equity: float,
        sales: float,
        total_assets: float,
        total_liabilities: float,
    ) -> AltmanZResult:
        """
        Altman Z-Score 破产预测（制造业原版，适配上市公司）。

        Parameters
        ----------
        working_capital        营运资本（流动资产 - 流动负债，亿元）
        retained_earnings      留存收益（亿元）
        ebit                   息税前利润（亿元）
        market_value_equity    股权市值（亿元）
        sales                  营业收入（亿元）
        total_assets           总资产（亿元）
        total_liabilities      总负债（亿元）

        Returns
        -------
        AltmanZResult

        公式
        ----
        Z = 1.2×X1 + 1.4×X2 + 3.3×X3 + 0.6×X4 + 1.0×X5
        X1 = 营运资本/总资产
        X2 = 留存收益/总资产
        X3 = EBIT/总资产
        X4 = 股权市值/总负债
        X5 = 营业收入/总资产

        风险区间：
        Z > 2.99 → 安全区（P_default ≈ 5%）
        1.81 < Z < 2.99 → 灰色区（P_default ≈ 35%）
        Z < 1.81 → 破产区（P_default ≈ 70%）
        """
        if total_assets <= 0:
            return AltmanZResult(
                z_score=0.0,
                zone="distress",
                implied_default_probability=0.70,
                summary="总资产为零或负数，无法计算Z-Score，默认判定为破产区。",
            )

        x1 = working_capital / total_assets
        x2 = retained_earnings / total_assets
        x3 = ebit / total_assets
        x4 = market_value_equity / total_liabilities if total_liabilities > 0 else 10.0
        x5 = sales / total_assets

        z = 1.2 * x1 + 1.4 * x2 + 3.3 * x3 + 0.6 * x4 + 1.0 * x5

        if z > 2.99:
            zone = "safe"
            p_default = 0.05
            zone_desc = "安全区（Z>2.99）"
        elif z >= 1.81:
            zone = "grey"
            p_default = 0.35
            zone_desc = "灰色区（1.81≤Z≤2.99）"
        else:
            zone = "distress"
            p_default = 0.70
            zone_desc = "破产区（Z<1.81）"

        summary = (
            f"Altman Z-Score={z:.3f} | {zone_desc} | "
            f"隐含违约概率={p_default:.0%} | "
            f"X1={x1:.3f} X2={x2:.3f} X3={x3:.3f} X4={x4:.3f} X5={x5:.3f}"
        )

        return AltmanZResult(
            z_score=round(z, 4),
            zone=zone,
            implied_default_probability=p_default,
            summary=summary,
        )

    # ------------------------------------------------------------------
    # 核心估值：双轨期望价值计算
    # Core: Dual-Track Expected Value
    # ------------------------------------------------------------------

    def value(
        self,
        *,
        going_concern_dcf_rmb: float,
        liquidation_nav_rmb: float,
        p_distress: float,
        restructuring_cost_rmb: float = 0.0,
        next_round_funding_close_probability: float = 1.0,
        distress_method: str = "bond_pricing",
    ) -> DistressValuationResult:
        """
        计算双轨分离期望估值。

        Parameters
        ----------
        going_concern_dcf_rmb             持续经营DCF价值（亿元）
        liquidation_nav_rmb               清算净资产价值（亿元）
        p_distress                        破产概率（0-1，由 from_bond_pricing 或 from_altman_z 提供）
        restructuring_cost_rmb            重组/破产处置成本（亿元）
        next_round_funding_close_probability 下轮融资成功关闭概率（0-1），用于调整存活率
        distress_method                   使用的破产概率计算方法

        Returns
        -------
        DistressValuationResult

        算法
        ----
        p_survival = 1 - p_distress
        adjusted_p_survival = p_survival × (0.5 + 0.5 × next_round_prob)
        adjusted_p_distress = 1 - adjusted_p_survival
        expected_value = going_concern × adjusted_p_survival
                       + liquidation × adjusted_p_distress
                       - restructuring_cost
        """
        warnings: list[str] = []
        recommendations: list[str] = []

        p_distress = max(0.0, min(1.0, p_distress))
        p_survival = 1.0 - p_distress

        # 以下轮融资概率二次调整存活率
        adjusted_p_survival = p_survival * (0.5 + 0.5 * next_round_funding_close_probability)
        adjusted_p_distress = 1.0 - adjusted_p_survival

        expected_value = (
            going_concern_dcf_rmb * adjusted_p_survival
            + liquidation_nav_rmb * adjusted_p_distress
            - restructuring_cost_rmb
        )

        # 与传统DCF对比
        traditional_dcf = going_concern_dcf_rmb
        if traditional_dcf > 0:
            discount_pct = (traditional_dcf - expected_value) / traditional_dcf * 100
        else:
            discount_pct = 0.0

        # 风险警告
        if p_distress > 0.5:
            warnings.append(
                f"🚨 破产概率 {p_distress:.0%} 超过50%！"
                "双轨估值已大幅低于传统DCF，建议将清算价值作为主要估值参考，"
                "而非持续经营价值。"
            )
        elif p_distress > 0.3:
            warnings.append(
                f"⚠️ 破产概率 {p_distress:.0%} 处于危险区间（>30%）。"
                f"双轨估值对传统DCF折价 {discount_pct:.1f}%，"
                "建议在Term Sheet中加入优先清算权以保护下行。"
            )

        if next_round_funding_close_probability < 0.5:
            warnings.append(
                f"下轮融资关闭概率仅 {next_round_funding_close_probability:.0%}，"
                "存活率经融资不确定性调整后进一步下降，"
                f"调整后存活率={adjusted_p_survival:.0%}。"
            )

        if liquidation_nav_rmb < going_concern_dcf_rmb * 0.2:
            warnings.append(
                f"清算价值 ({liquidation_nav_rmb:.2f}亿) 仅为持续经营价值的 "
                f"{liquidation_nav_rmb/going_concern_dcf_rmb:.0%}，"
                "说明资产具有高度专用性，破产情形下价值损失极大，下行保护薄弱。"
            )
            recommendations.append(
                "清算价值过低，建议在协议中要求：优先清算权1x或以上 + 参与分配权，"
                "确保在最坏情形下的本金保护。"
            )

        recommendations.append(
            f"双轨期望价值={expected_value:.2f}亿元，较传统DCF {traditional_dcf:.2f}亿 "
            f"折价 {discount_pct:.1f}%。"
            "建议以双轨估值作为谈判定价上限，以清算价值作为绝对底线。"
        )

        summary = (
            f"双轨期望价值: {expected_value:.2f}亿元 | "
            f"传统DCF: {traditional_dcf:.2f}亿 | "
            f"折价: {discount_pct:.1f}% | "
            f"调整后存活率: {adjusted_p_survival:.0%} | "
            f"清算价值: {liquidation_nav_rmb:.2f}亿 | "
            f"方法: {distress_method}"
        )

        return DistressValuationResult(
            going_concern_value_rmb=round(going_concern_dcf_rmb, 4),
            liquidation_nav_rmb=round(liquidation_nav_rmb, 4),
            p_survival=round(p_survival, 4),
            p_distress=round(p_distress, 4),
            restructuring_cost_rmb=round(restructuring_cost_rmb, 4),
            expected_deal_value_rmb=round(expected_value, 4),
            traditional_dcf_value_rmb=round(traditional_dcf, 4),
            value_discount_vs_traditional_pct=round(discount_pct, 2),
            distress_method=distress_method,
            summary=summary,
            warnings=warnings,
            recommendations=recommendations,
            details={
                "p_distress_raw": p_distress,
                "p_survival_raw": p_survival,
                "adjusted_p_survival": round(adjusted_p_survival, 4),
                "adjusted_p_distress": round(adjusted_p_distress, 4),
                "next_round_funding_close_probability": next_round_funding_close_probability,
                "going_concern_dcf_rmb": going_concern_dcf_rmb,
                "liquidation_nav_rmb": liquidation_nav_rmb,
                "restructuring_cost_rmb": restructuring_cost_rmb,
            },
        )


# ==== ORIGIN: financial_restatement.py ====
"""
财务报表外科手术模块
Financial Statement Restatement Module

对应达莫达兰工具六：无形资产资本化
一级市场融合点：R&D资本化重构ROIC、CAC资本化还原LTV/CAC真实护城河

核心洞见：
- GAAP/IFRS要求将R&D费用化，导致知识密集型企业的ROIC被系统性低估
- 正确做法：将历史R&D支出资本化，按行业摊销年限分摊，重构真实投入资本
- CAC（客户获取成本）具有长期经济价值，应视为资产而非当期费用
- SBC（股票激励）是真实成本，不是"非现金项目"——必须从EBITDA中扣除
- 经过R&D资本化、CAC资本化、SBC调整后的ROIC才能反映企业真实的资本效率

模块组成：
- IntangibleCapitalizer：R&D资本化、CAC资本化、财务重述计算
- RDCapitalizationResult：R&D资本化结果
- RestatedFinancialsResult：重述后财务数据（调整EBIT和ROIC）
- SBCAdjustmentResult：SBC费用化调整结果
"""




# ---------------------------------------------------------------------------
# 行业R&D摊销年限参考表
# Industry R&D Amortization Period Reference
# ---------------------------------------------------------------------------

R_AND_D_AMORTIZATION_YEARS: Dict[str, int] = {
    "药企": 10,
    "SaaS": 3,
    "AI": 2,
    "咨询": 5,
    "半导体": 7,
    "医疗器械": 8,
    "消费品": 3,
}


# ---------------------------------------------------------------------------
# R&D资本化结果
# R&D Capitalization Result
# ---------------------------------------------------------------------------

@dataclass
class RDCapitalizationResult:
    """
    R&D资本化计算结果
    R&D Capitalization Calculation Result.

    Fields
    ------
    rd_asset_value              资本化后R&D资产价值（亿元）
    current_year_amortization   当年R&D摊销费用（亿元）
    adjustment_to_ebit          对EBIT的调整量 = 当年R&D支出 - 当年摊销
                                 （正值表示EBIT被低估，应上调）
    annual_rd_history           历史R&D支出序列（亿元）
    """

    rd_asset_value: float                  # R&D资产价值（亿元）
    current_year_amortization: float       # 当年摊销（亿元）
    adjustment_to_ebit: float             # EBIT调整量（亿元）
    annual_rd_history: list[float]
    summary: str
    details: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# 重述后财务数据
# Restated Financials Result
# ---------------------------------------------------------------------------

@dataclass
class RestatedFinancialsResult:
    """
    R&D资本化后的财务重述结果
    Restated financials after R&D capitalization.

    Fields
    ------
    reported_ebit               申报EBIT（亿元）
    restated_ebit               重述后EBIT（亿元）
    reported_invested_capital   申报投入资本（亿元）
    restated_invested_capital   重述后投入资本（亿元）
    reported_roic               申报ROIC
    restated_roic               重述后ROIC
    ebit_improvement_pct        EBIT改善幅度（%）
    roic_improvement_pct        ROIC改善幅度（%）
    """

    reported_ebit: float
    restated_ebit: float
    reported_invested_capital: float
    restated_invested_capital: float
    reported_roic: float
    restated_roic: float
    ebit_improvement_pct: float
    roic_improvement_pct: float
    summary: str
    warnings: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    details: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# SBC调整结果
# SBC Adjustment Result
# ---------------------------------------------------------------------------

@dataclass
class SBCAdjustmentResult:
    """
    股票激励费用（SBC）调整结果
    Stock-Based Compensation (SBC) Adjustment Result.

    Fields
    ------
    reported_ebitda   申报EBITDA（亿元，通常被管理层加回SBC）
    adjusted_ebitda   调整后EBITDA（已扣除SBC，反映真实运营现金流）
    sbc_expense       SBC费用（亿元）
    sbc_as_pct_of_ebitda SBC占申报EBITDA的比例
    """

    reported_ebitda: float
    adjusted_ebitda: float
    sbc_expense: float
    sbc_as_pct_of_ebitda: float
    summary: str
    warnings: list[str] = field(default_factory=list)
    details: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# 无形资产资本化引擎
# Intangible Asset Capitalizer
# ---------------------------------------------------------------------------

class IntangibleCapitalizer:
    """
    无形资产资本化引擎（R&D + CAC + SBC调整）
    Intangible Asset Capitalization Engine

    方法论概述
    ----------
    R&D资本化（Damodaran方法）：
    - 对历史N年的R&D支出，计算每笔支出中尚未摊销完的部分
    - rd_asset = Σ rd_history[i] × (remaining_years / total_years)
    - 第i年（从最新一年倒数）：remaining_years = amortization_years - i

    CAC资本化：
    - 将历史销售&营销支出视为客户资产的投资
    - 用LTV/CAC比率估算资产价值（简化方法）
    - capitalized_cac = avg(sales_marketing_history) × ltv_to_cac_ratio

    ROIC重述：
    - 申报ROIC = reported_ebit / reported_invested_capital
    - 重述ROIC = restated_ebit / restated_invested_capital
    - 通常：重述EBIT > 申报EBIT（R&D费用 > 当年摊销，EBIT被低估）
    - 通常：重述投入资本 > 申报投入资本（加入R&D资产）
    """

    def capitalize_rd(
        self,
        *,
        rd_history: list[float],
        amortization_years: int,
    ) -> RDCapitalizationResult:
        """
        对历史R&D支出序列执行资本化计算。

        Parameters
        ----------
        rd_history          历史R&D支出序列（亿元，从最早年份到最新年份排列）
        amortization_years  行业对应的R&D摊销年限（年）

        Returns
        -------
        RDCapitalizationResult

        算法
        ----
        对rd_history中最近 amortization_years 年的数据：
        - 最近一年（index=-1）剩余摊销年数 = amortization_years - 0（即整个资产价值）
        - 前一年（index=-2）剩余摊销年数 = amortization_years - 1
        - ...以此类推

        rd_asset = Σ rd_history[-k] × (amortization_years - (k-1)) / amortization_years
        current_year_amortization = Σ rd_history[-k] / amortization_years
        """
        if amortization_years <= 0:
            amortization_years = 1

        # 取最近 amortization_years 年的数据
        n_history = len(rd_history)
        effective_history = rd_history[-amortization_years:] if n_history >= amortization_years else rd_history
        n_eff = len(effective_history)

        rd_asset_value = 0.0
        current_year_amortization = 0.0

        for i, rd_amount in enumerate(effective_history):
            # i=0是最早一年，i=n_eff-1是最新一年
            years_elapsed = n_eff - 1 - i                                   # 距今已过去几年
            years_remaining = max(0, amortization_years - years_elapsed)    # 剩余摊销年数
            unamortized_fraction = years_remaining / amortization_years
            rd_asset_value += rd_amount * unamortized_fraction
            # 每笔R&D支出贡献的当年摊销 = rd/amortization_years（等额摊销）
            if years_elapsed < amortization_years:
                current_year_amortization += rd_amount / amortization_years

        # 当年R&D支出（最新一期）
        current_year_rd = rd_history[-1] if rd_history else 0.0
        adjustment_to_ebit = current_year_rd - current_year_amortization

        summary = (
            f"R&D资本化资产价值: {rd_asset_value:.2f}亿元 | "
            f"当年摊销: {current_year_amortization:.2f}亿 | "
            f"EBIT调整量(+表示被低估): {adjustment_to_ebit:+.2f}亿 | "
            f"摊销年限: {amortization_years}年 | "
            f"历史数据点: {n_eff}年"
        )

        return RDCapitalizationResult(
            rd_asset_value=round(rd_asset_value, 4),
            current_year_amortization=round(current_year_amortization, 4),
            adjustment_to_ebit=round(adjustment_to_ebit, 4),
            annual_rd_history=list(rd_history),
            summary=summary,
            details={
                "amortization_years": amortization_years,
                "n_history_used": n_eff,
                "current_year_rd": current_year_rd,
            },
        )

    def capitalize_cac(
        self,
        *,
        sales_marketing_history: list[float],
        ltv_to_cac_ratio: float,
    ) -> float:
        """
        计算资本化CAC资产价值（简化方法）。

        Parameters
        ----------
        sales_marketing_history  历史销售与营销费用序列（亿元）
        ltv_to_cac_ratio         LTV/CAC比率（反映客户终身价值与获取成本之比）

        Returns
        -------
        float  资本化CAC资产价值（亿元）

        算法
        ----
        capitalized_cac = avg(sales_marketing_history) × ltv_to_cac_ratio

        LTV/CAC > 3 通常被认为是健康的SaaS业务门槛。
        此处将平均年销售营销支出视为客户资产的年投入，
        乘以LTV/CAC倍数得到对应的客户资产价值。
        """
        if not sales_marketing_history:
            return 0.0
        avg_sm = sum(sales_marketing_history) / len(sales_marketing_history)
        return round(avg_sm * ltv_to_cac_ratio, 4)

    def restate_financials(
        self,
        *,
        reported_ebit: float,
        reported_invested_capital: float,
        capitalized_rd_asset: float,
        current_year_rd: float,
        amortization_years: int,
        revenue: float = 0.0,
        capitalized_cac: float = 0.0,
    ) -> RestatedFinancialsResult:
        """
        对申报财务数据进行R&D资本化重述，计算调整后ROIC。

        Parameters
        ----------
        reported_ebit             申报EBIT（亿元）
        reported_invested_capital 申报投入资本（亿元）
        capitalized_rd_asset      R&D资本化后的资产价值（亿元，由 capitalize_rd 提供）
        current_year_rd           当年R&D支出（亿元）
        amortization_years        R&D摊销年限
        revenue                   当年营业收入（亿元，用于ROIC分母校验）
        capitalized_cac           资本化CAC资产价值（亿元）

        Returns
        -------
        RestatedFinancialsResult
        """
        warnings: list[str] = []
        recommendations: list[str] = []

        # 当年R&D摊销 = capitalized_rd_asset / amortization_years（近似）
        # 更精确：来自 capitalize_rd 的 current_year_amortization
        # 这里用资产价值反推摊销（当没有完整历史时的近似）
        current_year_amortization = (
            capitalized_rd_asset / amortization_years if amortization_years > 0 else 0.0
        )

        # EBIT重述：加回当年R&D，减去摊销
        adjustment = current_year_rd - current_year_amortization
        restated_ebit = reported_ebit + adjustment

        # 投入资本重述：加入R&D资产 + CAC资产
        restated_invested_capital = reported_invested_capital + capitalized_rd_asset + capitalized_cac

        # ROIC计算（不含税调整，用于比较性分析）
        if reported_invested_capital > 0:
            reported_roic = reported_ebit / reported_invested_capital
        else:
            reported_roic = 0.0

        if restated_invested_capital > 0:
            restated_roic = restated_ebit / restated_invested_capital
        else:
            restated_roic = 0.0

        # 改善幅度
        if reported_ebit != 0:
            ebit_improvement_pct = (restated_ebit - reported_ebit) / abs(reported_ebit) * 100
        else:
            ebit_improvement_pct = 0.0

        if reported_roic != 0:
            roic_improvement_pct = (restated_roic - reported_roic) / abs(reported_roic) * 100
        else:
            roic_improvement_pct = 0.0

        # 警告
        if restated_roic < reported_roic:
            warnings.append(
                f"R&D资本化后ROIC从 {reported_roic:.1%} 下降至 {restated_roic:.1%}，"
                "说明资本化增加的分母效应大于EBIT提升效应，"
                "企业实际资本效率低于报表呈现。"
            )
        else:
            recommendations.append(
                f"R&D资本化后ROIC从 {reported_roic:.1%} 提升至 {restated_roic:.1%}，"
                "真实盈利能力被GAAP费用化低估，重述后ROIC更能反映企业护城河质量。"
            )

        if restated_roic < 0.08:
            warnings.append(
                f"重述后ROIC仅 {restated_roic:.1%}，低于一般资本成本门槛（8-10%），"
                "企业当前未实现经济利润（EVA < 0），需明确ROIC改善路径。"
            )

        summary = (
            f"申报EBIT: {reported_ebit:.2f}亿 → 重述后: {restated_ebit:.2f}亿 ({ebit_improvement_pct:+.1f}%) | "
            f"申报ROIC: {reported_roic:.1%} → 重述后: {restated_roic:.1%} ({roic_improvement_pct:+.1f}%) | "
            f"R&D资产化入: {capitalized_rd_asset:.2f}亿 + CAC资产: {capitalized_cac:.2f}亿"
        )

        return RestatedFinancialsResult(
            reported_ebit=round(reported_ebit, 4),
            restated_ebit=round(restated_ebit, 4),
            reported_invested_capital=round(reported_invested_capital, 4),
            restated_invested_capital=round(restated_invested_capital, 4),
            reported_roic=round(reported_roic, 6),
            restated_roic=round(restated_roic, 6),
            ebit_improvement_pct=round(ebit_improvement_pct, 2),
            roic_improvement_pct=round(roic_improvement_pct, 2),
            summary=summary,
            warnings=warnings,
            recommendations=recommendations,
            details={
                "current_year_rd": current_year_rd,
                "current_year_amortization": round(current_year_amortization, 4),
                "adjustment_to_ebit": round(adjustment, 4),
                "capitalized_rd_asset": capitalized_rd_asset,
                "capitalized_cac": capitalized_cac,
                "revenue": revenue,
                "amortization_years": amortization_years,
            },
        )

    @staticmethod
    def adjust_for_sbc(
        reported_ebitda: float,
        sbc_expense: float,
    ) -> SBCAdjustmentResult:
        """
        从EBITDA中扣除股票激励费用（SBC），还原真实运营现金流。

        Parameters
        ----------
        reported_ebitda   管理层申报的EBITDA（通常已将SBC加回，亿元）
        sbc_expense       SBC费用（亿元）

        Returns
        -------
        SBCAdjustmentResult

        核心观点
        --------
        管理层和某些卖方分析师惯用"Adjusted EBITDA"将SBC加回，
        理由是SBC是"非现金项目"。这是典型的会计误导：
        - SBC稀释了老股东股权（相当于用股票支付员工工资）
        - 若换算为现金支付，必然会显著减少运营利润
        - Damodaran明确指出：SBC是真实成本，不应被加回
        """
        warnings: list[str] = []

        adjusted_ebitda = reported_ebitda - sbc_expense

        sbc_as_pct = (
            sbc_expense / reported_ebitda * 100
            if reported_ebitda > 0
            else 0.0
        )

        if sbc_as_pct > 20:
            warnings.append(
                f"⚠️ SBC费用占申报EBITDA的 {sbc_as_pct:.1f}%（>20%警戒线）！"
                "管理层通过Adjusted EBITDA严重粉饰盈利能力，"
                "实际运营现金流能力远低于申报数字。"
                "建议只接受扣除SBC后的EBITDA作为估值基础。"
            )
        elif sbc_as_pct > 10:
            warnings.append(
                f"SBC占申报EBITDA的 {sbc_as_pct:.1f}%（>10% 需关注），"
                "在建模时应使用调整后EBITDA={adjusted_ebitda:.2f}亿而非申报值。"
            )

        summary = (
            f"申报EBITDA: {reported_ebitda:.2f}亿 | "
            f"SBC费用: {sbc_expense:.2f}亿 ({sbc_as_pct:.1f}%) | "
            f"调整后EBITDA: {adjusted_ebitda:.2f}亿"
        )

        return SBCAdjustmentResult(
            reported_ebitda=round(reported_ebitda, 4),
            adjusted_ebitda=round(adjusted_ebitda, 4),
            sbc_expense=round(sbc_expense, 4),
            sbc_as_pct_of_ebitda=round(sbc_as_pct, 2),
            summary=summary,
            warnings=warnings,
            details={
                "reported_ebitda": reported_ebitda,
                "sbc_expense": sbc_expense,
                "adjusted_ebitda": round(adjusted_ebitda, 4),
            },
        )
