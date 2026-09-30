"""Public-data smoke test using Binance's official Python Spot SDK."""

from __future__ import annotations

import sys

from bstocks_alpha.binance_market import exchange_info, reference_price, reference_price_calculation


def main() -> None:
    symbol = sys.argv[1].upper() if len(sys.argv) > 1 else "SPYBUSDT"
    print("symbol:", symbol)
    print("exchange_info:", exchange_info(symbol))
    print("reference_price:", reference_price(symbol))
    print("reference_price_calculation:", reference_price_calculation(symbol))


if __name__ == "__main__":
    main()
