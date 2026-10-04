from datetime import UTC, datetime

from quantos.contracts import EvidenceDomain
from quantos.data import (
    DataQualityReport,
    DataQualityState,
    MarketSnapshot,
)
from quantos.evidence import (
    DataQualityEvidenceProvider,
    EvidenceEngine,
    TopOfBookLiquidityEvidenceProvider,
)


NOW = datetime(2026, 10, 4, tzinfo=UTC)


def snapshot() -> MarketSnapshot:
    return MarketSnapshot(
        instrument_id="SPYBUSDT.BINANCE",
        as_of=NOW,
        values={"book_bid": 100.0, "book_ask": 100.2},
        source_ids=("book",),
        quality=(
            DataQualityReport(
                source_id="book",
                as_of=NOW,
                state=DataQualityState.HEALTHY,
                freshness_s=0.1,
                completeness=1.0,
                last_event_at=NOW,
            ),
        ),
    )


def test_evidence_engine_collects_multiple_domains() -> None:
    batch = EvidenceEngine(
        (
            DataQualityEvidenceProvider(),
            TopOfBookLiquidityEvidenceProvider(),
        )
    ).collect(
        instrument="SPYBUSDT.BINANCE",
        as_of=NOW,
        context={"snapshot": snapshot()},
    )

    assert {item.domain for item in batch.evidence} == {
        EvidenceDomain.DATA_QUALITY,
        EvidenceDomain.LIQUIDITY,
    }
    assert batch.failures == ()


def test_evidence_engine_isolates_provider_failure() -> None:
    class BrokenProvider:
        @property
        def name(self) -> str:
            return "broken"

        def collect_evidence(self, **_: object) -> tuple[()]:
            raise RuntimeError("provider failed")

    batch = EvidenceEngine((BrokenProvider(),)).collect(
        instrument="SPYBUSDT.BINANCE",
        as_of=NOW,
        context={"snapshot": snapshot()},
    )

    assert batch.evidence == ()
    assert batch.failures[0].provider == "broken"
