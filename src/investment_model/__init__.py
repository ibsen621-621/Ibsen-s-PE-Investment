"""
一级市场投资决策模型
Primary Market Investment Decision Model

Based on: 《投的好，更要退的好（2024版）》by 李刚强
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
]
