import pytest

from bstocks_alpha.scanner import preferred_convergence_side, rank_executable_edges, summarize
from bstocks_alpha.snapshot import BasisObservation


def observation(symbol: str, long_edge: float, short_edge: float) -> BasisObservation:
    return BasisObservation(
        observed_at_utc="2026-09-30T00:00:00+00:00",
        observed_timestamp_ms=200,
        symbol=symbol,
        base_asset=symbol.removesuffix("USDT"),
        inferred_underlying_ticker=symbol.removesuffix("BUSDT"),
        bid=100.0,
        ask=100.1,
        mid=100.05,
        spread_bps=10.0,
        reference_price=100.0,
        reference_timestamp_ms=123,
        reference_lag_ms=77,
        basis_bps=5.0,
        long_convergence_bps=long_edge,
        short_convergence_bps=short_edge,
        gross_convergence_edge_bps=max(long_edge, short_edge),
        external_calculation_id=2,
    )


def test_rank_executable_edges() -> None:
    low = observation("SPYBUSDT", 4.0, -10.0)
    high = observation("NVDABUSDT", 20.0, -30.0)
    short = observation("TSLABUSDT", -40.0, 12.0)

    result = rank_executable_edges([low, short, high], threshold_bps=10.0)

    assert [item.symbol for item in result] == ["NVDABUSDT", "TSLABUSDT"]
    assert preferred_convergence_side(short) == "SHORT"
    assert preferred_convergence_side(high) == "LONG"


def test_summary_tracks_max_gross_edge() -> None:
    items = [observation("SPYBUSDT", 3.0, -5.0), observation("NVDABUSDT", 8.0, -2.0)]
    result = summarize(items)
    assert result.count == 2
    assert result.max_gross_convergence_edge_bps == pytest.approx(8.0)
