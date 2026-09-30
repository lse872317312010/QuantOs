"""Dynamic bStocks discovery using Binance official Spot metadata."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from binance_common.errors import Error as BinanceError
from binance_sdk_spot.spot import Spot

from .binance_market import exchange_info, reference_price_calculation


@dataclass(frozen=True, slots=True)
class BStockInstrument:
    symbol: str
    base_asset: str
    quote_asset: str
    status: str
    external_calculation_id: int | None

    @property
    def inferred_underlying_ticker(self) -> str:
        """Infer ticker from Binance naming convention; not authoritative metadata."""
        return self.base_asset.removesuffix("B")


def _candidate_symbols(
    payload: dict[str, Any],
    *,
    quote_asset: str = "USDT",
) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for item in payload.get("symbols", []):
        base = str(item.get("baseAsset", ""))
        if (
            item.get("status") == "TRADING"
            and item.get("quoteAsset") == quote_asset
            and base.endswith("B")
        ):
            candidates.append(item)
    return candidates


def discover_bstocks(
    client: Spot | None = None,
    *,
    quote_asset: str = "USDT",
) -> list[BStockInstrument]:
    """Discover current Binance bStocks Spot pairs without a static allowlist."""
    info = exchange_info(client=client, symbol_status="TRADING")
    instruments: list[BStockInstrument] = []

    for item in _candidate_symbols(info, quote_asset=quote_asset):
        symbol = str(item["symbol"])
        try:
            calculation = reference_price_calculation(symbol, client=client)
        except BinanceError:
            continue

        if calculation.get("calculationType") != "EXTERNAL":
            continue

        instruments.append(
            BStockInstrument(
                symbol=symbol,
                base_asset=str(item["baseAsset"]),
                quote_asset=str(item["quoteAsset"]),
                status=str(item["status"]),
                external_calculation_id=calculation.get("externalCalculationId"),
            )
        )

    return sorted(instruments, key=lambda item: item.symbol)
