from datetime import UTC, datetime

from bstocks_alpha.evidence import BStocksBasisEvidenceProvider
from quantos.contracts import EvidenceDomain
from quantos.data import DataQualityReport, DataQualityState, MarketSnapshot


NOW = datetime(2026, 10, 4, tzinfo=UTC)


def test_bstocks_basis_provider_emits_directional_microstructure_evidence() -> None:
    snapshot = MarketSnapshot(
        instrument_id="SPYBUSDT.BINANCE",
        as_of=NOW,
        values={
            "book_bid": 99.8,
            "book_ask": 100.0,
            "reference_price": 101.0,
        },
        source_ids=("binance.bstocks.book", "binance.bstocks.reference"),
        quality=(
            DataQualityReport(
                source_id="binance.bstocks.book",
                as_of=NOW,
                state=DataQualityState.HEALTHY,
                freshness_s=0.1,
                completeness=1.0,
            ),
            DataQualityReport(
                source_id="binance.bstocks.reference",
                as_of=NOW,
                state=DataQualityState.HEALTHY,
                freshness_s=0.2,
                completeness=1.0,
            ),
        ),
    )

    evidence = BStocksBasisEvidenceProvider().collect_evidence(
        instrument=snapshot.instrument_id,
        as_of=NOW,
        context={"snapshot": snapshot},
    )[0]

    assert evidence.domain is EvidenceDomain.MICROSTRUCTURE
    assert evidence.directional_score > 0
    assert evidence.metadata["preferred_side"] == "LONG"
    assert evidence.metadata["gross_convergence_edge_bps"] > 0
