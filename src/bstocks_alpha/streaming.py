"""Continuous bStocks basis collection using Binance official WebSocket Streams."""

from __future__ import annotations

import argparse
import asyncio
import os
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from binance_sdk_spot.spot import (
    SPOT_WS_STREAMS_PROD_URL,
    ConfigurationWebSocketStreams,
    Spot,
)

from .dataset import append_snapshot_csv
from .scanner import summarize
from .snapshot import BasisObservation, _observation
from .universe import BStockInstrument, discover_bstocks

MAX_STREAMS_PER_CONNECTION = 1024
DEFAULT_SUBSCRIPTION_DELAY_SECONDS = 0.30


@dataclass(frozen=True, slots=True)
class _BookState:
    bid: float
    ask: float
    update_id: int | None
    received_timestamp_ms: int


@dataclass(frozen=True, slots=True)
class _ReferenceState:
    price: float
    valid_timestamp_ms: int
    received_timestamp_ms: int


class LiveBasisState:
    """Pair the latest official bookTicker and referencePrice events per symbol."""

    def __init__(self) -> None:
        self._books: dict[str, _BookState] = {}
        self._references: dict[str, _ReferenceState] = {}

    @staticmethod
    def _now_ms() -> int:
        return int(time.time() * 1000)

    def on_book(self, data: Any, received_timestamp_ms: int | None = None) -> None:
        symbol = getattr(data, "s", None)
        bid = getattr(data, "b", None)
        ask = getattr(data, "a", None)
        if symbol is None or bid is None or ask is None:
            return

        self._books[str(symbol).upper()] = _BookState(
            bid=float(bid),
            ask=float(ask),
            update_id=getattr(data, "u", None),
            received_timestamp_ms=received_timestamp_ms or self._now_ms(),
        )

    def on_reference(self, data: Any, received_timestamp_ms: int | None = None) -> None:
        symbol = getattr(data, "s", None)
        price = getattr(data, "r", None)
        valid_timestamp_ms = getattr(data, "t", None)
        if symbol is None or price is None or valid_timestamp_ms is None:
            return

        self._references[str(symbol).upper()] = _ReferenceState(
            price=float(price),
            valid_timestamp_ms=int(valid_timestamp_ms),
            received_timestamp_ms=received_timestamp_ms or self._now_ms(),
        )

    def observations(
        self,
        instruments: list[BStockInstrument],
        *,
        observed: datetime | None = None,
    ) -> list[BasisObservation]:
        sampled_at = observed or datetime.now(UTC)
        observed_timestamp_ms = int(sampled_at.timestamp() * 1000)
        observations: list[BasisObservation] = []

        for instrument in instruments:
            book = self._books.get(instrument.symbol)
            reference = self._references.get(instrument.symbol)
            if book is None or reference is None:
                continue

            try:
                observations.append(
                    _observation(
                        instrument,
                        {"bidPrice": book.bid, "askPrice": book.ask},
                        {
                            "referencePrice": reference.price,
                            "timestamp": reference.valid_timestamp_ms,
                        },
                        observed_at_utc=sampled_at.isoformat(),
                        observed_timestamp_ms=observed_timestamp_ms,
                        book_age_ms=max(0, observed_timestamp_ms - book.received_timestamp_ms),
                        reference_receive_age_ms=max(
                            0,
                            observed_timestamp_ms - reference.received_timestamp_ms,
                        ),
                        book_update_id=book.update_id,
                    )
                )
            except (TypeError, ValueError):
                continue

        return observations


def _select_instruments(
    instruments: list[BStockInstrument],
    symbols: set[str] | None,
) -> list[BStockInstrument]:
    if not symbols:
        return instruments
    selected = [item for item in instruments if item.symbol in symbols]
    missing = symbols - {item.symbol for item in selected}
    if missing:
        raise ValueError(f"Requested symbols are not discovered bStocks: {sorted(missing)}")
    return selected


async def collect_stream(
    *,
    csv_path: str,
    quote_asset: str = "USDT",
    symbols: set[str] | None = None,
    duration_seconds: float = 300.0,
    sample_seconds: float = 1.0,
    subscription_delay_seconds: float = DEFAULT_SUBSCRIPTION_DELAY_SECONDS,
) -> None:
    """Collect synchronized bStocks book/reference snapshots from official Binance streams."""
    if sample_seconds <= 0:
        raise ValueError("sample_seconds must be positive")
    if subscription_delay_seconds < 0.25:
        raise ValueError("subscription_delay_seconds must be >= 0.25 to respect stream controls")

    instruments = _select_instruments(
        discover_bstocks(quote_asset=quote_asset),
        {symbol.upper() for symbol in symbols} if symbols else None,
    )
    stream_count = len(instruments) * 2
    if stream_count > MAX_STREAMS_PER_CONNECTION:
        raise ValueError(
            f"{stream_count} streams exceed Binance single-connection limit "
            f"{MAX_STREAMS_PER_CONNECTION}"
        )

    ws_config = ConfigurationWebSocketStreams(
        stream_url=os.getenv("STREAM_URL", SPOT_WS_STREAMS_PROD_URL)
    )
    client = Spot(config_ws_streams=ws_config)
    connection = None
    handles: list[Any] = []
    state = LiveBasisState()

    try:
        connection = await client.websocket_streams.create_connection()

        for instrument in instruments:
            book_stream = await connection.book_ticker(symbol=instrument.symbol.lower())
            book_stream.on("message", state.on_book)
            handles.append(book_stream)
            await asyncio.sleep(subscription_delay_seconds)

            reference_stream = await connection.reference_price(symbol=instrument.symbol.lower())
            reference_stream.on("message", state.on_reference)
            handles.append(reference_stream)
            await asyncio.sleep(subscription_delay_seconds)

        print(f"subscribed instruments={len(instruments)} streams={len(handles)}")

        loop = asyncio.get_running_loop()
        deadline = None if duration_seconds <= 0 else loop.time() + duration_seconds

        while deadline is None or loop.time() < deadline:
            await asyncio.sleep(sample_seconds)
            observations = state.observations(instruments)
            append_snapshot_csv(observations, csv_path)
            summary = summarize(observations)
            print(
                f"sample={summary.count}/{len(instruments)} "
                f"mean_basis={summary.mean_basis_bps:.2f}bps "
                f"max_gross_edge={summary.max_gross_convergence_edge_bps:.2f}bps"
            )
    finally:
        if connection is not None:
            await connection.close_connection(close_session=True)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Collect Binance bStocks book/reference data via official WebSocket Streams"
    )
    parser.add_argument("--quote", default="USDT")
    parser.add_argument(
        "--symbols",
        help="Optional comma-separated subset, e.g. SPYBUSDT,NVDABUSDT",
    )
    parser.add_argument("--duration-seconds", type=float, default=300.0)
    parser.add_argument("--sample-seconds", type=float, default=1.0)
    parser.add_argument(
        "--subscription-delay-seconds",
        type=float,
        default=DEFAULT_SUBSCRIPTION_DELAY_SECONDS,
    )
    parser.add_argument("--csv", default="data/stream_basis.csv")
    return parser


def main() -> None:
    args = _parser().parse_args()
    symbols = (
        {item.strip().upper() for item in args.symbols.split(",") if item.strip()}
        if args.symbols
        else None
    )
    asyncio.run(
        collect_stream(
            csv_path=args.csv,
            quote_asset=args.quote,
            symbols=symbols,
            duration_seconds=args.duration_seconds,
            sample_seconds=args.sample_seconds,
            subscription_delay_seconds=args.subscription_delay_seconds,
        )
    )


if __name__ == "__main__":
    main()
