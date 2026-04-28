#!/usr/bin/env python3
"""
一级市场投资决策模型 — 命令行界面
Primary Market Investment Decision Model — CLI

Usage:
    python main.py angel          # Evaluate angel-stage investment
    python main.py vc             # Evaluate VC-stage investment
    python main.py pe             # Evaluate PE-stage investment
    python main.py bse            # Evaluate BSE-targeting investment
    python main.py gp             # Score a GP (LP due diligence)
    python main.py exit           # Analyze exit timing
    python main.py montecarlo     # Monte Carlo probabilistic simulations
    python main.py curves         # Mathematical curve fitting & exit signals
    python main.py jcurve         # J-curve & fund cashflow model
    python main.py liquidity      # Dynamic liquidity discount model
    python main.py comps          # Comparable company valuation anchor
    python main.py strip          # GP MOC unrealised value stripper
    python main.py hardtech       # Hard-tech P/Strategic evaluation
    python main.py postinvest     # GP post-investment capability assessment
    python main.py doubledown     # Inflection-point follow-on decision
    python main.py dealstructure  # Deal structure & defensive clause check
    python main.py duediligence   # Fundamental due diligence (DuPont + growth quality)
    python main.py lpbehavior     # LP behavioral bias corrector
    python main.py narrativedcf   # [v4.0] SpaceX三段式叙事SOTP-DCF估值
    python main.py probability    # [v4.0] 扩张期权 + 蒙特卡洛概率分布
    python main.py pricinggym     # [v4.0] 投行定价体操拆解（SpaceX案例）
    python main.py macrorisk      # [v4.0] 动态宏观风险重定价（中东战争场景）
    python main.py distress       # [v4.0] 截断/破产双轨分离估值
    python main.py restatement    # [v4.0] 财务报表外科手术（R&D资本化）
    python main.py cyclical       # [v4.0] 周期股常态化（Exxon/Toyota案例）
    python main.py stack          # [v4.0] 完整三层堆栈评估 + IC Memo输出
    python main.py demo           # Run full demo with sample data
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
    LPBehaviorChecker,
    InvestmentPhilosophyChecker,
    HardTechStrategyEvaluator,
    TECH_PATH_CORE_PLUGIN,
    TECH_PATH_SYSTEM_REBUILD,
    TECH_PATH_INCREMENTAL,
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
    GPPostInvestmentEvaluator,
    DoubleDownDecisionModel,
    AntiDilutionChecker,
    BuybackFeasibilityChecker,
    DuPontAnalyzer,
    GrowthQualityChecker,
    # v4.0 — 达莫达兰估值工具箱
    NarrativeDCFValuer,
    BusinessSegment,
    ExpansionOptionValuer,
    ValuationDistribution,
    PricingGymnasticsDetector,
    Comp,
    ImpliedERPCalculator,
    SovereignCRPAdjuster,
    MacroRiskEngine,
    DistressDualTrackValuer,
    IntangibleCapitalizer,
    CyclicalNormalizer,
    ThreeLayerValuationStack,
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


def demo_hardtech() -> None:
    print_section("硬科技战略评估 — P/Strategic 战略容错率")

    evaluator = HardTechStrategyEvaluator()

    print("\n[场景A: 国产GPU芯片（核心插件替换型 + 卡脖子）]")
    result_a = evaluator.evaluate(
        tech_path_type=TECH_PATH_CORE_PLUGIN,
        is_chokepoint_tech=True,
        has_gov_procurement=True,
        tech_readiness_level=7,         # TRL7: 系统样机在实际环境中演示
        is_domestic_substitution=True,
        is_hard_tech=True,
    )
    print(f"\n  技术路径: {result_a.tech_path_assessment}")
    print(f"  战略评分: {result_a.strategic_score}/10 | 战略估值修正系数: {result_a.strategic_valuation_multiplier}x")
    for w in result_a.warnings:
        print(f"  ⚠️  {w}")
    for r in result_a.recommendations:
        print(f"  💡 {r}")

    print("\n[场景B: 氢能基础设施（系统性基础设施重构）]")
    result_b = evaluator.evaluate(
        tech_path_type=TECH_PATH_SYSTEM_REBUILD,
        is_chokepoint_tech=False,
        has_gov_procurement=False,
        tech_readiness_level=4,         # TRL4: 实验室环境验证
        is_domestic_substitution=False,
        is_hard_tech=True,
    )
    print(f"\n  技术路径: {result_b.tech_path_assessment}")
    print(f"  战略评分: {result_b.strategic_score}/10 | 战略估值修正系数: {result_b.strategic_valuation_multiplier}x")
    for w in result_b.warnings:
        print(f"  ⚠️  {w}")

    print("\n[场景C: 哲学检验整合（升级版 — 含战略参数）]")
    checker = InvestmentPhilosophyChecker()
    result_c = checker.check(
        investment_thesis="国产先进封装技术，突破英特尔/台积电CoWoS垄断",
        has_exit_plan=True,
        has_profit_taking_triggers=True,
        sector="半导体封装",
        is_hard_tech=True,
        is_domestic_substitution=True,
        is_autonomous_controllable=True,
        is_internet_traffic_model=False,
        fund_stage="vc",
        assumed_exit_rate_pct=14.0,
        valuation_vs_intrinsic_pct=40.0,
        tech_path_type=TECH_PATH_CORE_PLUGIN,
        is_chokepoint_tech=True,
        has_gov_procurement=True,
        tech_readiness_level=6,
    )
    print(f"\n  {result_c.summary}")
    print(f"  战略估值修正系数: {result_c.strategic_valuation_multiplier}x")
    print(f"  技术路径评估: {result_c.tech_path_assessment[:60]}...")


def demo_postinvest() -> None:
    print_section("GP投后管理能力评估 — 四重境界模型")

    evaluator = GPPostInvestmentEvaluator()

    scenarios = [
        ("顶级GP（第四境界 — 退出导向）", dict(
            has_financial_monitoring=True,
            has_3r_services=True,
            has_strategic_empowerment=True,
            has_exit_oriented_management=True,
            portfolio_company_survival_rate=0.72,
            avg_time_to_next_round_months=14.0,
        )),
        ("中等GP（第二境界 — 3R服务）", dict(
            has_financial_monitoring=True,
            has_3r_services=True,
            has_strategic_empowerment=False,
            has_exit_oriented_management=False,
            portfolio_company_survival_rate=0.55,
            avg_time_to_next_round_months=22.0,
        )),
        ("初级GP（第一境界 — 查账）", dict(
            has_financial_monitoring=True,
            has_3r_services=False,
            has_strategic_empowerment=False,
            has_exit_oriented_management=False,
            portfolio_company_survival_rate=0.40,
            avg_time_to_next_round_months=30.0,
        )),
    ]

    for label, kwargs in scenarios:
        result = evaluator.evaluate(**kwargs)
        print(f"\n  [{label}]")
        print(f"  {result.summary}")
        for w in result.warnings:
            print(f"    ⚠️  {w}")
        for r in result.recommendations:
            print(f"    💡 {r}")


def demo_doubledown() -> None:
    print_section("拐点追投决策模型 — 跨越死亡谷")

    model = DoubleDownDecisionModel()

    scenarios = [
        ("固态电池企业：技术突破，强信号", dict(
            initial_investment_rmb=0.5,
            current_valuation_rmb=8.0,
            initial_valuation_rmb=2.0,
            tech_milestone_achieved=True,       # 良率突破80%
            benchmark_customer_secured=True,    # 比亚迪订单
            revenue_inflection=True,            # 营收从0到5000万
            competitive_moat_strengthened=True, # 专利壁垒建立
            follow_on_round_quality="top_tier",
            fund_remaining_capacity_rmb=5.0,
        )),
        ("AI软件企业：弱信号+估值偏高", dict(
            initial_investment_rmb=1.0,
            current_valuation_rmb=25.0,
            initial_valuation_rmb=4.0,
            tech_milestone_achieved=False,
            benchmark_customer_secured=True,
            revenue_inflection=False,
            competitive_moat_strengthened=False,
            follow_on_round_quality="mid_tier",
            fund_remaining_capacity_rmb=8.0,
        )),
        ("医疗器械：信号不足，不建议追投", dict(
            initial_investment_rmb=0.3,
            current_valuation_rmb=3.0,
            initial_valuation_rmb=1.5,
            tech_milestone_achieved=False,
            benchmark_customer_secured=False,
            revenue_inflection=False,
            competitive_moat_strengthened=False,
            follow_on_round_quality="weak",
            fund_remaining_capacity_rmb=3.0,
        )),
    ]

    for label, kwargs in scenarios:
        result = model.decide(**kwargs)
        print(f"\n  [{label}]")
        print(f"  {result.summary}")
        for w in result.warnings:
            print(f"    ⚠️  {w}")
        for r in result.recommendations:
            print(f"    💡 {r}")


def demo_dealstructure() -> None:
    print_section("交易结构与底线防守 — 老股转让与回购条款检验")

    print("\n[老股转让检验]")
    anti_checker = AntiDilutionChecker()

    print("\n  [场景A: 创始人3折套现老股（红旗）]")
    result_a = anti_checker.check(
        founder_selling_pct=25.0,           # 出售25%持股
        selling_discount_pct=70.0,          # 折扣70%（即3折成交）
        latest_round_valuation_rmb=20.0,    # 最新轮20亿估值
        has_anti_dilution_clause=True,
        anti_dilution_type="full_ratchet",
    )
    print(f"  {result_a.summary}")
    for w in result_a.warnings:
        print(f"    ⚠️  {w}")

    print("\n  [场景B: 正常老股转让（低风险）]")
    result_b = anti_checker.check(
        founder_selling_pct=5.0,
        selling_discount_pct=20.0,
        latest_round_valuation_rmb=20.0,
        has_anti_dilution_clause=True,
        anti_dilution_type="weighted_average",
    )
    print(f"  {result_b.summary}")

    print("\n[回购条款可行性检验]")
    buyback_checker = BuybackFeasibilityChecker()

    print("\n  [场景A: 高风险对赌（营收目标过高+无连带担保）]")
    result_c = buyback_checker.check(
        buyback_trigger_metric="revenue",
        buyback_trigger_value=5.0,          # 目标5亿营收
        actual_value=2.0,                   # 实际2亿
        founder_personal_assets_rmb=0.5,    # 创始人0.5亿
        has_joint_liability=False,
        company_cash_reserve_rmb=0.8,
        buyback_amount_rmb=3.0,
    )
    print(f"  {result_c.summary}")
    for w in result_c.warnings:
        print(f"    ⚠️  {w}")

    print("\n  [场景B: 可执行对赌（合理指标+连带担保）]")
    result_d = buyback_checker.check(
        buyback_trigger_metric="profit",
        buyback_trigger_value=0.8,          # 目标8000万利润
        actual_value=0.5,                   # 实际5000万
        founder_personal_assets_rmb=3.0,
        has_joint_liability=True,
        company_cash_reserve_rmb=2.0,
        buyback_amount_rmb=2.5,
    )
    print(f"  {result_d.summary}")
    for r in result_d.recommendations:
        print(f"    💡 {r}")


def demo_duediligence() -> None:
    print_section("基本面尽调 — 杜邦分析 + 增长质量检验")

    print("\n[杜邦分析]")
    dupont = DuPontAnalyzer()

    scenarios = [
        ("高利润模式：某创新医疗器械企业", dict(
            net_profit_rmb=3.0,
            revenue_rmb=15.0,
            total_assets_rmb=20.0,
            total_equity_rmb=15.0,
        )),
        ("高周转模式：某连锁零售企业", dict(
            net_profit_rmb=0.5,
            revenue_rmb=30.0,
            total_assets_rmb=10.0,
            total_equity_rmb=6.0,
        )),
        ("高杠杆风险：某商业地产项目", dict(
            net_profit_rmb=2.0,
            revenue_rmb=20.0,
            total_assets_rmb=80.0,
            total_equity_rmb=16.0,
        )),
    ]

    for label, kwargs in scenarios:
        result = dupont.analyze(**kwargs)
        print(f"\n  [{label}]")
        print(f"  {result.summary}")
        for w in result.warnings:
            print(f"    ⚠️  {w}")
        for r in result.recommendations:
            print(f"    💡 {r}")

    print("\n[增长质量检验 — 伪增长检测]")
    growth_checker = GrowthQualityChecker()

    print("\n  [场景A: 真实增长 — SaaS企业]")
    result_g = growth_checker.check(
        gmv_rmb=5.0,
        revenue_rmb=5.0,
        user_retention_rate_pct=92.0,       # 年留存92%
        nps_score=55,
        customer_acquisition_cost_rmb=0.05,
        lifetime_value_rmb=0.30,
        revenue_from_subsidies_pct=5.0,
        business_model="saas",
        net_dollar_retention_pct=118.0,     # NDR 118%
    )
    print(f"  {result_g.summary}")

    print("\n  [场景B: 伪增长 — 烧钱补贴驱动的To C平台]")
    result_h = growth_checker.check(
        gmv_rmb=50.0,
        revenue_rmb=5.0,
        user_retention_rate_pct=18.0,       # 月留存仅18%
        nps_score=-15,
        customer_acquisition_cost_rmb=0.20,
        lifetime_value_rmb=0.30,
        revenue_from_subsidies_pct=45.0,
        business_model="to_c",
    )
    print(f"  {result_h.summary}")
    for w in result_h.warnings:
        print(f"    ⚠️  {w}")


def demo_lpbehavior() -> None:
    print_section("LP行为学纠偏 — 灵魂拷问检测")

    checker = LPBehaviorChecker()

    print("\n[场景A: 理性LP — 有数据支撑的独立判断]")
    result_a = checker.check(
        attracted_by_narrative=True,
        has_concrete_evidence=True,
        following_famous_fund=True,
        has_independent_analysis=True,
        estimated_win_probability_pct=25.0,
        expected_return_multiple=8.0,
        expected_loss_multiple=0.2,
    )
    print(f"\n  {result_a.summary}")
    print(f"  期望值: {result_a.expected_value:.2f}x")
    for q in result_a.soul_questions:
        print(f"  ❓ {q}")

    print("\n[场景B: 高风险LP — 多重行为偏差]")
    result_b = checker.check(
        attracted_by_narrative=True,
        has_concrete_evidence=False,      # 未看具体数据
        following_famous_fund=True,
        has_independent_analysis=False,   # 未做独立分析
        estimated_win_probability_pct=30.0,
        expected_return_multiple=3.0,
        expected_loss_multiple=0.1,
    )
    print(f"\n  {result_b.summary}")
    for w in result_b.warnings:
        print(f"  ⚠️  {w}")
    for q in result_b.soul_questions:
        print(f"  ❓ {q}")


# ---------------------------------------------------------------------------
# v4.0 达莫达兰估值工具箱 Demo 函数
# v4.0 Damodaran Toolkit Demo Functions
# ---------------------------------------------------------------------------

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
          f"（约{result.sotp_ev_rmb/720:.1f}万亿美元，按1USD=7.2RMB）")


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


def run_full_demo() -> None:
    print(f"\n{'*' * 70}")
    print("  一级市场投资决策模型 v4.0")
    print("  基于《投的好，更要退的好（2024版）》— 李刚强")
    print("  v4.0 新增：达莫达兰'故事+数字'估值工具箱七大工具 + 三层堆栈聚合")
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
    # v3.0 modules
    demo_hardtech()
    demo_postinvest()
    demo_doubledown()
    demo_dealstructure()
    demo_duediligence()
    demo_lpbehavior()
    # v4.0 达莫达兰工具箱
    demo_narrativedcf()
    demo_probability()
    demo_pricinggym()
    demo_macrorisk()
    demo_distress()
    demo_restatement()
    demo_cyclical()
    demo_stack()

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
    "hardtech": demo_hardtech,
    "postinvest": demo_postinvest,
    "doubledown": demo_doubledown,
    "dealstructure": demo_dealstructure,
    "duediligence": demo_duediligence,
    "lpbehavior": demo_lpbehavior,
    # v4.0 — 达莫达兰估值工具箱
    "narrativedcf": demo_narrativedcf,
    "probability": demo_probability,
    "pricinggym": demo_pricinggym,
    "macrorisk": demo_macrorisk,
    "distress": demo_distress,
    "restatement": demo_restatement,
    "cyclical": demo_cyclical,
    "stack": demo_stack,
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

