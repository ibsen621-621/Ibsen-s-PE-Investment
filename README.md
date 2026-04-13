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