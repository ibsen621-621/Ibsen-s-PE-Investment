"""
交易结构与底线防守模块
Deal Structure & Defensive Clause Module

Implements:
- AntiDilutionChecker: Old-share transfer and anti-dilution clause detection
- BuybackFeasibilityChecker: Buyback / valuation adjustment clause feasibility

All amounts in 亿元 RMB.
"""

from __future__ import annotations

from dataclasses import dataclass, field


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
