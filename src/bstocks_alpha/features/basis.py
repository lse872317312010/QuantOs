"""bStocks alpha primitives."""

from __future__ import annotations


def reference_basis(token_price: float, reference_price: float) -> float:
    """Return token/reference relative basis as a decimal fraction."""
    if reference_price <= 0:
        raise ValueError("reference_price must be positive")
    return token_price / reference_price - 1.0


def reference_basis_bps(token_price: float, reference_price: float) -> float:
    """Return token/reference basis in basis points."""
    return reference_basis(token_price, reference_price) * 10_000.0
