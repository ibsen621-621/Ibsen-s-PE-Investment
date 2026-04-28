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

from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from typing import List, Optional

from .narrative_dcf import NarrativeDCFResult
from .pricing_deconstructor import PricingDeconstructionResult


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
