"""Command line scanner for Binance bStocks reference-price basis."""

from __future__ import annotations

import argparse

from .dataset import append_snapshot_csv
from .scanner import rank_anomalies, summarize
from .snapshot import collect_basis_snapshot
from .universe import discover_bstocks


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Scan Binance bStocks reference-price basis")
    parser.add_argument("--quote", default="USDT")
    parser.add_argument("--threshold-bps", type=float, default=25.0)
    parser.add_argument("--csv", default="data/basis_snapshots.csv")
    parser.add_argument("--no-write", action="store_true")
    return parser


def main() -> None:
    args = _parser().parse_args()

    instruments = discover_bstocks(quote_asset=args.quote)
    batch = collect_basis_snapshot(instruments)
    observations = list(batch.observations)
    summary = summarize(observations)

    if not args.no_write:
        append_snapshot_csv(observations, args.csv)

    print(
        f"bStocks={len(instruments)} observations={summary.count} "
        f"mean_basis={summary.mean_basis_bps:.2f}bps "
        f"max_abs={summary.max_abs_basis_bps:.2f}bps "
        f"mean_spread={summary.mean_spread_bps:.2f}bps"
    )

    anomalies = rank_anomalies(observations, threshold_bps=args.threshold_bps)
    print("symbol         basis_bps  spread_bps  mid          reference")
    for item in anomalies:
        print(
            f"{item.symbol:<14} {item.basis_bps:>9.2f}  {item.spread_bps:>10.2f}  "
            f"{item.mid:>11.4f}  {item.reference_price:>11.4f}"
        )

    if batch.failures:
        print(f"failures={len(batch.failures)}")
        for failure in batch.failures:
            print(f"  {failure.symbol}: {failure.error}")


if __name__ == "__main__":
    main()
