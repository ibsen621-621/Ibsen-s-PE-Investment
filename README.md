# 一级市场投资决策模型

> 基于《投的好，更要退的好（2024版）》— 李刚强  
> Primary Market Investment Decision Model based on "Invest Well, Exit Better (2024 Edition)"

## 核心功能 | Features

本模型将书中五大维度的投资框架量化为可执行的 Python 决策工具，v3.0 新增五大维度升级：

| 模块 | 功能描述 |
|------|----------|
| **投资阶段模型** | 天使轮50-50-1、VC 100-10-10、PE三年三倍/四年四倍、北交所安全垫模型 |
| **财务指标计算** | IRR（含Newton-Raphson多期现金流）、DPI/TVPI转化率分析、戴维斯双杀风险检测 |
| **退出分析系统** | 三条抛物线退出时机、流动性危机预警、退出决策委员会多渠道评估 |
| **LP评估框架** | GP六大核心指标评分卡、三不三要资产配置建议 |
| **投资哲学检验** | 价值投机一致性、政治经济视角评分、退出率现实性校验 |
| **🆕 硬科技战略评估** | P/Strategic维度：技术落地路径检验、卡脖子PMF评估、战略估值修正系数 |
| **🆕 投后管理与拐点追投** | GP四重境界评分（40分制）、死亡谷穿越拐点追投决策模型 |
| **🆕 交易结构与底线防守** | 老股转让红旗检测、反稀释条款触发、回购可行性评估 |
| **🆕 基本面尽调** | 杜邦分析ROE三因子拆解、伪增长检测（LTV/CAC/留存/NPS/补贴） |
| **🆕 LP行为学纠偏** | 宏大叙事陷阱检测、FOMO跟风检测、期望值冷酷数学计算、灵魂拷问清单 |

---

## 快速开始 | Quick Start

```bash
# 安装依赖
pip install -r requirements.txt

# 运行完整演示
python main.py demo

# 单独运行各模块
python main.py angel       # 天使轮投资评估
python main.py vc          # VC成长期评估
python main.py pe          # PE中后期评估
python main.py bse         # 北交所投资评估
python main.py irr         # IRR计算
python main.py dpi         # DPI/TVPI分析
python main.py valuation   # 戴维斯双杀检测
python main.py exit        # 退出时机分析
python main.py committee   # 退出决策委员会
python main.py gp          # GP评分卡
python main.py allocation  # LP资产配置建议
python main.py philosophy  # 投资哲学检验

# 新增命令 (v3.0)
python main.py hardtech       # 硬科技战略评估 (P/Strategic)
python main.py postinvest     # GP投后管理境界评估
python main.py doubledown     # 拐点追投决策模型
python main.py dealstructure  # 交易结构与底线防守
python main.py duediligence   # 基本面尽调（杜邦+伪增长检测）
python main.py lpbehavior     # LP行为学纠偏

# 运行测试
python -m pytest tests/ -v
```

---

## 模型框架 | Model Architecture

```
src/investment_model/
├── stages.py           # 投资阶段量化模型 (Angel / VC / PE / BSE)
├── metrics.py          # 财务指标计算器 (IRR / DPI-TVPI / 估值分析)
├── exit.py             # 退出分析系统 (时机分析 / 决策委员会)
├── lp_evaluation.py    # LP评估框架 (GP评分卡 / 资产配置 / LP行为纠偏)
├── philosophy.py       # 投资哲学检验器 (含P/Strategic硬科技战略评估)
├── simulation.py       # 蒙特卡洛模拟引擎
├── curves.py           # 数学增长曲线与退出信号
├── fund_cashflow.py    # 基金现金流模型
├── post_investment.py  # 🆕 投后管理与拐点追投模块
├── deal_structure.py   # 🆕 交易结构与底线防守模块
└── due_diligence.py    # 🆕 基本面尽调定量交叉验证模块
```

---

## 五大升级维度 | Five New Dimensions (v3.0)

### 一、P/Strategic 硬科技战略评估

升级 `philosophy.py` 中的 `InvestmentPhilosophyChecker`，新增 `HardTechStrategyEvaluator`：

- **技术落地路径分类**：`core_plugin_replacement`（高容错）/ `system_infrastructure_rebuild`（极高风险）/ `incremental_improvement`（中等）
- **强制PMF评估**：卡脖子技术具备"国资兜底"属性，估值不应单纯使用财务PE/PS
- **战略估值修正系数**（`strategic_valuation_multiplier`，1.0-3.0x）：可被其他估值模块引用
- **NASA TRL技术成熟度**（1-9级）量化技术风险

### 二、投后管理与拐点追投（`post_investment.py`）

- **GP投后四重境界**（总分40分）：统计统筹→3R服务→战略赋能→退出导向型投后
- **拐点信号强度计算**（0-100分）：技术里程碑(30)+标杆客户(25)+营收拐点(20)+竞争壁垒(15)+跟投质量(10)
- **决策规则**：信号≥70且估值增幅<5倍→强烈追投；信号≥50→谨慎追投；信号<50→不追投

### 三、交易结构与底线防守（`deal_structure.py`）

- **老股红旗检测**：折价≥60%自动触发警报，出售>20%触发动机审查
- **反稀释条款触发**：区分Full Ratchet和加权平均，评估估值锚影响
- **回购可行性评估**：对赌指标合理性 + 创始人资产覆盖率 + 连带责任检查

### 四、基本面尽调（`due_diligence.py`）

- **杜邦分析**：ROE三因子（净利润率×资产周转率×权益乘数），自动判断高利润/高周转/高杠杆模式
- **增长质量验证**：LTV/CAC<3x→警告；月留存<30%→伪增长；NPS<0→护城河缺失；补贴>30%→虚假增长；SaaS NDR<100%→客户流失

### 五、LP行为学纠偏（`lp_evaluation.py`）

- **宏大叙事陷阱**：被院士/万亿赛道吸引但无具体数据→红旗
- **FOMO跟风检测**：因知名机构投了才跟投且无独立分析→红旗
- **期望值冷酷计算**：EV = 胜率×回报倍数 + 败率×亏损倍数，EV<1.0→负期望值警告
- **灵魂拷问清单**：个性化追问LP决策路径的核心盲点

---

## 使用示例 | Usage Example

```python
from src.investment_model import (
    HardTechStrategyEvaluator, TECH_PATH_CORE_PLUGIN,
    GPPostInvestmentEvaluator, DoubleDownDecisionModel,
    AntiDilutionChecker, DuPontAnalyzer, LPBehaviorChecker,
)

# 硬科技战略评估
evaluator = HardTechStrategyEvaluator()
result = evaluator.evaluate(
    tech_path_type=TECH_PATH_CORE_PLUGIN,
    is_chokepoint_tech=True,
    has_gov_procurement=True,
    tech_readiness_level=7,
)
print(result.strategic_valuation_multiplier)  # 2.17x

# GP投后境界评估
post_evaluator = GPPostInvestmentEvaluator()
post_result = post_evaluator.evaluate(
    has_financial_monitoring=True,
    has_3r_services=True,
    has_strategic_empowerment=True,
    has_exit_oriented_management=True,
    portfolio_company_survival_rate=0.70,
    avg_time_to_next_round_months=15.0,
)
print(post_result.level, post_result.score)  # 4, 40

# 杜邦分析
dupont = DuPontAnalyzer()
dup_result = dupont.analyze(
    net_profit_rmb=3.0, revenue_rmb=15.0,
    total_assets_rmb=20.0, total_equity_rmb=15.0,
)
print(dup_result.roe, dup_result.business_model)  # 0.2, high_margin

# LP行为纠偏
checker = LPBehaviorChecker()
lp_result = checker.check(
    attracted_by_narrative=True, has_concrete_evidence=False,
    following_famous_fund=True, has_independent_analysis=False,
    estimated_win_probability_pct=30.0,
    expected_return_multiple=3.0, expected_loss_multiple=0.1,
)
print(lp_result.narrative_trap_detected, lp_result.expected_value)  # True, 0.97
```

---

## 测试覆盖 | Test Coverage

```
tests/
├── test_stages.py          # 22 tests — 投资阶段模型
├── test_metrics.py         # 18 tests — 财务指标计算器
├── test_exit.py            # 23 tests — 退出分析模型
├── test_lp_evaluation.py   # 18 tests — LP/GP评估框架
├── test_philosophy.py      # 26 tests — 投资哲学检验（含硬科技战略）
├── test_simulation.py      # 20 tests — 蒙特卡洛模拟
├── test_curves.py          # 31 tests — 数学增长曲线
├── test_post_investment.py # 🆕 22 tests — 投后管理与拐点追投
├── test_deal_structure.py  # 🆕 20 tests — 交易结构与底线防守
├── test_due_diligence.py   # 🆕 22 tests — 基本面尽调
└── test_lp_behavior.py     # 🆕 15 tests — LP行为学纠偏
```

运行 `python -m pytest tests/ -v` 可验证全部 268 个测试用例。

---

*本模型仅供研究与学习参考，不构成任何投资建议。*
---

## v4.0 升级：达莫达兰估值工具箱融合

> "不要因为难，就放弃第一性原理；你100%会犯错，但这正是风险的本质。"
> —— Aswath Damodaran

融合理念：**用 Layer 1 内在价值（DCF）做"地板价"，用 Layer 3 退出定价做"天花板价"，用 Layer 2 期权做"想象空间"，三层堆栈形成安全边际带宽。**

---

### 七大工具一句话概述

| 工具编号 | 模块文件 | 核心类 | 一句话概述 |
|---------|---------|--------|----------|
| 工具一 | `narrative_dcf.py` | `NarrativeDCFValuer` | 叙事→TAM→市占率→利润率，SOTP-DCF自上而下重构，用Sales-to-Capital锚定烧钱率 |
| 工具二 | `probabilistic_valuation.py` | `ExpansionOptionValuer`, `ValuationDistribution` | Black-Scholes扩张期权量化"想象空间"，10000次蒙特卡洛替代Bull/Base/Bear |
| 工具三 | `pricing_deconstructor.py` | `PricingGymnasticsDetector` | 识破投行"跨期乘数/樱桃挑选/乘数压缩"三大定价体操，输出FA话术解码表 |
| 工具四 | `macro_risk.py` | `ImpliedERPCalculator`, `MacroRiskEngine` | GGM反推实时隐含ERP，主权CDS替代滞后信用评级，动态捕捉宏观风险重定价 |
| 工具五 | `distress_valuation.py` | `DistressDualTrackValuer` | 双轨期望值 = 持续经营×P(存活) + 清算NAV×P(破产)，从债券折价倒推隐含违约概率 |
| 工具六 | `financial_restatement.py` | `IntangibleCapitalizer` | R&D/CAC资本化重构ROIC，SBC必须扣除，GAAP会计准则是内在估值的"死敌" |
| 工具七 | `cyclical_normalization.py` | `CyclicalNormalizer` | 剔除商品周期噪音，7年修剪均值+OLS回归，输出DCF建议用常态化营业利润率 |
| 聚合器 | `damodaran_stack.py` | `ThreeLayerValuationStack` | 三层堆栈串联，自动生成IC Memo Markdown，一键输出投决会材料 |

---

### 三层估值堆栈架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                    三层估值堆栈 (Three-Layer Stack)                    │
├─────────────────────────────────────────────────────────────────────┤
│  Layer 3  │  市场退出定价（天花板）  │  CompsValuationAnchor          │
│           │  EV/Sales × 终局营收    │  + PricingGymnasticsDetector   │
├───────────┼────────────────────────┼──────────────────────────────-─┤
│  Layer 2  │  扩张期权溢价（想象空间）│  ExpansionOptionValuer         │
│           │  Black-Scholes 定价     │  (Black-Scholes, stdlib only)  │
├───────────┼────────────────────────┼────────────────────────────────┤
│  Layer 1  │  内在价值 DCF（地板价） │  NarrativeDCFValuer (SOTP)     │
│           │  叙事→TAM→FCF折现       │  + IntangibleCapitalizer       │
│           │                        │  + CyclicalNormalizer          │
├─────────────────────────────────────────────────────────────────────┤
│  风险调整  │  MacroRiskEngine (ERP) + DistressDualTrackValuer (P_s)  │
├─────────────────────────────────────────────────────────────────────┤
│  安全边际  │  (天花板 - 地板) / 进场价 - 1                             │
│  决策规则  │  >40% → INVEST  │  20-40% → NEGOTIATE_TERMS  │ <20% → PASS │
└─────────────────────────────────────────────────────────────────────┘
```

---

### 新增 CLI 命令

```bash
python main.py narrativedcf   # SpaceX三段式（航天发射/Starlink/xAI）SOTP估值
python main.py probability    # 火星采矿扩张期权 + AI独角兽TAM/Margin概率分布
python main.py pricinggym     # 投行1.75万亿定价SpaceX的体操拆解
python main.py macrorisk      # 2026年3月中东战争场景：Implied ERP 4.37%→4.77%
python main.py distress       # 类LVS困境标的：债券76%隐含违约概率双轨估值
python main.py restatement    # 类Amgen生物药企R&D资本化重述
python main.py cyclical       # Exxon/Toyota跨周期利润率常态化
python main.py stack          # 完整三层堆栈：AI独角兽Pre-IPO项目输出IC Memo
python main.py demo           # 全量演示（含所有v3.0 + v4.0模块）
```

---

### 融合后的 IC Memo 新模板

v4.0三层堆栈聚合器（`damodaran_stack.py::ThreeLayerValuationStack`）自动生成以下结构的 Markdown IC Memo：

```markdown
# IC Memo — {项目名称}
**分析日期**: YYYY-MM-DD  **分析师**: {分析师}

## 一、投资摘要
| 指标 | 数值 |
|------|------|
| 进场估值 | X亿元 |
| DCF地板价（Layer 1） | X亿元 |
| 期权溢价（Layer 2） | X亿元 |
| 退出天花板（Layer 3） | X亿元 |
| 安全边际带宽 | X% |
| **投资建议** | **INVEST / NEGOTIATE_TERMS / PASS** |

## 二、Layer 1 — 内在价值（叙事DCF）
{各板块终局营收 / 终局FCF / PV / 累计烧钱 明细表}

## 三、Layer 2 — 期权价值
{扩张期权列表及Black-Scholes定价}

## 四、Layer 3 — 市场退出定价
{可比公司天花板 + 定价体操红旗}

## 五、风险因子
{警告列表}

## 六、达氏纪律三原则检验
- **双锚原则**: 地板价 vs 天花板
- **强制概率化**: 存活率 P(survival)
- **强制反向尽调**: 定价操纵检测结果

## 七、投资建议与条款要求
{决策依据 + 条款建议}
```

---

### 达氏纪律三原则

1. **双锚原则**：必须同时有"地板价"（DCF内在价值）和"天花板价"（市场退出定价）。单锚定价（只有可比乘数）是情绪定价，不是估值。

2. **强制概率化**：禁止使用 Bull/Base/Bear 单点情景。对所有关键变量（TAM、利润率、S/C比）设定概率分布，输出估值分布钟形图，用分位数而非单一数字向投委会汇报。

3. **强制反向尽调**：每个投资机会必须找到至少3个反向论据（低估值锚、看空报告、周期高点警示）。投行话术解码是入场前的必备防御工具。

---

### v4.0 模块文件树

```
src/investment_model/
├── stages.py           # 投资阶段模型（Angel/VC/PE/BSE）
├── metrics.py          # 财务指标（IRR/DPI-TVPI/Comps/Valuation）
├── exit.py             # 退出分析（ExitAnalyzer/LiquidityDiscount）
├── lp_evaluation.py    # LP/GP评估（Scorecard/Allocation/Behavior）
├── philosophy.py       # 投资哲学检验（含硬科技战略）
├── simulation.py       # 蒙特卡洛引擎
├── curves.py           # 数学增长曲线
├── fund_cashflow.py    # J曲线与基金现金流
├── post_investment.py  # 投后管理与拐点追投
├── deal_structure.py   # 交易结构与底线防守
├── due_diligence.py    # 基本面尽调（杜邦+增长质量）
│   ──────── v4.0 新增 ────────
├── narrative_dcf.py          # 工具一：叙事SOTP-DCF
├── probabilistic_valuation.py # 工具二：概率估值与扩张期权
├── pricing_deconstructor.py  # 工具三：定价体操拆解
├── macro_risk.py             # 工具四：动态宏观风险重定价
├── distress_valuation.py     # 工具五：截断/破产双轨分离
├── financial_restatement.py  # 工具六：财务报表外科手术
├── cyclical_normalization.py # 工具七：周期股常态化
├── damodaran_stack.py        # 聚合器：三层估值堆栈 + IC Memo
└── __init__.py               # 导出所有模块（含v4.0新增类）
```

---

### 测试覆盖 (v4.0) | Test Coverage (v4.0)

```
tests/
├── test_stages.py               # 22 tests — 投资阶段模型
├── test_metrics.py              # 18 tests — 财务指标计算器
├── test_exit.py                 # 23 tests — 退出分析模型
├── test_lp_evaluation.py        # 18 tests — LP/GP评估框架
├── test_philosophy.py           # 26 tests — 投资哲学（含硬科技战略）
├── test_simulation.py           # 20 tests — 蒙特卡洛模拟
├── test_curves.py               # 31 tests — 数学增长曲线
├── test_new_modules.py          # 41 tests — J曲线/流动性/Comps等
├── test_post_investment.py      # 22 tests — 投后管理与拐点追投
├── test_deal_structure.py       # 20 tests — 交易结构与底线防守
├── test_due_diligence.py        # 22 tests — 基本面尽调
├── test_lp_behavior.py          # 15 tests — LP行为学纠偏
└── test_damodaran_toolkit.py    # 🆕 61 tests — 达莫达兰工具箱 (v4.0)
```

运行 `python -m pytest tests/ -v` 可验证全部 **329 个测试用例**。

---

### v4.0 使用示例

```python
from src.investment_model import (
    NarrativeDCFValuer, BusinessSegment,
    ExpansionOptionValuer,
    ThreeLayerValuationStack,
)

# Layer 1: 叙事DCF
valuer = NarrativeDCFValuer()
dcf_result = valuer.value([
    BusinessSegment(
        name="AI推理云",
        tam_rmb=7200.0,
        terminal_market_share_pct=8.0,
        terminal_operating_margin_pct=32.0,
        sales_to_capital_ratio=1.3,
        years_to_terminal=8,
        discount_rate=0.13,
        industry_type="SaaS",
    )
])
print(f"DCF地板价: {dcf_result.sotp_ev_rmb:.0f}亿元")

# Layer 2: 扩张期权
option_valuer = ExpansionOptionValuer()
option = option_valuer.value(
    underlying_value_rmb=3600.0,
    exercise_cost_rmb=1800.0,
    time_to_expiry_years=7.0,
    volatility=0.55,
    risk_free_rate=0.035,
    probability_of_viability=0.10,
)
print(f"期权价值: {option.option_value_rmb:.0f}亿元")

# 三层堆栈聚合 → IC Memo
stack = ThreeLayerValuationStack()
result = stack.evaluate(
    project_name="某AI独角兽Pre-IPO",
    entry_price_rmb=600.0,
    narrative_dcf_result=dcf_result,
    expansion_option_values_rmb=[option.option_value_rmb],
    market_comps_ceiling_rmb=5000.0,
    p_survival=0.80,
    analyst_name="李分析师",
)
print(result.recommendation)      # INVEST / NEGOTIATE_TERMS / PASS
print(result.ic_memo_markdown)    # 完整Markdown IC Memo
```

---

*本模型仅供研究与学习参考，不构成任何投资建议。*
