"""
一级市场投资决策模型
Primary Market Investment Decision Model

Based on: 《投的好，更要退的好（2024版）》by 李刚强
v4.0 新增：达莫达兰"故事+数字"估值工具箱融合（Aswath Damodaran Toolkit Integration）
"""

from .stages import AngelModel, VCModel, PEModel, BSEModel
from .metrics import (
    IRRCalculator,
    DPITVPICalculator,
    ValuationAnalyzer,
    CompsValuationAnchor,
    CompanyComp,
    UnrealisedValueStripper,
)
from .exit import ExitAnalyzer, ExitDecisionCommittee, LiquidityDiscountModel
from .lp_evaluation import GPScorecard, AssetAllocationAdvisor, LPBehaviorChecker
from .philosophy import (
    InvestmentPhilosophyChecker,
    HardTechStrategyEvaluator,
    TECH_PATH_CORE_PLUGIN,
    TECH_PATH_SYSTEM_REBUILD,
    TECH_PATH_INCREMENTAL,
)
from .simulation import (
    MonteCarloEngine,
    PortfolioSimulator,
    LognormalParam,
    NormalParam,
    PoissonParam,
)
from .curves import (
    LogisticGrowthCurve,
    GompertzCurve,
    CapitalCycleCurve,
    CapitalCyclePoint,
    ExitSignalDetector,
)
from .fund_cashflow import FundCashflowModel
from .post_investment import GPPostInvestmentEvaluator, DoubleDownDecisionModel
from .deal_structure import AntiDilutionChecker, BuybackFeasibilityChecker
from .due_diligence import DuPontAnalyzer, GrowthQualityChecker

# ---------------------------------------------------------------------------
# v4.0 达莫达兰估值工具箱 / Damodaran Valuation Toolkit (v4.0)
# ---------------------------------------------------------------------------
from .narrative_dcf import (
    NarrativeDCFValuer,
    NarrativeDCFResult,
    BusinessSegment,
    SegmentValuationDetail,
    INDUSTRY_S2C_BENCHMARKS,
)
from .probabilistic_valuation import (
    ExpansionOptionValuer,
    ExpansionOptionResult,
    ValuationDistribution,
    ValuationDistributionResult,
)
from .pricing_deconstructor import (
    PricingGymnasticsDetector,
    PricingDeconstructionResult,
    Comp,
)
from .macro_risk import (
    ImpliedERPCalculator,
    ImpliedERPResult,
    SovereignCRPAdjuster,
    SovereignCRPResult,
    MacroRiskEngine,
    MacroRiskResult,
    SOVEREIGN_CDS_REFERENCE,
)
from .distress_valuation import (
    DistressDualTrackValuer,
    DistressValuationResult,
    AltmanZResult,
)
from .financial_restatement import (
    IntangibleCapitalizer,
    RDCapitalizationResult,
    RestatedFinancialsResult,
    SBCAdjustmentResult,
    R_AND_D_AMORTIZATION_YEARS,
)
from .cyclical_normalization import (
    CyclicalNormalizer,
    NormalizationResult,
    RegressionResult,
)
from .damodaran_stack import (
    ThreeLayerValuationStack,
    ThreeLayerValuationResult,
)

__all__ = [
    # Stage models
    "AngelModel",
    "VCModel",
    "PEModel",
    "BSEModel",
    # Core metrics
    "IRRCalculator",
    "DPITVPICalculator",
    "ValuationAnalyzer",
    "CompsValuationAnchor",
    "CompanyComp",
    "UnrealisedValueStripper",
    # Exit models
    "ExitAnalyzer",
    "ExitDecisionCommittee",
    "LiquidityDiscountModel",
    # LP/GP evaluation
    "GPScorecard",
    "AssetAllocationAdvisor",
    "LPBehaviorChecker",
    # Philosophy
    "InvestmentPhilosophyChecker",
    "HardTechStrategyEvaluator",
    "TECH_PATH_CORE_PLUGIN",
    "TECH_PATH_SYSTEM_REBUILD",
    "TECH_PATH_INCREMENTAL",
    # Monte Carlo / simulation
    "MonteCarloEngine",
    "PortfolioSimulator",
    "LognormalParam",
    "NormalParam",
    "PoissonParam",
    # Mathematical curves
    "LogisticGrowthCurve",
    "GompertzCurve",
    "CapitalCycleCurve",
    "CapitalCyclePoint",
    "ExitSignalDetector",
    # Fund cash flows
    "FundCashflowModel",
    # Post-investment management
    "GPPostInvestmentEvaluator",
    "DoubleDownDecisionModel",
    # Deal structure
    "AntiDilutionChecker",
    "BuybackFeasibilityChecker",
    # Due diligence
    "DuPontAnalyzer",
    "GrowthQualityChecker",
    # v4.0 — Damodaran Toolkit: Tool 1 叙事DCF
    "NarrativeDCFValuer",
    "NarrativeDCFResult",
    "BusinessSegment",
    "SegmentValuationDetail",
    "INDUSTRY_S2C_BENCHMARKS",
    # v4.0 — Damodaran Toolkit: Tool 2 概率估值与期权
    "ExpansionOptionValuer",
    "ExpansionOptionResult",
    "ValuationDistribution",
    "ValuationDistributionResult",
    # v4.0 — Damodaran Toolkit: Tool 3 定价体操拆解
    "PricingGymnasticsDetector",
    "PricingDeconstructionResult",
    "Comp",
    # v4.0 — Damodaran Toolkit: Tool 4 动态宏观风险
    "ImpliedERPCalculator",
    "ImpliedERPResult",
    "SovereignCRPAdjuster",
    "SovereignCRPResult",
    "MacroRiskEngine",
    "MacroRiskResult",
    "SOVEREIGN_CDS_REFERENCE",
    # v4.0 — Damodaran Toolkit: Tool 5 截断/破产双轨分离
    "DistressDualTrackValuer",
    "DistressValuationResult",
    "AltmanZResult",
    # v4.0 — Damodaran Toolkit: Tool 6 财务报表外科手术
    "IntangibleCapitalizer",
    "RDCapitalizationResult",
    "RestatedFinancialsResult",
    "SBCAdjustmentResult",
    "R_AND_D_AMORTIZATION_YEARS",
    # v4.0 — Damodaran Toolkit: Tool 7 周期股常态化
    "CyclicalNormalizer",
    "NormalizationResult",
    "RegressionResult",
    # v4.0 — Damodaran Toolkit: 三层堆栈聚合器
    "ThreeLayerValuationStack",
    "ThreeLayerValuationResult",
]
