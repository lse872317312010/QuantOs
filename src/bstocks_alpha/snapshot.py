"""Reference-basis snapshot collection."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime

from binance_common.errors import Error as BinanceError
from binance_sdk_spot.spot import Spot

from .binance_market import book_tickers, reference_price
from .features.basis import reference_basis_bps
from .universe import BStockInstrument


@dataclass(frozen=True, slots=True)
class BasisObservation:
    observed_at_utc: str
    observed_timestamp_ms: int
    symbol: str
    base_asset: str
    inferred_underlying_ticker: str
    bid: float
    ask: float
    mid: float
    spread_bps: float
    reference_price: float
    reference_timestamp_ms: int
    reference_lag_ms: int
    basis_bps: float
    long_convergence_bps: float
    short_convergence_bps: float
    gross_convergence_edge_bps: float
    external_calculation_id: int | None


@dataclass(frozen=True, slots=True)
class SnapshotFailure:
    symbol: str
    error: str


@dataclass(frozen=True, slots=True)
class BasisSnapshotBatch:
    observations: tuple[BasisObservation, ...]
    failures: tuple[SnapshotFailure, ...]


def _observation(
    instrument: BStockInstrument,
    ticker: dict,
    reference: dict,
    *,
    observed_at_utc: str,
    observed_timestamp_ms: int,
) -> BasisObservation:
    bid = float(ticker["bidPrice"])
    ask = float(ticker["askPrice"])
    ref = float(reference["referencePrice"])
    reference_timestamp_ms = int(reference["timestamp"])

    if bid <= 0 or ask <= 0 or ask < bid:
        raise ValueError(f"invalid best bid/ask for {instrument.symbol}: {bid}/{ask}")
    if ref <= 0:
        raise ValueError(f"invalid reference price for {instrument.symbol}: {ref}")

    mid = (bid + ask) / 2.0
    spread_bps = (ask - bid) / mid * 10_000.0
    long_convergence_bps = (ref / ask - 1.0) * 10_000.0
    short_convergence_bps = (bid / ref - 1.0) * 10_000.0

    return BasisObservation(
        observed_at_utc=observed_at_utc,
        observed_timestamp_ms=observed_timestamp_ms,
        symbol=instrument.symbol,
        base_asset=instrument.base_asset,
        inferred_underlying_ticker=instrument.inferred_underlying_ticker,
        bid=bid,
        ask=ask,
        mid=mid,
        spread_bps=spread_bps,
        reference_price=ref,
        reference_timestamp_ms=reference_timestamp_ms,
        reference_lag_ms=observed_timestamp_ms - reference_timestamp_ms,
        basis_bps=reference_basis_bps(mid, ref),
        long_convergence_bps=long_convergence_bps,
        short_convergence_bps=short_convergence_bps,
        gross_convergence_edge_bps=max(long_convergence_bps, short_convergence_bps),
        external_calculation_id=instrument.external_calculation_id,
    )


def collect_basis_snapshot(
    instruments: Iterable[BStockInstrument],
    client: Spot | None = None,
) -> BasisSnapshotBatch:
    """Collect one cross-sectional bStocks basis snapshot from official Binance data."""
    instrument_list = list(instruments)
    wanted = {item.symbol for item in instrument_list}
    tickers = {
        str(item["symbol"]): item
        for item in book_tickers(client=client)
        if item.get("symbol") in wanted
    }

    observed = datetime.now(UTC)
    observed_at_utc = observed.isoformat()
    observed_timestamp_ms = int(observed.timestamp() * 1000)
    observations: list[BasisObservation] = []
    failures: list[SnapshotFailure] = []

    for instrument in instrument_list:
        ticker = tickers.get(instrument.symbol)
        if ticker is None:
            failures.append(SnapshotFailure(instrument.symbol, "book ticker unavailable"))
            continue

        try:
            ref = reference_price(instrument.symbol, client=client)
            observations.append(
                _observation(
                    instrument,
                    ticker,
                    ref,
                    observed_at_utc=observed_at_utc,
                    observed_timestamp_ms=observed_timestamp_ms,
                )
            )
        except (BinanceError, KeyError, TypeError, ValueError) as exc:
            failures.append(SnapshotFailure(instrument.symbol, str(exc)))

    return BasisSnapshotBatch(tuple(observations), tuple(failures))
