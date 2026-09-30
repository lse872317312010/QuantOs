from bstocks_alpha import universe


def test_candidate_symbols_filters_to_trading_usdt_b_suffix() -> None:
    payload = {
        "symbols": [
            {"symbol": "SPYBUSDT", "baseAsset": "SPYB", "quoteAsset": "USDT", "status": "TRADING"},
            {"symbol": "BTCUSDT", "baseAsset": "BTC", "quoteAsset": "USDT", "status": "TRADING"},
            {"symbol": "SPYBUSDC", "baseAsset": "SPYB", "quoteAsset": "USDC", "status": "TRADING"},
            {"symbol": "OLDBUSDT", "baseAsset": "OLDB", "quoteAsset": "USDT", "status": "BREAK"},
        ]
    }
    result = universe._candidate_symbols(payload)
    assert [item["symbol"] for item in result] == ["SPYBUSDT"]


def test_discover_bstocks_confirms_external_reference(monkeypatch) -> None:
    monkeypatch.setattr(
        universe,
        "exchange_info",
        lambda **_: {
            "symbols": [
                {
                    "symbol": "SPYBUSDT",
                    "baseAsset": "SPYB",
                    "quoteAsset": "USDT",
                    "status": "TRADING",
                },
                {
                    "symbol": "BNBUSDT",
                    "baseAsset": "BNB",
                    "quoteAsset": "USDT",
                    "status": "TRADING",
                },
            ]
        },
    )
    monkeypatch.setattr(
        universe,
        "reference_price_calculation",
        lambda symbol, client=None: {
            "symbol": symbol,
            "calculationType": "EXTERNAL",
            "externalCalculationId": 2,
        },
    )

    result = universe.discover_bstocks()
    assert [item.symbol for item in result] == ["SPYBUSDT"]
    assert result[0].inferred_underlying_ticker == "SPY"
