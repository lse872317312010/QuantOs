"""Thin access to Binance's official Spot SDK.

No custom HTTP client, signing code, retry layer, or WebSocket implementation belongs here.
"""

from __future__ import annotations

from typing import Any

from binance_common.configuration import ConfigurationRestAPI
from binance_sdk_spot.spot import Spot


def public_spot_client() -> Spot:
    """Create an unauthenticated Binance Spot REST client for public market data."""
    return Spot(config_rest_api=ConfigurationRestAPI())


def _to_builtin(payload: Any) -> Any:
    """Convert Binance SDK response models to plain Python containers."""
    if payload is None or isinstance(payload, (str, int, float, bool, dict, list)):
        return payload
    if hasattr(payload, "to_dict"):
        return payload.to_dict()
    if hasattr(payload, "model_dump"):
        return payload.model_dump(by_alias=True, exclude_none=True)
    raise TypeError(f"Unsupported Binance SDK payload type: {type(payload)!r}")


def exchange_info(
    symbol: str | None = None,
    client: Spot | None = None,
    *,
    symbol_status: str | None = None,
) -> dict[str, Any]:
    """Return Binance exchange metadata/rules."""
    spot = client or public_spot_client()
    data = spot.rest_api.exchange_info(
        symbol=symbol,
        show_permission_sets=False,
        symbol_status=symbol_status,
    ).data()
    result = _to_builtin(data)
    if not isinstance(result, dict):
        raise TypeError("exchangeInfo returned a non-object payload")
    return result


def reference_price(symbol: str, client: Spot | None = None) -> dict[str, Any]:
    """Return Binance official reference-price payload for a symbol."""
    spot = client or public_spot_client()
    result = _to_builtin(spot.rest_api.reference_price(symbol=symbol).data())
    if not isinstance(result, dict):
        raise TypeError("referencePrice returned a non-object payload")
    return result


def reference_price_calculation(symbol: str, client: Spot | None = None) -> dict[str, Any]:
    """Return Binance official explanation of reference-price calculation."""
    spot = client or public_spot_client()
    result = _to_builtin(spot.rest_api.reference_price_calculation(symbol=symbol).data())
    if not isinstance(result, dict):
        raise TypeError("referencePriceCalculation returned a non-object payload")
    return result


def book_tickers(client: Spot | None = None) -> list[dict[str, Any]]:
    """Return best bid/ask for all Spot symbols in one official SDK call."""
    spot = client or public_spot_client()
    result = _to_builtin(spot.rest_api.ticker_book_ticker().data())
    if isinstance(result, dict):
        return [result]
    if not isinstance(result, list):
        raise TypeError("bookTicker returned an unsupported payload")
    return result
