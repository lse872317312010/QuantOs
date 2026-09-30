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


def reference_price(symbol: str, client: Spot | None = None) -> Any:
    """Return Binance's official reference-price payload for ``symbol``."""
    spot = client or public_spot_client()
    return spot.rest_api.reference_price(symbol=symbol).data()


def reference_price_calculation(symbol: str, client: Spot | None = None) -> Any:
    """Return Binance's official explanation of reference-price calculation."""
    spot = client or public_spot_client()
    return spot.rest_api.reference_price_calculation(symbol=symbol).data()


def exchange_info(symbol: str, client: Spot | None = None) -> Any:
    """Return Binance exchange metadata/rules for a symbol."""
    spot = client or public_spot_client()
    return spot.rest_api.exchange_info(symbol=symbol).data()
