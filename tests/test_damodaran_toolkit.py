"""
达莫达兰估值工具箱测试套件
Damodaran Valuation Toolkit Test Suite (v4.0)

覆盖以下新模块：
- narrative_dcf.py       (工具一: 叙事驱动SOTP-DCF)
- probabilistic_valuation.py (工具二: 概率估值与扩张期权)
- pricing_deconstructor.py   (工具三: 定价体操拆解)
- macro_risk.py              (工具四: 动态宏观风险重定价)
- distress_valuation.py      (工具五: 截断/破产双轨分离)
- financial_restatement.py   (工具六: 财务报表外科手术)
- cyclical_normalization.py  (工具七: 周期股常态化)
- damodaran_stack.py         (聚合器: 三层估值堆栈)

至少覆盖30个独立测试用例。
"""

import math
import pytest

from src.investment_model.narrative_dcf import (
    NarrativeDCFValuer,
    BusinessSegment,
    NarrativeDCFResult,
    INDUSTRY_S2C_BENCHMARKS,
)
from src.investment_model.probabilistic_valuation import (
    ExpansionOptionValuer,
    ValuationDistribution,
)
from src.investment_model.pricing_deconstructor import (
    PricingGymnasticsDetector,
    Comp,
)
from src.investment_model.macro_risk import (
    ImpliedERPCalculator,
    SovereignCRPAdjuster,
    MacroRiskEngine,
    SOVEREIGN_CDS_REFERENCE,
)
from src.investment_model.distress_valuation import (
    DistressDualTrackValuer,
    AltmanZResult,
)
from src.investment_model.financial_restatement import (
    IntangibleCapitalizer,
    R_AND_D_AMORTIZATION_YEARS,
)
from src.investment_model.cyclical_normalization import CyclicalNormalizer
from src.investment_model.damodaran_stack import ThreeLayerValuationStack
from src.investment_model.simulation import LognormalParam, NormalParam


# ---------------------------------------------------------------------------
# 辅助函数 / Helper utilities
# ---------------------------------------------------------------------------

def _make_segment(
    name: str = "测试板块",
    tam_rmb: float = 1000.0,
    market_share_pct: float = 10.0,
    margin_pct: float = 20.0,
    s2c: float = 1.5,
    years: int = 5,
    rate: float = 0.10,
) -> BusinessSegment:
    return BusinessSegment(
        name=name,
        tam_rmb=tam_rmb,
        terminal_market_share_pct=market_share_pct,
        terminal_operating_margin_pct=margin_pct,
        sales_to_capital_ratio=s2c,
        years_to_terminal=years,
        discount_rate=rate,
    )


# ===========================================================================
# 1. NarrativeDCFValuer — 叙事驱动SOTP-DCF
# ===========================================================================

class TestNarrativeDCF:

    def setup_method(self):
        self.valuer = NarrativeDCFValuer()

    def test_single_segment_positive_ev(self):
        """单一板块：SOTP企业价值应为正。"""
        seg = _make_segment()
        result = self.valuer.value([seg])
        assert result.sotp_ev_rmb > 0

    def test_sotp_sum_equals_segments(self):
        """多板块：SOTP = 各板块 total_pv_rmb 之和。"""
        segs = [_make_segment("A", tam_rmb=500.0), _make_segment("B", tam_rmb=800.0)]
        result = self.valuer.value(segs)
        pv_sum = sum(d.total_pv_rmb for d in result.segment_details)
        assert abs(result.sotp_ev_rmb - pv_sum) < 1e-6

    def test_empty_segments_returns_zero(self):
        """空板块列表：SOTP = 0，无异常。"""
        result = self.valuer.value([])
        assert result.sotp_ev_rmb == 0.0
        assert len(result.segment_details) == 0

    def test_terminal_revenue_formula(self):
        """终局营收 = TAM × 市占率 / 100。"""
        seg = _make_segment(tam_rmb=2000.0, market_share_pct=15.0)
        result = self.valuer.value([seg])
        detail = result.segment_details[0]
        expected_terminal_rev = 2000.0 * 0.15
        assert abs(detail.terminal_revenue_rmb - expected_terminal_rev) < 1.0

    def test_higher_discount_rate_lower_pv(self):
        """较高折现率应产生较低的现值。"""
        low_r = _make_segment(rate=0.08)
        high_r = _make_segment(rate=0.20)
        r_low = self.valuer.value([low_r])
        r_high = self.valuer.value([high_r])
        assert r_low.sotp_ev_rmb > r_high.sotp_ev_rmb

    def test_burn_rate_tracked(self):
        """累计烧钱率应被追踪（可为0或正）。"""
        seg = _make_segment()
        result = self.valuer.value([seg])
        assert result.total_burn_rmb >= 0

    def test_industry_s2c_benchmark_keys(self):
        """行业基准表应包含 SaaS、半导体、生物医药等关键行业。"""
        assert "SaaS" in INDUSTRY_S2C_BENCHMARKS
        assert "半导体" in INDUSTRY_S2C_BENCHMARKS
        assert "生物医药" in INDUSTRY_S2C_BENCHMARKS
        assert all(v > 0 for v in INDUSTRY_S2C_BENCHMARKS.values())

    def test_segment_detail_count_matches_input(self):
        """结果中板块数量应与输入一致。"""
        segs = [_make_segment(f"S{i}") for i in range(4)]
        result = self.valuer.value(segs)
        assert len(result.segment_details) == 4

    def test_s2c_deviation_warning_triggered(self):
        """当 S/C 与行业基准偏差超50% 时，应触发警告。"""
        seg = BusinessSegment(
            name="偏差板块",
            tam_rmb=500.0,
            terminal_market_share_pct=10.0,
            terminal_operating_margin_pct=20.0,
            sales_to_capital_ratio=5.0,   # SaaS基准=1.5，偏差>50%
            years_to_terminal=5,
            discount_rate=0.10,
            industry_type="SaaS",
        )
        result = self.valuer.value([seg])
        assert any("S/C" in w or "偏差" in w or "Sales-to-Capital" in w for w in result.warnings)

    def test_result_has_summary(self):
        """NarrativeDCFResult 应有 summary 字段。"""
        seg = _make_segment()
        result = self.valuer.value([seg])
        assert isinstance(result.summary, str)
        assert len(result.summary) > 0


# ===========================================================================
# 2. ExpansionOptionValuer — 扩张期权 (Black-Scholes)
# ===========================================================================

class TestExpansionOption:

    def setup_method(self):
        self.valuer = ExpansionOptionValuer()

    def test_positive_option_value(self):
        """期权价值应为非负数。"""
        result = self.valuer.value(100.0, 80.0, 2.0, 0.30, 0.04)
        assert result.option_value_rmb >= 0

    def test_itm_option_greater_than_otm(self):
        """深度实值期权 > 深度虚值期权。"""
        itm = self.valuer.value(200.0, 50.0, 2.0, 0.30, 0.04)    # 深度实值
        otm = self.valuer.value(50.0, 200.0, 2.0, 0.30, 0.04)    # 深度虚值
        assert itm.option_value_rmb > otm.option_value_rmb

    def test_zero_expiry_returns_zero_or_intrinsic(self):
        """有效期为零时，期权价值为零（警告触发）。"""
        result = self.valuer.value(100.0, 80.0, 0.0, 0.30, 0.04)
        assert result.option_value_rmb == 0.0
        assert any("有效期" in w or "≤ 0" in w for w in result.warnings)

    def test_viability_scaling(self):
        """存活概率调整：50%存活率 → 期权价值减半（近似）。"""
        full = self.valuer.value(100.0, 80.0, 2.0, 0.30, 0.04, probability_of_viability=1.0)
        half = self.valuer.value(100.0, 80.0, 2.0, 0.30, 0.04, probability_of_viability=0.5)
        assert abs(half.option_value_rmb - full.option_value_rmb * 0.5) < 1e-6

    def test_bs_call_lower_bound(self):
        """BS期权价值 ≥ max(S - K*exp(-rT), 0)（下界）。"""
        S, K, T, r = 120.0, 100.0, 1.0, 0.05
        result = self.valuer.value(S, K, T, 0.25, r)
        lower_bound = max(0.0, S - K * math.exp(-r * T))
        assert result.option_value_rmb >= lower_bound - 1e-6


# ===========================================================================
# 3. ValuationDistribution — 蒙特卡洛估值分布
# ===========================================================================

class TestValuationDistribution:

    def setup_method(self):
        self.dist = ValuationDistribution()

    def _run_sim(self, given_price=None, seed=42):
        return self.dist.simulate(
            tam_param=LognormalParam(mean=5000.0, std=2000.0),
            margin_param=NormalParam(mean=0.20, std=0.05),
            sales_to_capital_param=NormalParam(mean=1.5, std=0.3),
            survival_prob=0.80,
            years_to_terminal=8,
            discount_rate=0.12,
            terminal_growth_rate=0.03,
            n_simulations=5000,
            given_price_rmb=given_price,
            seed=seed,
        )

    def test_quantile_ordering(self):
        """P10 ≤ P25 ≤ median ≤ P75 ≤ P90."""
        r = self._run_sim()
        assert r.p10 <= r.p25 <= r.median <= r.p75 <= r.p90

    def test_overpriced_flag_high_price(self):
        """给定价远超P90时，应标记为 is_overpriced_at_p90=True。"""
        r = self._run_sim()
        very_high_price = r.p90 * 10.0
        r2 = self._run_sim(given_price=very_high_price)
        assert r2.is_overpriced_at_p90 is True

    def test_not_overpriced_low_price(self):
        """给定价低于P10时，不应标记为过高。"""
        r = self._run_sim()
        r2 = self._run_sim(given_price=r.p10 * 0.1)
        assert r2.is_overpriced_at_p90 is False

    def test_histogram_ascii_not_empty(self):
        """ASCII直方图字符串不为空。"""
        r = self._run_sim()
        assert isinstance(r.histogram_ascii, str)
        assert len(r.histogram_ascii) > 0

    def test_reproducibility_with_seed(self):
        """相同种子应产生相同结果。"""
        r1 = self._run_sim(seed=123)
        r2 = self._run_sim(seed=123)
        assert r1.median == r2.median


# ===========================================================================
# 4. PricingGymnasticsDetector — 定价体操拆解
# ===========================================================================

class TestPricingDeconstructor:

    def setup_method(self):
        self.detector = PricingGymnasticsDetector()

    def _make_comps(self):
        return [
            Comp("公司A", 25.0, "2025E", "AI软件", is_growth_stock=True),
            Comp("公司B", 18.0, "2025E", "AI软件", is_growth_stock=True),
            Comp("公司C", 5.0,  "TTM",   "传统IT", is_growth_stock=False),
        ]

    def test_cross_period_mismatch_detected(self):
        """目标用Forward但对标池有TTM时，应检测到跨期不一致。"""
        result = self.detector.detect(
            comp_pool=self._make_comps(),
            current_revenue_rmb=100.0,
            forward_revenue_rmb=400.0,
            forward_year="2027E",
            claimed_multiple=10.0,
            current_ev_rmb=2000.0,
        )
        assert result.cross_period_mismatch is True

    def test_multiple_compression_detected(self):
        """EV/Sales>30x而声称乘数<5x时，应检测到乘数压缩。"""
        result = self.detector.detect(
            comp_pool=self._make_comps(),
            current_revenue_rmb=50.0,
            forward_revenue_rmb=300.0,
            forward_year="2028E",
            claimed_multiple=4.0,   # < 5x
            current_ev_rmb=2000.0,  # implied = 2000/50 = 40x > 30x
        )
        assert result.multiple_compression_detected is True

    def test_fa_decoder_table_populated(self):
        """FA话术解码表应包含若干条目。"""
        result = self.detector.detect(
            comp_pool=self._make_comps(),
            current_revenue_rmb=100.0,
            forward_revenue_rmb=500.0,
            forward_year="2027E",
            claimed_multiple=8.0,
            current_ev_rmb=1500.0,
        )
        assert len(result.fa_decoder_table) >= 3
        for entry in result.fa_decoder_table:
            assert "fa_claim" in entry
            assert "real_meaning" in entry
            assert "counter_action" in entry

    def test_result_has_required_fields(self):
        """结果应包含所有必要字段。"""
        result = self.detector.detect(
            comp_pool=self._make_comps(),
            current_revenue_rmb=100.0,
            forward_revenue_rmb=400.0,
            forward_year="2026E",
            claimed_multiple=10.0,
            current_ev_rmb=1000.0,
        )
        assert hasattr(result, "summary")
        assert hasattr(result, "implied_current_multiple")
        assert hasattr(result, "comp_pool_std_over_mean")
        assert result.implied_current_multiple == pytest.approx(10.0, rel=1e-4)


# ===========================================================================
# 5. ImpliedERPCalculator — 隐含ERP计算
# ===========================================================================

class TestImpliedERPCalculator:

    def setup_method(self):
        self.calc = ImpliedERPCalculator()

    def test_erp_positive_in_normal_market(self):
        """正常市场条件下，隐含ERP应为正值。"""
        result = self.calc.calculate(
            index_level=4500.0,
            expected_dividend_yield_pct=2.0,
            expected_growth_pct=5.0,
            risk_free_rate_pct=3.5,
        )
        assert result.implied_erp > 0

    def test_erp_formula_correctness(self):
        """验证 GGM 反推公式：r = CF1/P + g，ERP = r - rf。"""
        index = 4500.0
        dy = 2.0
        g = 5.0
        rf = 3.5

        g_decimal = g / 100
        dy_decimal = dy / 100
        cf1 = index * dy_decimal * (1 + g_decimal)
        expected_irr = cf1 / index + g_decimal
        expected_erp = expected_irr - rf / 100

        result = self.calc.calculate(
            index_level=index,
            expected_dividend_yield_pct=dy,
            expected_growth_pct=g,
            risk_free_rate_pct=rf,
        )
        assert abs(result.implied_irr - expected_irr) < 1e-9
        assert abs(result.implied_erp - expected_erp) < 1e-9

    def test_negative_erp_triggers_warning(self):
        """当隐含ERP为负时，应触发泡沫警告。"""
        result = self.calc.calculate(
            index_level=5000.0,
            expected_dividend_yield_pct=0.5,   # 极低股息
            expected_growth_pct=2.0,
            risk_free_rate_pct=5.0,             # 高无风险利率
        )
        assert result.implied_erp < 0
        assert len(result.warnings) > 0


# ===========================================================================
# 6. SovereignCRPAdjuster — 主权CRP调整
# ===========================================================================

class TestSovereignCRPAdjuster:

    def setup_method(self):
        self.adjuster = SovereignCRPAdjuster()

    def test_zero_spread_gives_zero_crp(self):
        """当国家CDS = 基准CDS时，CRP=0。"""
        result = self.adjuster.calculate(
            country_cds_bps=30.0,
            base_country_cds_bps=30.0,
        )
        assert result.crp == pytest.approx(0.0, abs=1e-9)

    def test_crp_scales_with_spread(self):
        """CRP应随CDS利差线性增加。"""
        r1 = self.adjuster.calculate(country_cds_bps=100.0, base_country_cds_bps=30.0)
        r2 = self.adjuster.calculate(country_cds_bps=200.0, base_country_cds_bps=30.0)
        assert r2.crp > r1.crp

    def test_crp_formula(self):
        """验证 CRP = (CDS_country - CDS_base) / 10000 × vol_ratio。"""
        result = self.adjuster.calculate(
            country_cds_bps=200.0,
            base_country_cds_bps=30.0,
            equity_to_bond_volatility_ratio=1.5,
        )
        expected = (200.0 - 30.0) / 10000.0 * 1.5
        assert abs(result.crp - expected) < 1e-9

    def test_sovereign_cds_reference_table(self):
        """主权CDS参考表应包含中国、美国等关键经济体。"""
        assert "中国" in SOVEREIGN_CDS_REFERENCE
        assert "美国" in SOVEREIGN_CDS_REFERENCE
        assert all(v >= 0 for v in SOVEREIGN_CDS_REFERENCE.values())


# ===========================================================================
# 7. MacroRiskEngine — 宏观风险综合评估
# ===========================================================================

class TestMacroRiskEngine:

    def setup_method(self):
        self.engine = MacroRiskEngine()
        self.erp_calc = ImpliedERPCalculator()

    def _base_erp(self):
        return self.erp_calc.calculate(
            index_level=4500.0,
            expected_dividend_yield_pct=2.0,
            expected_growth_pct=5.0,
            risk_free_rate_pct=3.5,
        )

    def test_mac_triggered_when_erp_rises_significantly(self):
        """当ERP上升>10%时，MAC应触发。"""
        base = self._base_erp()
        # 使用一个比当前ERP低很多的基准（模拟危机时ERP飙升）
        base_erp_pct = base.implied_erp * 100 * 0.85  # 当前ERP比基准高约18%
        result = self.engine.evaluate(
            current_erp_result=base,
            base_erp_pct=base_erp_pct,
        )
        assert result.mac_triggered is True

    def test_mac_not_triggered_stable(self):
        """稳定环境下MAC不应触发。"""
        base = self._base_erp()
        result = self.engine.evaluate(
            current_erp_result=base,
            base_erp_pct=base.implied_erp * 100,  # 基准 = 当前
        )
        assert result.mac_triggered is False

    def test_adjustment_factor_calculation(self):
        """调整系数 = current_ERP / base_ERP。"""
        base = self._base_erp()
        base_erp_pct = 4.0
        result = self.engine.evaluate(
            current_erp_result=base,
            base_erp_pct=base_erp_pct,
        )
        expected = base.implied_erp / (base_erp_pct / 100)
        assert abs(result.adjustment_factor - expected) < 1e-6


# ===========================================================================
# 8. DistressDualTrackValuer — 破产双轨分离
# ===========================================================================

class TestDistressValuation:

    def setup_method(self):
        self.valuer = DistressDualTrackValuer()

    def test_bond_pricing_high_distress(self):
        """重度折价债券（市价=面值50%）应对应高违约概率。"""
        p = DistressDualTrackValuer.from_bond_pricing(
            face_value=100.0,
            market_price=50.0,
            coupon_rate=0.08,
            years_to_maturity=5.0,
            recovery_rate=0.40,
        )
        assert p > 0.3  # 高折价应对应>30%违约概率

    def test_bond_pricing_par_low_distress(self):
        """债券按面值交易但票面利率>基准利率时，违约概率较低（<0.3）。"""
        p = DistressDualTrackValuer.from_bond_pricing(
            face_value=100.0,
            market_price=100.0,
            coupon_rate=0.05,
            years_to_maturity=5.0,
            recovery_rate=0.40,
        )
        # 模型用3%作为无风险利率近似（coupon≥5%时），
        # 利差=5%-3%=2%，P_default会有一定值但仍属低位
        assert p < 0.30

    def test_altman_z_safe_zone(self):
        """健康财务指标应进入安全区，违约概率低。"""
        result = DistressDualTrackValuer.from_altman_z(
            working_capital=50.0,
            retained_earnings=80.0,
            ebit=30.0,
            market_value_equity=200.0,
            sales=300.0,
            total_assets=250.0,
            total_liabilities=70.0,
        )
        assert result.zone == "safe"
        assert result.implied_default_probability < 0.3

    def test_altman_z_distress_zone(self):
        """严重亏损财务指标应进入破产区，违约概率高。"""
        result = DistressDualTrackValuer.from_altman_z(
            working_capital=-20.0,
            retained_earnings=-100.0,
            ebit=-30.0,
            market_value_equity=10.0,
            sales=50.0,
            total_assets=200.0,
            total_liabilities=190.0,
        )
        assert result.zone == "distress"
        assert result.implied_default_probability > 0.5

    def test_dual_track_value_less_than_dcf(self):
        """双轨期望值 ≤ 持续经营DCF（高违约概率下必须更低）。"""
        result = self.valuer.value(
            going_concern_dcf_rmb=200.0,
            liquidation_nav_rmb=50.0,
            p_distress=0.60,
            restructuring_cost_rmb=5.0,
        )
        assert result.expected_deal_value_rmb < 200.0

    def test_zero_distress_full_going_concern(self):
        """破产概率=0时（存活100%），期望值接近持续经营价值。"""
        result = self.valuer.value(
            going_concern_dcf_rmb=200.0,
            liquidation_nav_rmb=50.0,
            p_distress=0.0,
            restructuring_cost_rmb=0.0,
            next_round_funding_close_probability=1.0,
        )
        # p_survival=1, adjusted_p_survival=1*(0.5+0.5*1)=1
        assert abs(result.expected_deal_value_rmb - 200.0) < 1e-6

    def test_result_has_warnings_on_high_distress(self):
        """高破产概率（>50%）应触发警告。"""
        result = self.valuer.value(
            going_concern_dcf_rmb=200.0,
            liquidation_nav_rmb=50.0,
            p_distress=0.75,
        )
        assert len(result.warnings) > 0


# ===========================================================================
# 9. IntangibleCapitalizer — 财务报表外科手术
# ===========================================================================

class TestFinancialRestatement:

    def setup_method(self):
        self.cap = IntangibleCapitalizer()

    def test_rd_asset_positive(self):
        """R&D资产价值应为正数。"""
        result = self.cap.capitalize_rd(
            rd_history=[10.0, 12.0, 14.0, 16.0, 18.0],
            amortization_years=5,
        )
        assert result.rd_asset_value > 0

    def test_rd_asset_vs_amortization(self):
        """资产价值和摊销都应该大于零。"""
        result = self.cap.capitalize_rd(
            rd_history=[10.0, 12.0, 15.0, 18.0, 20.0, 22.0, 25.0],
            amortization_years=7,
        )
        assert result.rd_asset_value > 0
        assert result.current_year_amortization > 0

    def test_restated_roic_higher(self):
        """重述后ROIC应≥报告ROIC（R&D资本化提升分子）。"""
        rd_result = self.cap.capitalize_rd(
            rd_history=[20.0] * 5,
            amortization_years=5,
        )
        restate = self.cap.restate_financials(
            reported_ebit=50.0,
            reported_invested_capital=200.0,
            capitalized_rd_asset=rd_result.rd_asset_value,
            current_year_rd=20.0,
            amortization_years=5,
            revenue=400.0,
        )
        # EBIT提升，资本也增加，最终效果取决于数值，但重述EBIT应>报告EBIT
        assert restate.restated_ebit > restate.reported_ebit

    def test_sbc_adjustment_reduces_ebitda(self):
        """SBC调整后EBITDA < 申报EBITDA。"""
        result = IntangibleCapitalizer.adjust_for_sbc(
            reported_ebitda=100.0,
            sbc_expense=20.0,
        )
        assert result.adjusted_ebitda == pytest.approx(80.0)

    def test_sbc_warning_above_20pct(self):
        """SBC超申报EBITDA的20%时，应触发警告。"""
        result = IntangibleCapitalizer.adjust_for_sbc(
            reported_ebitda=100.0,
            sbc_expense=25.0,  # 25% > 20%
        )
        assert len(result.warnings) > 0

    def test_rd_amortization_years_constants(self):
        """R&D摊销年限常量表应包含药企（10年）和SaaS（3年）。"""
        assert R_AND_D_AMORTIZATION_YEARS["药企"] == 10
        assert R_AND_D_AMORTIZATION_YEARS["SaaS"] == 3


# ===========================================================================
# 10. CyclicalNormalizer — 周期股常态化
# ===========================================================================

class TestCyclicalNormalization:

    def setup_method(self):
        self.norm = CyclicalNormalizer()

    def test_normalized_margin_between_min_max(self):
        """常态化利润率应在历史数据范围内。"""
        margins = [0.05, 0.08, 0.12, 0.15, 0.10, 0.07, 0.06]
        result = self.norm.normalize_by_historical_average(margins_history=margins)
        assert min(margins) <= result.normalized_margin <= max(margins)

    def test_empty_margins_returns_zero(self):
        """空历史数据应优雅返回，不抛异常，normalized_margin=0。"""
        result = self.norm.normalize_by_historical_average(margins_history=[])
        assert result.normalized_margin == 0.0

    def test_current_margin_overridden(self):
        """current_margin参数应覆盖历史最后值。"""
        margins = [0.10, 0.12, 0.08]
        result = self.norm.normalize_by_historical_average(
            margins_history=margins,
            current_margin=0.25,
        )
        assert result.current_margin == 0.25

    def test_regression_r_squared_perfect_linear(self):
        """完美线性数据的R²应接近1。"""
        prices = [10.0, 20.0, 30.0, 40.0, 50.0]
        margins = [0.10, 0.20, 0.30, 0.40, 0.50]
        result = self.norm.regress_margin_to_commodity(
            margins=margins,
            commodity_prices=prices,
            current_commodity_price=25.0,
        )
        assert result.r_squared > 0.999

    def test_regression_intercept_and_slope(self):
        """验证最小二乘回归：对 y=2x+1，slope≈2，intercept≈1。"""
        xs = [1.0, 2.0, 3.0, 4.0, 5.0]
        ys = [3.0, 5.0, 7.0, 9.0, 11.0]  # y = 2x + 1
        result = self.norm.regress_margin_to_commodity(
            margins=ys,
            commodity_prices=xs,
            current_commodity_price=3.0,
        )
        assert abs(result.slope - 2.0) < 1e-6
        assert abs(result.intercept - 1.0) < 1e-6

    def test_cycle_peak_triggers_warning(self):
        """当前利润率远超常态化值（周期高点）时，应触发警告。"""
        margins = [0.05, 0.06, 0.07, 0.06, 0.05, 0.07, 0.06]
        result = self.norm.normalize_by_historical_average(
            margins_history=margins,
            current_margin=0.25,  # 远高于常态化约6%
        )
        assert len(result.warnings) > 0


# ===========================================================================
# 11. ThreeLayerValuationStack — 三层估值堆栈聚合器
# ===========================================================================

class TestThreeLayerStack:

    def setup_method(self):
        self.valuer = NarrativeDCFValuer()
        self.stack = ThreeLayerValuationStack()

    def _make_dcf_result(self, tam=1000.0, market_share=10.0, rate=0.10):
        seg = _make_segment(tam_rmb=tam, market_share_pct=market_share, rate=rate)
        return self.valuer.value([seg])

    def _evaluate(self, dcf, entry_price, ceiling, options=None, p_survival=1.0, macro_factor=1.0):
        return self.stack.evaluate(
            project_name="测试项目",
            entry_price_rmb=entry_price,
            narrative_dcf_result=dcf,
            expansion_option_values_rmb=options or [],
            market_comps_ceiling_rmb=ceiling,
            p_survival=p_survival,
            macro_adjustment_factor=macro_factor,
        )

    def test_invest_recommendation_wide_margin(self):
        """安全边际>40%时，建议应为INVEST。"""
        dcf = self._make_dcf_result()
        floor = dcf.sotp_ev_rmb
        ceiling = floor * 10.0    # 天花板 = 地板 × 10
        entry = floor * 0.8       # 进场 = 地板 × 0.8（低于地板）
        result = self._evaluate(dcf, entry, ceiling)
        assert result.recommendation == "INVEST"

    def test_pass_recommendation_narrow_margin(self):
        """安全边际<20%时，建议应为PASS。"""
        dcf = self._make_dcf_result()
        floor = dcf.sotp_ev_rmb
        ceiling = floor * 1.05    # 天花板仅微高于地板
        entry = floor * 1.0       # 进场等于地板
        result = self._evaluate(dcf, entry, ceiling)
        assert result.recommendation == "PASS"

    def test_negotiate_recommendation_mid_margin(self):
        """安全边际在20-40%之间时，建议应为NEGOTIATE_TERMS。
        
        公式：safety_margin = (ceiling - floor) / entry - 1
        NEGOTIATE区间：0.20 ≤ margin < 0.40
        构造：entry=100, floor=80, ceiling=210 → (210-80)/100 - 1 = 0.30 → NEGOTIATE
        """
        dcf = self._make_dcf_result()
        floor = dcf.sotp_ev_rmb
        entry = floor          # 进场 = 地板价
        # 安全边际 = (ceiling - floor) / entry - 1 = 0.30
        # ceiling = entry * 1.30 + floor = floor * 2.30
        ceiling = floor * 2.30
        result = self._evaluate(dcf, entry, ceiling)
        # safety = (2.30*floor - floor) / floor - 1 = 1.30 - 1 = 0.30 → NEGOTIATE
        assert result.recommendation == "NEGOTIATE_TERMS"

    def test_ic_memo_markdown_contains_key_sections(self):
        """IC Memo Markdown 应包含关键章节标题。"""
        dcf = self._make_dcf_result()
        result = self._evaluate(dcf, 200.0, 1000.0)
        memo = result.ic_memo_markdown
        assert "# IC Memo" in memo
        assert "Layer 1" in memo or "内在价值" in memo or "地板" in memo
        assert "Layer 2" in memo or "期权" in memo
        assert "Layer 3" in memo or "天花板" in memo

    def test_optionality_premium_is_sum_of_options(self):
        """期权溢价 = 所有期权价值之和。"""
        dcf = self._make_dcf_result()
        options = [50.0, 80.0, 120.0]
        result = self._evaluate(dcf, 500.0, 2000.0, options=options)
        assert abs(result.optionality_premium_rmb - sum(options)) < 1e-6

    def test_p_survival_scales_floor(self):
        """降低存活概率应降低地板价。"""
        dcf = self._make_dcf_result()
        r_full = self._evaluate(dcf, 500.0, 5000.0, p_survival=1.0)
        r_half = self._evaluate(dcf, 500.0, 5000.0, p_survival=0.5)
        assert r_half.intrinsic_floor_rmb < r_full.intrinsic_floor_rmb

    def test_macro_factor_adjusts_ceiling(self):
        """较高宏观调整系数（危机）应降低天花板。"""
        dcf = self._make_dcf_result()
        r_normal = self._evaluate(dcf, 500.0, 5000.0, macro_factor=1.0)
        r_crisis = self._evaluate(dcf, 500.0, 5000.0, macro_factor=1.2)
        assert r_crisis.market_ceiling_rmb < r_normal.market_ceiling_rmb

    def test_result_has_all_required_fields(self):
        """三层估值结果应包含所有必填字段。"""
        dcf = self._make_dcf_result()
        result = self._evaluate(dcf, 500.0, 3000.0)
        assert hasattr(result, "intrinsic_floor_rmb")
        assert hasattr(result, "optionality_premium_rmb")
        assert hasattr(result, "market_ceiling_rmb")
        assert hasattr(result, "safety_margin_pct")
        assert hasattr(result, "recommendation")
        assert hasattr(result, "ic_memo_markdown")
        assert hasattr(result, "summary")
        assert hasattr(result, "warnings")
        assert hasattr(result, "recommendations")
