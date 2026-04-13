"""
投后管理与拐点追投模块
Post-Investment Management & Inflection-Point Follow-on Module

Implements:
- GPPostInvestmentEvaluator: Quantifies GP post-investment capabilities (4 levels, 40pts)
- DoubleDownDecisionModel: Follow-on investment decision at inflection points

All amounts in 亿元 RMB.
"""

from __future__ import annotations

from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# GP Post-Investment Level Evaluator / GP投后管理境界评估
# ---------------------------------------------------------------------------

@dataclass
class PostInvestmentResult:
    """GP投后管理能力评估结果 / GP post-investment capability result."""
    level: int              # 1-4 境界
    score: int              # 0-40 分
    summary: str
    warnings: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)


class GPPostInvestmentEvaluator:
    """
    GP投后管理四重境界评分器
    GP Post-Investment Four-Level Capability Scorer

    Four levels of post-investment capability (总分40分):
    Level 1 — 统计统筹 (Financial monitoring & compliance):      10 pts
    Level 2 — 3R服务 (PR / HR / IR services):                  20 pts
    Level 3 — 战略与业务赋能 (Strategic & business empowerment): 30 pts
    Level 4 — 退出导向型投后 (Exit-oriented management):         40 pts

    Only GPs with Level 3 + Level 4 capabilities can truly navigate full
    market cycles and deliver consistent fund-level returns.
    """

    LEVEL_SCORES = {1: 10, 2: 20, 3: 30, 4: 40}

    def evaluate(
        self,
        *,
        has_financial_monitoring: bool,         # Level 1: 财务监控/查账能力
        has_3r_services: bool,                  # Level 2: PR/HR/IR服务能力
        has_strategic_empowerment: bool,        # Level 3: 战略与业务赋能能力
        has_exit_oriented_management: bool,     # Level 4: 退出导向型投后能力
        portfolio_company_survival_rate: float = 0.5,   # 被投企业存活率（0-1）
        avg_time_to_next_round_months: float = 18.0,    # 平均完成下一轮融资时间（月）
    ) -> PostInvestmentResult:
        """
        Evaluate GP post-investment capabilities.

        Parameters
        ----------
        has_financial_monitoring:        GP can monitor portfolio financials & compliance
        has_3r_services:                 GP provides PR, HR recruitment, and IR services
        has_strategic_empowerment:       GP connects resources, customers, strategic partners
        has_exit_oriented_management:    GP proactively plans exits and facilitates M&A
        portfolio_company_survival_rate: Fraction of portfolio companies still operating
        avg_time_to_next_round_months:   Average months from initial investment to next round
        """
        warnings: list[str] = []
        recommendations: list[str] = []

        # Determine highest achieved level (cumulative capability ladder)
        if has_exit_oriented_management and has_strategic_empowerment:
            level = 4
        elif has_strategic_empowerment and has_3r_services:
            level = 3
        elif has_3r_services and has_financial_monitoring:
            level = 2
        elif has_financial_monitoring:
            level = 1
        else:
            level = 0  # No meaningful post-investment capability

        score = self.LEVEL_SCORES.get(level, 0)

        # Level-specific analysis
        if level <= 2:
            warnings.append(
                f"GP投后管理仅达到第{level}层境界（最高40分，当前{score}分）。"
                "缺乏战略赋能与退出导向型投后能力，难以帮助早期项目穿越死亡谷。"
            )
            recommendations.append(
                "建议GP重点培养第3层（战略与业务赋能）能力："
                "建立行业资源网络，能够主动为被投企业导入标杆客户和战略合作伙伴。"
            )

        if level < 4:
            recommendations.append(
                "缺乏第4层（退出导向型投后）能力：GP应主动规划退出路径，"
                "提前3年开始并购标的梳理，而非被动等待IPO窗口。"
            )

        if level >= 3:
            recommendations.append(
                f"GP已具备第{level}层投后能力（{score}/40分），"
                "具备穿越市场周期的核心实力。重点检验其战略赋能的真实案例与成功率。"
            )

        # Survival rate check
        if portfolio_company_survival_rate < 0.5:
            warnings.append(
                f"被投企业存活率 {portfolio_company_survival_rate:.0%} 偏低，"
                "反映投后管理对企业发展的实质帮助有限，需深入核查原因。"
            )

        # Next-round timing check
        if avg_time_to_next_round_months > 24:
            warnings.append(
                f"被投企业平均 {avg_time_to_next_round_months:.0f} 个月完成下一轮融资，"
                "超过行业正常周期（18个月），可能反映GP资源导入效率不足。"
            )

        level_desc = {
            0: "无有效投后管理能力",
            1: "第一境界：统计统筹（查账/财务监控）",
            2: "第二境界：3R服务（PR公关/HR招聘/IR投资者关系）",
            3: "第三境界：战略与业务赋能（行业资源导入/客户对接）",
            4: "第四境界：退出导向型投后（主动规划退出路径/并购撮合）",
        }

        summary = (
            f"GP投后管理境界: {level_desc.get(level, '未知')} | "
            f"综合得分: {score}/40 | "
            f"被投存活率: {portfolio_company_survival_rate:.0%} | "
            f"平均下轮融资: {avg_time_to_next_round_months:.0f}个月"
        )

        return PostInvestmentResult(
            level=level,
            score=score,
            summary=summary,
            warnings=warnings,
            recommendations=recommendations,
        )


# ---------------------------------------------------------------------------
# Double-Down Follow-on Decision Model / 拐点追投决策模型
# ---------------------------------------------------------------------------

@dataclass
class DoubleDownResult:
    """拐点追投决策结果 / Inflection-point follow-on decision result."""
    signal_strength: float          # 0-100 拐点信号强度
    recommended_action: str         # "strong_follow_on" / "cautious_follow_on" / "no_follow_on"
    suggested_amount_rmb: float     # 建议追投金额（亿元）
    summary: str
    warnings: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)


class DoubleDownDecisionModel:
    """
    拐点追投决策模型（跨越死亡谷）
    Inflection-Point Double-Down Decision Model (Crossing the Valley of Death)

    When early-stage projects pass the Valley of Death (死亡谷), specific
    inflection signals should trigger a "big bet" recommendation rather than
    being deterred by higher valuations.

    Signal weights (total 100 pts):
    - tech_milestone_achieved:     30 pts (良率突破/成本降至商用水平)
    - benchmark_customer_secured:  25 pts (标杆客户验证)
    - revenue_inflection:          20 pts (营收出现拐点)
    - competitive_moat_strengthened: 15 pts (竞争壁垒加强)
    - follow_on_round_quality:     10 pts (top_tier=10, mid_tier=5, weak=0)

    Decision rules:
    - Signal ≥ 70 AND valuation increase < 5x → Strong follow-on
    - Signal ≥ 50 BUT valuation increase > 5x → Cautious follow-on
    - Signal < 50 → No follow-on (valuation appreciation alone is not enough)
    """

    SIGNAL_WEIGHTS = {
        "tech_milestone": 30,
        "benchmark_customer": 25,
        "revenue_inflection": 20,
        "competitive_moat": 15,
        "follow_on_quality_max": 10,
    }

    FOLLOW_ON_QUALITY_SCORES = {
        "top_tier": 10,
        "mid_tier": 5,
        "weak": 0,
    }

    def decide(
        self,
        *,
        initial_investment_rmb: float,          # 首轮投资额（亿元）
        current_valuation_rmb: float,           # 当前估值（亿元）
        initial_valuation_rmb: float,           # 首轮估值（亿元）
        tech_milestone_achieved: bool,          # 技术里程碑是否达成
        benchmark_customer_secured: bool,       # 是否拿到标杆客户验证
        revenue_inflection: bool,               # 营收是否出现拐点
        competitive_moat_strengthened: bool,    # 竞争壁垒是否加强
        follow_on_round_quality: str,           # "top_tier" / "mid_tier" / "weak"
        fund_remaining_capacity_rmb: float,     # 基金剩余可投额度（亿元）
    ) -> DoubleDownResult:
        """
        Decide whether to follow on at an inflection point.

        Parameters
        ----------
        initial_investment_rmb:        First-round investment amount (亿元)
        current_valuation_rmb:         Current company valuation (亿元)
        initial_valuation_rmb:         Valuation at first investment (亿元)
        tech_milestone_achieved:       Key tech milestone reached (e.g., yield breakthrough)
        benchmark_customer_secured:    Marquee customer validation obtained
        revenue_inflection:            Revenue growth inflection point observed
        competitive_moat_strengthened: Competitive barriers have materially strengthened
        follow_on_round_quality:       Quality of co-investors in follow-on round
        fund_remaining_capacity_rmb:   Remaining uninvested capacity in fund (亿元)
        """
        warnings: list[str] = []
        recommendations: list[str] = []

        # --- Calculate inflection signal strength / 计算拐点信号强度 ---
        signal_strength = 0.0
        if tech_milestone_achieved:
            signal_strength += self.SIGNAL_WEIGHTS["tech_milestone"]
        if benchmark_customer_secured:
            signal_strength += self.SIGNAL_WEIGHTS["benchmark_customer"]
        if revenue_inflection:
            signal_strength += self.SIGNAL_WEIGHTS["revenue_inflection"]
        if competitive_moat_strengthened:
            signal_strength += self.SIGNAL_WEIGHTS["competitive_moat"]
        quality_score = self.FOLLOW_ON_QUALITY_SCORES.get(follow_on_round_quality, 0)
        signal_strength += quality_score

        # --- Valuation increase multiple / 估值涨幅倍数 ---
        if initial_valuation_rmb > 0:
            valuation_increase = current_valuation_rmb / initial_valuation_rmb
        else:
            valuation_increase = 1.0

        # --- Decision logic / 决策逻辑 ---
        if signal_strength >= 70 and valuation_increase < 5.0:
            recommended_action = "strong_follow_on"
            # Suggest up to 30% of remaining capacity, max 3x initial investment
            suggested_amount = min(
                fund_remaining_capacity_rmb * 0.30,
                initial_investment_rmb * 3.0,
            )
            recommendations.append(
                f"拐点信号强度 {signal_strength:.0f}/100，估值涨幅 {valuation_increase:.1f}x。"
                "项目已经过死亡谷关键验证，建议大额加注。"
                "估值变贵是追投的理由，不是拒绝的理由。"
            )
            if tech_milestone_achieved and benchmark_customer_secured:
                recommendations.append(
                    "技术里程碑+标杆客户双重验证完成，这是最强的拐点信号组合，"
                    "参考美元基金在头部项目集中加仓的策略。"
                )

        elif signal_strength >= 50 and valuation_increase < 5.0:
            # Decent signal, reasonable valuation — cautious follow-on
            recommended_action = "cautious_follow_on"
            suggested_amount = min(
                fund_remaining_capacity_rmb * 0.20,
                initial_investment_rmb * 2.0,
            )
            recommendations.append(
                f"拐点信号强度 {signal_strength:.0f}/100，估值涨幅 {valuation_increase:.1f}x，价格合理。"
                "信号尚未达到大额加注门槛，建议适度追投并设定下一里程碑节点作为进一步加仓触发点。"
            )

        elif signal_strength >= 50 and valuation_increase >= 5.0:
            recommended_action = "cautious_follow_on"
            # Conservative: max 15% of remaining capacity, max 1.5x initial
            suggested_amount = min(
                fund_remaining_capacity_rmb * 0.15,
                initial_investment_rmb * 1.5,
            )
            warnings.append(
                f"估值较首轮增长 {valuation_increase:.1f}x（>5倍），溢价较高。"
                "虽有拐点信号，但需控制追投仓位，避免过度集中风险。"
            )
            recommendations.append(
                "建议谨慎追投，控制仓位在首轮投资额的1-1.5倍以内，"
                "重点验证下一个里程碑节点后再决定是否进一步加注。"
            )

        elif signal_strength >= 70 and valuation_increase >= 5.0:
            recommended_action = "cautious_follow_on"
            # Signal is strong but valuation is very high
            suggested_amount = min(
                fund_remaining_capacity_rmb * 0.20,
                initial_investment_rmb * 2.0,
            )
            warnings.append(
                f"拐点信号强（{signal_strength:.0f}/100）但估值增幅已达 {valuation_increase:.1f}x，"
                "建议控制追投仓位并在协议中加入保护条款。"
            )

        else:
            recommended_action = "no_follow_on"
            suggested_amount = 0.0
            warnings.append(
                f"拐点信号强度仅 {signal_strength:.0f}/100，尚未出现明确的死亡谷穿越信号。"
                "估值上涨本身不是追投的理由，关键缺失信号："
            )
            missing = []
            if not tech_milestone_achieved:
                missing.append("技术里程碑未达成")
            if not benchmark_customer_secured:
                missing.append("标杆客户未落地")
            if not revenue_inflection:
                missing.append("营收拐点未出现")
            if missing:
                warnings.append("  · " + " / ".join(missing))
            recommendations.append(
                "建议持续观察，待核心里程碑（良率/成本/标杆客户）达成后再评估追投。"
                "过早加注可能使基金陷入沉没成本陷阱。"
            )

        # Fund capacity check
        if suggested_amount > fund_remaining_capacity_rmb * 0.5:
            warnings.append(
                f"建议追投金额 {suggested_amount:.2f}亿 超过基金剩余可投额度的50%，"
                "建议评估组合集中度风险，考虑是否引入联合投资方。"
            )
            suggested_amount = min(suggested_amount, fund_remaining_capacity_rmb * 0.5)

        if follow_on_round_quality == "weak":
            warnings.append(
                "本轮跟投方质量偏弱，缺乏顶级机构背书，需额外审查估值合理性。"
            )

        action_labels = {
            "strong_follow_on": "✅ 强烈建议追投",
            "cautious_follow_on": "⚠️ 谨慎追投，控制仓位",
            "no_follow_on": "❌ 不建议追投",
        }

        summary = (
            f"{action_labels.get(recommended_action, recommended_action)} | "
            f"拐点信号: {signal_strength:.0f}/100 | "
            f"估值涨幅: {valuation_increase:.1f}x | "
            f"建议追投金额: {suggested_amount:.2f}亿元"
        )

        return DoubleDownResult(
            signal_strength=round(signal_strength, 1),
            recommended_action=recommended_action,
            suggested_amount_rmb=round(suggested_amount, 2),
            summary=summary,
            warnings=warnings,
            recommendations=recommendations,
        )
