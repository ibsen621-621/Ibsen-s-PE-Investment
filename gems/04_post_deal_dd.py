# ==== GEMS FILE: 04_post_deal_dd.py ====
# Merged from: post_investment.py, deal_structure.py, due_diligence.py
# For Gemini Gems knowledge base — v4.0
# NOTE: This is a knowledge reference file, not executable production code.
#       Cross-module imports have been annotated for clarity.

from __future__ import annotations
from dataclasses import dataclass, field


# ==== ORIGIN: post_investment.py ====
"""
投后管理与拐点追投模块
Post-Investment Management & Inflection-Point Follow-on Module

Implements:
- GPPostInvestmentEvaluator: Quantifies GP post-investment capabilities (4 levels, 40pts)
- DoubleDownDecisionModel: Follow-on investment decision at inflection points

All amounts in 亿元 RMB.
"""




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


# ==== ORIGIN: deal_structure.py ====
"""
交易结构与底线防守模块
Deal Structure & Defensive Clause Module

Implements:
- AntiDilutionChecker: Old-share transfer and anti-dilution clause detection
- BuybackFeasibilityChecker: Buyback / valuation adjustment clause feasibility

All amounts in 亿元 RMB.
"""




# ---------------------------------------------------------------------------
# Anti-Dilution Checker / 老股转让与反稀释检验
# ---------------------------------------------------------------------------

@dataclass
class AntiDilutionResult:
    """老股转让与反稀释检验结果 / Anti-dilution and old-share transfer result."""
    founder_red_flag: bool          # 创始人套现红旗
    anti_dilution_triggered: bool   # 反稀释条款是否触发
    valuation_anchor_impact: str    # 对下一轮估值锚的影响评估
    risk_level: str                 # "low" / "medium" / "high" / "critical"
    summary: str
    warnings: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)


class AntiDilutionChecker:
    """
    老股转让与反稀释条款检验器
    Old-Share Transfer & Anti-Dilution Clause Checker

    Detects red flags when founders sell shares at steep discounts and evaluates
    whether anti-dilution clauses are triggered.

    Key rules:
    - Founder selling at ≥60% discount (3-4折 of latest round price) → Red flag
    - Selling > 20% of founder's stake → Suspicious motivation
    - Anti-dilution triggers: full ratchet is more aggressive than weighted average
    """

    def check(
        self,
        *,
        founder_selling_pct: float,             # 创始人出售股份比例（占其持股%）
        selling_discount_pct: float,            # 相对最新轮估值的折扣（0-100, 60=6折）
        latest_round_valuation_rmb: float,      # 最新轮融资估值（亿元）
        has_anti_dilution_clause: bool,         # 是否有反稀释条款
        anti_dilution_type: str,               # "full_ratchet" / "weighted_average" / "none"
    ) -> AntiDilutionResult:
        """
        Check old-share transfer for red flags and anti-dilution triggers.

        Parameters
        ----------
        founder_selling_pct:        % of founder's total stake being sold (0-100)
        selling_discount_pct:       Discount vs latest round price (0-100; 60=60% off)
        latest_round_valuation_rmb: Post-money valuation of latest round (亿元)
        has_anti_dilution_clause:   Whether any anti-dilution clause exists
        anti_dilution_type:         Type of anti-dilution protection
        """
        warnings: list[str] = []
        recommendations: list[str] = []

        # --- Red flag: deep discount on founder share sale ---
        founder_red_flag = False
        if selling_discount_pct >= 60:
            founder_red_flag = True
            warnings.append(
                f"⚠️ 红旗！创始人以 {100 - selling_discount_pct:.0f}折（折扣{selling_discount_pct:.0f}%）"
                f"出售老股，相对最新轮估值 {latest_round_valuation_rmb:.1f}亿 大幅折价套现。"
                "此举通常预示创始人对公司前景信心不足或有强烈的流动性需求。"
            )
            recommendations.append(
                "在决定跟进投资前，强制要求创始人说明折价出售原因："
                "是个人财务压力、股权纠纷，还是对业务前景的悲观预期？"
            )
        elif selling_discount_pct >= 40:
            warnings.append(
                f"创始人以 {100 - selling_discount_pct:.0f}折出售老股，折价 {selling_discount_pct:.0f}%，"
                "需关注其套现动机，建议书面了解原因。"
            )

        # --- Red flag: large proportion of founder stake sold ---
        if founder_selling_pct > 20:
            founder_red_flag = True
            warnings.append(
                f"创始人出售比例达 {founder_selling_pct:.0f}%，超过20%警戒线。"
                "大额减持可能严重影响市场对创始人信心的判断，"
                "并可能触发其他投资人的反稀释或优先权条款。"
            )

        # --- Valuation anchor impact ---
        effective_price_fraction = 1.0 - selling_discount_pct / 100.0
        effective_valuation_rmb = latest_round_valuation_rmb * effective_price_fraction

        if selling_discount_pct >= 40:
            valuation_anchor_impact = (
                f"老股实际成交估值约 {effective_valuation_rmb:.2f}亿（最新轮的"
                f"{effective_price_fraction:.0%}），"
                "可能成为下一轮融资的隐性估值锚，导致新投资方以此为基础压低入场价格。"
            )
            warnings.append(
                f"老股折价可能破坏下一轮融资的估值叙事：市场传递信号是估值"
                f"{latest_round_valuation_rmb:.1f}亿存在水分。"
            )
        else:
            valuation_anchor_impact = (
                f"老股折价幅度在合理范围内（{selling_discount_pct:.0f}%），"
                "对下一轮估值锚影响有限，属正常流动性折价。"
            )

        # --- Anti-dilution trigger check ---
        anti_dilution_triggered = False
        if has_anti_dilution_clause and selling_discount_pct >= 30:
            anti_dilution_triggered = True
            if anti_dilution_type == "full_ratchet":
                warnings.append(
                    "Full Ratchet完全棘轮反稀释条款可能被触发："
                    "投资人有权将持股成本调整至本次老股成交价，"
                    "将对创始人持股比例产生严重稀释，需立即核查条款细节。"
                )
            elif anti_dilution_type == "weighted_average":
                warnings.append(
                    "加权平均反稀释条款可能被触发：影响相对温和，"
                    "但仍将增加创始人的稀释幅度，建议核查触发门槛和计算公式。"
                )

        if not has_anti_dilution_clause:
            recommendations.append(
                "当前无反稀释条款保护：在市场下行或估值回调时，"
                "投资人将无任何条款保护，建议在下一轮投资时明确加入反稀释条款。"
            )

        # --- Risk level ---
        if founder_red_flag and anti_dilution_triggered:
            risk_level = "critical"
        elif founder_red_flag:
            risk_level = "high"
        elif anti_dilution_triggered or selling_discount_pct >= 40:
            risk_level = "medium"
        else:
            risk_level = "low"

        risk_labels = {
            "low": "✅ 低风险",
            "medium": "⚠️ 中等风险",
            "high": "🔴 高风险",
            "critical": "🚨 极高风险",
        }

        summary = (
            f"老股转让风险评估: {risk_labels[risk_level]} | "
            f"折价幅度: {selling_discount_pct:.0f}% | "
            f"出售比例: {founder_selling_pct:.0f}% | "
            f"反稀释触发: {'是' if anti_dilution_triggered else '否'}"
        )

        return AntiDilutionResult(
            founder_red_flag=founder_red_flag,
            anti_dilution_triggered=anti_dilution_triggered,
            valuation_anchor_impact=valuation_anchor_impact,
            risk_level=risk_level,
            summary=summary,
            warnings=warnings,
            recommendations=recommendations,
        )


# ---------------------------------------------------------------------------
# Buyback Feasibility Checker / 回购与对赌条款可行性检验
# ---------------------------------------------------------------------------

@dataclass
class BuybackFeasibilityResult:
    """回购与对赌条款可行性评估结果 / Buyback and valuation-adjustment clause result."""
    is_trigger_metric_reasonable: bool     # 对赌指标是否合理
    is_buyback_executable: bool            # 回购在财务上是否可执行
    has_meaningful_guarantee: bool         # 是否有实质性担保
    feasibility_score: float               # 0-100 可行性综合评分
    summary: str
    warnings: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)


class BuybackFeasibilityChecker:
    """
    回购与对赌条款可行性检验器
    Buyback & Valuation-Adjustment Clause Feasibility Checker

    Evaluates whether a buyback agreement is practically enforceable, not just
    legally valid. Key insight: when the buyback trigger fires, the company is
    likely already in financial distress — making buyback execution extremely
    difficult without founder personal asset backing.
    """

    # "Reasonable" growth commitment thresholds / 合理对赌增速阈值
    MAX_REASONABLE_REVENUE_GROWTH = 0.50    # 50% YoY revenue growth
    MAX_REASONABLE_PROFIT_GROWTH = 0.60     # 60% YoY profit growth

    def check(
        self,
        *,
        buyback_trigger_metric: str,            # "revenue" / "profit" / "ipo_timeline"
        buyback_trigger_value: float,           # 触发回购的指标目标值
        actual_value: float,                    # 实际达成值
        founder_personal_assets_rmb: float,    # 创始人个人可变现资产（亿元）
        has_joint_liability: bool,              # 是否有实控人连带责任担保
        company_cash_reserve_rmb: float,        # 公司现金储备（亿元）
        buyback_amount_rmb: float,              # 回购总金额（亿元）
    ) -> BuybackFeasibilityResult:
        """
        Check if a buyback clause is realistically enforceable.

        Parameters
        ----------
        buyback_trigger_metric:       Metric type for buyback trigger
        buyback_trigger_value:        Target value for the trigger metric
        actual_value:                 Actual achieved metric value
        founder_personal_assets_rmb:  Founder's liquid personal assets (亿元)
        has_joint_liability:          Does the controlling shareholder have joint liability?
        company_cash_reserve_rmb:     Company's current cash position (亿元)
        buyback_amount_rmb:           Total buyback obligation amount (亿元)
        """
        warnings: list[str] = []
        recommendations: list[str] = []

        # --- Check if trigger metric is reasonable ---
        is_trigger_metric_reasonable = True

        if buyback_trigger_metric == "revenue":
            if buyback_trigger_value > 0 and actual_value > 0:
                implied_growth = (buyback_trigger_value - actual_value) / actual_value
                if implied_growth > self.MAX_REASONABLE_REVENUE_GROWTH:
                    is_trigger_metric_reasonable = False
                    warnings.append(
                        f"对赌营收目标隐含增速 {implied_growth:.0%}，"
                        f"超过合理阈值 {self.MAX_REASONABLE_REVENUE_GROWTH:.0%}。"
                        "过高的对赌目标往往是不可执行的'空头支票'，"
                        "且可能诱导管理层短视行为（如虚构收入）。"
                    )
        elif buyback_trigger_metric == "profit":
            if buyback_trigger_value > 0 and actual_value > 0:
                implied_growth = (buyback_trigger_value - actual_value) / actual_value
                if implied_growth > self.MAX_REASONABLE_PROFIT_GROWTH:
                    is_trigger_metric_reasonable = False
                    warnings.append(
                        f"对赌利润目标隐含增速 {implied_growth:.0%}，"
                        f"超过合理阈值 {self.MAX_REASONABLE_PROFIT_GROWTH:.0%}。"
                        "高利润对赌可能导致企业削减研发和销售费用以保护短期利润，"
                        "牺牲长期竞争力换取短期达标。"
                    )
        elif buyback_trigger_metric == "ipo_timeline":
            warnings.append(
                "IPO时间线对赌：上市进度受监管政策、市场环境等外部因素影响极大，"
                "属于不可控对赌指标，建议改为可控的财务指标对赌。"
            )

        # --- Check if trigger has fired ---
        trigger_fired = actual_value < buyback_trigger_value

        # --- Buyback executability analysis ---
        total_available_assets = company_cash_reserve_rmb
        if has_joint_liability:
            total_available_assets += founder_personal_assets_rmb

        coverage_ratio = total_available_assets / buyback_amount_rmb if buyback_amount_rmb > 0 else 0.0
        is_buyback_executable = coverage_ratio >= 1.0

        if trigger_fired:
            warnings.append(
                f"对赌触发！实际值 {actual_value:.2f} 未达目标 {buyback_trigger_value:.2f}，"
                f"回购条款已触发，回购金额 {buyback_amount_rmb:.2f}亿元。"
            )

        if not is_buyback_executable:
            shortfall = buyback_amount_rmb - total_available_assets
            warnings.append(
                f"回购可执行性存疑：可调动资产 {total_available_assets:.2f}亿"
                f"（公司现金 {company_cash_reserve_rmb:.2f}亿"
                + (f" + 创始人个人资产 {founder_personal_assets_rmb:.2f}亿" if has_joint_liability else "")
                + f"）不足以覆盖回购金额 {buyback_amount_rmb:.2f}亿，"
                f"缺口 {shortfall:.2f}亿。"
                "对赌触发时企业通常已现金流紧张，回购很可能是空头支票。"
            )

        if not has_joint_liability:
            warnings.append(
                "无实控人连带责任担保：法律层面的回购义务仅约束公司主体，"
                "当公司资产不足时投资人将面临实质性损失，无法追索创始人个人资产。"
            )
            recommendations.append(
                "强烈建议在协议中加入实控人连带责任担保条款，"
                "确保回购义务能够穿透到个人资产层面。"
            )

        has_meaningful_guarantee = has_joint_liability and coverage_ratio >= 0.5

        # --- Feasibility score ---
        score = 100.0
        if not is_trigger_metric_reasonable:
            score -= 25
        if not has_joint_liability:
            score -= 30
        if coverage_ratio < 1.0:
            score -= max(0, (1.0 - coverage_ratio) * 30)
        if buyback_trigger_metric == "ipo_timeline":
            score -= 15
        feasibility_score = max(0.0, min(100.0, score))

        summary = (
            f"回购可行性评分: {feasibility_score:.0f}/100 | "
            f"触发指标合理性: {'✅' if is_trigger_metric_reasonable else '❌'} | "
            f"连带责任担保: {'✅' if has_joint_liability else '❌'} | "
            f"资产覆盖率: {coverage_ratio:.1%} | "
            f"{'⚠️ 对赌已触发' if trigger_fired else '对赌未触发'}"
        )

        if feasibility_score >= 70:
            recommendations.append("回购条款整体可行性尚可，但仍需持续监控公司财务状况。")
        else:
            recommendations.append(
                "回购条款存在重大可执行性风险，建议在当前条款外叠加其他保护措施，"
                "如股权质押、优先清算权或分期支付安排。"
            )

        return BuybackFeasibilityResult(
            is_trigger_metric_reasonable=is_trigger_metric_reasonable,
            is_buyback_executable=is_buyback_executable,
            has_meaningful_guarantee=has_meaningful_guarantee,
            feasibility_score=round(feasibility_score, 1),
            summary=summary,
            warnings=warnings,
            recommendations=recommendations,
        )


# ==== ORIGIN: due_diligence.py ====
"""
基本面尽调定量交叉验证模块
Fundamental Due Diligence Quantitative Cross-Validation Module

Implements:
- DuPontAnalyzer: ROE decomposition into three business model drivers
- GrowthQualityChecker: Pseudo-growth detection (伪增长检测)

All amounts in 亿元 RMB.
"""




# ---------------------------------------------------------------------------
# DuPont Analyzer / 杜邦分析
# ---------------------------------------------------------------------------

@dataclass
class DuPontResult:
    """杜邦分析结果 / DuPont analysis result."""
    net_profit_margin: float        # 净利润率
    asset_turnover: float           # 资产周转率
    equity_multiplier: float        # 权益乘数（杠杆）
    roe: float                      # 净资产收益率 = 三因子之积
    business_model: str             # 业务模式："high_margin" / "high_turnover" / "high_leverage" / "balanced"
    model_description: str          # 模式描述
    summary: str
    warnings: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)


class DuPontAnalyzer:
    """
    杜邦分析器 — ROE三因子拆解
    DuPont Analyzer — Three-Factor ROE Decomposition

    ROE = Net Profit Margin × Asset Turnover × Equity Multiplier
          净利润率          × 资产周转率       × 权益乘数

    Business model classification:
    - High Margin (高利润模式):    Net margin > 15%  → 高端制造、医药、软件
    - High Turnover (高周转模式):  Asset turnover > 2.0 → 消费零售、电商
    - High Leverage (高杠杆模式):  Equity multiplier > 3.0 → 地产、金融 (⚠️ 风险)
    - Balanced (均衡模式):         No single dominant factor
    """

    # Thresholds / 判断阈值
    HIGH_MARGIN_THRESHOLD = 0.15       # 净利润率 > 15%
    HIGH_TURNOVER_THRESHOLD = 2.0      # 资产周转率 > 2.0x
    HIGH_LEVERAGE_THRESHOLD = 3.0      # 权益乘数 > 3.0x

    def analyze(
        self,
        *,
        net_profit_rmb: float,      # 净利润（亿元）
        revenue_rmb: float,         # 营业收入（亿元）
        total_assets_rmb: float,    # 总资产（亿元）
        total_equity_rmb: float,    # 股东权益（亿元）
    ) -> DuPontResult:
        """
        Decompose ROE into its three DuPont components.

        Parameters
        ----------
        net_profit_rmb:     Net profit (亿元)
        revenue_rmb:        Total revenue (亿元)
        total_assets_rmb:   Total assets (亿元)
        total_equity_rmb:   Shareholders' equity (亿元)
        """
        warnings: list[str] = []
        recommendations: list[str] = []

        # Guard against division by zero
        if revenue_rmb <= 0:
            raise ValueError("revenue_rmb must be positive")
        if total_assets_rmb <= 0:
            raise ValueError("total_assets_rmb must be positive")
        if total_equity_rmb <= 0:
            raise ValueError("total_equity_rmb must be positive")

        # --- DuPont three-factor decomposition ---
        net_profit_margin = net_profit_rmb / revenue_rmb
        asset_turnover = revenue_rmb / total_assets_rmb
        equity_multiplier = total_assets_rmb / total_equity_rmb
        roe = net_profit_margin * asset_turnover * equity_multiplier

        # --- Business model classification ---
        is_high_margin = net_profit_margin > self.HIGH_MARGIN_THRESHOLD
        is_high_turnover = asset_turnover > self.HIGH_TURNOVER_THRESHOLD
        is_high_leverage = equity_multiplier > self.HIGH_LEVERAGE_THRESHOLD

        if is_high_leverage:
            business_model = "high_leverage"
            model_description = (
                f"高杠杆模式（权益乘数 {equity_multiplier:.1f}x）："
                "典型于地产、金融行业。高杠杆放大收益的同时也放大风险，"
                "在信用收缩周期中可能面临流动性危机。"
            )
            warnings.append(
                f"权益乘数 {equity_multiplier:.1f}x 超过 {self.HIGH_LEVERAGE_THRESHOLD}x 警戒线。"
                "高杠杆经营模式在利率上升或融资收紧环境下存在重大财务风险。"
            )
        elif is_high_margin and is_high_turnover:
            business_model = "high_margin_turnover"
            model_description = (
                f"高利润+高周转复合模式（净利率 {net_profit_margin:.1%}, "
                f"周转率 {asset_turnover:.2f}x）：相对罕见，通常代表极强的竞争壁垒，"
                "如具备定价权的高频消费品企业。"
            )
            recommendations.append(
                "高利润+高周转兼具是企业竞争优势极强的信号，建议深入验证其可持续性。"
            )
        elif is_high_margin:
            business_model = "high_margin"
            model_description = (
                f"高利润模式（净利率 {net_profit_margin:.1%}）："
                "典型于高端制造、创新医药、企业软件。依赖技术壁垒或品牌溢价，"
                "增长相对稳健但扩张速度通常较慢。"
            )
            recommendations.append(
                "高利润模式：关键验证点是利润率的可持续性——"
                "是否面临仿制药/国产替代竞争？技术壁垒有多高？"
            )
        elif is_high_turnover:
            business_model = "high_turnover"
            model_description = (
                f"高周转模式（资产周转率 {asset_turnover:.2f}x）："
                "典型于消费零售、电商、快消。依赖极高的运营效率，"
                "单次利润薄但通过高频次积累总回报。"
            )
            recommendations.append(
                "高周转模式：关键验证点是运营效率的护城河——"
                "是否具备供应链、SKU选品或履约能力上的不可复制优势？"
            )
        else:
            business_model = "balanced"
            model_description = (
                f"均衡模式（净利率 {net_profit_margin:.1%}, "
                f"周转率 {asset_turnover:.2f}x, 杠杆 {equity_multiplier:.1f}x）："
                "无单一驱动因子，增长路径相对多元，需结合行业背景具体分析。"
            )

        # ROE quality check
        if roe < 0.05:
            warnings.append(
                f"ROE {roe:.1%} 低于5%，资本回报率不足，"
                "需判断是处于高投入成长期还是竞争力不足导致的结构性低回报。"
            )
        elif roe >= 0.20:
            recommendations.append(
                f"ROE {roe:.1%} ≥ 20%，资本回报率优秀，"
                "但需排除高杠杆拉高ROE的情况（已在权益乘数中检查）。"
            )

        summary = (
            f"杜邦分析 | 净利润率: {net_profit_margin:.1%} | "
            f"资产周转率: {asset_turnover:.2f}x | "
            f"权益乘数: {equity_multiplier:.2f}x | "
            f"ROE: {roe:.1%} | 模式: {model_description.split('：')[0]}"
        )

        return DuPontResult(
            net_profit_margin=round(net_profit_margin, 4),
            asset_turnover=round(asset_turnover, 4),
            equity_multiplier=round(equity_multiplier, 4),
            roe=round(roe, 4),
            business_model=business_model,
            model_description=model_description,
            summary=summary,
            warnings=warnings,
            recommendations=recommendations,
        )


# ---------------------------------------------------------------------------
# Growth Quality Checker / 增长质量检验（伪增长检测）
# ---------------------------------------------------------------------------

@dataclass
class GrowthQualityResult:
    """增长质量验证结果 / Growth quality validation result."""
    is_genuine_growth: bool         # 是否为真实增长（非伪增长）
    quality_score: float            # 0-100 增长质量综合评分
    pseudo_growth_flags: list[str]  # 伪增长信号列表
    summary: str
    warnings: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)


class GrowthQualityChecker:
    """
    增长质量检验器 — 伪增长检测
    Growth Quality Checker — Pseudo-Growth Detection

    Validates whether reported growth is genuine and sustainable, or driven by
    subsidies, low-quality user acquisition, or financial engineering.

    Key checks:
    - LTV/CAC ratio: < 3x → unsustainable customer acquisition
    - User retention: < 30% monthly → no product stickiness
    - NPS: < 0 → poor reputation, no moat
    - Subsidy dependence: > 30% of revenue → fake growth
    - SaaS NDR: < 100% → customer attrition
    """

    # Quality thresholds / 质量阈值
    MIN_LTV_CAC_RATIO = 3.0         # Minimum viable LTV/CAC
    MIN_RETENTION_RATE_TOC = 30.0   # Min monthly retention % for ToC
    MIN_RETENTION_RATE_TOB = 70.0   # Min annual retention % for ToB/SaaS
    MAX_SUBSIDY_REVENUE_PCT = 30.0  # Max subsidy as % of revenue
    MIN_NPS = 0                     # Minimum acceptable NPS
    MIN_NDR = 100.0                 # Min Net Dollar Retention for SaaS

    def check(
        self,
        *,
        gmv_rmb: float,                         # 平台GMV（亿元）
        revenue_rmb: float,                     # 确认收入（亿元）
        user_retention_rate_pct: float,         # 用户留存率（%，月留存或年留存）
        nps_score: float,                       # 净推荐值 -100 to 100
        customer_acquisition_cost_rmb: float,   # 获客成本（亿元/百万用户 or 单用户）
        lifetime_value_rmb: float,              # 用户生命周期价值（同单位）
        revenue_from_subsidies_pct: float,      # 补贴占收入比例（%）
        business_model: str,                    # "to_c" / "to_b" / "saas"
        net_dollar_retention_pct: float = 100.0,  # SaaS NDR（%），仅SaaS适用
    ) -> GrowthQualityResult:
        """
        Check whether reported growth is genuine or pseudo-growth.

        Parameters
        ----------
        gmv_rmb:                     Platform GMV (亿元)
        revenue_rmb:                 Recognized revenue (亿元)
        user_retention_rate_pct:     User retention rate (% — monthly for ToC, annual for ToB/SaaS)
        nps_score:                   Net Promoter Score (-100 to 100)
        customer_acquisition_cost_rmb: CAC per unit (亿元/unit, must match LTV unit)
        lifetime_value_rmb:          LTV per unit (亿元/unit)
        revenue_from_subsidies_pct:  Subsidy as % of revenue
        business_model:              Business model type
        net_dollar_retention_pct:    SaaS Net Dollar Retention (% — only relevant for "saas")
        """
        warnings: list[str] = []
        recommendations: list[str] = []
        pseudo_growth_flags: list[str] = []
        score = 100.0  # Start with perfect score, deduct for issues

        # --- Check 1: LTV/CAC ratio ---
        if customer_acquisition_cost_rmb > 0:
            ltv_cac = lifetime_value_rmb / customer_acquisition_cost_rmb
        else:
            ltv_cac = float("inf")

        if ltv_cac < self.MIN_LTV_CAC_RATIO:
            pseudo_growth_flags.append(
                f"LTV/CAC = {ltv_cac:.1f}x < {self.MIN_LTV_CAC_RATIO}x"
            )
            warnings.append(
                f"LTV/CAC仅 {ltv_cac:.1f}x，低于可持续阈值 {self.MIN_LTV_CAC_RATIO}x。"
                "以当前获客成本烧钱增长不可持续，用户质量或产品价值存在根本性问题。"
            )
            score -= 25
        elif ltv_cac >= 5.0:
            recommendations.append(
                f"LTV/CAC = {ltv_cac:.1f}x，获客经济模型优秀，"
                "具备规模化的财务基础。"
            )

        # --- Check 2: User retention ---
        if business_model == "to_c":
            retention_threshold = self.MIN_RETENTION_RATE_TOC
            retention_label = "月留存率"
        else:
            retention_threshold = self.MIN_RETENTION_RATE_TOB
            retention_label = "年留存率"

        if user_retention_rate_pct < retention_threshold:
            pseudo_growth_flags.append(
                f"{retention_label} {user_retention_rate_pct:.0f}% < {retention_threshold:.0f}%"
            )
            warnings.append(
                f"{retention_label}仅 {user_retention_rate_pct:.0f}%，"
                f"低于 {retention_threshold:.0f}% 基准线。"
                "产品粘性严重不足，用户增长依赖持续拉新而非口碑传播，"
                "属于典型的'漏水桶'式伪增长。"
            )
            score -= 25
        elif user_retention_rate_pct >= retention_threshold * 1.5:
            recommendations.append(
                f"{retention_label} {user_retention_rate_pct:.0f}% 优秀，"
                "产品具备强粘性和自然口碑传播潜力。"
            )

        # --- Check 3: NPS ---
        if nps_score < self.MIN_NPS:
            pseudo_growth_flags.append(f"NPS = {nps_score:.0f} < 0")
            warnings.append(
                f"NPS {nps_score:.0f} 为负值：用户口碑差，贬损者多于推荐者。"
                "无法依赖口碑传播降低获客成本，难以建立护城河，"
                "当前增长依赖持续营销投入维持。"
            )
            score -= 20
        elif nps_score >= 50:
            recommendations.append(
                f"NPS {nps_score:.0f} 优秀（≥50），具备强口碑传播效应和忠实用户基础。"
            )

        # --- Check 4: Subsidy dependence ---
        if revenue_from_subsidies_pct > self.MAX_SUBSIDY_REVENUE_PCT:
            pseudo_growth_flags.append(
                f"补贴占收入 {revenue_from_subsidies_pct:.0f}% > {self.MAX_SUBSIDY_REVENUE_PCT:.0f}%"
            )
            warnings.append(
                f"补贴占收入比例 {revenue_from_subsidies_pct:.0f}%，"
                f"超过 {self.MAX_SUBSIDY_REVENUE_PCT:.0f}% 警戒线。"
                "当前增长高度依赖补贴驱动，一旦补贴退坡将面临营收断崖下跌，"
                "属于典型的政策性伪增长。"
            )
            score -= 20

        # --- Check 5: GMV vs Revenue quality ---
        if gmv_rmb > 0 and revenue_rmb > 0:
            gmv_revenue_ratio = gmv_rmb / revenue_rmb
            if gmv_revenue_ratio > 20:
                warnings.append(
                    f"GMV/营收比达 {gmv_revenue_ratio:.0f}x，"
                    "可能存在以GMV掩盖真实变现能力不足的情况，"
                    "需核查货币化率（Take Rate）的合理性和可持续性。"
                )

        # --- Check 6: SaaS Net Dollar Retention ---
        if business_model == "saas":
            if net_dollar_retention_pct < self.MIN_NDR:
                pseudo_growth_flags.append(
                    f"NDR {net_dollar_retention_pct:.0f}% < {self.MIN_NDR:.0f}%"
                )
                warnings.append(
                    f"SaaS净收入留存率（NDR）{net_dollar_retention_pct:.0f}% < 100%："
                    "存量客户在净缩减，新增客户收入无法弥补流失，"
                    "增长本质上是在'漏桶'中注水，商业模式存在根本性问题。"
                )
                score -= 25
            elif net_dollar_retention_pct >= 120:
                recommendations.append(
                    f"SaaS NDR {net_dollar_retention_pct:.0f}% ≥ 120%，"
                    "存量客户持续扩容，具备典型的SaaS复利增长特征。"
                )

        # Final score cap
        score = max(0.0, min(100.0, score))
        is_genuine_growth = len(pseudo_growth_flags) == 0 and score >= 60

        flag_summary = (
            f"伪增长信号: {len(pseudo_growth_flags)}个 [{'; '.join(pseudo_growth_flags)}]"
            if pseudo_growth_flags
            else "无伪增长信号"
        )

        summary = (
            f"增长质量评分: {score:.0f}/100 | "
            f"{'✅ 真实增长' if is_genuine_growth else '❌ 存在伪增长风险'} | "
            f"LTV/CAC: {ltv_cac:.1f}x | NPS: {nps_score:.0f} | {flag_summary}"
        )

        if is_genuine_growth:
            recommendations.append(
                f"增长质量综合评分 {score:.0f}/100，增长信号真实可靠，"
                "具备规模化的基础条件。"
            )
        else:
            recommendations.append(
                f"增长质量评分 {score:.0f}/100，存在 {len(pseudo_growth_flags)} 个伪增长信号，"
                "建议在投资前要求管理层就各伪增长指标提供合理解释和改善路径。"
            )

        return GrowthQualityResult(
            is_genuine_growth=is_genuine_growth,
            quality_score=round(score, 1),
            pseudo_growth_flags=pseudo_growth_flags,
            summary=summary,
            warnings=warnings,
            recommendations=recommendations,
        )
