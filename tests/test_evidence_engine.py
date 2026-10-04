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
    ScalarRegimeEvidenceProvider,
    TopOfBookLiquidityEvidenceProvider,
    ZScoreAnomalyEvidenceProvider,
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


def test_anomaly_and_regime_providers_add_independent_domains() -> None:
    snap = snapshot()
    snap = MarketSnapshot(
        instrument_id=snap.instrument_id,
        as_of=snap.as_of,
        values={**snap.values, "basis_bps": 30.0},
        source_ids=snap.source_ids,
        quality=snap.quality,
    )
    batch = EvidenceEngine(
        (
            ZScoreAnomalyEvidenceProvider("basis_bps", min_abs_z=2.0),
            ScalarRegimeEvidenceProvider(
                "realized_vol_bps",
                low_threshold=10.0,
                high_threshold=30.0,
            ),
        )
    ).collect(
        instrument=snap.instrument_id,
        as_of=NOW,
        context={
            "snapshot": snap,
            "baselines": {"basis_bps": {"mean": 0.0, "std": 10.0}},
            "metrics": {"realized_vol_bps": 40.0},
        },
    )

    assert {item.domain for item in batch.evidence} == {
        EvidenceDomain.ANOMALY,
        EvidenceDomain.REGIME,
    }
    regimes = [item for item in batch.evidence if item.domain is EvidenceDomain.REGIME]
    assert regimes[0].metadata["regime"] == "HIGH"
