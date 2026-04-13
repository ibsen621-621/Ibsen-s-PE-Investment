"""
投资哲学检查器
Investment Philosophy Checker

Validates an investment thesis against the core philosophies:
1. Value speculation vs value investing
2. Political economy lens (hard tech / autonomous control)
3. Exit rate reality check
4. Hard-tech strategy evaluator (P/Strategic dimension)
"""

from __future__ import annotations

from dataclasses import dataclass, field


EXIT_RATE_BENCHMARKS = {
    "top_pe": (0.25, 0.28),      # 25-28% (source: [cite 203, 205])
    "top_vc": (0.12, 0.16),      # ~16% (source: [cite 207])
    "top_angel": (0.03, 0.05),   # < 5% (source: [cite 208])
}

# Technology path types / 技术路径类型
TECH_PATH_CORE_PLUGIN = "core_plugin_replacement"        # 核心插件替换（高容错）
TECH_PATH_SYSTEM_REBUILD = "system_infrastructure_rebuild"  # 系统性基础设施重构（极高风险）
TECH_PATH_INCREMENTAL = "incremental_improvement"        # 渐进式改良（中等）


@dataclass
class HardTechStrategyResult:
    """硬科技战略评估结果 / Hard-tech strategy evaluation result."""
    tech_path_type: str             # 技术路径类型
    tech_path_score: float          # 技术路径得分 0-10
    is_chokepoint_tech: bool        # 是否卡脖子技术
    trl_level: int                  # 技术成熟度等级 1-9 (NASA TRL)
    strategic_premium_coefficient: float  # 战略价值系数/含权量 1.0-3.0
    strategic_score: float          # 综合战略得分 0-10
    strategic_valuation_multiplier: float  # 估值修正系数（可被估值模块引用）
    tech_path_assessment: str       # 技术路径评估描述
    warnings: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)


@dataclass
class PhilosophyCheckResult:
    is_value_speculative: bool
    political_economy_score: float  # 0-10
    exit_rate_realistic: bool
    overall_alignment: bool
    summary: str
    warnings: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    # New hard-tech strategy fields / 新增硬科技战略字段
    strategic_score: float = 0.0
    strategic_valuation_multiplier: float = 1.0
    tech_path_assessment: str = ""


class HardTechStrategyEvaluator:
    """
    硬科技战略评估器 — P/Strategic维度
    Hard-Tech Strategy Evaluator — P/Strategic Dimension

    Evaluates hard-tech investments from a strategic (non-purely-financial) lens.
    Introduces the concept of strategic_valuation_multiplier to adjust valuations
    for chokepoint technologies beyond simple PE/PS ratios.

    Key dimensions:
    - Technology landing path (技术落地路径)
    - Forced PMF check via "national urgency" (强制PMF — 国家急需属性)
    - P/Strategic strategic tolerance as correction coefficient (战略容错率)
    """

    # TRL (Technology Readiness Level) thresholds
    TRL_EARLY = 3         # Basic proof-of-concept / 基础概念验证
    TRL_MID = 6           # System prototype demo / 系统原型演示
    TRL_COMMERCIAL = 8    # System qualified for operations / 系统量产就绪

    def evaluate(
        self,
        *,
        tech_path_type: str,                    # TECH_PATH_* constant
        is_chokepoint_tech: bool,               # 是否卡脖子技术
        has_gov_procurement: bool,              # 是否有政府/国企采购
        tech_readiness_level: int,              # TRL 1-9 (NASA standard)
        is_domestic_substitution: bool = False,
        is_hard_tech: bool = True,
    ) -> HardTechStrategyResult:
        """
        Evaluate the strategic dimension of a hard-tech investment.

        Parameters
        ----------
        tech_path_type:          Type of technology landing path (see TECH_PATH_* constants)
        is_chokepoint_tech:      Is this a chokepoint/bottleneck technology (卡脖子)?
        has_gov_procurement:     Has the project secured government or SOE procurement?
        tech_readiness_level:    NASA TRL scale 1-9; 1=basic research, 9=proven in operations
        is_domestic_substitution: Is it replacing foreign technology?
        is_hard_tech:            Is the project a hard-tech company?
        """
        warnings: list[str] = []
        recommendations: list[str] = []

        # --- Tech path scoring / 技术路径评分 ---
        if tech_path_type == TECH_PATH_CORE_PLUGIN:
            tech_path_score = 8.0
            tech_path_assessment = (
                "核心插件替换型：容错率高，替代速度快（如固态电池替换液态、国产GPU替换英伟达）。"
                "系统阻力小，客户迁移成本低，技术演进路径清晰。"
            )
        elif tech_path_type == TECH_PATH_SYSTEM_REBUILD:
            tech_path_score = 3.0
            tech_path_assessment = (
                "系统性基础设施重构型：存在极高系统性阻力（如氢能大规模民用）。"
                "需要多方协同、基础设施配套、政策强力支撑，落地周期极长。"
            )
            warnings.append(
                "系统性基础设施重构类项目：系统性阻力极大，落地时间窗口难以预判，"
                "商业化进程通常比预期慢5-10年，建议大幅提高安全边际。"
            )
        else:  # TECH_PATH_INCREMENTAL or unknown
            tech_path_score = 5.5
            tech_path_assessment = (
                "渐进式改良型：在现有系统上进行量变式优化，风险适中，"
                "市场接受度相对平稳，但护城河可能较浅。"
            )

        # --- Strategic premium coefficient / 战略价值系数 ---
        # Base coefficient for non-chokepoint hard tech
        strategic_premium = 1.0

        if is_chokepoint_tech:
            strategic_premium = 2.0  # Base chokepoint premium
            warnings.append(
                "卡脖子技术赛道：估值锚不应单纯使用财务PE/PS，"
                "国资兜底可能性使其具备超额战略溢价（含权量）。"
            )
            recommendations.append(
                "建议引入战略价值系数（strategic_valuation_multiplier）对财务估值进行修正，"
                "该系数已自动计算并可被其他估值模块引用。"
            )
            if has_gov_procurement:
                strategic_premium = min(3.0, strategic_premium + 0.5)
        elif is_domestic_substitution:
            strategic_premium = 1.4

        if has_gov_procurement and not is_chokepoint_tech:
            strategic_premium = min(3.0, strategic_premium + 0.3)

        # Clamp to [1.0, 3.0]
        strategic_premium = max(1.0, min(3.0, strategic_premium))

        # --- TRL adjustment / 技术成熟度调整 ---
        if tech_readiness_level < self.TRL_EARLY:
            warnings.append(
                f"技术成熟度仅TRL {tech_readiness_level}（基础研究阶段），"
                "距商用落地还有巨大不确定性，建议在技术验证期限制投资规模。"
            )
            trl_adj = -1.5
        elif tech_readiness_level < self.TRL_MID:
            trl_adj = 0.0
        elif tech_readiness_level < self.TRL_COMMERCIAL:
            trl_adj = 1.0
            recommendations.append(
                f"TRL {tech_readiness_level} — 系统原型验证阶段，关注良率和成本是否达到商用阈值。"
            )
        else:
            trl_adj = 2.0  # TRL 8-9: near or at commercial readiness

        # --- Composite strategic score / 综合战略得分 ---
        strategic_score = min(10.0, max(0.0, tech_path_score + trl_adj))
        if is_chokepoint_tech:
            strategic_score = min(10.0, strategic_score + 1.0)
        if has_gov_procurement:
            strategic_score = min(10.0, strategic_score + 0.5)

        # Strategic valuation multiplier (for use by other valuation modules)
        # Combines strategic premium with TRL readiness
        trl_readiness_factor = tech_readiness_level / 9.0
        strategic_valuation_multiplier = (
            1.0 + (strategic_premium - 1.0) * trl_readiness_factor
        )
        strategic_valuation_multiplier = round(
            max(1.0, min(3.0, strategic_valuation_multiplier)), 2
        )

        if strategic_score >= 8.0:
            recommendations.append(
                "战略评分极高：项目具备强国家战略属性，即使短期财务亏损，"
                "也可能获得持续国资采购或政策补贴支撑。建议适当放宽IRR要求，"
                f"应用战略估值修正系数 {strategic_valuation_multiplier:.2f}x。"
            )
        elif strategic_score < 4.0:
            warnings.append(
                "战略评分偏低：项目在当前政治经济逻辑下战略属性不突出，"
                "需更依赖纯商业逻辑支撑估值，建议回归财务PE/PS锚定。"
            )

        return HardTechStrategyResult(
            tech_path_type=tech_path_type,
            tech_path_score=round(tech_path_score, 1),
            is_chokepoint_tech=is_chokepoint_tech,
            trl_level=tech_readiness_level,
            strategic_premium_coefficient=round(strategic_premium, 2),
            strategic_score=round(strategic_score, 1),
            strategic_valuation_multiplier=strategic_valuation_multiplier,
            tech_path_assessment=tech_path_assessment,
            warnings=warnings,
            recommendations=recommendations,
        )


class InvestmentPhilosophyChecker:
    """
    投资哲学一致性检验器

    Source framework: 《投的好，更要退的好（2024版）》by 李刚强

    Key principles:
    1. Value Speculation (价值投机): Use company growth as foundation, but take
       profit decisively when capital fever causes valuations to diverge severely
       from intrinsic value. (source: [cite 21, 22, 23])

    2. Political Economy Lens: PE has shifted from "internet economy" (traffic/scale)
       to "political economy" (autonomous control / domestic substitution / hard tech).
       Scarcity and "chokehold" attributes command huge premiums. (source: [cite 289, 290])

    3. Exit Reality: Be realistic about exit rates — even top PE funds only exit 25-28%
       of portfolio companies. Plan for the distribution, not the outlier. (source: [cite 203-208])

    4. P/Strategic (硬科技战略容错率): Beyond pure PE/PS valuation, evaluate the
       strategic tolerance and national urgency attributes of hard-tech investments.
    """

    def __init__(self) -> None:
        self._hardtech_evaluator = HardTechStrategyEvaluator()

    def check(
        self,
        *,
        investment_thesis: str,
        has_exit_plan: bool,
        has_profit_taking_triggers: bool,
        sector: str,
        is_hard_tech: bool,
        is_domestic_substitution: bool,
        is_autonomous_controllable: bool,
        is_internet_traffic_model: bool,
        fund_stage: str,                  # "angel", "vc", "pe"
        assumed_exit_rate_pct: float,     # The exit rate the fund is assuming
        valuation_vs_intrinsic_pct: float, # How far current valuation is above intrinsic value
        # New hard-tech strategy parameters / 新增硬科技战略参数
        tech_path_type: str = TECH_PATH_INCREMENTAL,
        is_chokepoint_tech: bool = False,
        has_gov_procurement: bool = False,
        tech_readiness_level: int = 5,    # NASA TRL 1-9
    ) -> PhilosophyCheckResult:
        """
        Check if an investment decision aligns with the three core philosophy tenets,
        now extended with the P/Strategic hard-tech dimension.

        Parameters
        ----------
        investment_thesis:           One-line description of investment rationale
        has_exit_plan:               Does the investment memo include a concrete exit plan?
        has_profit_taking_triggers:  Are stop-profit triggers defined?
        sector:                      Sector/industry
        is_hard_tech:                Is this a hard-tech company?
        is_domestic_substitution:    Does the company replace foreign tech/products?
        is_autonomous_controllable:  Is it in the autonomous-control/security space?
        is_internet_traffic_model:   Is the business model driven by internet traffic/scale?
        fund_stage:                  Stage of fund
        assumed_exit_rate_pct:       What exit rate is the fund planning around?
        valuation_vs_intrinsic_pct:  Valuation premium over estimated intrinsic value (%)
        tech_path_type:              Technology landing path type (TECH_PATH_* constants)
        is_chokepoint_tech:          Is this a chokepoint/bottleneck technology (卡脖子)?
        has_gov_procurement:         Has the project secured government or SOE procurement?
        tech_readiness_level:        NASA TRL 1-9 (1=basic research, 9=proven in operations)
        """
        warnings: list[str] = []
        recommendations: list[str] = []

        # --- Hard-tech strategy evaluation (new P/Strategic dimension) ---
        hardtech_result = self._hardtech_evaluator.evaluate(
            tech_path_type=tech_path_type,
            is_chokepoint_tech=is_chokepoint_tech,
            has_gov_procurement=has_gov_procurement,
            tech_readiness_level=tech_readiness_level,
            is_domestic_substitution=is_domestic_substitution,
            is_hard_tech=is_hard_tech,
        )
        # Merge warnings/recommendations from hard-tech evaluation
        warnings.extend(hardtech_result.warnings)
        recommendations.extend(hardtech_result.recommendations)

        # --- Check 1: Value speculation vs long-hold value investing ---
        if not has_exit_plan:
            warnings.append(
                "投资备忘录缺乏明确退出计划。中国一级市场基金存续期7-9年，"
                "不应依赖长线持有等待价值实现。"
            )
            recommendations.append("在投前即制定清晰的退出路径（IPO/并购/老股转让）和时间窗口。")

        if not has_profit_taking_triggers:
            warnings.append("未定义止盈触发条件，可能在资本狂热期错失最佳退出窗口（戴维斯双杀风险）。")
            recommendations.append("设立估值溢价触发点（如超出行业PE中位数50%时启动退出评估）。")

        if valuation_vs_intrinsic_pct > 100:
            warnings.append(
                f"当前估值较内在价值溢价 {valuation_vs_intrinsic_pct:.0f}%，"
                "已严重透支未来成长，符合'价值投机'止盈信号。"
            )
            recommendations.append("根据价值投机原则，建议启动分批退出程序。")

        is_value_speculative = has_exit_plan and has_profit_taking_triggers

        # --- Check 2: Political economy lens ---
        pe_signals = sum([is_hard_tech, is_domestic_substitution, is_autonomous_controllable])
        political_economy_score = float(pe_signals) / 3.0 * 10.0

        if is_internet_traffic_model:
            warnings.append(
                "互联网流量/规模驱动型商业模式在当前政治经济逻辑下溢价有限，"
                "需重新评估未来估值扩张空间。"
            )
            political_economy_score = max(0, political_economy_score - 3)

        if pe_signals == 0 and not is_internet_traffic_model:
            warnings.append(
                "项目既不符合硬科技/国产替代属性，也不是成熟互联网模式，"
                "需明确其在当前投资逻辑下的稀缺性所在。"
            )

        if pe_signals >= 2:
            pass  # no warning needed — strong political economy alignment

        # --- Check 3: Exit rate reality ---
        stage_key = {"angel": "top_angel", "vc": "top_vc", "pe": "top_pe"}.get(
            fund_stage, "top_vc"
        )
        lo, hi = EXIT_RATE_BENCHMARKS[stage_key]
        benchmark_center = (lo + hi) / 2 * 100  # as percentage

        assumed_pct = assumed_exit_rate_pct
        exit_rate_realistic = assumed_pct <= hi * 100 * 1.5  # allow 50% over benchmark

        if assumed_exit_rate_pct > hi * 100:
            warnings.append(
                f"计划退出率 {assumed_exit_rate_pct:.0f}% 超过顶级{fund_stage.upper()}基金"
                f"实际退出率基准 {hi * 100:.0f}%。"
                "过度乐观的退出假设将导致基金业绩测算严重失真。"
            )
            recommendations.append(
                f"建议将退出率假设调整至 {benchmark_center:.0f}% 附近，"
                "并为无法退出的项目制定减值预案。"
            )

        overall_alignment = (
            is_value_speculative
            and political_economy_score >= 4
            and exit_rate_realistic
        )

        summary_parts = [
            f"价值投机就绪: {'✅' if is_value_speculative else '❌'}",
            f"政治经济视角得分: {political_economy_score:.1f}/10",
            f"退出率假设合理性: {'✅' if exit_rate_realistic else '❌'}",
            f"战略评分: {hardtech_result.strategic_score:.1f}/10",
            f"综合哲学对齐度: {'✅ 对齐' if overall_alignment else '⚠️ 存在偏差'}",
        ]

        return PhilosophyCheckResult(
            is_value_speculative=is_value_speculative,
            political_economy_score=round(political_economy_score, 1),
            exit_rate_realistic=exit_rate_realistic,
            overall_alignment=overall_alignment,
            summary=" | ".join(summary_parts),
            warnings=warnings,
            recommendations=recommendations,
            strategic_score=hardtech_result.strategic_score,
            strategic_valuation_multiplier=hardtech_result.strategic_valuation_multiplier,
            tech_path_assessment=hardtech_result.tech_path_assessment,
        )
