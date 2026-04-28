"""
定价体操拆解模块
Pricing Gymnastics Deconstructor Module

对应达莫达兰工具三：识破投行相对定价的防身术
一级市场融合点：FA话术解码、对标池完整性检验、乘数跨期操纵识别

核心洞见：
- 相对定价（乘数法）本身不是估值，是"定价"——本质上是跟同类资产比较谁贵谁便宜
- 投行FA最擅长的五种"定价体操"：
  1. 用未来年份收入（E）锚定低乘数，忽视当前高乘数的畸形
  2. 对标池只选高增长标杆，剔除行业中位数
  3. 不同年份乘数混搭（TTM vs 2026E），制造伪对比
  4. 以未实现的"协同效应"单独估值
  5. 用DAU/GMV等非盈利指标绕开盈利能力检验
- 本模块量化检测上述操纵，提供反向尽调清单

模块组成：
- Comp：可比公司数据类
- PricingGymnasticsDetector：检测定价操纵的五种模式，生成FA话术解码表
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# 可比公司数据类
# Comparable Company Data Class
# ---------------------------------------------------------------------------

@dataclass
class Comp:
    """
    可比公司数据
    Comparable company data point.

    Fields
    ------
    name               公司名称
    ev_sales_multiple  EV/Sales 乘数
    reference_year     乘数对应年份（"TTM" / "2024E" / "2025E" 等）
    sector             所属行业/子赛道
    is_growth_stock    是否为高增长股票（若非，则不宜与高增长标的对比）
    """

    name: str
    ev_sales_multiple: float
    reference_year: str               # "TTM" / "2024E" / "2025E" etc.
    sector: str = ""
    is_growth_stock: bool = True


# ---------------------------------------------------------------------------
# 输出数据类
# Output Data Class
# ---------------------------------------------------------------------------

@dataclass
class PricingDeconstructionResult:
    """
    定价体操拆解结果
    Pricing gymnastics deconstruction result.

    Fields
    ------
    red_flags                    检测到的红旗列表
    fa_decoder_table             FA话术 → 真实含义 → 反制动作 对照表
    implied_current_multiple     基于当前收入的隐含乘数（EV/当前Revenue）
    comp_pool_std_over_mean      对标池乘数离散度（标准差/均值）
    cherry_pick_detected         是否检测到樱桃采摘（对标池选择性偏差）
    cross_period_mismatch        是否存在跨期乘数混搭（TTM vs Forward混用）
    multiple_compression_detected 是否检测到乘数压缩操纵（当前高乘数被未来低乘数掩盖）
    missing_anchor_count         对标池中缺少的低估值锚数量
    """

    red_flags: list[str]
    fa_decoder_table: list[dict]         # FA话术解码表
    implied_current_multiple: float      # 当前隐含EV/Sales
    comp_pool_std_over_mean: float       # 对标池离散度
    cherry_pick_detected: bool
    cross_period_mismatch: bool
    multiple_compression_detected: bool
    missing_anchor_count: int
    summary: str
    warnings: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    details: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# 定价体操检测引擎
# Pricing Gymnastics Detection Engine
# ---------------------------------------------------------------------------

class PricingGymnasticsDetector:
    """
    定价体操检测引擎
    Pricing Gymnastics Detection Engine

    检测逻辑概述：
    1. 跨期混搭（Cross-Period Mismatch）：
       - 若目标公司用 Forward Revenue 计算乘数，但可比公司用 TTM → 系统性低估目标乘数
    2. 樱桃采摘（Cherry-Picking）：
       - 对标池乘数标准差/均值 > 0.5 → 分散度过高，说明对标不同质
       - 对标池中 < claimed_multiple/2 的公司数量 → 缺失的低估值锚
    3. 乘数压缩操纵（Multiple Compression）：
       - 当前隐含乘数 > 30 但宣称乘数 < 5 → 用远期乘数掩盖当前畸形估值
    4. 生成 FA 话术解码表（至少5条），覆盖一级市场常见套路
    """

    # 常见FA话术解码表（固定知识库）
    FA_DECODER_KNOWLEDGE_BASE: list[dict] = [
        {
            "fa_claim": "参照可比公司2025E EV/Sales 3x，本项目估值合理",
            "real_meaning": "2025E乘数掩盖了当前可能高达20-30x的TTM乘数；"
                            "Forward估值依赖未来Revenue兑现，一旦增速低于预期，乘数立即回归高位",
            "counter_action": "要求同时披露基于当前TTM Revenue的EV/Sales，并做乘数压缩敏感性分析",
        },
        {
            "fa_claim": "对标Palantir/Snowflake等头部SaaS，给予高溢价",
            "real_meaning": "选取了行业top 5%的公司作为对标，忽略了90%的中位数公司；"
                            "头部溢价不适用于尚未穿越PMF的早期项目",
            "counter_action": "要求FA提供完整的行业可比公司池（含中位数），剔除市值>100亿美元的头部公司",
        },
        {
            "fa_claim": "本项目年增速200%，享受增长溢价",
            "real_meaning": "高增速从极低基数出发，Rule of 40测试（增速+利润率）往往不达标；"
                            "早期高增速持续性存疑，需要验证同期对标公司是否有类似增速",
            "counter_action": "要求提供Rule of 40评分、NRR（净收入留存率）以及增速衰减曲线",
        },
        {
            "fa_claim": "并购协同效应另行估值，不计入基础估值",
            "real_meaning": "协同效应高度不确定，研究表明超过70%的并购未能实现预期协同；"
                            "单独为不确定性付溢价是对买方不利的定价",
            "counter_action": "拒绝为协同效应单独付费，要求将协同效应纳入DCF敏感性分析而非单独乘数",
        },
        {
            "fa_claim": "参照GMV/DAU/MAU等运营指标估值，EV/GMV仅0.3x",
            "real_meaning": "非盈利指标估值绕开了Profitability检验；"
                            "GMV变现率和货币化路径的不确定性被定价忽视",
            "counter_action": "坚持使用Revenue-based乘数，要求提供从GMV到Revenue的变现率路径及时间表",
        },
        {
            "fa_claim": "本轮由知名机构领投，估值已经过市场验证",
            "real_meaning": "机构领投不等于估值合理——机构也会追风口犯错；"
                            "需独立核查机构是否做了真正的基本面分析，还是仅在跟风",
            "counter_action": "要求查阅领投机构的投资备忘录摘要，或直接与其GP沟通投资逻辑",
        },
        {
            "fa_claim": "海外同类公司估值是我们的5倍，中国折价后仍有3倍空间",
            "real_meaning": "中外市场结构差异巨大（监管/货币/退出渠道），"
                            "直接套用海外乘数是错误的跨市场比较；A股/港股估值体系与纳斯达克存在结构性差异",
            "counter_action": "要求使用同一市场（A股/港股）的可比公司，对海外对标打30-50%市场折扣",
        },
    ]

    def detect(
        self,
        *,
        comp_pool: list[Comp],
        current_revenue_rmb: float,
        forward_revenue_rmb: float,
        forward_year: str,
        claimed_multiple: float,
        current_ev_rmb: float,
    ) -> PricingDeconstructionResult:
        """
        检测定价体操并生成完整分析报告。

        Parameters
        ----------
        comp_pool             可比公司池
        current_revenue_rmb   目标公司当前收入（亿元，TTM）
        forward_revenue_rmb   目标公司Forward收入（亿元）
        forward_year          Forward收入对应年份（例如 "2025E"）
        claimed_multiple      FA/投行宣称的EV/Sales乘数
        current_ev_rmb        当前企业价值（亿元）

        Returns
        -------
        PricingDeconstructionResult
        """
        warnings: list[str] = []
        recommendations: list[str] = []
        red_flags: list[str] = []

        # --- 1. 计算当前隐含乘数 ---
        if current_revenue_rmb > 0:
            implied_current_multiple = current_ev_rmb / current_revenue_rmb
        else:
            implied_current_multiple = 0.0
            warnings.append("当前收入为零，无法计算TTM EV/Sales乘数。")

        # --- 2. 检测跨期乘数混搭 ---
        comp_reference_years = {c.reference_year for c in comp_pool}
        target_uses_forward = bool(forward_year) and forward_year.upper() != "TTM"
        comps_use_ttm = "TTM" in comp_reference_years
        cross_period_mismatch = target_uses_forward and comps_use_ttm and len(comp_pool) > 0

        if cross_period_mismatch:
            red_flags.append(
                f"⚠️ 跨期乘数混搭：目标公司使用 {forward_year} Forward Revenue，"
                "但部分可比公司使用 TTM，造成系统性低估目标公司乘数的假象。"
            )
            recommendations.append(
                "要求FA统一使用TTM Revenue计算所有可比公司和目标公司的乘数，"
                "消除跨期比较的偏差。"
            )

        # --- 3. 对标池离散度检验（樱桃采摘）---
        multiples = [c.ev_sales_multiple for c in comp_pool]
        if len(multiples) >= 2:
            mean_m = sum(multiples) / len(multiples)
            variance_m = sum((m - mean_m) ** 2 for m in multiples) / len(multiples)
            std_m = math.sqrt(variance_m)
            comp_pool_std_over_mean = std_m / mean_m if mean_m > 0 else 0.0
        else:
            mean_m = multiples[0] if multiples else 0.0
            comp_pool_std_over_mean = 0.0

        cherry_pick_detected = comp_pool_std_over_mean > 0.5
        if cherry_pick_detected:
            red_flags.append(
                f"⚠️ 对标池离散度过高（标准差/均值={comp_pool_std_over_mean:.2f} > 0.5）："
                "可比公司之间估值分散度大，说明对标公司不同质，存在选择性偏差。"
            )
            recommendations.append(
                "要求FA缩小对标池范围，仅保留商业模式、收入规模（±50%）和增速高度相似的公司，"
                "确保对标池同质性。"
            )

        # 缺失低估值锚数量
        low_threshold = claimed_multiple / 2.0
        missing_anchor_count = sum(
            1 for c in comp_pool if c.ev_sales_multiple < low_threshold
        )
        total_below_claimed = sum(
            1 for c in comp_pool if c.ev_sales_multiple < claimed_multiple
        )
        if total_below_claimed == 0 and len(comp_pool) > 0:
            red_flags.append(
                f"⚠️ 所有可比公司乘数均高于宣称乘数 {claimed_multiple:.1f}x，"
                "对标池只选了估值更高的公司，形成向上偏差。"
            )

        # --- 4. 乘数压缩操纵检测 ---
        multiple_compression_detected = (
            implied_current_multiple > 30 and claimed_multiple < 5
        )
        if multiple_compression_detected:
            red_flags.append(
                f"🚨 乘数压缩操纵：当前TTM EV/Sales={implied_current_multiple:.1f}x，"
                f"但宣称乘数仅 {claimed_multiple:.1f}x（基于远期收入）。"
                "用远期乘数掩盖当前高估，若增速未达预期将面临剧烈估值回调。"
            )
            recommendations.append(
                f"当前TTM乘数达 {implied_current_multiple:.1f}x，"
                "要求建立Revenue Bridge（当前→Forward年份），逐季验证增速可实现性，"
                "并在Term Sheet中加入估值重置条款（如未完成里程碑则触发反稀释）。"
            )

        # --- 5. 非成长股混入检测 ---
        non_growth_comps = [c.name for c in comp_pool if not c.is_growth_stock]
        if non_growth_comps:
            names_str = ", ".join(non_growth_comps)
            red_flags.append(
                f"⚠️ 对标池混入非成长股：{names_str}。"
                "非成长股的低乘数用于拉低对标池均值，制造'相对低估'假象。"
            )

        # --- 6. 生成FA话术解码表（从知识库中选取相关条目）---
        fa_decoder_table = self.FA_DECODER_KNOWLEDGE_BASE[:5]  # 展示前5条核心话术

        # --- 整合评估 ---
        n_red_flags = len(red_flags)
        if n_red_flags >= 3:
            warnings.append(
                f"检测到 {n_red_flags} 个定价操纵信号，建议拒绝当前估值框架，"
                "要求FA从头以内在价值DCF方法重新定价。"
            )
        elif n_red_flags >= 1:
            warnings.append(
                f"检测到 {n_red_flags} 个定价操纵信号，在接受当前乘数估值前，"
                "逐一核查并要求FA提供书面解释。"
            )
        else:
            recommendations.append(
                "未检测到明显定价体操信号，可比公司池质量尚可，"
                "但仍建议进行独立DCF验证以锚定内在价值地板价。"
            )

        summary = (
            f"定价体操检测: {n_red_flags}个红旗 | "
            f"当前TTM乘数={implied_current_multiple:.1f}x vs 宣称{claimed_multiple:.1f}x | "
            f"对标池离散度={comp_pool_std_over_mean:.2f} | "
            f"跨期混搭={'是' if cross_period_mismatch else '否'} | "
            f"樱桃采摘={'检测到' if cherry_pick_detected else '未检测到'}"
        )

        return PricingDeconstructionResult(
            red_flags=red_flags,
            fa_decoder_table=fa_decoder_table,
            implied_current_multiple=round(implied_current_multiple, 2),
            comp_pool_std_over_mean=round(comp_pool_std_over_mean, 4),
            cherry_pick_detected=cherry_pick_detected,
            cross_period_mismatch=cross_period_mismatch,
            multiple_compression_detected=multiple_compression_detected,
            missing_anchor_count=missing_anchor_count,
            summary=summary,
            warnings=warnings,
            recommendations=recommendations,
            details={
                "n_comps": len(comp_pool),
                "comp_multiples": multiples,
                "mean_comp_multiple": round(mean_m, 2) if multiples else 0.0,
                "implied_current_multiple": round(implied_current_multiple, 2),
                "claimed_multiple": claimed_multiple,
                "forward_year": forward_year,
                "current_revenue_rmb": current_revenue_rmb,
                "forward_revenue_rmb": forward_revenue_rmb,
            },
        )
