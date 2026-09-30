"""Cross-sectional basis statistics and anomaly ranking."""

from __future__ import annotations

from dataclasses import dataclass
from statistics import fmean, median

from .snapshot import BasisObservation


@dataclass(frozen=True, slots=True)
class BasisScanSummary:
    count: int
    mean_basis_bps: float
    median_basis_bps: float
    mean_abs_basis_bps: float
    max_abs_basis_bps: float
    mean_spread_bps: float


def summarize(observations: list[BasisObservation]) -> BasisScanSummary:
    if not observations:
        return BasisScanSummary(0, 0.0, 0.0, 0.0, 0.0, 0.0)

    basis = [item.basis_bps for item in observations]
    abs_basis = [abs(value) for value in basis]
    spreads = [item.spread_bps for item in observations]

    return BasisScanSummary(
        count=len(observations),
        mean_basis_bps=fmean(basis),
        median_basis_bps=median(basis),
        mean_abs_basis_bps=fmean(abs_basis),
        max_abs_basis_bps=max(abs_basis),
        mean_spread_bps=fmean(spreads),
    )


def rank_anomalies(
    observations: list[BasisObservation],
    *,
    threshold_bps: float = 25.0,
) -> list[BasisObservation]:
    """Rank observations whose absolute midpoint/reference basis crosses a threshold."""
    return sorted(
        (item for item in observations if abs(item.basis_bps) >= threshold_bps),
        key=lambda item: abs(item.basis_bps),
        reverse=True,
    )
