#!/usr/bin/env python3
"""
一级市场投资决策模型 — 命令行界面
Primary Market Investment Decision Model — CLI

Usage:
    python main.py angel   # Evaluate angel-stage investment
    python main.py vc      # Evaluate VC-stage investment
    python main.py pe      # Evaluate PE-stage investment
    python main.py bse     # Evaluate BSE-targeting investment
    python main.py gp      # Score a GP (LP due diligence)
    python main.py exit    # Analyze exit timing
    python main.py demo    # Run full demo with sample data
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
    GPScorecard,
    AssetAllocationAdvisor,
    InvestmentPhilosophyChecker,
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


def run_full_demo() -> None:
    print(f"\n{'*' * 70}")
    print("  一级市场投资决策模型 v1.0")
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
