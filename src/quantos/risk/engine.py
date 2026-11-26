"""Risk aggregation across independent analytical providers."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from quantos.contracts import Evidence, RiskAssessment
from quantos.interfaces import RiskProvider
from quantos.time import as_utc


@dataclass(frozen=True, slots=True)
class RiskFailure:
    provider: str
    error: str


@dataclass(frozen=True, slots=True)
class RiskBatch:
    instrument: str
    as_of: datetime
    assessment: RiskAssessment
    failures: tuple[RiskFailure, ...] = ()


class RiskEngine:
    """Combine risk providers conservatively; blockers and worst dimension survive."""

    def __init__(self, providers: tuple[RiskProvider, ...]) -> None:
        self.providers = providers

    def assess(
        self,
        *,
        instrument: str,
        as_of: datetime,
        evidence: Sequence[Evidence],
        context: dict[str, Any],
    ) -> RiskBatch:
        as_of = as_utc(as_of)
        for item in evidence:
            item.require_available(as_of)
        assessments: list[RiskAssessment] = []
        failures: list[RiskFailure] = []

        for provider in self.providers:
            try:
                result = provider.assess(
                    instrument=instrument, as_of=as_of, evidence=evidence, context=context,
                )
                if not isinstance(result, RiskAssessment):
                    raise TypeError("risk provider must return a RiskAssessment")
                assessments.append(result)
            except Exception as exc:  # noqa: BLE001 - isolate independent risk providers
                failures.append(RiskFailure(provider=provider.name, error=str(exc)))

        dimensions: dict[str, float] = {}
        blockers: list[str] = []
        warnings: list[str] = []
        overall_score = 0.0
        for assessment in assessments:
            overall_score = max(overall_score, assessment.overall_score)
            blockers.extend(assessment.blockers)
            warnings.extend(assessment.warnings)
            for name, value in assessment.dimensions.items():
                dimensions[name] = max(dimensions.get(name, 0.0), value)

        if not self.providers:
            blockers.append("no risk providers configured")
        blockers.extend(f"risk provider unavailable: {failure.provider}" for failure in failures)
        if failures or not self.providers:
            overall_score = 1.0

        combined = RiskAssessment(
            overall_score=overall_score,
            blockers=tuple(dict.fromkeys(blockers)),
            warnings=tuple(dict.fromkeys(warnings)),
            dimensions=dimensions,
        )
        return RiskBatch(
            instrument=instrument,
            as_of=as_of,
            assessment=combined,
            failures=tuple(failures),
        )
