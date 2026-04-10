"""
LP / GP 评估框架
LP Evaluation & GP Scorecard

Implements:
- GP Scorecard with 6 core indicators (source: [cite 496, 497, 498])
- Asset Allocation Advisor (三不与三要 / Three-no Three-yes framework)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# GP Scorecard — 6 Core Indicators
# ---------------------------------------------------------------------------

@dataclass
class GPScorecardResult:
    total_score: float              # 0-100
    grade: str                      # "A", "B", "C", "D"
    is_investable: bool
    indicator_scores: dict[str, float]
    summary: str
    red_flags: list[str] = field(default_factory=list)
    green_flags: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)


class GPScorecard:
    """
    GP综合评分卡 — 六大核心指标

    DO NOT rely on star deals or inflated IRR. Instead evaluate:
    1. Historical real DPI data
    2. MOC with paper gains stripped out (fair value adjusted)
    3. Old LP re-investment rate
    4. Fund size vs GP stage/capability match
    5. Concentration in core winners (conviction)
    6. Government-guidance fund proportion (返投压力)

    Source: [cite 496, 497, 498]
    """

    WEIGHTS = {
        "dpi": 0.30,
        "moc_quality": 0.20,
        "lp_reinvest_rate": 0.15,
        "fund_stage_match": 0.15,
        "concentration": 0.10,
        "gov_fund_ratio": 0.10,
    }

    def evaluate(
        self,
        *,
        # 1. DPI — actual cash returned to LPs / total capital called
        historical_dpi: float,

        # 2. MOC quality — adjusted MOC after removing unrealised paper gains
        reported_moc: float,
        unrealised_pct: float,          # % of MOC that is paper / unrealised

        # 3. Old LP re-investment rate
        lp_reinvestment_rate_pct: float,  # % of existing LPs who re-invested

        # 4. Fund size vs team capability match
        fund_size_rmb: float,           # 亿元
        team_managed_assets_rmb: float, # 亿元 — historically managed by this team
        target_stage: str,              # "angel", "vc", "pe"

        # 5. Core portfolio concentration
        top3_investment_pct: float,     # % of fund capital in top 3 positions

        # 6. Government guidance fund proportion
        gov_fund_pct: float,            # % of total LP base that is gov guidance funds
    ) -> GPScorecardResult:
        """
        Score a GP across 6 core indicators.

        Returns a 0-100 composite score with grade and detailed breakdown.
        """
        red_flags: list[str] = []
        green_flags: list[str] = []
        recommendations: list[str] = []
        indicator_scores: dict[str, float] = {}

        # 1. DPI (max score: 30)
        # ≥ 1.5x = excellent (88 global conversion), 1.0-1.5 = good, < 1.0 = poor
        if historical_dpi >= 1.5:
            dpi_score = 30
            green_flags.append(f"DPI {historical_dpi:.2f}x — 实质性现金回报优秀。")
        elif historical_dpi >= 1.0:
            dpi_score = 18
        elif historical_dpi >= 0.7:
            dpi_score = 8
            red_flags.append(
                f"DPI {historical_dpi:.2f}x — 现金回款不足，账面浮盈转化能力存疑。"
            )
        else:
            dpi_score = 0
            red_flags.append(
                f"DPI {historical_dpi:.2f}x — 极低！LP本金尚未收回，存在重大风险。"
            )
        indicator_scores["dpi"] = dpi_score

        # 2. MOC quality (max score: 20)
        adjusted_moc = reported_moc * (1 - unrealised_pct / 100)
        if adjusted_moc >= 2.5:
            moc_score = 20
            green_flags.append(f"剔除未变现水分后MOC {adjusted_moc:.2f}x — 实质回报丰厚。")
        elif adjusted_moc >= 1.5:
            moc_score = 12
        elif adjusted_moc >= 1.0:
            moc_score = 6
            red_flags.append(
                f"调整后MOC {adjusted_moc:.2f}x (剔除{unrealised_pct:.0f}%未变现)，"
                "实质回报平庸。"
            )
        else:
            moc_score = 0
            red_flags.append(
                f"调整后MOC {adjusted_moc:.2f}x — 账面浮盈占比过高，"
                "真实回报严重低于宣传数据。"
            )
        indicator_scores["moc_quality"] = moc_score

        # 3. LP re-investment rate (max score: 15)
        if lp_reinvestment_rate_pct >= 80:
            lp_score = 15
            green_flags.append(f"老LP复投率 {lp_reinvestment_rate_pct:.0f}% — 历史满意度极高。")
        elif lp_reinvestment_rate_pct >= 60:
            lp_score = 10
        elif lp_reinvestment_rate_pct >= 40:
            lp_score = 5
            red_flags.append(
                f"老LP复投率 {lp_reinvestment_rate_pct:.0f}% — 历史LP认可度不足，"
                "需深入了解原因。"
            )
        else:
            lp_score = 0
            red_flags.append(
                f"老LP复投率 {lp_reinvestment_rate_pct:.0f}% — 极低！"
                "历史表现未获LP信任，高度警惕。"
            )
        indicator_scores["lp_reinvest_rate"] = lp_score

        # 4. Fund size vs stage match (max score: 15)
        # Rough benchmarks: Angel<5亿, VC 5-30亿, PE 30-200亿
        stage_limits = {"angel": 5, "vc": 30, "pe": 200}
        stage_limit = stage_limits.get(target_stage, 50)
        size_ratio = fund_size_rmb / stage_limit

        if size_ratio <= 1.0 and fund_size_rmb <= team_managed_assets_rmb * 1.5:
            match_score = 15
            green_flags.append(
                f"基金规模 {fund_size_rmb:.0f}亿与团队历史管理规模匹配。"
            )
        elif size_ratio <= 1.5:
            match_score = 10
        elif size_ratio <= 2.5:
            match_score = 5
            red_flags.append(
                f"基金规模 {fund_size_rmb:.0f}亿 相对{target_stage}阶段偏大，"
                "可能超出团队能力圈，导致投资动作变形。"
            )
        else:
            match_score = 0
            red_flags.append(
                f"基金规模严重超出团队能力边界，"
                "大概率导致投资策略偏离、回报摊薄。"
            )
        indicator_scores["fund_stage_match"] = match_score

        # 5. Concentration / conviction (max score: 10)
        # High concentration (top 3 > 40%) shows conviction
        if top3_investment_pct >= 50:
            conc_score = 10
            green_flags.append(
                f"核心项目集中度 {top3_investment_pct:.0f}% — 重仓赢家策略，体现投资魄力。"
            )
        elif top3_investment_pct >= 30:
            conc_score = 6
        else:
            conc_score = 3
            recommendations.append(
                "核心项目持仓分散，可能存在'撒胡椒面'投资风格，"
                "建议了解是否具备重仓优质资产的决策机制。"
            )
        indicator_scores["concentration"] = conc_score

        # 6. Government fund proportion (max score: 10)
        # Too high (> 40%) creates 返投压力 (re-investment location pressure)
        if gov_fund_pct <= 20:
            gov_score = 10
            green_flags.append(
                f"政府引导基金占比 {gov_fund_pct:.0f}% — 低政策依赖，"
                "投资决策相对独立自主。"
            )
        elif gov_fund_pct <= 40:
            gov_score = 6
        else:
            gov_score = 2
            red_flags.append(
                f"政府引导基金占比 {gov_fund_pct:.0f}% — 返投压力过大，"
                "可能导致强迫投资本地企业，投资决策系统性变形。"
            )
        indicator_scores["gov_fund_ratio"] = gov_score

        # Total score
        total = sum(indicator_scores.values())
        if total >= 80:
            grade = "A"
        elif total >= 65:
            grade = "B"
        elif total >= 45:
            grade = "C"
        else:
            grade = "D"

        is_investable = grade in ("A", "B")

        summary = (
            f"GP综合评分: {total:.0f}/100 | 等级: {grade} | "
            f"{'✅ 建议投资' if is_investable else '❌ 建议暂缓'}\n"
            f"红旗数量: {len(red_flags)} | 绿旗数量: {len(green_flags)}"
        )

        if not is_investable:
            recommendations.append(
                "综合评分不达标，建议暂缓投资。如坚持投入，"
                "须将承诺金额控制在资产配置盲池仓位的20%-30%以内，"
                "重点作为观察GP真实能力的低成本窗口。"
            )

        return GPScorecardResult(
            total_score=round(total, 1),
            grade=grade,
            is_investable=is_investable,
            indicator_scores=indicator_scores,
            summary=summary,
            red_flags=red_flags,
            green_flags=green_flags,
            recommendations=recommendations,
        )


# ---------------------------------------------------------------------------
# Asset Allocation Advisor — 三不与三要
# ---------------------------------------------------------------------------

@dataclass
class AllocationAdvice:
    blind_pool_pct: float       # recommended blind-pool fund allocation %
    special_fund_pct: float     # recommended special/co-investment allocation %
    fund_of_funds_pct: float    # recommended FoF allocation (likely 0)
    total_pe_allocation_pct: float
    summary: str
    warnings: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)


class AssetAllocationAdvisor:
    """
    LP资产配置顾问 — 三不与三要框架

    Three-NO rules (source: [cite 475, 476, 478]):
    1. 不碰市场化母基金 (No market-rate FoF — double-fee structure kills DPI)
    2. 不重仓盲池基金   (No over-concentration in blind-pool funds)
    3. 不投GP自有资金占比低的基金 (No GP if no meaningful co-investment)

    Three-YES rules:
    1. 控制盲池仓位 20%-30%  (Blind pools: observation & deal-flow access)
    2. 重仓精选专项基金       (Concentrate in carefully selected special funds)
    3. 要求GP大比例跟投       (Require GP to have meaningful skin in the game)
    """

    def advise(
        self,
        *,
        total_investable_assets_rmb: float,     # 亿元
        risk_tolerance: str,                    # "conservative", "moderate", "aggressive"
        pe_budget_pct: float,                   # % of total to allocate to PE/VC
        gp_coinvestment_rate_pct: float,        # GP's own co-investment %
        is_market_rate_fof: bool,               # Is this a market-rate FoF?
        years_of_observation: int = 0,          # Years the LP has observed this GP
    ) -> AllocationAdvice:
        """
        Provide LP asset allocation guidance.

        Parameters
        ----------
        total_investable_assets_rmb:  Total liquid investable capital (亿元)
        risk_tolerance:               Risk appetite
        pe_budget_pct:                % of total capital earmarked for PE/VC
        gp_coinvestment_rate_pct:     GP's own money as % of fund size
        is_market_rate_fof:           Whether the vehicle is a market-rate FoF
        years_of_observation:         How long LP has watched this GP
        """
        warnings: list[str] = []
        recommendations: list[str] = []

        # Hard rule: never invest in market-rate FoF
        if is_market_rate_fof:
            return AllocationAdvice(
                blind_pool_pct=0,
                special_fund_pct=0,
                fund_of_funds_pct=0,
                total_pe_allocation_pct=0,
                summary=(
                    "❌ 市场化母基金: 建议零配置。"
                    "双重收费结构（管理费+carry叠加）导致DPI极难回本，"
                    "实质上是把高净值LP变成接盘侠。"
                ),
                warnings=[
                    "市场化母基金的双重收费结构是天然的回报杀手，"
                    "务必坚决规避。"
                ],
            )

        # Warn if GP co-investment is too low
        if gp_coinvestment_rate_pct < 3:
            warnings.append(
                f"GP跟投比例仅 {gp_coinvestment_rate_pct:.1f}%，"
                "利益绑定不足，难以确保GP与LP目标一致。建议要求GP提高跟投比例至5%以上。"
            )

        # Base allocation by risk tolerance
        base_pe_pct = pe_budget_pct
        risk_caps = {"conservative": 15.0, "moderate": 25.0, "aggressive": 40.0}
        max_pe_pct = risk_caps.get(risk_tolerance, 20.0)
        actual_pe_pct = min(base_pe_pct, max_pe_pct)

        if base_pe_pct > max_pe_pct:
            warnings.append(
                f"目标PE配置比例 {base_pe_pct:.0f}% 超过"
                f"{risk_tolerance}风险偏好的上限 {max_pe_pct:.0f}%，"
                "建议降低配置。"
            )

        # Blind pool: 20-30% of PE allocation
        if years_of_observation < 2:
            blind_pool_pct = min(actual_pe_pct * 0.30, actual_pe_pct)
            recommendations.append(
                "观察期少于2年，建议以盲池基金为主要接触方式，"
                "重点考察GP的真实投资能力和退出能力。"
            )
        else:
            blind_pool_pct = actual_pe_pct * 0.25

        special_fund_pct = actual_pe_pct - blind_pool_pct

        summary_lines = [
            f"总可投资产: {total_investable_assets_rmb:.1f}亿元",
            f"建议PE/VC总配置: {actual_pe_pct:.1f}%（{total_investable_assets_rmb * actual_pe_pct / 100:.2f}亿元）",
            f"  其中 盲池基金: {blind_pool_pct:.1f}%（用于观察GP实力，获取项目流）",
            f"  其中 精选专项: {special_fund_pct:.1f}%（GP须大比例跟投，深度利益绑定）",
            f"  其中 市场化母基金: 0%（坚决规避双重收费结构）",
        ]

        return AllocationAdvice(
            blind_pool_pct=round(blind_pool_pct, 2),
            special_fund_pct=round(special_fund_pct, 2),
            fund_of_funds_pct=0.0,
            total_pe_allocation_pct=round(actual_pe_pct, 2),
            summary="\n".join(summary_lines),
            warnings=warnings,
            recommendations=recommendations,
        )
