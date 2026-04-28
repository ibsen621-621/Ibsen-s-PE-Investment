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

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


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
