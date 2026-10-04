from datetime import UTC, datetime

from quantos.contracts import Evidence, EvidenceDomain
from quantos.portfolio import PortfolioSnapshot, Position
from quantos.risk import (
    ConcentrationRiskProvider,
    DataQualityRiskProvider,
    LiquidityRiskProvider,
    RiskEngine,
)

NOW = datetime(2026, 10, 4, tzinfo=UTC)


def test_portfolio_snapshot_calculates_weight_and_gross_exposure() -> None:
    portfolio = PortfolioSnapshot(
        as_of=NOW,
        total_equity=100_000.0,
        positions=(
            Position("SPYBUSDT.BINANCE", 1.0, 25_000.0, "USDT"),
            Position("BTCUSDT.BINANCE", 1.0, -10_000.0, "USDT"),
        ),
    )
    assert portfolio.weight("SPYBUSDT.BINANCE") == 0.25
    assert portfolio.gross_exposure() == 0.35


def test_risk_engine_combines_quality_liquidity_and_concentration() -> None:
    evidence = (
        Evidence(
            domain=EvidenceDomain.DATA_QUALITY,
            source="book",
            summary="healthy",
            observed_at=NOW,
            confidence=1.0,
        ),
        Evidence(
            domain=EvidenceDomain.LIQUIDITY,
            source="book",
            summary="spread",
            observed_at=NOW,
            confidence=1.0,
            metadata={"spread_bps": 30.0},
        ),
    )
    portfolio = PortfolioSnapshot(
        as_of=NOW,
        total_equity=100_000.0,
        positions=(Position("SPYBUSDT.BINANCE", 1.0, 25_000.0, "USDT"),),
    )
    batch = RiskEngine(
        (
            DataQualityRiskProvider(),
            LiquidityRiskProvider(),
            ConcentrationRiskProvider(),
        )
    ).assess(
        instrument="SPYBUSDT.BINANCE",
        as_of=NOW,
        evidence=evidence,
        context={"portfolio": portfolio},
    )

    assert batch.assessment.blockers == ()
    assert any("elevated" in warning for warning in batch.assessment.warnings)
    assert any("concentrated" in warning for warning in batch.assessment.warnings)
    assert set(batch.assessment.dimensions) == {"data_quality", "liquidity", "concentration"}


def test_data_quality_and_liquidity_can_block_candidate() -> None:
    evidence = (
        Evidence(
            domain=EvidenceDomain.DATA_QUALITY,
            source="reference",
            summary="unavailable",
            observed_at=NOW,
            confidence=0.0,
        ),
        Evidence(
            domain=EvidenceDomain.LIQUIDITY,
            source="book",
            summary="wide spread",
            observed_at=NOW,
            confidence=1.0,
            metadata={"spread_bps": 100.0},
        ),
    )
    batch = RiskEngine((DataQualityRiskProvider(), LiquidityRiskProvider())).assess(
        instrument="SPYBUSDT.BINANCE",
        as_of=NOW,
        evidence=evidence,
        context={},
    )
    assert len(batch.assessment.blockers) == 2
    assert batch.assessment.overall_score == 1.0
