"""Generic risk providers derived from evidence and portfolio context."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import Any

from quantos.contracts import Evidence, EvidenceDomain, RiskAssessment
from quantos.portfolio import PortfolioSnapshot


class DataQualityRiskProvider:
    def __init__(self, *, blocker_confidence: float = 0.1) -> None:
        if not 0.0 <= blocker_confidence <= 1.0:
            raise ValueError("blocker_confidence must be between 0 and 1")
        self.blocker_confidence = blocker_confidence

    @property
    def name(self) -> str:
        return "data-quality-risk"

    def assess(
        self,
        *,
        instrument: str,
        as_of: datetime,
        evidence: Sequence[Evidence],
        context: dict[str, Any],
    ) -> RiskAssessment:
        relevant = [item for item in evidence if item.domain is EvidenceDomain.DATA_QUALITY]
        if not relevant:
            return RiskAssessment(
                overall_score=0.7,
                warnings=("no data-quality evidence",),
                dimensions={"data_quality": 0.7},
            )

        minimum_confidence = min(item.confidence for item in relevant)
        risk_score = 1.0 - minimum_confidence
        blockers: tuple[str, ...] = ()
        warnings: tuple[str, ...] = ()
        if minimum_confidence <= self.blocker_confidence:
            blockers = ("critical data source unavailable or unusable",)
        elif risk_score >= 0.5:
            warnings = ("data quality is degraded",)

        return RiskAssessment(
            overall_score=risk_score,
            blockers=blockers,
            warnings=warnings,
            dimensions={"data_quality": risk_score},
        )


class LiquidityRiskProvider:
    def __init__(
        self,
        *,
        warning_spread_bps: float = 25.0,
        blocker_spread_bps: float = 75.0,
    ) -> None:
        if warning_spread_bps <= 0 or blocker_spread_bps <= warning_spread_bps:
            raise ValueError("spread thresholds must be positive and ordered")
        self.warning_spread_bps = warning_spread_bps
        self.blocker_spread_bps = blocker_spread_bps

    @property
    def name(self) -> str:
        return "liquidity-risk"

    def assess(
        self,
        *,
        instrument: str,
        as_of: datetime,
        evidence: Sequence[Evidence],
        context: dict[str, Any],
    ) -> RiskAssessment:
        spreads = [
            float(item.metadata["spread_bps"])
            for item in evidence
            if item.domain is EvidenceDomain.LIQUIDITY and "spread_bps" in item.metadata
        ]
        if not spreads:
            return RiskAssessment(
                overall_score=0.5,
                warnings=("liquidity evidence unavailable",),
                dimensions={"liquidity": 0.5},
            )

        spread = max(spreads)
        risk_score = min(1.0, spread / self.blocker_spread_bps)
        blockers: tuple[str, ...] = ()
        warnings: tuple[str, ...] = ()
        if spread >= self.blocker_spread_bps:
            blockers = (f"spread {spread:.2f} bps exceeds liquidity blocker",)
        elif spread >= self.warning_spread_bps:
            warnings = (f"spread {spread:.2f} bps is elevated",)

        return RiskAssessment(
            overall_score=risk_score,
            blockers=blockers,
            warnings=warnings,
            dimensions={"liquidity": risk_score},
        )


class ConcentrationRiskProvider:
    def __init__(
        self,
        *,
        warning_weight: float = 0.20,
        blocker_weight: float = 0.35,
    ) -> None:
        if not 0 < warning_weight < blocker_weight <= 1:
            raise ValueError("portfolio weight thresholds must be ordered within (0, 1]")
        self.warning_weight = warning_weight
        self.blocker_weight = blocker_weight

    @property
    def name(self) -> str:
        return "concentration-risk"

    def assess(
        self,
        *,
        instrument: str,
        as_of: datetime,
        evidence: Sequence[Evidence],
        context: dict[str, Any],
    ) -> RiskAssessment:
        portfolio = context.get("portfolio")
        if portfolio is None:
            return RiskAssessment(
                overall_score=0.0,
                warnings=("portfolio context unavailable",),
                dimensions={"concentration": 0.0},
            )
        if not isinstance(portfolio, PortfolioSnapshot):
            raise TypeError("context['portfolio'] must be a PortfolioSnapshot")

        weight = abs(portfolio.weight(instrument))
        risk_score = min(1.0, weight / self.blocker_weight)
        blockers: tuple[str, ...] = ()
        warnings: tuple[str, ...] = ()
        if weight >= self.blocker_weight:
            blockers = (f"portfolio weight {weight:.1%} exceeds concentration blocker",)
        elif weight >= self.warning_weight:
            warnings = (f"portfolio weight {weight:.1%} is concentrated",)

        return RiskAssessment(
            overall_score=risk_score,
            blockers=blockers,
            warnings=warnings,
            dimensions={"concentration": risk_score},
        )
