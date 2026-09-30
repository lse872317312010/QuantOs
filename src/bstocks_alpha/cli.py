"""Command line scanner for Binance bStocks reference-price basis."""

from __future__ import annotations

import argparse

from .dataset import append_snapshot_csv
from .scanner import preferred_convergence_side, rank_executable_edges, summarize
from .snapshot import collect_basis_snapshot
from .universe import discover_bstocks


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Scan Binance bStocks reference-price basis")
    parser.add_argument("--quote", default="USDT")
    parser.add_argument("--threshold-bps", type=float, default=0.0)
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
        f"max_abs_basis={summary.max_abs_basis_bps:.2f}bps "
        f"mean_spread={summary.mean_spread_bps:.2f}bps "
        f"max_gross_edge={summary.max_gross_convergence_edge_bps:.2f}bps"
    )

    opportunities = rank_executable_edges(observations, threshold_bps=args.threshold_bps)
    print("symbol         side   gross_edge  basis_bps  spread_bps  ref_lag_ms")
    for item in opportunities:
        print(
            f"{item.symbol:<14} {preferred_convergence_side(item):<5} "
            f"{item.gross_convergence_edge_bps:>10.2f} "
            f"{item.basis_bps:>10.2f} {item.spread_bps:>10.2f} "
            f"{item.reference_lag_ms:>10d}"
        )

    if batch.failures:
        print(f"failures={len(batch.failures)}")
        for failure in batch.failures:
            print(f"  {failure.symbol}: {failure.error}")


if __name__ == "__main__":
    main()
