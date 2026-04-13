"""
基本面尽调定量交叉验证模块
Fundamental Due Diligence Quantitative Cross-Validation Module

Implements:
- DuPontAnalyzer: ROE decomposition into three business model drivers
- GrowthQualityChecker: Pseudo-growth detection (伪增长检测)

All amounts in 亿元 RMB.
"""

from __future__ import annotations

from dataclasses import dataclass, field


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
