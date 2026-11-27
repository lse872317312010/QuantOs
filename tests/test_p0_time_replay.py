"""Cross-check the P0 verification tree using fixed exchange dates and synthetic captures."""

import csv
import json
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import polars as pl
import pytest

from bstocks_alpha.data_plane import BOOK_SOURCE_ID, REFERENCE_SOURCE_ID, register_basis_csv
from bstocks_alpha.research import analyze_file, label_us_equity_sessions
from bstocks_alpha.validation import MATCHED_EXIT_MS
from quantos.data import AnalyticalCatalog, SnapshotBuilder, SnapshotSourceQuery
from quantos.learning import SessionCloseHorizon

FIXTURES = Path(__file__).parent / "fixtures"
CAPTURES = FIXTURES / "p0_synthetic_captures.csv"
START = datetime(2026, 11, 2, 15, tzinfo=UTC)
NY = ZoneInfo("America/New_York")


def test_session_labels_and_next_close_share_the_same_utc_boundaries():
    with (FIXTURES / "p0_xnys_boundaries.csv").open() as source:
        cases = list(csv.DictReader(source))
    instants = [datetime.fromisoformat(row["instant_utc"]) for row in cases]
    millisecond = timedelta(milliseconds=1)
    epoch_origin = datetime(1970, 1, 1, tzinfo=UTC)
    epochs = [(instant - epoch_origin) // millisecond for instant in instants]
    labels = label_us_equity_sessions(pl.DataFrame({"observed_timestamp_ms": epochs}))
    by_epoch = {row["observed_timestamp_ms"]: row for row in labels.to_dicts()}
    assert len(by_epoch) == len(cases)
    horizon = SessionCloseHorizon.from_calendar(
        "XNYS", 1, start=date(2026, 3, 1), end=date(2026, 12, 1)
    )
    for case, instant, epoch in zip(cases, instants, epochs, strict=True):
        row = by_epoch[epoch]
        expected_session = case["market_session"]
        assert (row["market_date"], row["market_session"]) == (
            case["market_date"],
            expected_session,
        )
        assert row["session_date"] == (
            None if expected_session == "CLOSED" else case["market_date"]
        )
        expected_close = datetime.fromisoformat(case["next_close_utc"])
        for registration in (instant, instant.astimezone(NY)):
            target = horizon.target_after(registration)
            assert target == expected_close
            assert target.tzinfo is UTC


@pytest.mark.parametrize(("max_lag_ms", "expected_matches"), [(0, 3), (100, 5), (101, 6)])
@pytest.mark.parametrize("reverse_input", [False, True], ids=["original", "reversed"])
def test_research_files_match_independent_quote_search(
    tmp_path, max_lag_ms, expected_matches, reverse_input
):
    raw = pl.read_csv(CAPTURES)
    source = CAPTURES
    if reverse_input:
        source = tmp_path / "reverse.csv"
        raw.reverse().write_csv(source)

    target = tmp_path / "research"
    analyze_file(source, target, horizons_s=(1, 2), max_match_lag_ms=max_lag_ms)
    config = json.loads((target / "analysis_config.json").read_text())
    assert config["input_observations"] == 9
    assert config["unverified_or_late_observations"] == 3
    assert config["usable_observations"] == 6

    # Explicit list of receipts eligible when each source row was sampled.
    # ALPHA@1000 and a second ALPHA@1100 arrived 1 ms late. Another ALPHA@0
    # has no receipt evidence. BETA@2000 is a legacy stream row with update ID 6.
    eligible_ids = {1, 2, 4, 5, 6, 7}
    eligible = {
        row["book_update_id"]: row
        for row in raw.to_dicts()
        if row["book_update_id"] in eligible_ids
    }
    saved = pl.read_parquet(target / "signals.parquet")
    assert sorted(saved["book_update_id"]) == sorted(eligible_ids)
    outcomes = pl.read_parquet(target / "forward_outcomes.parquet")
    assert sorted(outcomes.select("book_update_id", "horizon_s").iter_rows()) == [
        (key, horizon) for key in sorted(eligible) for horizon in (1, 2)
    ]
    matches = 0
    for result in outcomes.iter_rows(named=True):
        entry = eligible[result["book_update_id"]]
        target_ms = entry["observed_timestamp_ms"] + result["horizon_s"] * 1000
        # Exhaustive search over six rows, independent of the production as-of join.
        candidates = [
            row
            for row in eligible.values()
            if row["symbol"] == entry["symbol"]
            and target_ms <= row["observed_timestamp_ms"] <= target_ms + max_lag_ms
        ]
        if not candidates:
            assert result[MATCHED_EXIT_MS] is None
            assert result["forward_match_lag_ms"] is None
            assert result["forward_trade_return_bps"] is None
            continue
        exit_quote = min(candidates, key=lambda row: row["observed_timestamp_ms"])
        assert result[MATCHED_EXIT_MS] == exit_quote["observed_timestamp_ms"]
        assert result["forward_match_lag_ms"] == exit_quote["observed_timestamp_ms"] - target_ms
        if entry["symbol"] == "ALPHA":
            expected_return = exit_quote["bid"] / entry["ask"] - 1
        else:
            expected_return = 1 - exit_quote["ask"] / entry["bid"]
        assert result["forward_trade_return_bps"] == pytest.approx(10_000 * expected_return)
        matches += 1
    assert matches == expected_matches


def test_catalog_replays_both_sides_at_the_actual_receipt(tmp_path):
    catalog = AnalyticalCatalog(tmp_path / "catalog.duckdb")
    register_basis_csv(catalog, CAPTURES, output_dir=tmp_path / "parquet")
    builder = SnapshotBuilder(catalog)
    sources = (
        SnapshotSourceQuery(BOOK_SOURCE_ID, "ts_event", "instrument_id", ("bid",)),
        SnapshotSourceQuery(REFERENCE_SOURCE_ID, "ts_event", "instrument_id", ("reference_price",)),
    )
    cases = [
        (-1, None, None),
        (0, 99, 101),
        (999, 99, 101),
        (1000, 99, 101),
        (1001, 900, 902),
        (1099, 900, 902),
        (1100, 102, 104),
        (1101, 800, 802),
    ]
    for offset, bid, reference in cases:
        snap = builder.build(
            "ALPHA.BINANCE", as_of=START + timedelta(milliseconds=offset), sources=sources
        )
        assert (snap.values.get("bid"), snap.values.get("reference_price")) == (bid, reference), (
            offset
        )
