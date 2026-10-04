"""bStocks-specific evidence providers built on generic QuantOs snapshots."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from decimal import Decimal
from typing import Any

from quantos.contracts import Evidence, EvidenceDomain
from quantos.data import DataQualityState, MarketSnapshot


def _float(value: Any) -> float:
    return float(value) if isinstance(value, Decimal) else float(value)


class BStocksBasisEvidenceProvider:
    """Convert current book/reference state into directional microstructure evidence."""

    @property
    def name(self) -> str:
        return "binance-bstocks-basis"

    def collect_evidence(
        self,
        *,
        instrument: str,
        as_of: datetime,
        context: dict[str, Any],
    ) -> Sequence[Evidence]:
        snapshot = context.get("snapshot")
        if not isinstance(snapshot, MarketSnapshot):
            raise ValueError("context['snapshot'] must be a MarketSnapshot")

        required = ("book_bid", "book_ask", "reference_price")
        if any(snapshot.values.get(key) is None for key in required):
            return ()

        bid = _float(snapshot.values["book_bid"])
        ask = _float(snapshot.values["book_ask"])
        reference = _float(snapshot.values["reference_price"])
        if bid <= 0 or ask < bid or reference <= 0:
            raise ValueError("invalid bStocks book/reference values")

        mid = (bid + ask) / 2.0
        basis_bps = (mid / reference - 1.0) * 10_000.0
        long_edge_bps = (reference / ask - 1.0) * 10_000.0
        short_edge_bps = (bid / reference - 1.0) * 10_000.0

        if long_edge_bps >= short_edge_bps:
            stance = "LONG"
            edge_bps = long_edge_bps
            directional_score = min(1.0, max(0.0, edge_bps / 100.0))
        else:
            stance = "SHORT"
            edge_bps = short_edge_bps
            directional_score = -min(1.0, max(0.0, edge_bps / 100.0))

        quality_scores = [
            {
                DataQualityState.HEALTHY: 1.0,
                DataQualityState.DEGRADED: 0.7,
                DataQualityState.INCOMPLETE: 0.5,
                DataQualityState.STALE: 0.2,
                DataQualityState.UNAVAILABLE: 0.0,
            }[report.state]
            for report in snapshot.quality
        ]
        confidence = min(quality_scores) if quality_scores else 0.5

        return (
            Evidence(
                domain=EvidenceDomain.MICROSTRUCTURE,
                source=self.name,
                summary=f"{stance} convergence edge {edge_bps:.2f} bps",
                observed_at=as_of,
                confidence=confidence,
                directional_score=directional_score,
                metadata={
                    "instrument": instrument,
                    "basis_bps": basis_bps,
                    "long_edge_bps": long_edge_bps,
                    "short_edge_bps": short_edge_bps,
                    "preferred_side": stance,
                    "gross_convergence_edge_bps": edge_bps,
                },
            ),
        )
