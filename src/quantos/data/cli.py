"""Operator CLI for the local QuantOs analytical catalog."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from datetime import UTC, datetime
from typing import Any

from .catalog import AnalyticalCatalog
from .health import catalog_health


def _json_default(value: Any) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def _parse_as_of(raw: str | None) -> datetime:
    if raw is None:
        return datetime.now(UTC)
    parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise argparse.ArgumentTypeError("--as-of must include a timezone")
    return parsed


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Inspect the QuantOs analytical data catalog")
    parser.add_argument("--catalog", default="data/quantos.duckdb")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("sources", help="List registered data sources")
    subparsers.add_parser("instruments", help="List registered instruments")
    health_parser = subparsers.add_parser("health", help="Assess registered source freshness")
    health_parser.add_argument("--as-of")
    return parser


def main() -> None:
    args = _parser().parse_args()
    catalog = AnalyticalCatalog(args.catalog)

    if args.command == "sources":
        payload = [asdict(source) for source in catalog.list_sources()]
    elif args.command == "instruments":
        payload = [asdict(instrument) for instrument in catalog.list_instruments()]
    else:
        payload = [
            asdict(report)
            for report in catalog_health(catalog, as_of=_parse_as_of(args.as_of))
        ]

    print(json.dumps(payload, indent=2, default=_json_default, sort_keys=True))


if __name__ == "__main__":
    main()
