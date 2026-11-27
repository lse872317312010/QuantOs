"""Source schema and payload faults must fail closed through the analyst journal."""

import json
from datetime import UTC, datetime

import duckdb
import pytest

from quantos.contracts import DecisionState, Evidence, EvidenceDomain
from quantos.data import (
    AnalyticalCatalog,
    DataQualityState,
    DataSource,
    SnapshotBuilder,
    SnapshotSourceQuery,
)
from quantos.data.catalog import SourceAvailabilityError
from quantos.decision import DecisionJournal, RuleBasedDecisionSynthesizer
from quantos.evidence import DataQualityEvidenceProvider, EvidenceEngine
from quantos.risk import DataQualityRiskProvider, RiskEngine
from quantos.workspace import AnalystReviewEngine


def _reject_constant(token: str) -> None:
    raise ValueError(f"nonstandard JSON constant: {token}")


@pytest.mark.parametrize(
    ("missing", "bad_value"),
    [
        ("bid", None),
        ("instrument_id", None),
        (None, "NULL"),
        (None, "'NaN'"),
        (None, "'Infinity'"),
        (None, "'-Infinity'"),
    ],
    ids=["missing-bid", "missing-id", "null", "nan", "positive-inf", "negative-inf"],
)
def test_source_fault_is_unavailable_without_erasing_other_sources(tmp_path, missing, bad_value):
    catalog = AnalyticalCatalog(tmp_path / "catalog.duckdb")
    cutoff = datetime(2026, 11, 25, 10, tzinfo=UTC)
    fields = {
        "ts_event": "TIMESTAMPTZ '2026-11-25 10:00:00+00' AS ts_event",
        "ts_received": "TIMESTAMPTZ '2026-11-25 10:00:00+00' AS ts_received",
        "instrument_id": "'X.BINANCE' AS instrument_id",
        "bid": "99.0 AS bid",
    }
    for source_id in ("broken", "good"):
        parquet = tmp_path / f"{source_id}.parquet"
        projection = ", ".join(
            f"CAST({bad_value} AS DOUBLE) AS bid"
            if source_id == "broken" and name == "bid" and bad_value is not None
            else expr
            for name, expr in fields.items()
            if source_id == "good" or name != missing
        )
        with duckdb.connect() as con:
            con.execute(f"COPY (SELECT {projection}) TO ? (FORMAT PARQUET)", [str(parquet)])
        catalog.register_source(
            DataSource(source_id, "fixture", "quotes", "market", expected_interval_s=1),
            parquet_path=parquet,
        )

    if missing is not None:
        with pytest.raises(SourceAvailabilityError, match=missing):
            catalog.query_as_of(
                "broken",
                as_of=cutoff,
                timestamp_column="ts_event",
                instrument_column="instrument_id",
                instrument_id="X.BINANCE",
                columns=("bid",),
            )

    snapshot = SnapshotBuilder(catalog).build(
        "X.BINANCE",
        as_of=cutoff,
        sources=(
            SnapshotSourceQuery("broken", "ts_event", "instrument_id", ("bid",), "broken_"),
            SnapshotSourceQuery("good", "ts_event", "instrument_id", ("bid",), "good_"),
        ),
    )
    assert snapshot.values == {"good_bid": 99.0}
    assert snapshot.source_ids == ("good",)
    by_source = {report.source_id: report for report in snapshot.quality}
    assert by_source["broken"].state is DataQualityState.UNAVAILABLE
    assert by_source["broken"].freshness_s is None
    assert (missing or "bid") in by_source["broken"].issues[0]
    assert by_source["good"].state is DataQualityState.HEALTHY

    class StrongSignal:
        name = "synthetic-positive-signal"

        def collect_evidence(self, *, instrument, as_of, context):
            return (
                Evidence(
                    domain=EvidenceDomain.STRATEGY,
                    source=self.name,
                    summary=f"{instrument} synthetic positive signal",
                    observed_at=as_of,
                    confidence=1.0,
                    directional_score=1.0,
                ),
            )

    journal = DecisionJournal(tmp_path / "review.jsonl")
    engine = AnalystReviewEngine(
        evidence_engine=EvidenceEngine((DataQualityEvidenceProvider(), StrongSignal())),
        risk_engine=RiskEngine((DataQualityRiskProvider(),)),
        synthesizer=RuleBasedDecisionSynthesizer(),
        journal=journal,
    )
    review = engine.review(
        instruments=("X.BINANCE",),
        as_of=cutoff,
        context_by_instrument={"X.BINANCE": {"snapshot": snapshot}},
    )
    candidate = review.snapshot.candidates[0]
    assert candidate.state is DecisionState.BLOCKED
    assert candidate.priority_score == 0
    assert "critical data source unavailable or unusable" in candidate.risk.blockers
    assert {item.source: item.confidence for item in candidate.evidence} == {
        "broken": 0.0,
        "good": 1.0,
        "synthetic-positive-signal": 1.0,
    }
    assert journal.entries()[0]["candidates"][0]["state"] == "BLOCKED"

    # Positive control: the same signal and healthy source must remain reviewable.
    healthy = SnapshotBuilder(catalog).build(
        "X.BINANCE",
        as_of=cutoff,
        sources=(SnapshotSourceQuery("good", "ts_event", "instrument_id", ("bid",)),),
    )
    control = engine.review(
        instruments=("X.BINANCE",),
        as_of=cutoff,
        context_by_instrument={"X.BINANCE": {"snapshot": healthy}},
    )
    assert control.snapshot.candidates[0].state is DecisionState.CANDIDATE
    assert not control.snapshot.candidates[0].risk.blockers
    assert journal.entries()[-1]["candidates"][0]["state"] == "CANDIDATE"

    entries = tuple(
        json.loads(line, parse_constant=_reject_constant)
        for line in journal.path.read_text(encoding="utf-8").splitlines()
    )
    assert entries == journal.entries()
    blocked_entry, control_entry = (entry["candidates"][0] for entry in entries)
    assert blocked_entry["priority_score"] == 0
    assert blocked_entry["risk"]["blockers"] == list(candidate.risk.blockers)
    assert control_entry["risk"]["blockers"] == []
