# ==== GEMS FILE: 08_damodaran_stack_demo.py ====
# Merged from: damodaran_stack.py
# For Gemini Gems knowledge base — v4.0
# NOTE: This is a knowledge reference file, not executable production code.
#       Cross-module imports have been annotated for clarity.

from __future__ import annotations
import datetime
from dataclasses import dataclass, field
from typing import List, Optional


# ==== ORIGIN: damodaran_stack.py ====
"""
达莫达兰三层估值堆栈聚合器
Damodaran Three-Layer Valuation Stack Aggregator

融合灵魂：用Layer 1内在价值(DCF)做"地板价"，
用Layer 3退出定价做"天花板价"，
用Layer 2期权做"想象空间"，
三层堆栈形成安全边际带宽。

哲学原则：
"不要因为难，就放弃第一性原理；你100%会犯错，但这正是风险的本质。" —— Aswath Damodaran

三层估值框架设计逻辑：
- Layer 1（内在价值/地板价）：叙事驱动DCF，基于第一性原理，代表企业内在合理价值
  不依赖市场情绪，是最诚实的估值锚点。若进场价低于地板价，这是真正的"安全边际"。
- Layer 2（期权价值/想象空间）：量化尚未实现的扩张机会价值。
  不是在给商业计划书打分，而是用Black-Scholes严格定价"选择权"。
- Layer 3（市场退出定价/天花板价）：退出时市场愿意支付的价格，取决于当时的可比公司乘数。
  这是PE投资的"终局定价"，但其实是定价而非估值，高度依赖市场情绪。

安全边际带宽 = (天花板 - 地板) / 进场价 - 1
- > 40%：INVEST（强安全边际，值得投资）
- 20-40%：NEGOTIATE_TERMS（边际合格，需要更好的条款保护）
- < 20%：PASS（安全边际不足，过价）

模块组成：
- ThreeLayerValuationResult：三层估值汇总结果 + IC Memo
- ThreeLayerValuationStack：三层堆栈聚合引擎
"""



# NOTE: NarrativeDCFResult is defined in gems/05_narrative_dcf.py
# NOTE: PricingDeconstructionResult is defined in gems/06_probabilistic_pricing.py
# ---------------------------------------------------------------------------
# 三层估值结果
# Three-Layer Valuation Result
# ---------------------------------------------------------------------------

@dataclass
class ThreeLayerValuationResult:
    """
    达莫达兰三层估值堆栈聚合结果
    Damodaran Three-Layer Valuation Stack Aggregation Result.

    Fields
    ------
    intrinsic_floor_rmb      Layer 1: DCF地板价（亿元，已按存活率和宏观系数调整）
    optionality_premium_rmb  Layer 2: 期权溢价总和（亿元）
    market_ceiling_rmb       Layer 3: 退出天花板价（亿元，已按宏观系数调整）
    entry_price_rmb          进场估值（亿元）
    safety_margin_pct        安全边际带宽 = (天花板 - 地板) / 进场价 - 1（×100%）
    recommendation           投资建议: "INVEST" / "NEGOTIATE_TERMS" / "PASS"
    ic_memo_markdown         完整IC Memo（Markdown格式）
    """

    intrinsic_floor_rmb: float       # Layer 1: DCF地板价（亿元）
    optionality_premium_rmb: float   # Layer 2: 期权溢价（亿元）
    market_ceiling_rmb: float        # Layer 3: 退出天花板（亿元）
    entry_price_rmb: float           # 进场估值（亿元）
    safety_margin_pct: float         # 安全边际带宽（%）
    recommendation: str              # "INVEST" / "NEGOTIATE_TERMS" / "PASS"
    ic_memo_markdown: str            # 完整IC Memo（Markdown）
    summary: str
    warnings: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    details: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# 三层估值堆栈引擎
# Three-Layer Valuation Stack Engine
# ---------------------------------------------------------------------------

class ThreeLayerValuationStack:
    """
    达莫达兰三层估值堆栈聚合引擎
    Damodaran Three-Layer Valuation Stack Aggregation Engine

    安全边际判断逻辑
    ----------------
    safety_margin = (adjusted_ceiling - intrinsic_floor) / entry_price - 1

    - > invest_threshold (默认40%) → INVEST：地板到天花板的空间远大于进场价，有真实安全边际
    - negotiate_threshold~invest_threshold → NEGOTIATE_TERMS：空间有限，需要更强的条款保护
    - < negotiate_threshold (默认20%) → PASS：安全边际不足，定价偏高，宁愿错过也不要贸然入场

    宏观调整
    --------
    intrinsic_floor = sotp_ev × p_survival / macro_adjustment_factor
    adjusted_ceiling = market_ceiling / macro_adjustment_factor

    当macro_adjustment_factor > 1 时（ERP高于历史），折现率隐含上升，
    分子不变分母变大，两个端点均下调。这是诚实地反映宏观风险的做法。
    """

    # 默认安全边际阈值（可通过构造函数自定义）
    DEFAULT_INVEST_THRESHOLD: float = 0.40    # 40%
    DEFAULT_NEGOTIATE_THRESHOLD: float = 0.20  # 20%

    def __init__(
        self,
        invest_threshold: float = DEFAULT_INVEST_THRESHOLD,
        negotiate_threshold: float = DEFAULT_NEGOTIATE_THRESHOLD,
    ) -> None:
        """
        初始化三层估值堆栈。

        Parameters
        ----------
        invest_threshold       INVEST门槛（安全边际下限，默认40%）
        negotiate_threshold    NEGOTIATE_TERMS门槛（安全边际下限，默认20%）
        """
        self.invest_threshold = invest_threshold
        self.negotiate_threshold = negotiate_threshold

    def evaluate(
        self,
        *,
        project_name: str,
        entry_price_rmb: float,
        # Layer 1
        narrative_dcf_result: NarrativeDCFResult,
        # Layer 2
        expansion_option_values_rmb: list[float],
        # Layer 3
        market_comps_ceiling_rmb: float,
        pricing_detection_result: Optional[PricingDeconstructionResult] = None,
        # 风险调整
        p_survival: float = 1.0,
        macro_adjustment_factor: float = 1.0,
        # 元数据
        analyst_name: str = "PE Analyst",
        investment_date: str = "",
    ) -> ThreeLayerValuationResult:
        """
        执行三层估值堆栈评估，生成IC Memo。

        Parameters
        ----------
        project_name                 项目名称
        entry_price_rmb              进场估值（亿元）
        narrative_dcf_result         Layer 1: 叙事DCF结果（来自 NarrativeDCFValuer）
        expansion_option_values_rmb  Layer 2: 扩张期权价值列表（亿元）
        market_comps_ceiling_rmb     Layer 3: 退出天花板价（亿元，来自可比公司分析）
        pricing_detection_result     定价体操检测结果（可选，用于IC Memo风险章节）
        p_survival                   存活概率（0-1，用于调整Layer 1地板价）
        macro_adjustment_factor      宏观调整系数（当前ERP/基准ERP，通常≥1）
        analyst_name                 分析师姓名
        investment_date              投资日期（留空则使用今天）

        Returns
        -------
        ThreeLayerValuationResult
        """
        warnings: list[str] = []
        recommendations: list[str] = []

        # --- Layer 1: 地板价（DCF，按存活率和宏观系数调整）---
        sotp_ev = narrative_dcf_result.sotp_ev_rmb
        if macro_adjustment_factor <= 0:
            macro_adjustment_factor = 1.0
            warnings.append("宏观调整系数 ≤ 0，已重置为1.0。")

        intrinsic_floor = sotp_ev * p_survival / macro_adjustment_factor

        # --- Layer 2: 期权溢价（求和）---
        optionality_premium = sum(expansion_option_values_rmb)

        # --- Layer 3: 退出天花板（按宏观系数调整）---
        adjusted_ceiling = market_comps_ceiling_rmb / macro_adjustment_factor

        # --- 安全边际计算 ---
        if entry_price_rmb > 0:
            safety_margin_pct = (adjusted_ceiling - intrinsic_floor) / entry_price_rmb - 1
        else:
            safety_margin_pct = 0.0
            warnings.append("进场估值 ≤ 0，安全边际计算无效。")

        # --- 投资建议 ---
        if safety_margin_pct >= self.invest_threshold:
            recommendation = "INVEST"
            recommendations.append(
                f"✅ 安全边际带宽 {safety_margin_pct:.1%}（>{self.invest_threshold:.0%}），"
                "三层估值堆栈验证通过，建议进场投资。"
                f"地板价={intrinsic_floor:.2f}亿 vs 天花板={adjusted_ceiling:.2f}亿，"
                "空间充裕，具备真实安全边际。"
            )
        elif safety_margin_pct >= self.negotiate_threshold:
            recommendation = "NEGOTIATE_TERMS"
            recommendations.append(
                f"⚠️ 安全边际带宽 {safety_margin_pct:.1%}（位于{self.negotiate_threshold:.0%}-{self.invest_threshold:.0%}之间），"
                "边际合格但空间有限。建议谈判更强的条款保护："
                "① 1x优先清算权  ② 棘轮反稀释  ③ 里程碑分期付款"
            )
        else:
            recommendation = "PASS"
            warnings.append(
                f"❌ 安全边际带宽仅 {safety_margin_pct:.1%}（<{self.negotiate_threshold:.0%}），"
                "当前定价过高，三层估值堆栈不支持进场。"
                "宁愿错过也不要以无安全边际的价格入场。"
            )

        # 参数检验
        if p_survival < 0.5:
            warnings.append(
                f"存活概率 {p_survival:.0%} 较低，地板价已大幅折减至 {intrinsic_floor:.2f}亿，"
                "建议优先解决存活率风险（融资路径/客户验证）再做投资决策。"
            )

        if macro_adjustment_factor > 1.10:
            warnings.append(
                f"宏观调整系数={macro_adjustment_factor:.3f}（>1.10，MAC已触发），"
                "地板价和天花板均已向下调整，市场宏观风险处于高位。"
            )

        if pricing_detection_result and len(pricing_detection_result.red_flags) > 0:
            warnings.append(
                f"定价体操检测发现 {len(pricing_detection_result.red_flags)} 个红旗，"
                "天花板价来自可比公司分析，可靠性存疑。"
                "请参考IC Memo第四章的详细分析。"
            )

        # --- 生成IC Memo ---
        date_str = investment_date or datetime.date.today().strftime("%Y-%m-%d")
        ic_memo = self._generate_ic_memo(
            project_name=project_name,
            date_str=date_str,
            analyst_name=analyst_name,
            entry_price_rmb=entry_price_rmb,
            intrinsic_floor=intrinsic_floor,
            optionality_premium=optionality_premium,
            adjusted_ceiling=adjusted_ceiling,
            safety_margin_pct=safety_margin_pct,
            recommendation=recommendation,
            narrative_dcf_result=narrative_dcf_result,
            expansion_option_values_rmb=expansion_option_values_rmb,
            market_comps_ceiling_rmb=market_comps_ceiling_rmb,
            macro_adjustment_factor=macro_adjustment_factor,
            p_survival=p_survival,
            pricing_detection_result=pricing_detection_result,
            all_warnings=warnings,
            all_recommendations=recommendations,
        )

        summary = (
            f"[{project_name}] 三层估值堆栈 | "
            f"地板={intrinsic_floor:.2f}亿 | 期权={optionality_premium:.2f}亿 | "
            f"天花板={adjusted_ceiling:.2f}亿 | 进场={entry_price_rmb:.2f}亿 | "
            f"安全边际={safety_margin_pct:.1%} | 建议: {recommendation}"
        )

        return ThreeLayerValuationResult(
            intrinsic_floor_rmb=round(intrinsic_floor, 4),
            optionality_premium_rmb=round(optionality_premium, 4),
            market_ceiling_rmb=round(adjusted_ceiling, 4),
            entry_price_rmb=round(entry_price_rmb, 4),
            safety_margin_pct=round(safety_margin_pct, 4),
            recommendation=recommendation,
            ic_memo_markdown=ic_memo,
            summary=summary,
            warnings=warnings,
            recommendations=recommendations,
            details={
                "sotp_ev_rmb": sotp_ev,
                "p_survival": p_survival,
                "macro_adjustment_factor": macro_adjustment_factor,
                "raw_market_ceiling": market_comps_ceiling_rmb,
                "adjusted_ceiling": round(adjusted_ceiling, 4),
                "n_options": len(expansion_option_values_rmb),
                "option_values": expansion_option_values_rmb,
                "pricing_red_flags": (
                    pricing_detection_result.red_flags
                    if pricing_detection_result else []
                ),
            },
        )

    # ------------------------------------------------------------------
    # IC Memo 生成器
    # IC Memo Generator
    # ------------------------------------------------------------------

    def _generate_ic_memo(
        self,
        *,
        project_name: str,
        date_str: str,
        analyst_name: str,
        entry_price_rmb: float,
        intrinsic_floor: float,
        optionality_premium: float,
        adjusted_ceiling: float,
        safety_margin_pct: float,
        recommendation: str,
        narrative_dcf_result: NarrativeDCFResult,
        expansion_option_values_rmb: list[float],
        market_comps_ceiling_rmb: float,
        macro_adjustment_factor: float,
        p_survival: float,
        pricing_detection_result: Optional[PricingDeconstructionResult],
        all_warnings: list[str],
        all_recommendations: list[str],
    ) -> str:
        """生成完整IC Memo（Markdown格式）。"""

        rec_action_map = {
            "INVEST": "支持进场",
            "NEGOTIATE_TERMS": "建议谈判条款后进场",
            "PASS": "不支持进场，建议放弃",
        }
        rec_action_str = rec_action_map.get(recommendation, recommendation)

        rec_emoji_map = {"INVEST": "✅", "NEGOTIATE_TERMS": "⚠️", "PASS": "❌"}
        rec_emoji = rec_emoji_map.get(recommendation, "")

        # --- 第一章：投资摘要表格 ---
        summary_table = (
            "| 指标 | 数值 |\n"
            "|------|------|\n"
            f"| 进场估值 | {entry_price_rmb:.2f}亿元 |\n"
            f"| DCF地板价（Layer 1） | {intrinsic_floor:.2f}亿元 |\n"
            f"| 期权溢价（Layer 2） | {optionality_premium:.2f}亿元 |\n"
            f"| 退出天花板（Layer 3） | {adjusted_ceiling:.2f}亿元 |\n"
            f"| 安全边际带宽 | {safety_margin_pct:.1%} |\n"
            f"| **投资建议** | **{rec_emoji} {recommendation}** |\n"
            f"| 存活概率 | {p_survival:.0%} |\n"
            f"| 宏观调整系数 | {macro_adjustment_factor:.3f} |\n"
        )

        # --- 第二章：Layer 1 — 板块明细表格 ---
        if narrative_dcf_result.segment_details:
            seg_header = "| 板块 | 终局收入(亿) | 终局FCF(亿) | PV(亿) | 累计烧钱(亿) |\n"
            seg_sep = "|------|-------------|------------|--------|-------------|\n"
            seg_rows = "".join(
                f"| {d.name} | {d.terminal_revenue_rmb:.2f} | {d.terminal_fcf_rmb:.2f} "
                f"| {d.total_pv_rmb:.2f} | {d.cumulative_burn_rmb:.2f} |\n"
                for d in narrative_dcf_result.segment_details
            )
            seg_table = seg_header + seg_sep + seg_rows
            seg_table += (
                f"\n**SOTP合计企业价值（原始）**: {narrative_dcf_result.sotp_ev_rmb:.2f}亿元  \n"
                f"**存活率调整后地板价**: {intrinsic_floor:.2f}亿元（×{p_survival:.0%} / {macro_adjustment_factor:.3f}）\n"
            )
        else:
            seg_table = "_（无板块明细）_\n"

        # --- 第三章：Layer 2 — 期权列表 ---
        if expansion_option_values_rmb:
            option_lines = "\n".join(
                f"- 期权 {i+1}: **{v:.2f}亿元**"
                for i, v in enumerate(expansion_option_values_rmb)
            )
            option_lines += f"\n\n**期权溢价合计**: {optionality_premium:.2f}亿元"
        else:
            option_lines = "_（无扩张期权）_"

        # --- 第四章：Layer 3 — 退出定价分析 ---
        ceiling_analysis = (
            f"- 可比公司退出天花板（原始）: **{market_comps_ceiling_rmb:.2f}亿元**\n"
            f"- 宏观调整后天花板: **{adjusted_ceiling:.2f}亿元**（÷{macro_adjustment_factor:.3f}）\n"
        )
        if pricing_detection_result:
            n_red = len(pricing_detection_result.red_flags)
            ceiling_analysis += f"- 定价体操检测: 发现 **{n_red} 个红旗**\n"
            if pricing_detection_result.red_flags:
                ceiling_analysis += "\n".join(
                    f"  - {rf}" for rf in pricing_detection_result.red_flags[:3]
                )
                ceiling_analysis += "\n"

        # --- 第五章：风险因子 ---
        if all_warnings:
            risk_section = "\n".join(f"- {w}" for w in all_warnings)
        else:
            risk_section = "_未发现重大风险信号。_"

        # --- 第六章：达氏纪律三原则检验 ---
        pricing_red_flags_str = (
            f"检测到{len(pricing_detection_result.red_flags)}个定价操纵信号"
            if pricing_detection_result and pricing_detection_result.red_flags
            else "未检测到明显定价操纵"
        )

        damodaran_check = (
            f"- **双锚原则**: 地板价={intrinsic_floor:.2f}亿 vs 天花板={adjusted_ceiling:.2f}亿  \n"
            f"  估值带宽={(adjusted_ceiling - intrinsic_floor):.2f}亿元，"
            f"安全边际={safety_margin_pct:.1%}\n"
            f"- **强制概率化**: 存活率P(survival)={p_survival:.0%}，"
            f"已将破产/融资失败情形纳入估值\n"
            f"- **强制反向尽调**: {pricing_red_flags_str}\n"
        )

        # --- 第七章：投资建议与条款要求 ---
        if all_recommendations:
            reco_section = "\n".join(f"- {r}" for r in all_recommendations)
        else:
            reco_section = f"- 投资建议: **{recommendation}**"

        # --- 组装完整IC Memo ---
        memo = f"""# IC Memo — {project_name}

**分析日期**: {date_str}  **分析师**: {analyst_name}

---

## 一、投资摘要

{summary_table}

> **决策依据**: 安全边际带宽={safety_margin_pct:.1%}，
> 三层堆栈（DCF地板={intrinsic_floor:.2f}亿 → 期权溢价={optionality_premium:.2f}亿 → 退出天花板={adjusted_ceiling:.2f}亿）
> {rec_action_str}。

---

## 二、Layer 1 — 内在价值（叙事DCF）

{seg_table}

---

## 三、Layer 2 — 期权价值

{option_lines}

---

## 四、Layer 3 — 市场退出定价

{ceiling_analysis}

---

## 五、风险因子

{risk_section}

---

## 六、达氏纪律三原则检验

{damodaran_check}

---

## 七、投资建议与条款要求

{reco_section}

---

*本IC Memo由达莫达兰三层估值堆栈模型自动生成，仅供投资决策参考。*
*所有估值结果均基于输入假设，实际结果可能因叙事偏差、宏观变化而显著偏离。*
"""
        return memo



# ==== ORIGIN: main.py (v4.0 CLI demo functions) ====
# Simplified CLI demos showing how to use the full Damodaran valuation stack.
# These functions demonstrate end-to-end usage of all v4.0 modules.


def demo_narrativedcf() -> None:
    print_section("v4.0 工具一：叙事驱动SOTP-DCF — SpaceX三段式估值")

    valuer = NarrativeDCFValuer()

    segments = [
        BusinessSegment(
            name="航天发射（猎鹰/重型猎鹰）",
            tam_rmb=3600.0,       # 全球商业发射市场~500亿美元≈3600亿RMB
            terminal_market_share_pct=55.0,  # 终局：垄断性市占率55%
            terminal_operating_margin_pct=28.0,
            sales_to_capital_ratio=0.6,      # 重资产，S/C=0.6（航天发射基准）
            years_to_terminal=10,
            discount_rate=0.09,
            industry_type="航天发射",
            tax_rate=0.21,
        ),
        BusinessSegment(
            name="Starlink宽带卫星",
            tam_rmb=28800.0,      # 全球宽带市场~4000亿美元≈28800亿RMB，取10%
            terminal_market_share_pct=10.0,
            terminal_operating_margin_pct=35.0,
            sales_to_capital_ratio=1.1,
            years_to_terminal=12,
            discount_rate=0.11,
            industry_type="宽带卫星",
            tax_rate=0.21,
        ),
        BusinessSegment(
            name="xAI大模型（To-C利基）",
            tam_rmb=14400.0,      # AI市场~2000亿美元≈14400亿RMB，取5%利基
            terminal_market_share_pct=5.0,
            terminal_operating_margin_pct=30.0,
            sales_to_capital_ratio=1.3,
            years_to_terminal=8,
            discount_rate=0.14,  # AI高不确定性，折现率更高
            industry_type="AI大模型",
            tax_rate=0.21,
        ),
    ]

    result = valuer.value(segments, terminal_growth_rate=0.03)

    print_result(result)
    print(f"\n  SOTP分段明细:")
    print(f"  {'板块':20} {'终局营收':>10} {'终值':>12} {'合计PV':>12} {'累计烧钱':>10}")
    print("  " + "-" * 68)
    for seg in result.segment_details:
        print(
            f"  {seg.name:20} {seg.terminal_revenue_rmb:>8.0f}亿 "
            f"{seg.terminal_value_rmb:>10.0f}亿 "
            f"{seg.total_pv_rmb:>10.0f}亿 "
            f"{seg.cumulative_burn_rmb:>8.0f}亿"
        )
    print(f"\n  → SOTP企业价值: {result.sotp_ev_rmb:.0f}亿元 "
          f"（约{result.sotp_ev_rmb/USD_TO_RMB_RATE/10000:.1f}万亿美元，按1USD={USD_TO_RMB_RATE}RMB）")


def demo_probability() -> None:
    print_section("v4.0 工具二：扩张期权 + 蒙特卡洛概率分布")

    print("\n[场景A: 火星采矿扩张期权]")
    option_valuer = ExpansionOptionValuer()
    mars_option = option_valuer.value(
        underlying_value_rmb=1440.0,   # 远期火星采矿业务NPV≈200亿美元≈1440亿RMB
        exercise_cost_rmb=2160.0,      # 行权成本≈300亿美元投资
        time_to_expiry_years=10.0,
        volatility=0.60,               # 极高不确定性
        risk_free_rate=0.035,
        probability_of_viability=0.15, # 15%可行概率
    )
    print_result(mars_option)
    print(f"\n  d1={mars_option.d1:.4f} | d2={mars_option.d2:.4f}")
    print(f"  内在价值: {mars_option.intrinsic_value_rmb:.2f}亿 | 时间价值: {mars_option.time_value_rmb:.2f}亿")

    print("\n[场景B: AI独角兽TAM/Margin概率估值分布（10000次蒙特卡洛）]")
    dist = ValuationDistribution()
    result = dist.simulate(
        tam_param=LognormalParam(mean=10000.0, std=4000.0),    # TAM 亿元，高度不确定
        margin_param=NormalParam(mean=0.22, std=0.08),          # 利润率
        sales_to_capital_param=LognormalParam(mean=1.3, std=0.3),
        survival_prob=0.75,
        years_to_terminal=8,
        discount_rate=0.12,
        terminal_growth_rate=0.03,
        n_simulations=10000,
        given_price_rmb=12600.0,  # 投行1.75万亿美元≈12600亿RMB（折算）
        seed=42,
    )
    print_result(result)
    print(f"\n  估值分布（亿元）:")
    print(f"  P10={result.p10:.0f} | P25={result.p25:.0f} | 中位={result.median:.0f} "
          f"| P75={result.p75:.0f} | P90={result.p90:.0f} | 均值={result.mean:.0f}")
    print(f"\n  [ASCII分布图]\n{result.histogram_ascii}")
    if result.is_overpriced_at_p90:
        print(f"  ⚠️  定价 {result.given_price_rmb if hasattr(result,'given_price_rmb') else '给定价'}亿元 "
              f"已超越P90分位！投行报价位于估值分布右尾，买入意味着零容错率。")


def demo_pricinggym() -> None:
    print_section("v4.0 工具三：定价体操拆解 — SpaceX投行1.75万亿定价分析")

    detector = PricingGymnasticsDetector()

    # 构造对标池（投行精心挑选的高估值同业）
    comp_pool = [
        Comp(name="Palantir",    ev_sales_multiple=28.0, reference_year="2025E", sector="AI软件", is_growth_stock=True),
        Comp(name="Rocket Lab",  ev_sales_multiple=12.0, reference_year="2025E", sector="小卫星", is_growth_stock=True),
        Comp(name="Planet Labs", ev_sales_multiple=8.5,  reference_year="2025E", sector="遥感", is_growth_stock=True),
        Comp(name="Iridium",     ev_sales_multiple=6.0,  reference_year="TTM",   sector="卫星通信", is_growth_stock=False),
        # 被刻意遗漏的低估值锚：Boeing(1.2x), Northrop(2.1x), Raytheon(1.8x)
    ]

    result = detector.detect(
        comp_pool=comp_pool,
        current_revenue_rmb=432.0,    # SpaceX当前年收入~60亿美元≈432亿RMB
        forward_revenue_rmb=2160.0,   # 2030年预测收入~300亿美元
        forward_year="2030E",
        claimed_multiple=8.0,         # 投行声称8x EV/Sales（基于2030年收入）
        current_ev_rmb=126000.0,      # 1.75万亿美元≈126000亿RMB
    )

    print_result(result)
    print(f"\n  当前真实乘数: {result.implied_current_multiple:.1f}x EV/Sales（基于当期营收）")
    print(f"  对标池离散度（Std/Mean）: {result.comp_pool_std_over_mean:.1%}")
    print(f"\n  FA话术解码表:")
    print(f"  {'FA话术':28} {'真实含义':28} {'反向操作':25}")
    print("  " + "-" * 85)
    for row in result.fa_decoder_table[:5]:
        fa = row.get("fa_claim", "")[:26]
        real = row.get("real_meaning", "")[:26]
        action = row.get("counter_action", "")[:23]
        print(f"  {fa:28} {real:28} {action:25}")


def demo_macrorisk() -> None:
    print_section("v4.0 工具四：动态宏观风险重定价 — 2026年3月中东战争场景")

    erp_calc = ImpliedERPCalculator()
    crp_calc = SovereignCRPAdjuster()
    engine = MacroRiskEngine()

    print("\n[Step 1: 2026年1月基准ERP（战前平静期）]")
    base_erp = erp_calc.calculate(
        index_level=5200.0,          # S&P 500基准点位
        expected_dividend_yield_pct=1.8,
        expected_growth_pct=5.5,
        risk_free_rate_pct=3.8,
    )
    print_result(base_erp)
    print(f"  → 隐含IRR: {base_erp.implied_irr:.2%} | 隐含ERP: {base_erp.implied_erp:.2%}")

    print("\n[Step 2: 2026年3月战争爆发后ERP（恐慌重定价）]")
    crisis_erp = erp_calc.calculate(
        index_level=4800.0,          # 指数下跌~8%
        expected_dividend_yield_pct=2.0,
        expected_growth_pct=4.5,     # 增长预期下调
        risk_free_rate_pct=4.0,      # 避险资金推高国债
    )
    print_result(crisis_erp)
    print(f"  → 隐含IRR: {crisis_erp.implied_irr:.2%} | 隐含ERP: {crisis_erp.implied_erp:.2%}")

    print("\n[Step 3: 伊拉克主权CDS飙升 — 国家风险溢价重新计价]")
    iraq_crp = crp_calc.calculate(
        country_cds_bps=850.0,       # 战时伊拉克CDS飙升至850bps
        base_country_cds_bps=30.0,
        equity_to_bond_volatility_ratio=1.5,
    )
    print_result(iraq_crp)
    print(f"  → 伊拉克CRP: {iraq_crp.crp:.2%}（须叠加至所有伊拉克相关资产折现率）")

    print("\n[Step 4: 宏观风险综合评估 — MAC触发判断]")
    macro_result = engine.evaluate(
        current_erp_result=crisis_erp,
        base_erp_pct=base_erp.implied_erp * 100,
        crp_result=iraq_crp,
    )
    print_result(macro_result)
    print(f"  → 估值时点调整系数: {macro_result.adjustment_factor:.3f}")
    print(f"  → MAC触发: {'⚠️ 是 — 建议暂停估值定价，重新谈判' if macro_result.mac_triggered else '否'}")


def demo_distress() -> None:
    print_section("v4.0 工具五：截断/破产双轨分离估值 — 困境标的双轨模型")

    valuer = DistressDualTrackValuer()

    print("\n[场景A: 从债券市场定价反推隐含违约概率（类LVS债券）]")
    p_default_bond = DistressDualTrackValuer.from_bond_pricing(
        face_value=100.0,      # 债券面值100亿元
        market_price=55.0,     # 市场成交价55亿元（重度折价）
        coupon_rate=0.075,     # 票面利率7.5%
        years_to_maturity=10.0,
        recovery_rate=0.40,
    )
    print(f"  债券隐含违约概率: {p_default_bond:.1%}（市场真金白银定价的破产风险）")

    print("\n[场景B: Altman Z-Score路径]")
    z_result = DistressDualTrackValuer.from_altman_z(
        working_capital=5.0,
        retained_earnings=-80.0,   # 累计亏损
        ebit=-10.0,
        market_value_equity=50.0,
        sales=120.0,
        total_assets=200.0,
        total_liabilities=180.0,
    )
    print(f"  Z-Score: {z_result.z_score:.2f} | 区间: {z_result.zone} | 违约概率: {z_result.implied_default_probability:.1%}")

    print("\n[双轨期望估值（使用债券路径违约概率）]")
    result = valuer.value(
        going_concern_dcf_rmb=180.0,   # 持续经营DCF价值
        liquidation_nav_rmb=60.0,      # 清算NAV（含土地/设备）
        p_distress=p_default_bond,
        restructuring_cost_rmb=8.0,
        next_round_funding_close_probability=0.35,  # 下轮融资成功率35%
    )
    print_result(result)
    print(f"\n  持续经营价值: {result.going_concern_value_rmb:.1f}亿 × P(存活)={result.p_survival:.1%}")
    print(f"  清算价值:     {result.liquidation_nav_rmb:.1f}亿 × P(破产)={result.p_distress:.1%}")
    print(f"  期望成交价:   {result.expected_deal_value_rmb:.1f}亿元")
    print(f"  vs 传统DCF强制估值折价: {result.value_discount_vs_traditional_pct:.1f}%")


def demo_restatement() -> None:
    print_section("v4.0 工具六：财务报表外科手术 — 生物药企R&D资本化重述（类Amgen）")

    capitalizer = IntangibleCapitalizer()

    print("\n[Step 1: R&D历史费用资本化（10年摊销，药企标准）]")
    rd_history = [35.0, 38.0, 42.0, 45.0, 50.0, 55.0, 58.0, 60.0, 65.0, 70.0]  # 亿元
    rd_result = capitalizer.capitalize_rd(
        rd_history=rd_history,
        amortization_years=10,
    )
    print(f"  R&D历史（近10年，亿元）: {[f'{x:.0f}' for x in rd_history]}")
    print(f"  资本化后R&D资产价值: {rd_result.rd_asset_value:.1f}亿元")
    print(f"  当年摊销额: {rd_result.current_year_amortization:.1f}亿元")
    print(f"  对EBIT的调整（+当年R&D - 摊销）: {rd_result.adjustment_to_ebit:.1f}亿元")

    print("\n[Step 2: 财务报表重述（EBIT+Invested Capital→ROIC重构）]")
    restate_result = capitalizer.restate_financials(
        reported_ebit=80.0,
        reported_invested_capital=350.0,
        capitalized_rd_asset=rd_result.rd_asset_value,
        current_year_rd=70.0,
        amortization_years=10,
        revenue=500.0,
    )
    print_result(restate_result)
    print(f"\n  报告EBIT: {restate_result.reported_ebit:.1f}亿 → 重述EBIT: {restate_result.restated_ebit:.1f}亿")
    print(f"  报告Invested Capital: {restate_result.reported_invested_capital:.1f}亿 → "
          f"重述: {restate_result.restated_invested_capital:.1f}亿")
    print(f"  报告ROIC: {restate_result.reported_roic:.1%} → 重述ROIC: {restate_result.restated_roic:.1%}")

    print("\n[Step 3: SBC调整 — 扣回股权激励水分]")
    sbc_result = IntangibleCapitalizer.adjust_for_sbc(
        reported_ebitda=180.0,
        sbc_expense=42.0,   # SBC占申报EBITDA的23%（行业常见）
    )
    print(f"  申报EBITDA: {sbc_result.reported_ebitda:.1f}亿 | SBC: {sbc_result.sbc_expense:.1f}亿 "
          f"（占{sbc_result.sbc_as_pct_of_ebitda:.1f}%）")
    print(f"  调整后真实EBITDA: {sbc_result.adjusted_ebitda:.1f}亿元")
    for w in sbc_result.warnings:
        print(f"  ⚠️  {w}")


def demo_cyclical() -> None:
    print_section("v4.0 工具七：周期股常态化 — Exxon美孚 & Toyota跨周期利润率")

    normalizer = CyclicalNormalizer()

    print("\n[场景A: Exxon美孚 — 原油周期利润率常态化]")
    exxon_margins = [0.06, 0.04, 0.08, 0.14, 0.17, 0.12, -0.02, 0.09, 0.18, 0.15]
    exxon_result = normalizer.normalize_by_historical_average(
        margins_history=exxon_margins,
        lookback_years=7,
        current_margin=0.15,
    )
    print(f"  历史利润率序列: {[f'{m:.0%}' for m in exxon_margins]}")
    print(f"  原始平均: {exxon_result.raw_average_margin:.1%} | 修剪均值（去极值）: {exxon_result.trimmed_average_margin:.1%}")
    print(f"  当前利润率: {exxon_result.current_margin:.1%} | 常态化建议值: {exxon_result.normalized_margin:.1%}")
    print_result(exxon_result)

    print("\n[场景B: Exxon — 营收利润率对原油价格回归分析]")
    oil_prices = [55, 45, 65, 80, 95, 75, 30, 60, 90, 85]  # 美元/桶
    regression = normalizer.regress_margin_to_commodity(
        margins=exxon_margins,
        commodity_prices=[float(p) for p in oil_prices],
        current_commodity_price=85.0,
    )
    print(f"  回归方程: 利润率 = {regression.slope:.4f} × 油价 + {regression.intercept:.4f}")
    print(f"  R² = {regression.r_squared:.3f} | 当前油价($85)对应常态化利润率: {regression.at_current_commodity_price:.1%}")
    print(f"  当前油价位于历史 {regression.commodity_price_percentile:.0f} 分位")

    print("\n[场景C: Toyota汽车 — 制造业周期利润率常态化]")
    toyota_margins = [0.08, 0.07, 0.09, 0.06, -0.01, 0.05, 0.09, 0.10, 0.08, 0.11]
    toyota_result = normalizer.normalize_by_historical_average(
        margins_history=toyota_margins,
        lookback_years=7,
        current_margin=0.11,
    )
    print(f"  常态化营业利润率（DCF建议使用）: {toyota_result.normalized_margin:.1%}")
    for w in toyota_result.warnings:
        print(f"  ⚠️  {w}")


def demo_stack() -> None:
    print_section("v4.0 完整三层堆栈 — AI独角兽Pre-IPO项目IC Memo")

    # --- Layer 1: 叙事DCF ---
    valuer = NarrativeDCFValuer()
    segments = [
        BusinessSegment(
            name="AI推理云（To-B SaaS）",
            tam_rmb=7200.0,
            terminal_market_share_pct=8.0,
            terminal_operating_margin_pct=32.0,
            sales_to_capital_ratio=1.3,
            years_to_terminal=8,
            discount_rate=0.13,
            industry_type="SaaS",
        ),
        BusinessSegment(
            name="具身智能机器人（To-C硬件）",
            tam_rmb=14400.0,
            terminal_market_share_pct=3.0,
            terminal_operating_margin_pct=22.0,
            sales_to_capital_ratio=0.9,
            years_to_terminal=10,
            discount_rate=0.16,
            industry_type="AI大模型",
        ),
    ]
    dcf_result = valuer.value(segments, terminal_growth_rate=0.03)

    # --- Layer 2: 扩张期权 ---
    option_valuer = ExpansionOptionValuer()
    agi_option = option_valuer.value(
        underlying_value_rmb=3600.0,   # AGI商业化远期价值
        exercise_cost_rmb=1800.0,
        time_to_expiry_years=7.0,
        volatility=0.55,
        risk_free_rate=0.035,
        probability_of_viability=0.10,
    )

    # --- Layer 3: 退出天花板（可比公司）---
    anchor = CompsValuationAnchor(safety_factor=0.75)
    anchor.add_comps([
        CompanyComp("Palantir", "AI决策", pe_multiple=95.0, ev_ebitda=50.0, ps_multiple=28.0),
        CompanyComp("C3.ai", "企业AI", pe_multiple=None, ev_ebitda=None, ps_multiple=12.0),
        CompanyComp("Scale AI", "AI数据", pe_multiple=None, ev_ebitda=None, ps_multiple=20.0),
    ])
    comps_result = anchor.analyze("AI决策")
    # 退出天花板：用可比PS中位数 × 预期3年后营收
    forward_revenue = 1200.0   # 预计3年后营收1200亿元
    ceiling_ps = comps_result.median_ps if hasattr(comps_result, "median_ps") else 20.0
    market_ceiling = forward_revenue * ceiling_ps

    # --- 定价体操检测 ---
    detector = PricingGymnasticsDetector()
    pricing_result = detector.detect(
        comp_pool=[
            Comp("Palantir", 28.0, "2025E", "AI软件"),
            Comp("C3.ai", 12.0, "TTM", "企业AI"),
        ],
        current_revenue_rmb=180.0,
        forward_revenue_rmb=1200.0,
        forward_year="2027E",
        claimed_multiple=15.0,
        current_ev_rmb=dcf_result.sotp_ev_rmb * 1.5,  # FA通常溢价50%报价
    )

    # --- 宏观风险调整 ---
    erp_calc = ImpliedERPCalculator()
    current_erp = erp_calc.calculate(
        index_level=5000.0,
        expected_dividend_yield_pct=1.9,
        expected_growth_pct=5.0,
        risk_free_rate_pct=4.0,
    )
    macro_engine = MacroRiskEngine()
    macro_result = macro_engine.evaluate(
        current_erp_result=current_erp,
        base_erp_pct=4.37,
    )

    # --- 三层堆栈聚合 ---
    stack = ThreeLayerValuationStack()
    entry_price = dcf_result.sotp_ev_rmb * 1.3   # 进场估值 = DCF地板价×1.3

    stack_result = stack.evaluate(
        project_name="AI独角兽 Pre-IPO（示例项目）",
        entry_price_rmb=entry_price,
        narrative_dcf_result=dcf_result,
        expansion_option_values_rmb=[agi_option.option_value_rmb],
        market_comps_ceiling_rmb=market_ceiling,
        pricing_detection_result=pricing_result,
        p_survival=0.80,
        macro_adjustment_factor=macro_result.adjustment_factor,
        analyst_name="PE Analyst (Demo)",
        investment_date="2026-04-28",
    )

    print_result(stack_result)
    print(f"\n  地板价（Layer 1 DCF）: {stack_result.intrinsic_floor_rmb:.0f}亿元")
    print(f"  期权溢价（Layer 2）:   {stack_result.optionality_premium_rmb:.0f}亿元")
    print(f"  天花板（Layer 3）:     {stack_result.market_ceiling_rmb:.0f}亿元")
    print(f"  进场估值:             {stack_result.entry_price_rmb:.0f}亿元")
    print(f"  安全边际带宽:         {stack_result.safety_margin_pct:.1%}")
    print(f"\n  投资建议: 【{stack_result.recommendation}】")
    print(f"\n{'=' * 70}")
    print("  IC MEMO (Markdown格式):")
    print('=' * 70)
    print(stack_result.ic_memo_markdown)


# ── Entry-point (standalone demo) ────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    DEMOS = {
        "narrativedcf": demo_narrativedcf,
        "probability":  demo_probability,
        "pricinggym":   demo_pricinggym,
        "macrorisk":    demo_macrorisk,
        "distress":     demo_distress,
        "restatement":  demo_restatement,
        "cyclical":     demo_cyclical,
        "stack":        demo_stack,
    }
    if len(sys.argv) < 2 or sys.argv[1] not in DEMOS:
        print("Usage: python gems/08_damodaran_stack_demo.py <command>")
        print("Commands:", ", ".join(DEMOS))
        sys.exit(1)
    DEMOS[sys.argv[1]]()
