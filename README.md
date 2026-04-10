# 一级市场投资决策模型

> 基于《投的好，更要退的好（2024版）》— 李刚强  
> Primary Market Investment Decision Model based on "Invest Well, Exit Better (2024 Edition)"

## 核心功能 | Features

本模型将书中五大维度的投资框架量化为可执行的 Python 决策工具：

| 模块 | 功能描述 |
|------|----------|
| **投资阶段模型** | 天使轮50-50-1、VC 100-10-10、PE三年三倍/四年四倍、北交所安全垫模型 |
| **财务指标计算** | IRR（含Newton-Raphson多期现金流）、DPI/TVPI转化率分析、戴维斯双杀风险检测 |
| **退出分析系统** | 三条抛物线退出时机、流动性危机预警、退出决策委员会多渠道评估 |
| **LP评估框架** | GP六大核心指标评分卡、三不三要资产配置建议 |
| **投资哲学检验** | 价值投机一致性、政治经济视角评分、退出率现实性校验 |

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

# 运行测试
python -m pytest tests/ -v
```

---

## 模型框架 | Model Architecture

```
src/investment_model/
├── stages.py        # 投资阶段量化模型 (Angel / VC / PE / BSE)
├── metrics.py       # 财务指标计算器 (IRR / DPI-TVPI / 估值分析)
├── exit.py          # 退出分析系统 (时机分析 / 决策委员会)
├── lp_evaluation.py # LP评估框架 (GP评分卡 / 资产配置建议)
└── philosophy.py    # 投资哲学检验器
```

---

## 五大投资维度 | Five Investment Dimensions

### 一、投资阶段量化模型

| 阶段 | 模型 | 核心参数 |
|------|------|---------|
| 天使轮 | **50-50-1** | 目标市值≥50亿 / 回报≥50倍 / 单项目回收整支基金 / 进入估值≤5000万 |
| 成长期VC | **100-10-10** | 目标市值≥100亿 / 回报≥10倍 / 净赚≥10亿 / 估值5-8亿 / 持股>13% |
| 中后期PE | **三年三倍/四年四倍** | 利润增速≥30% / PE扩张≥1倍 / IRR≥15% |
| 北交所 | **安全垫模型** | 进入PE≤10倍 / 安全垫≥50% / 利润增速≥20% |

### 二、退出能力建设

- **抛物线左侧退出**：行业/企业/资本三条曲线交汇的黄金退出点与白银退出点
- **持有即买入原则**：账面浮盈视为重新投资本金，预期收益无法覆盖风险则止盈
- **多元化退出**：IPO / 并购 / 老股转让 / S基金，给予接盘方10%-20%折扣

### 三、DPI/TVPI现实检验

| 基准 | DPI/TVPI转化率 |
|------|---------------|
| 全球顶尖基金 | 88% |
| 国内人民币基金（均值） | 36% |

### 四、GP六大核心指标

1. 历史基金真实 **DPI** 数据
2. 剔除未变现水分的真实 **MOC**
3. 老LP **复投率**（既往满意度）
4. 基金规模与团队能力的 **匹配度**
5. 核心项目 **筹码集中度**（重仓赢家的魄力）
6. **政府引导基金占比**（返投压力评估）

### 五、LP资产配置（三不三要）

- ❌ 不碰**市场化母基金**（双重收费结构）
- ❌ **盲池基金**仓位控制在20-30%
- ✅ **重仓精选专项基金**，要求GP大比例跟投

---

## 使用示例 | Usage Example

```python
from src.investment_model import VCModel, IRRCalculator, GPScorecard

# 评估VC投资机会
vc = VCModel()
result = vc.evaluate(
    entry_valuation_rmb=6.0,       # 6亿估值
    investment_amount_rmb=1.0,     # 1亿投入
    expected_market_cap_rmb=120.0, # 120亿退出
    fund_size_rmb=20.0,
)
print(result.summary)
# ✅ VC投资可行性通过 (4/5 项指标达标)。预测回报 10.3x，持股 14.3%。

# 计算IRR
irr = IRRCalculator()
irr_result = irr.from_multiple(investment_rmb=5.0, return_rmb=16.0, holding_years=3)
print(irr_result.summary)
# ✅ IRR = 47.36%，基准回报率 15%，达标。

# GP尽职调查评分
gp = GPScorecard()
gp_result = gp.evaluate(
    historical_dpi=1.5,
    reported_moc=3.0,
    unrealised_pct=30.0,
    lp_reinvestment_rate_pct=80.0,
    fund_size_rmb=30.0,
    team_managed_assets_rmb=35.0,
    target_stage="pe",
    top3_investment_pct=50.0,
    gov_fund_pct=20.0,
)
print(gp_result.summary)
# GP综合评分: 100/100 | 等级: A | ✅ 建议投资
```

---

## 测试覆盖 | Test Coverage

```
tests/
├── test_stages.py       # 22 tests — 投资阶段模型
├── test_metrics.py      # 18 tests — 财务指标计算器
├── test_exit.py         # 23 tests — 退出分析模型
├── test_lp_evaluation.py # 18 tests — LP评估框架
└── test_philosophy.py   # 9 tests  — 投资哲学检验
```

运行 `python -m pytest tests/ -v` 可验证全部 83 个测试用例。

---

*本模型仅供研究与学习参考，不构成任何投资建议。*