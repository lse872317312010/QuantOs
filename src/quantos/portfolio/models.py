"""Portfolio context contracts for human-in-the-loop analysis."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class Position:
    instrument_id: str
    quantity: float
    market_value: float
    currency: str

    def __post_init__(self) -> None:
        if not self.instrument_id:
            raise ValueError("instrument_id is required")


@dataclass(frozen=True, slots=True)
class PortfolioSnapshot:
    """Point-in-time portfolio state used for analytical context, not order routing."""

    as_of: datetime
    total_equity: float
    positions: tuple[Position, ...] = ()

    def __post_init__(self) -> None:
        if self.as_of.tzinfo is None:
            raise ValueError("as_of must be timezone-aware")
        if self.total_equity <= 0:
            raise ValueError("total_equity must be positive")

    def market_value(self, instrument_id: str) -> float:
        return sum(
            position.market_value
            for position in self.positions
            if position.instrument_id == instrument_id
        )

    def weight(self, instrument_id: str) -> float:
        return self.market_value(instrument_id) / self.total_equity

    def gross_exposure(self) -> float:
        return sum(abs(position.market_value) for position in self.positions) / self.total_equity
