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
from .lp_evaluation import GPScorecard, AssetAllocationAdvisor
from .philosophy import InvestmentPhilosophyChecker
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
    # Philosophy
    "InvestmentPhilosophyChecker",
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
]
