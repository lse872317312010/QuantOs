from datetime import UTC, datetime, timedelta

import pytest

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


@pytest.mark.parametrize(
    "providers", [(), (DataQualityRiskProvider(),), (LiquidityRiskProvider(),), (ConcentrationRiskProvider(),)]
)
def test_missing_inputs_for_configured_risk_checks_block(providers) -> None:
    result = RiskEngine(providers).assess(instrument="X", as_of=NOW, evidence=(), context={})
    assert result.assessment.blockers
    assert result.assessment.overall_score == 1.0


def test_future_portfolio_cannot_clear_concentration_risk() -> None:
    later = PortfolioSnapshot(as_of=NOW + timedelta(seconds=1), total_equity=1000.0)
    result = RiskEngine((ConcentrationRiskProvider(),)).assess(
        instrument="X", as_of=NOW, evidence=(), context={"portfolio": later},
    )
    assert result.assessment.blockers
    assert "newer" in result.failures[0].error


@pytest.mark.parametrize("invalid_spread", [float("nan"), float("inf"), -float("inf"), -1.0])
@pytest.mark.parametrize("invalid_first", [True, False])
def test_invalid_liquidity_spread_blocks_even_with_healthy_evidence(
    invalid_spread: float, invalid_first: bool,
) -> None:
    def quote(source: str, spread: float) -> Evidence:
        return Evidence(
            domain=EvidenceDomain.LIQUIDITY,
            source=source,
            summary="spread",
            observed_at=NOW,
            confidence=1.0,
            metadata={"spread_bps": spread},
        )

    evidence = (quote("invalid", invalid_spread), quote("healthy", 5.0))
    if not invalid_first:
        evidence = evidence[::-1]
    result = RiskEngine((LiquidityRiskProvider(),)).assess(
        instrument="X", as_of=NOW, evidence=evidence, context={},
    )
    assert result.assessment.overall_score == 1.0
    assert result.assessment.dimensions["liquidity"] == 1.0
    assert "invalid liquidity spread" in result.assessment.blockers
    assert result.failures == ()


@pytest.mark.parametrize(
    "warning, blocker",
    [(float("nan"), 75.0), (25.0, float("nan")), (25.0, float("inf"))],
)
def test_nonfinite_liquidity_thresholds_rejected(warning: float, blocker: float) -> None:
    with pytest.raises(ValueError, match="finite"):
        LiquidityRiskProvider(warning_spread_bps=warning, blocker_spread_bps=blocker)


@pytest.mark.parametrize("spread, blocked, warned", [(0.0, False, False), (25.0, False, True), (75.0, True, False)])
def test_valid_liquidity_spread_boundaries(spread: float, blocked: bool, warned: bool) -> None:
    evidence = Evidence(
        domain=EvidenceDomain.LIQUIDITY,
        source="book",
        summary="spread",
        observed_at=NOW,
        confidence=1.0,
        metadata={"spread_bps": spread},
    )
    result = RiskEngine((LiquidityRiskProvider(),)).assess(
        instrument="X", as_of=NOW, evidence=(evidence,), context={},
    )
    assert bool(result.assessment.blockers) is blocked
    assert bool(result.assessment.warnings) is warned
    assert result.assessment.overall_score == pytest.approx(min(1.0, spread / 75.0))
    assert result.failures == ()
