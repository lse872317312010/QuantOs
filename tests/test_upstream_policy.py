from __future__ import annotations

from pathlib import Path

FORBIDDEN_INFRA_NAMES = {
    "matching_engine.py",
    "order_manager.py",
    "websocket_client.py",
    "rest_client.py",
    "backtest_engine.py",
}


def test_no_obvious_reimplemented_infrastructure() -> None:
    root = Path(__file__).resolve().parents[1] / "src"
    present = {p.name for p in root.rglob("*.py")}
    assert not (present & FORBIDDEN_INFRA_NAMES)
