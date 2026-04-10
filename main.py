#!/usr/bin/env python3
"""
一级市场投资决策模型 — 命令行界面
Primary Market Investment Decision Model — CLI

Usage:
    python main.py angel       # Evaluate angel-stage investment
    python main.py vc          # Evaluate VC-stage investment
    python main.py pe          # Evaluate PE-stage investment
    python main.py bse         # Evaluate BSE-targeting investment
    python main.py gp          # Score a GP (LP due diligence)
    python main.py exit        # Analyze exit timing
    python main.py montecarlo  # Monte Carlo probabilistic simulations
    python main.py curves      # Mathematical curve fitting & exit signals
    python main.py jcurve      # J-curve & fund cashflow model
    python main.py liquidity   # Dynamic liquidity discount model
    python main.py comps       # Comparable company valuation anchor
    python main.py strip       # GP MOC unrealised value stripper
    python main.py demo        # Run full demo with sample data
"""

import sys

from src.investment_model import (
    AngelModel,
    VCModel,
    PEModel,
    BSEModel,
    IRRCalculator,
    DPITVPICalculator,
    ValuationAnalyzer,
    ExitAnalyzer,
    ExitDecisionCommittee,
    LiquidityDiscountModel,
    GPScorecard,
    AssetAllocationAdvisor,
    InvestmentPhilosophyChecker,
    MonteCarloEngine,
    PortfolioSimulator,
    LognormalParam,
    NormalParam,
    PoissonParam,
    LogisticGrowthCurve,
    GompertzCurve,
    CapitalCycleCurve,
    CapitalCyclePoint,
    ExitSignalDetector,
    FundCashflowModel,
    CompsValuationAnchor,
    CompanyComp,
    UnrealisedValueStripper,
)


SEPARATOR = "=" * 70


def print_section(title: str) -> None:
    print(f"\n{SEPARATOR}")
    print(f"  {title}")
    print(SEPARATOR)


def print_result(result) -> None:
    print(f"\n{result.summary}")
    if hasattr(result, "warnings") and result.warnings:
        print("\n⚠️  风险提示:")
        for w in result.warnings:
            print(f"   • {w}")
    if hasattr(result, "recommendations") and result.recommendations:
        print("\n💡 建议:")
        for r in result.recommendations:
            print(f"   • {r}")
    if hasattr(result, "details") and result.details:
        print("\n📊 计算明细:")
        for k, v in result.details.items():
            print(f"   {k}: {v}")


def demo_angel() -> None:
    print_section("天使轮投资评估 — 50-50-1模型")
    model = AngelModel()
    result = model.evaluate(
        entry_valuation_rmb=0.4,       # 4000万估值
        fund_size_rmb=2.0,             # 2亿基金
        investment_amount_rmb=0.1,     # 1000万投入
        expected_market_cap_rmb=60.0,  # 60亿退出市值
        dilution_rate=0.60,
        holding_years=7,
    )
    print_result(result)


def demo_vc() -> None:
    print_section("VC成长期投资评估 — 100-10-10模型")
    model = VCModel()
    result = model.evaluate(
        entry_valuation_rmb=6.0,           # 6亿估值（在5-8亿窗口内）
        investment_amount_rmb=1.0,         # 1亿投入
        expected_market_cap_rmb=120.0,     # 120亿退出市值
        fund_size_rmb=20.0,
        dilution_rate=0.40,
        holding_years=5,
    )
    print_result(result)


def demo_pe() -> None:
    print_section("中后期PE投资评估 — 三年三倍模型")
    model = PEModel()
    result = model.evaluate(
        entry_pe=15.0,
        current_profit_rmb=2.0,            # 2亿净利润
        annual_profit_growth_rate=0.35,    # 35%利润增速
        target_exit_pe=25.0,               # 上市后25倍PE
        investment_amount_rmb=5.0,         # 5亿投入
        holding_years=3,
    )
    print_result(result)


def demo_bse() -> None:
    print_section("北交所投资评估 — 安全垫模型")
    model = BSEModel()
    result = model.evaluate(
        entry_pe=8.0,                      # 8倍PE进入（≤10倍）
        current_profit_rmb=0.3,            # 3000万净利润
        annual_profit_growth_rate=0.25,    # 25%利润增速
        expected_listing_pe=18.0,          # 北交所18倍PE上市
        investment_amount_rmb=0.5,
        holding_years=3,
    )
    print_result(result)


def demo_irr() -> None:
    print_section("IRR计算 — 三年三倍投资案例")
    calc = IRRCalculator()

    # 5亿投入，3年后收回16亿（约3.2倍）
    result = calc.from_multiple(
        investment_rmb=5.0,
        return_rmb=16.0,
        holding_years=3,
        hurdle_rate=0.15,
    )
    print(f"\n{result.summary}")

    # Also test with full cash flows
    print("\n[复杂现金流示例: 早期追加投资]")
    result2 = calc.calculate(
        cash_flows=[-5.0, -1.0, 0.0, 0.0, 20.0],
        hurdle_rate=0.15,
    )
    print(result2.summary)


def demo_dpi_tvpi() -> None:
    print_section("DPI/TVPI分析 — 中国人民币基金现实检验")
    calc = DPITVPICalculator()

    print("\n[场景A: 优秀基金]")
    result_a = calc.calculate(
        total_invested_rmb=10.0,
        total_distributed_rmb=16.0,
        remaining_fair_value_rmb=6.0,
        benchmark="global",
    )
    print(result_a.summary)
    for w in result_a.warnings:
        print(f"  ⚠️  {w}")

    print("\n[场景B: 典型国内人民币基金]")
    result_b = calc.calculate(
        total_invested_rmb=10.0,
        total_distributed_rmb=5.0,
        remaining_fair_value_rmb=14.0,
        benchmark="china",
    )
    print(result_b.summary)
    for w in result_b.warnings:
        print(f"  ⚠️  {w}")


def demo_valuation_davis() -> None:
    print_section("戴维斯双杀风险分析 — 新能源/AI赛道")
    analyzer = ValuationAnalyzer()

    print("\n[场景: 人工智能六小龙后期轮次]")
    result = analyzer.analyze(
        current_pe=80.0,
        sector_median_pe=40.0,
        current_earnings_growth_pct=20.0,
        consensus_earnings_growth_pct=60.0,
        market_phase="boom",
    )
    print(result.summary)
    for w in result.warnings:
        print(f"  ⚠️  {w}")
    for r in result.recommendations:
        print(f"  💡 {r}")


def demo_exit_timing() -> None:
    print_section("退出时机分析 — 抛物线模型")
    analyzer = ExitAnalyzer()

    print("\n[场景: 三条曲线同时触顶]")
    result = analyzer.analyze_timing(
        industry_growth_stage="peak",
        company_growth_stage="peak",
        capital_cycle_stage="hot",
        current_return_multiple=4.5,
        hurdle_multiple=3.0,
        years_held=4,
        years_remaining_in_fund=2,
        has_liquid_secondary_market=True,
    )
    print(result.summary)
    print(f"建议操作: {result.recommended_action}")
    for w in result.warnings:
        print(f"  ⚠️  {w}")

    print("\n[场景: 港股小盘股流动性检测]")
    liquidity = analyzer.evaluate_liquidity(
        exchange="港股",
        daily_trading_volume_usd=500_000,
        stake_value_rmb=2.0,
        target_exit_days=90,
    )
    for k, v in liquidity.items():
        if v is not None:
            print(f"  {k}: {v}")


def demo_exit_committee() -> None:
    print_section("退出决策委员会 — 多元化退出评估")
    committee = ExitDecisionCommittee()

    channels = committee.evaluate_all_channels(
        peak_paper_valuation_rmb=20.0,
        company_sector="消费科技",
        years_to_fund_end=2,
        ipo_readiness_score=6.0,
        ma_buyer_interest_score=7.0,
        secondary_market_liquidity=8.0,
        lp_cash_urgency="high",
        macro_capital_sentiment="neutral",
    )

    memo = committee.generate_decision_memo(channels, holding_cost_rmb=8.0)
    print(memo)


def demo_gp_scorecard() -> None:
    print_section("GP评分卡 — LP尽职调查六大指标")
    scorecard = GPScorecard()

    result = scorecard.evaluate(
        historical_dpi=1.2,
        reported_moc=3.5,
        unrealised_pct=55.0,         # 55% is paper
        lp_reinvestment_rate_pct=70.0,
        fund_size_rmb=50.0,
        team_managed_assets_rmb=40.0,
        target_stage="pe",
        top3_investment_pct=45.0,
        gov_fund_pct=35.0,
    )
    print(f"\n{result.summary}")
    if result.red_flags:
        print("\n🚩 红旗警示:")
        for f in result.red_flags:
            print(f"   • {f}")
    if result.green_flags:
        print("\n✅ 正面指标:")
        for f in result.green_flags:
            print(f"   • {f}")
    if result.recommendations:
        print("\n💡 建议:")
        for r in result.recommendations:
            print(f"   • {r}")
    print(f"\n各指标得分明细: {result.indicator_scores}")


def demo_allocation() -> None:
    print_section("LP资产配置建议 — 三不三要框架")
    advisor = AssetAllocationAdvisor()

    print("\n[场景A: 正常PE/VC配置]")
    result_a = advisor.advise(
        total_investable_assets_rmb=5.0,
        risk_tolerance="moderate",
        pe_budget_pct=25.0,
        gp_coinvestment_rate_pct=5.0,
        is_market_rate_fof=False,
        years_of_observation=3,
    )
    print(result_a.summary)

    print("\n[场景B: 市场化母基金 (应避免)]")
    result_b = advisor.advise(
        total_investable_assets_rmb=5.0,
        risk_tolerance="moderate",
        pe_budget_pct=20.0,
        gp_coinvestment_rate_pct=1.0,
        is_market_rate_fof=True,
    )
    print(result_b.summary)


def demo_philosophy() -> None:
    print_section("投资哲学检验 — 价值投机 + 政治经济 + 退出现实")
    checker = InvestmentPhilosophyChecker()

    print("\n[项目: 国产工业软件替代]")
    result = checker.check(
        investment_thesis="国产PLC/SCADA软件，替代西门子，政策强催化",
        has_exit_plan=True,
        has_profit_taking_triggers=True,
        sector="工业软件",
        is_hard_tech=True,
        is_domestic_substitution=True,
        is_autonomous_controllable=True,
        is_internet_traffic_model=False,
        fund_stage="vc",
        assumed_exit_rate_pct=15.0,
        valuation_vs_intrinsic_pct=30.0,
    )
    print(result.summary)
    for w in result.warnings:
        print(f"  ⚠️  {w}")
    for r in result.recommendations:
        print(f"  💡 {r}")


def demo_montecarlo() -> None:
    print_section("蒙特卡洛模拟 — 概率回报区间")

    engine = MonteCarloEngine(n_simulations=5000, seed=42)

    print("\n[VC项目：120亿目标市值，60亿标准差]")
    result = engine.simulate_vc_return(
        entry_valuation_rmb=6.0,
        investment_amount_rmb=1.0,
        market_cap_dist=LognormalParam(mean=120.0, std=60.0),
        dilution_rate_dist=NormalParam(mean=0.40, std=0.08, lo=0.10, hi=0.80),
        hurdle_multiple=10.0,
    )
    print(result.summary)

    print("\n[PE项目：利润增速35% ± 5%，PE扩张15→25倍]")
    pe_result = engine.simulate_pe_return(
        entry_pe=15.0,
        current_profit_rmb=2.0,
        investment_amount_rmb=5.0,
        profit_growth_dist=NormalParam(mean=0.35, std=0.05, lo=0.05, hi=0.80),
        exit_pe_dist=NormalParam(mean=25.0, std=5.0, lo=10.0, hi=50.0),
        holding_years=3,
        hurdle_multiple=3.0,
    )
    print(pe_result.summary)

    print("\n[组合视角：20项目VC基金，幂律分布验证]")
    sim = PortfolioSimulator(n_simulations=3000, seed=7)
    portfolio = sim.simulate_vc_portfolio(
        fund_size_rmb=20.0,
        n_investments=20,
        survival_rate=0.35,
        winner_multiple_dist=LognormalParam(mean=15.0, std=25.0),
        loser_multiple_dist=LognormalParam(mean=0.25, std=0.15),
        macro_target_label="100-10-10",
        macro_target_fund_multiple=3.0,
    )
    print(portfolio.summary)


def demo_curves() -> None:
    print_section("数学增长曲线 & 退出信号自动触发")

    print("\n[企业成长 — Logistic曲线 (K=100亿, r=0.8, 顶点t=4年)]")
    company = LogisticGrowthCurve(K=100.0, r=0.8, t0=4.0)
    for t in [1, 2, 3, 4, 5, 6, 8]:
        print(f"  t={t}年: 营收={company.value(t):.1f}亿 | 增速={company.growth_rate(t) * 100:.1f}%")

    print("\n[行业成长 — Gompertz曲线 (K=200亿, b=5, c=0.4)]")
    industry = GompertzCurve(K=200.0, b=5.0, c=0.4)
    peak_t = industry.peak_derivative_time()
    print(f"  增速顶点: t={peak_t:.2f}年 | 顶点时营收={industry.value(peak_t):.1f}亿")

    print("\n[资本周期 — PE倍数历史数据拟合]")
    cap = CapitalCycleCurve([
        CapitalCyclePoint(0, 15, "cold"),
        CapitalCyclePoint(2, 25, "warming"),
        CapitalCyclePoint(4, 45, "hot"),
        CapitalCyclePoint(7, 20, "cooling"),
        CapitalCyclePoint(9, 12, "cold"),
    ])

    print("\n[退出信号检测 — 三曲线联动]")
    detector = ExitSignalDetector(industry, company, cap)
    report = detector.scan(t_start=0.0, t_end=9.0, dt=0.5)
    print(f"  {report.summary}")
    for sig in report.signals:
        print(f"  [{sig.t}年] {sig.signal_type.upper()}: {sig.trigger_reason}")
        print(f"    → {sig.recommended_action}")


def demo_jcurve() -> None:
    print_section("J曲线 & 基金现金流模型")

    model = FundCashflowModel()
    result = model.model(
        fund_name="示例PE基金",
        fund_size_rmb=10.0,
        capital_call_schedule=[0.30, 0.30, 0.25, 0.15],
        exit_schedule=[0, 0, 0, 0, 0.20, 0.30, 0.35, 0.15],
        nav_growth_rate=0.28,
    )
    print(result.summary)
    print("\n  年度现金流明细:")
    print(f"  {'年份':>4} {'资本催缴':>8} {'管理费':>7} {'分配':>8} {'DPI':>6} {'TVPI':>6}")
    print("  " + "-" * 52)
    for f in result.annual_flows:
        print(
            f"  {f.year:>4} {f.capital_call_rmb:>8.2f}亿 {f.management_fee_rmb:>5.2f}亿 "
            f"{f.distribution_rmb:>7.2f}亿 {f.dpi:>5.2f}x {f.tvpi:>5.2f}x"
        )


def demo_liquidity_discount() -> None:
    print_section("动态流动性折价模型 — 宏观周期敏感")

    model = LiquidityDiscountModel()
    scenarios = [
        ("VC — 降息周期 + S基金活跃", dict(asset_stage="vc", credit_cycle="rate_cut", s_fund_market="active")),
        ("PE — 中性环境", dict(asset_stage="pe", credit_cycle="neutral", s_fund_market="active")),
        ("VC — 温和加息 + S基金降温", dict(asset_stage="vc", credit_cycle="rate_hike_mild", s_fund_market="cooling")),
        ("PE — 激进加息 + S基金冰河期", dict(asset_stage="pe", credit_cycle="rate_hike_aggressive", s_fund_market="frozen")),
        ("PE — 基金临到期（1年）", dict(asset_stage="pe", credit_cycle="neutral", s_fund_market="cooling", years_to_fund_end=1)),
    ]
    for label, kwargs in scenarios:
        r = model.calculate(**kwargs)
        print(f"\n  [{label}]")
        print(f"  → 建议折价率: {r.total_discount_pct:.1f}%")
        for w in r.warnings:
            print(f"     ⚠️  {w}")


def demo_comps() -> None:
    print_section("可比公司估值锚 — 外部数据接口")

    anchor = CompsValuationAnchor(safety_factor=0.70)
    anchor.add_comps([
        CompanyComp("商汤科技", "AI视觉", pe_multiple=85.0, ev_ebitda=42.0, ps_multiple=16.0),
        CompanyComp("旷视科技", "AI视觉", pe_multiple=72.0, ev_ebitda=36.0, ps_multiple=13.0),
        CompanyComp("第四范式", "AI决策", pe_multiple=95.0, ev_ebitda=48.0, ps_multiple=20.0),
        CompanyComp("云从科技", "AI视觉", pe_multiple=65.0, ev_ebitda=33.0, ps_multiple=11.0),
        CompanyComp("格灵深瞳", "AI安防", pe_multiple=78.0, ev_ebitda=39.0, ps_multiple=14.0),
    ])
    result = anchor.analyze("AI视觉")
    print(result.summary)
    print(f"\n  PE分布: P25={result.percentile_25_pe} | 中位={result.median_pe} | P75={result.percentile_75_pe}")
    print(f"  进场建议PE上限（保守）: {result.conservative_entry_pe}x")
    for w in result.warnings:
        print(f"  ⚠️  {w}")


def demo_unrealised_strip() -> None:
    print_section("未变现水分剔除 — GP MOC自动校正")

    stripper = UnrealisedValueStripper()
    result = stripper.strip(
        reported_moc=4.2,
        reported_tvpi=4.2,
        total_invested_rmb=10.0,
        total_distributed_rmb=8.0,
        unrealised_holdings=[
            {"name": "某AI独角兽", "book_value": 25.0, "follow_on_discount_pct": 35.0},
            {"name": "某消费品牌", "book_value": 10.0, "follow_on_discount_pct": 15.0},
            {"name": "某SaaS企业", "book_value": 7.0, "follow_on_discount_pct": 0.0},
        ],
    )
    print(result.summary)
    print("\n  逐项持仓校正:")
    for h in result.unrealised_holdings:
        print(
            f"  • {h['name']}: 账面={h['book_value']:.1f}亿 | "
            f"后续融资折价={h['follow_on_discount_pct']:.0f}% | "
            f"校正值={h['adjusted_value']:.2f}亿"
        )
    for w in result.warnings:
        print(f"  ⚠️  {w}")


def run_full_demo() -> None:
    print(f"\n{'*' * 70}")
    print("  一级市场投资决策模型 v2.0")
    print("  基于《投的好，更要退的好（2024版）》— 李刚强")
    print(f"{'*' * 70}")

    demo_philosophy()
    demo_angel()
    demo_vc()
    demo_pe()
    demo_bse()
    demo_irr()
    demo_dpi_tvpi()
    demo_valuation_davis()
    demo_exit_timing()
    demo_exit_committee()
    demo_gp_scorecard()
    demo_allocation()
    demo_montecarlo()
    demo_curves()
    demo_jcurve()
    demo_liquidity_discount()
    demo_comps()
    demo_unrealised_strip()

    print(f"\n{'*' * 70}")
    print("  演示完成。如需评估具体项目，请修改 main.py 中的参数。")
    print(f"{'*' * 70}\n")


COMMANDS = {
    "angel": demo_angel,
    "vc": demo_vc,
    "pe": demo_pe,
    "bse": demo_bse,
    "irr": demo_irr,
    "dpi": demo_dpi_tvpi,
    "valuation": demo_valuation_davis,
    "exit": demo_exit_timing,
    "committee": demo_exit_committee,
    "gp": demo_gp_scorecard,
    "allocation": demo_allocation,
    "philosophy": demo_philosophy,
    "montecarlo": demo_montecarlo,
    "curves": demo_curves,
    "jcurve": demo_jcurve,
    "liquidity": demo_liquidity_discount,
    "comps": demo_comps,
    "strip": demo_unrealised_strip,
    "demo": run_full_demo,
}


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print(__doc__)
        print("可用命令:")
        for cmd in COMMANDS:
            print(f"  python main.py {cmd}")
        sys.exit(1)

    COMMANDS[sys.argv[1]]()
