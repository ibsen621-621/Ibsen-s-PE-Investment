# 一级市场投资决策模型 — Gemini Gems v4.0 知识库总览

> 基于《投的好，更要退的好（2024版）》— 李刚强 + 达莫达兰估值工具箱（v4.0）
> Primary Market Investment Decision Model + Damodaran Valuation Toolkit (v4.0)

---

## 为什么这 10 个文件是最优整合方案

Gemini Gems 平台每个 Gem 最多支持 **10 个知识文件**。原始 `src/investment_model/` 目录下共有 **19 个** Python 模块（v3.0 的 11 个 + v4.0 的 8 个），远超限额。

本方案的整合逻辑：

| 整合原则 | 具体体现 |
|---------|---------|
| **功能内聚** | 同一业务场景的工具合并（如 narrative_dcf + cyclical_normalization 同属"地板价估值"） |
| **调用链聚合** | 经常联动使用的模块放在一起（如 exit + lp_evaluation + philosophy 构成"完整尽调视角"） |
| **Layer 完整性** | 达莫达兰三层堆栈（Layer 1-3）各自独立为文件，便于 Gem 按层路由 |
| **文件均匀** | 每个文件 26-65KB，避免单文件过大影响摄取质量 |
| **API 可追溯** | 每段代码均保留 `# ==== ORIGIN: {source}.py ====` 分隔符，方便追溯来源 |

---

## 知识文件清单（10 个）

| 文件 | 合并来源 | 核心类/函数 | Gem 使用场景 |
|------|---------|-----------|------------|
| **01_stages_metrics.py** | `stages.py` + `metrics.py` | `AngelModel`, `VCModel`, `PEModel`, `BSEModel`, `IRRCalculator`, `DPITVPICalculator`, `ValuationAnalyzer`, `CompsValuationAnchor`, `UnrealisedValueStripper` | 阶段模型评估、IRR/DPI/TVPI 计算、戴维斯双杀检测、可比公司估值锚 |
| **02_exit_lp_gp.py** | `exit.py` + `lp_evaluation.py` + `philosophy.py` | `ExitAnalyzer`, `ExitDecisionCommittee`, `LiquidityDiscountModel`, `GPScorecard`, `AssetAllocationAdvisor`, `LPBehaviorChecker`, `InvestmentPhilosophyChecker`, `HardTechStrategyEvaluator` | 退出时机分析、GP 评分卡、LP 行为纠偏、P/Strategic 硬科技战略评估 |
| **03_simulation_curves_cashflow.py** | `simulation.py` + `curves.py` + `fund_cashflow.py` | `MonteCarloEngine`, `PortfolioSimulator`, `LognormalParam`, `NormalParam`, `PoissonParam`, `LogisticGrowthCurve`, `GompertzCurve`, `ExitSignalDetector`, `FundCashflowModel` | 蒙特卡洛概率模拟、增长曲线退出信号、J 曲线/基金现金流 |
| **04_post_deal_dd.py** | `post_investment.py` + `deal_structure.py` + `due_diligence.py` | `GPPostInvestmentEvaluator`, `DoubleDownDecisionModel`, `AntiDilutionChecker`, `BuybackFeasibilityChecker`, `DuPontAnalyzer`, `GrowthQualityChecker` | 投后管理境界评分、拐点追投决策、交易结构审查、基本面尽调 |
| **05_narrative_dcf.py** | `narrative_dcf.py` + `cyclical_normalization.py` | `NarrativeDCFValuer`, `BusinessSegment`, `NarrativeDCFResult`, `SegmentValuationDetail`, `CyclicalNormalizer`, `NormalizationResult`, `RegressionResult` | 叙事DCF地板价（Layer 1）、SOTP加总、周期股利润率常态化 |
| **06_probabilistic_pricing.py** | `probabilistic_valuation.py` + `pricing_deconstructor.py` | `ExpansionOptionValuer`, `ExpansionOptionResult`, `ValuationDistribution`, `ValuationDistributionResult`, `PricingGymnasticsDetector`, `Comp`, `PricingDeconstructionResult` | 扩张期权定价（Layer 2）、蒙特卡洛估值分布、FA话术解码/定价体操拆解 |
| **07_macro_distress_restatement.py** | `macro_risk.py` + `distress_valuation.py` + `financial_restatement.py` | `ImpliedERPCalculator`, `SovereignCRPAdjuster`, `MacroRiskEngine`, `DistressDualTrackValuer`, `IntangibleCapitalizer`, `SOVEREIGN_CDS_REFERENCE`, `R_AND_D_AMORTIZATION_YEARS` | 市场隐含ERP、国家风险溢价、MAC触发、破产双轨估值、R&D资本化/SBC调整 |
| **08_damodaran_stack_demo.py** | `damodaran_stack.py` + `main.py` (v4.0 demo) | `ThreeLayerValuationStack`, `ThreeLayerValuationResult` + 8 个完整 demo 函数 | 三层堆栈聚合（地板/期权/天花板）、IC Memo 自动生成、完整调用示例 |
| **09_README.md** | 本文件 | — | v3.0 + v4.0 全模块架构说明 |
| **10_gemini_gems_guide.md** | 系统指令 + 部署指引 | — | Gem 系统指令 + 完整部署步骤 + 10 个使用场景 |

---

## 模块架构总览

```
gems/ (Gemini Gems 知识库，v4.0)
│
├── 01_stages_metrics.py     ← v3.0 核心：阶段模型 + 财务指标
├── 02_exit_lp_gp.py         ← v3.0 核心：退出 + LP/GP + 哲学
├── 03_simulation_curves_cashflow.py  ← v3.0 核心：概率 + 曲线 + J曲线
├── 04_post_deal_dd.py        ← v3.0 新增：投后 + 交易结构 + 尽调
│
├── 05_narrative_dcf.py       ← v4.0 Layer 1：叙事DCF + 周期常态化
├── 06_probabilistic_pricing.py  ← v4.0 Layer 2+3辅助：期权 + 定价拆解
├── 07_macro_distress_restatement.py  ← v4.0 工具：宏观 + 困境 + 财务重述
├── 08_damodaran_stack_demo.py  ← v4.0 聚合器：三层堆栈 + IC Memo + Demo
│
├── 09_README.md              ← 本文件：架构总览
└── 10_gemini_gems_guide.md   ← 系统指令 + 部署指引 + 使用场景
```

---

## v3.0 模块（11 个原始文件 → 4 个 Gem 文件）

| 原始文件 | 整合到 | 核心功能 |
|---------|--------|---------|
| `stages.py` | 01 | 天使50-50-1、VC 100-10-10、PE三年三倍/四年四倍、北交所安全垫 |
| `metrics.py` | 01 | IRR（Newton-Raphson多期）、DPI/TVPI转化率、戴维斯双杀、可比公司锚 |
| `exit.py` | 02 | 三条抛物线退出时机、退出决策委员会、流动性折价模型 |
| `lp_evaluation.py` | 02 | GP六大核心指标评分卡、三不三要、LP行为纠偏 |
| `philosophy.py` | 02 | 价值投机一致性检验、政治经济视角、P/Strategic硬科技战略 |
| `simulation.py` | 03 | 蒙特卡洛引擎（LognormalParam/NormalParam/PoissonParam） |
| `curves.py` | 03 | Logistic/Gompertz曲线、资本周期、退出信号自动检测 |
| `fund_cashflow.py` | 03 | J曲线、基金现金流时序、GP Carry 计算 |
| `post_investment.py` | 04 | GP投后四重境界（40分制）、拐点追投决策 |
| `deal_structure.py` | 04 | 老股转让红旗、反稀释条款触发、回购可行性 |
| `due_diligence.py` | 04 | 杜邦ROE三因子、LTV/CAC/留存/NPS/NDR伪增长检测 |

---

## v4.0 达莫达兰估值工具箱（8 个新文件 → 4 个 Gem 文件）

> 对应 Aswath Damodaran 估值工具七件套，一级市场融合实现

| 原始文件 | 整合到 | 达莫达兰工具 | 核心公式/方法 |
|---------|--------|------------|-------------|
| `narrative_dcf.py` | 05 | 工具一：叙事→数字 SOTP-DCF | TAM×市占率→FCF→Gordon Growth终值；SOTP分板块折现 |
| `cyclical_normalization.py` | 05 | 工具七：周期常态化 | 历史7年修剪均值；大宗商品价格OLS回归 |
| `probabilistic_valuation.py` | 06 | 工具二：扩张期权+概率分布 | Black-Scholes Call（stdlib math实现）；蒙特卡洛10000次DCF |
| `pricing_deconstructor.py` | 06 | 工具三：定价体操识别 | 跨期乘数检测；樱桃采摘σ/μ>0.5；乘数压缩TTM>30x vs宣称<5x |
| `macro_risk.py` | 07 | 工具四：动态ERP+CRP | GGM反推隐含ERP；Damodaran CRP=(CDS差/10000)×股债波动率比 |
| `distress_valuation.py` | 07 | 工具五：双轨破产估值 | Hull公式P_default；Altman Z-Score；期望值=P(存活)×DCF+P(破产)×清算 |
| `financial_restatement.py` | 07 | 工具六：财务外科手术 | R&D资本化（逐年未摊销分）；CAC资本化；SBC调整；ROIC重述 |
| `damodaran_stack.py` | 08 | 三层堆栈聚合器 | safety_margin=(天花板-地板)/进场价-1；>40%→INVEST；20-40%→NEGOTIATE；<20%→PASS |

---

## 达莫达兰三层估值堆栈框架

```
┌─────────────────────────────────────────────────────────────────────┐
│                    三层估值堆栈（IC Memo决策框架）                    │
├─────────────────────────────────────────────────────────────────────┤
│  Layer 3: 退出天花板（市场定价上限）                                  │
│  ← 可比公司乘数 × 宏观调整系数⁻¹                                     │
│  ← 文件: 06_probabilistic_pricing.py (PricingGymnasticsDetector)   │
│                                                                      │
│  ▲ 安全边际带宽 = (天花板-地板)/进场价 - 1                            │
│  ▲ > 40% → INVEST | 20-40% → NEGOTIATE_TERMS | < 20% → PASS       │
│                                                                      │
│  Layer 2: 期权溢价（想象空间量化）                                    │
│  ← Black-Scholes Call 扩张期权                                       │
│  ← 文件: 06_probabilistic_pricing.py (ExpansionOptionValuer)       │
│                                                                      │
│  Layer 1: 内在价值地板（第一性原理DCF）                               │
│  ← 叙事驱动 SOTP-DCF × 存活概率 / 宏观调整系数                       │
│  ← 文件: 05_narrative_dcf.py (NarrativeDCFValuer)                  │
│  ← 辅助: 07 (ImpliedERPCalculator, CyclicalNormalizer)             │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 快速开始 | Quick Start

```python
# Python 原版（完整精度）
from src.investment_model import (
    # v3.0
    AngelModel, VCModel, PEModel, BSEModel,
    IRRCalculator, DPITVPICalculator, ValuationAnalyzer,
    ExitAnalyzer, GPScorecard, LPBehaviorChecker,
    HardTechStrategyEvaluator,
    # v4.0
    NarrativeDCFValuer, BusinessSegment,
    ExpansionOptionValuer, ValuationDistribution,
    PricingGymnasticsDetector, Comp,
    ImpliedERPCalculator, SovereignCRPAdjuster, MacroRiskEngine,
    DistressDualTrackValuer, IntangibleCapitalizer, CyclicalNormalizer,
    ThreeLayerValuationStack,
)

# 完整三层堆栈 demo
python main.py stack    # 输出 IC Memo
python main.py demo     # 运行全部模块演示

# 测试
python -m pytest tests/ -v   # 329 个测试用例
```

---

## 测试覆盖 | Test Coverage（v4.0 共 329 个测试）

```
tests/
├── test_stages.py                  # 22 tests — 投资阶段模型
├── test_metrics.py                 # 18 tests — 财务指标计算器
├── test_exit.py                    # 23 tests — 退出分析模型
├── test_lp_evaluation.py           # 18 tests — LP/GP评估框架
├── test_philosophy.py              # 26 tests — 投资哲学（含P/Strategic）
├── test_simulation.py              # 20 tests — 蒙特卡洛模拟
├── test_curves.py                  # 31 tests — 数学增长曲线
├── test_post_investment.py         # 22 tests — 投后管理与拐点追投
├── test_deal_structure.py          # 20 tests — 交易结构与底线防守
├── test_due_diligence.py           # 22 tests — 基本面尽调
├── test_lp_behavior.py             # 15 tests — LP行为学纠偏
├── test_damodaran_toolkit.py       # 92 tests — 达莫达兰v4.0工具箱
└── test_fund_cashflow.py           # (part of simulation tests)
```

---

## 版本历史

| 版本 | 发布日期 | 新增内容 |
|------|---------|---------|
| **v4.0** | 2025-Q1 | 达莫达兰七件套（叙事DCF、扩张期权、定价拆解、宏观ERP、双轨估值、财务重述、周期常态化）+ 三层堆栈聚合器 |
| **v3.0** | 2024-Q4 | P/Strategic硬科技战略、投后管理境界、交易结构防守、基本面尽调、LP行为纠偏 |
| **v2.0** | 2024-Q3 | 蒙特卡洛引擎、数学增长曲线、J曲线基金现金流 |
| **v1.0** | 2024-Q2 | 四阶段模型、IRR/DPI/TVPI、退出分析、GP评分卡 |

---

*本知识库仅供研究与学习参考，不构成任何投资建议。*
*Gemini Gems 部署详情请参阅 `10_gemini_gems_guide.md`。*
