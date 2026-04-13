"""
LP / GP 评估框架
LP Evaluation & GP Scorecard

Implements:
- GP Scorecard with 6 core indicators (source: [cite 496, 497, 498])
- Asset Allocation Advisor (三不与三要 / Three-no Three-yes framework)
- LP Behavior Checker (个人LP行为学纠偏)
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


# ---------------------------------------------------------------------------
# LP Behavior Checker / 个人LP行为学纠偏
# ---------------------------------------------------------------------------

@dataclass
class LPBehaviorResult:
    """个人LP行为学纠偏结果 / LP behavioral bias check result."""
    narrative_trap_detected: bool       # 宏大叙事陷阱检测
    fomo_detected: bool                 # FOMO跟风效应检测
    expected_value: float               # 期望收益值（倍数）
    is_rational_decision: bool          # 综合判断：是否为理性决策
    soul_questions: list[str]           # 给LP的灵魂拷问清单
    summary: str
    warnings: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)


class LPBehaviorChecker:
    """
    个人LP行为学纠偏器
    LP Behavioral Bias Corrector

    Individual LPs often lose money not because they can't calculate returns,
    but because of fundamental human biases. This checker performs a "soul
    interrogation" (灵魂拷问) on the LP's own decision-making process.

    Three core checks:
    1. Grand Narrative Trap (宏大叙事陷阱): Attracted by "trillion-dollar market,
       led by renowned academics" without concrete evidence
    2. FOMO Effect (跟风效应): Following famous funds without independent analysis
    3. Cold Math: Expected value calculation from win probability and return/loss multiples
    """

    def check(
        self,
        *,
        # 1. Narrative trap / 宏大叙事陷阱
        attracted_by_narrative: bool,       # 是否被宏大叙事（万亿赛道/院士领衔）吸引
        has_concrete_evidence: bool,        # 是否看到具体的订单/良率/财务数据
        # 2. FOMO effect / 跟风效应
        following_famous_fund: bool,        # 是否因知名机构投了才跟投
        has_independent_analysis: bool,     # 是否做了独立分析
        # 3. Expected value / 期望值计算
        estimated_win_probability_pct: float,   # 预估胜率（%，0-100）
        expected_return_multiple: float,        # 胜出时的预期回报倍数
        expected_loss_multiple: float,          # 失败时的亏损倍数（通常0.0-1.0，0=全亏）
    ) -> LPBehaviorResult:
        """
        Perform a behavioral bias check on the LP's investment decision.

        Parameters
        ----------
        attracted_by_narrative:          LP was attracted by grand narrative claims
        has_concrete_evidence:           LP has reviewed concrete orders, yields, financials
        following_famous_fund:           LP is following because a famous fund invested
        has_independent_analysis:        LP has done own independent due diligence
        estimated_win_probability_pct:   LP's estimated probability of success (0-100)
        expected_return_multiple:        Expected return multiple on success (e.g., 5.0 = 5x)
        expected_loss_multiple:          Expected value of loss on failure (0.0 = total loss,
                                         0.5 = recover 50% of capital)
        """
        warnings: list[str] = []
        recommendations: list[str] = []
        soul_questions: list[str] = []

        # --- Check 1: Grand narrative trap ---
        narrative_trap_detected = attracted_by_narrative and not has_concrete_evidence

        if narrative_trap_detected:
            warnings.append(
                "⚠️ 宏大叙事陷阱警告：您被'万亿赛道、院士领衔'等宏大叙事所吸引，"
                "但尚未看到具体的订单数据、技术良率或财务验证。"
                "宏大叙事是吸引注意力的工具，不是投资的依据。"
            )
            soul_questions.append(
                "【灵魂拷问1】您能说出该公司最近一个季度的具体营收数字、"
                "主要客户名称和产品良率吗？如果不能，您投的是叙事而非企业。"
            )
        elif attracted_by_narrative and has_concrete_evidence:
            recommendations.append(
                "叙事+数据双重验证：您既被赛道叙事吸引，也验证了具体数据，"
                "这是正确的投资路径——叙事给方向，数据定价值。"
            )
            soul_questions.append(
                "【建议】持续追踪核心数据指标（良率/订单/营收），"
                "当数据与叙事出现偏差时及时复盘。"
            )
        else:
            soul_questions.append(
                "【灵魂拷问1】您决策的核心依据是什么？请确保有具体数据支撑，"
                "而非仅基于行业趋势判断。"
            )

        # --- Check 2: FOMO effect ---
        fomo_detected = following_famous_fund and not has_independent_analysis

        if fomo_detected:
            warnings.append(
                "⚠️ FOMO跟风效应警告：您因某知名机构（如知名VC）投了而选择跟投，"
                "但并未做独立分析。知名机构也会犯错，且其投资逻辑和您的风险偏好可能完全不同。"
                "跟风是情绪驱动，不是投资逻辑。"
            )
            soul_questions.append(
                "【灵魂拷问2】如果该知名机构从未投过这家公司，"
                "您还会投吗？如果答案是'不会'，您投的是机构背书而非企业本身。"
            )
        elif following_famous_fund and has_independent_analysis:
            recommendations.append(
                "知名机构背书+独立分析：您在验证了知名机构的投资逻辑后形成了独立判断，"
                "这是成熟LP的正确做法。"
            )

        # --- Check 3: Expected value calculation ---
        win_prob = estimated_win_probability_pct / 100.0
        loss_prob = 1.0 - win_prob

        # EV = win_prob * return_multiple + loss_prob * loss_multiple
        # Note: loss_multiple should be ≤ 1.0 (0 = total loss, 1 = full return of capital)
        # We interpret expected_loss_multiple as what fraction of capital is returned on loss
        expected_value = win_prob * expected_return_multiple + loss_prob * expected_loss_multiple

        if expected_value < 1.0:
            warnings.append(
                f"❄️ 冷酷数学警告：期望值 = {win_prob:.0%} × {expected_return_multiple:.1f}x + "
                f"{loss_prob:.0%} × {expected_loss_multiple:.2f}x = {expected_value:.2f}x < 1.0x。"
                "从概率论角度，这笔投资的期望收益为负。"
                "除非您有充分理由认为胜率/回报倍数被低估，否则在数学上不应投资。"
            )
            soul_questions.append(
                f"【灵魂拷问3】您的期望值仅为 {expected_value:.2f}x，"
                "数学告诉您这不是一笔好投资。您是否有额外的信息不对称优势，"
                "使实际胜率远高于您的估算？"
            )
        elif expected_value >= 2.0:
            recommendations.append(
                f"期望值 {expected_value:.2f}x ≥ 2.0x，从赔率角度值得投资。"
                "核心风险是胜率估算是否准确——请务必验证您的胜率假设。"
            )
            soul_questions.append(
                f"【确认问题】您的期望值为 {expected_value:.2f}x，赔率合理。"
                f"请再次确认：您的胜率估算 {estimated_win_probability_pct:.0f}% 是基于什么证据？"
            )
        else:
            soul_questions.append(
                f"【灵魂拷问3】期望值 {expected_value:.2f}x，勉强达标。"
                "请量化您的核心风险：最可能让这笔投资失败的因素是什么？"
            )

        # --- Overall rationality assessment ---
        rationality_issues = sum([narrative_trap_detected, fomo_detected, expected_value < 1.0])
        is_rational_decision = rationality_issues == 0

        if rationality_issues >= 2:
            warnings.append(
                f"检测到 {rationality_issues} 个行为偏差，当前决策受情绪和认知偏差影响显著，"
                "建议暂缓投资决策，给自己48小时冷静期后重新评估。"
            )
        elif rationality_issues == 1:
            recommendations.append(
                "存在1个行为偏差需要关注，建议在消除该偏差后再做最终决策。"
            )

        soul_questions.append(
            "【终极问题】如果这笔投资亏损一半，您的生活质量会受到显著影响吗？"
            "一级市场投资的平均退出周期为7-9年，在此期间该资金不可动用，"
            "请确认您的资金期限与投资期限匹配。"
        )

        rationality_labels = {True: "✅ 决策路径基本理性", False: "⚠️ 存在显著行为偏差"}
        summary = (
            f"{rationality_labels[is_rational_decision]} | "
            f"宏大叙事陷阱: {'⚠️ 是' if narrative_trap_detected else '✅ 否'} | "
            f"FOMO跟风: {'⚠️ 是' if fomo_detected else '✅ 否'} | "
            f"期望值: {expected_value:.2f}x | "
            f"灵魂拷问: {len(soul_questions)}题"
        )

        return LPBehaviorResult(
            narrative_trap_detected=narrative_trap_detected,
            fomo_detected=fomo_detected,
            expected_value=round(expected_value, 3),
            is_rational_decision=is_rational_decision,
            soul_questions=soul_questions,
            summary=summary,
            warnings=warnings,
            recommendations=recommendations,
        )

