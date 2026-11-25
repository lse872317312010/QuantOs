"""bStocks-specific evidence providers built on generic QuantOs snapshots."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from pathlib import Path
from typing import Any

import polars as pl

from quantos.contracts import Evidence, EvidenceDomain
from quantos.data import DataQualityState, MarketSnapshot


def _float(value: Any) -> float:
    return float(value)


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
            raise TypeError("context['snapshot'] must be a MarketSnapshot")

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


class BStocksResearchGateEvidenceProvider:
    """Expose Research 008 promotion state as strategy evidence for the active signal cell."""

    def __init__(self, promotion_gate_path: str | Path) -> None:
        self.path = Path(promotion_gate_path)

    @property
    def name(self) -> str:
        return "binance-bstocks-research-gate"

    def collect_evidence(
        self,
        *,
        instrument: str,
        as_of: datetime,
        context: dict[str, Any],
    ) -> Sequence[Evidence]:
        if not self.path.exists():
            return ()

        required_context = ("horizon_s", "market_session", "preferred_side", "threshold_bps")
        if any(key not in context for key in required_context):
            return ()

        frame = pl.read_csv(self.path)
        required_columns = {
            "horizon_s",
            "market_session",
            "preferred_side",
            "threshold_bps",
            "research_state",
        }
        if not required_columns.issubset(frame.columns):
            raise ValueError("promotion gate is missing required research columns")

        matched = frame.filter(
            (pl.col("horizon_s") == int(context["horizon_s"]))
            & (pl.col("market_session") == str(context["market_session"]))
            & (pl.col("preferred_side") == str(context["preferred_side"]))
            & (pl.col("threshold_bps") == float(context["threshold_bps"]))
        )
        if matched.is_empty():
            return ()

        row = matched.row(0, named=True)
        state = str(row["research_state"])
        positive_rate = row.get("positive_oos_fold_rate")
        confidence = {
            "RESEARCH_CANDIDATE": float(positive_rate) if positive_rate is not None else 0.8,
            "OOS_WEAK": 0.35,
            "INSUFFICIENT_OOS_HISTORY": 0.2,
            "INSUFFICIENT_WALK_FORWARD": 0.15,
            "REJECTED_TRAIN": 0.05,
        }.get(state, 0.1)
        confidence = min(1.0, max(0.0, confidence))

        side = str(context["preferred_side"])
        if state == "RESEARCH_CANDIDATE":
            directional_score = confidence if side == "LONG" else -confidence
        else:
            directional_score = 0.0

        metadata = {
            "instrument": instrument,
            "model_scope": "bstocks-cross-sectional",
            "research_state": state,
            "horizon_s": int(context["horizon_s"]),
            "market_session": str(context["market_session"]),
            "preferred_side": side,
            "threshold_bps": float(context["threshold_bps"]),
        }
        for key in (
            "selected_folds",
            "test_market_dates",
            "mean_oos_daily_net_bps",
            "median_oos_daily_net_bps",
            "positive_oos_fold_rate",
            "train_fdr_q_value",
        ):
            if key in row:
                metadata[key] = row[key]

        return (
            Evidence(
                domain=EvidenceDomain.STRATEGY,
                source=self.name,
                summary=f"research validation state {state}",
                observed_at=as_of,
                confidence=confidence,
                directional_score=directional_score,
                metadata=metadata,
            ),
        )
