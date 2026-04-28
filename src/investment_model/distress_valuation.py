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

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional


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
            ytm = max(0.001, min(ytm, 0.99))  # 防止发散

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
