# Research 002 — continuous book/reference collection

## Why WebSocket now

The REST scanner is useful for spot checks, but basis persistence and mean reversion require a
time series. Binance already provides official WebSocket Streams for both individual-symbol
bookTicker and referencePrice, so this project does not implement its own WebSocket protocol.

For each discovered bStock we subscribe to two official streams:

    <symbol>@bookTicker
    <symbol>@referencePrice

The collector samples the latest paired state at a configurable interval and writes the same
BasisObservation schema used by the REST scanner.

## Rate-limit design

Binance documents a maximum of 1024 streams on a single connection and a 5-message-per-second
incoming control-message limit. The collector therefore:

- rejects universes requiring more than 1024 streams;
- spaces subscription requests by 0.30 seconds by default;
- refuses a subscription delay below 0.25 seconds;
- closes the connection as a unit instead of sending a burst of unsubscribe requests.

This is intentionally thin policy around the official SDK rather than a custom socket client.

## Timing fields

Streaming observations add:

- book_age_ms: sample time minus local receipt time of the latest bookTicker;
- reference_receive_age_ms: sample time minus local receipt time of the latest referencePrice;
- book_update_id: Binance bookTicker update ID when present;
- reference_lag_ms: sample time minus Binance engine timestamp at which the reference was valid.

These fields make stale observations measurable during later research.

## Run

    bstocks-stream --symbols SPYBUSDT,NVDABUSDT --duration-seconds 600

Default output:

    data/stream_basis.csv

A duration <= 0 keeps sampling until the process is stopped or the upstream connection closes.

## Next step

Do not trade from this collector. Accumulate data first, then estimate:

1. edge survival after fees and slippage;
2. forward returns at 1s / 5s / 30s / 5m horizons;
3. behavior by US-equity market regime;
4. sensitivity to book/reference event age.
