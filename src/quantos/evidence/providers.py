"""Generic evidence providers for data quality and liquidity."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from decimal import Decimal
from typing import Any

from quantos.contracts import Evidence, EvidenceDomain
from quantos.data import DataQualityState, MarketSnapshot


def _as_float(value: Any) -> float:
    if isinstance(value, Decimal):
        return float(value)
    return float(value)


def _snapshot(context: dict[str, Any]) -> MarketSnapshot:
    value = context.get("snapshot")
    if not isinstance(value, MarketSnapshot):
        raise ValueError("context['snapshot'] must be a MarketSnapshot")
    return value


class DataQualityEvidenceProvider:
    @property
    def name(self) -> str:
        return "data-quality"

    def collect_evidence(
        self,
        *,
        instrument: str,
        as_of: datetime,
        context: dict[str, Any],
    ) -> Sequence[Evidence]:
        snapshot = _snapshot(context)
        evidence: list[Evidence] = []

        for report in snapshot.quality:
            confidence = {
                DataQualityState.HEALTHY: 1.0,
                DataQualityState.DEGRADED: 0.7,
                DataQualityState.INCOMPLETE: 0.5,
                DataQualityState.STALE: 0.2,
                DataQualityState.UNAVAILABLE: 0.0,
            }[report.state]
            evidence.append(
                Evidence(
                    domain=EvidenceDomain.DATA_QUALITY,
                    source=report.source_id,
                    summary=f"{report.source_id} data quality is {report.state.value}",
                    observed_at=as_of,
                    confidence=confidence,
                    directional_score=0.0,
                    metadata={
                        "instrument": instrument,
                        "freshness_s": report.freshness_s,
                        "completeness": report.completeness,
                        "issues": report.issues,
                    },
                )
            )
        return evidence


class TopOfBookLiquidityEvidenceProvider:
    """Explain top-of-book spread from a generic snapshot."""

    def __init__(
        self,
        *,
        bid_field: str = "book_bid",
        ask_field: str = "book_ask",
        source: str = "top-of-book-liquidity",
    ) -> None:
        self.bid_field = bid_field
        self.ask_field = ask_field
        self._source = source

    @property
    def name(self) -> str:
        return self._source

    def collect_evidence(
        self,
        *,
        instrument: str,
        as_of: datetime,
        context: dict[str, Any],
    ) -> Sequence[Evidence]:
        snapshot = _snapshot(context)
        bid_raw = snapshot.values.get(self.bid_field)
        ask_raw = snapshot.values.get(self.ask_field)
        if bid_raw is None or ask_raw is None:
            return ()

        bid = _as_float(bid_raw)
        ask = _as_float(ask_raw)
        if bid <= 0 or ask < bid:
            raise ValueError(f"invalid top-of-book values: {bid}/{ask}")

        mid = (bid + ask) / 2.0
        spread_bps = (ask - bid) / mid * 10_000.0
        quality_confidences = [
            {
                DataQualityState.HEALTHY: 1.0,
                DataQualityState.DEGRADED: 0.7,
                DataQualityState.INCOMPLETE: 0.5,
                DataQualityState.STALE: 0.2,
                DataQualityState.UNAVAILABLE: 0.0,
            }[report.state]
            for report in snapshot.quality
        ]
        confidence = min(quality_confidences) if quality_confidences else 0.5

        return (
            Evidence(
                domain=EvidenceDomain.LIQUIDITY,
                source=self._source,
                summary=f"top-of-book spread {spread_bps:.2f} bps",
                observed_at=as_of,
                confidence=confidence,
                directional_score=0.0,
                metadata={
                    "instrument": instrument,
                    "bid": bid,
                    "ask": ask,
                    "mid": mid,
                    "spread_bps": spread_bps,
                },
            ),
        )
