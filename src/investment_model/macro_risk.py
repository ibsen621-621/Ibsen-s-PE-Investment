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

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, Optional


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
            "例如：若基础ERP=5%，叠加CRP后折现率应额外增加 {crp:.2%}。"
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
