"""Evidence collection orchestration for QuantOs."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from quantos.contracts import Evidence
from quantos.interfaces import EvidenceProvider


@dataclass(frozen=True, slots=True)
class EvidenceFailure:
    provider: str
    error: str


@dataclass(frozen=True, slots=True)
class EvidenceBatch:
    instrument: str
    as_of: datetime
    evidence: tuple[Evidence, ...]
    failures: tuple[EvidenceFailure, ...] = ()


class EvidenceEngine:
    """Run independent evidence providers without letting one failure erase the full view."""

    def __init__(self, providers: tuple[EvidenceProvider, ...]) -> None:
        self.providers = providers

    def collect(
        self,
        *,
        instrument: str,
        as_of: datetime,
        context: dict[str, Any],
    ) -> EvidenceBatch:
        evidence: list[Evidence] = []
        failures: list[EvidenceFailure] = []

        for provider in self.providers:
            try:
                evidence.extend(
                    provider.collect_evidence(
                        instrument=instrument,
                        as_of=as_of,
                        context=context,
                    )
                )
            except Exception as exc:  # provider boundary: preserve other evidence
                failures.append(EvidenceFailure(provider=provider.name, error=str(exc)))

        evidence.sort(key=lambda item: (item.domain.value, item.source, item.summary))
        return EvidenceBatch(
            instrument=instrument,
            as_of=as_of,
            evidence=tuple(evidence),
            failures=tuple(failures),
        )
