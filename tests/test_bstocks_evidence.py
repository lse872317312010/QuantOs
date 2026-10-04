from datetime import UTC, datetime

from pathlib import Path

from bstocks_alpha.evidence import BStocksBasisEvidenceProvider, BStocksResearchGateEvidenceProvider
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


def test_bstocks_research_gate_provider_emits_strategy_evidence(tmp_path: Path) -> None:
    gate = tmp_path / "promotion_gate.csv"
    gate.write_text(
        "horizon_s,market_session,preferred_side,threshold_bps,research_state,"
        "selected_folds,test_market_dates,mean_oos_daily_net_bps,"
        "median_oos_daily_net_bps,positive_oos_fold_rate,train_fdr_q_value\n"
        "5,REGULAR,LONG,10.0,RESEARCH_CANDIDATE,4,20,3.5,3.0,0.75,0.01\n",
        encoding="utf-8",
    )

    evidence = BStocksResearchGateEvidenceProvider(gate).collect_evidence(
        instrument="SPYBUSDT.BINANCE",
        as_of=NOW,
        context={
            "horizon_s": 5,
            "market_session": "REGULAR",
            "preferred_side": "LONG",
            "threshold_bps": 10.0,
        },
    )[0]

    assert evidence.domain is EvidenceDomain.STRATEGY
    assert evidence.directional_score > 0
    assert evidence.metadata["research_state"] == "RESEARCH_CANDIDATE"
    assert evidence.metadata["selected_folds"] == 4
