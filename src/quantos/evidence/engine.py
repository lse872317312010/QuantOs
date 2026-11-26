"""Evidence collection orchestration for QuantOs."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from quantos.contracts import Evidence
from quantos.interfaces import EvidenceProvider
from quantos.time import as_utc


@dataclass(frozen=True, slots=True)
class EvidenceFailure:
    provider: str
    error: str
    required: bool = False


@dataclass(frozen=True, slots=True)
class EvidenceBatch:
    instrument: str
    as_of: datetime
    evidence: tuple[Evidence, ...]
    failures: tuple[EvidenceFailure, ...] = ()


class EvidenceEngine:
    """Run independent evidence providers without letting one failure erase the full view."""

    def __init__(
        self,
        providers: tuple[EvidenceProvider, ...],
        *,
        required_providers: tuple[str, ...] = (),
    ) -> None:
        self.providers = providers
        self.required_providers = frozenset(required_providers)
        unknown = self.required_providers.difference(provider.name for provider in providers)
        if unknown:
            raise ValueError(f"unknown required evidence providers: {sorted(unknown)}")

    def collect(
        self,
        *,
        instrument: str,
        as_of: datetime,
        context: dict[str, Any],
    ) -> EvidenceBatch:
        as_of = as_utc(as_of)
        evidence: list[Evidence] = []
        failures: list[EvidenceFailure] = []

        for provider in self.providers:
            try:
                items = tuple(
                    provider.collect_evidence(
                        instrument=instrument,
                        as_of=as_of,
                        context=context,
                    )
                )
                if not items and provider.name in self.required_providers:
                    raise ValueError("required evidence provider returned no evidence")
                for item in items:
                    item.require_available(as_of)
                evidence.extend(items)
            except Exception as exc:  # noqa: BLE001 - provider boundary must isolate arbitrary provider errors
                failures.append(
                    EvidenceFailure(
                        provider=provider.name,
                        error=str(exc),
                        required=provider.name in self.required_providers,
                    )
                )

        evidence.sort(key=lambda item: (item.domain.value, item.source, item.summary))
        return EvidenceBatch(
            instrument=instrument,
            as_of=as_of,
            evidence=tuple(evidence),
            failures=tuple(failures),
        )
