import polars as pl
import pytest

from bstocks_alpha.robustness import threshold_stability_report


def outcome(
    sample: str,
    market_date: str,
    edge_bps: float,
    net_bps: float,
    *,
    horizon_s: int = 5,
) -> dict[str, object]:
    return {
        "sample": sample,
        "market_date": market_date,
        "horizon_s": horizon_s,
        "market_session": "REGULAR",
        "preferred_side": "LONG",
        "gross_convergence_edge_bps": edge_bps,
        "net_forward_trade_return_bps": net_bps,
    }


def test_threshold_report_uses_train_for_selection_and_keeps_test_descriptive() -> None:
    rows = []
    for day in range(1, 7):
        date = f"2026-09-{day:02d}"
        rows.append(outcome("TRAIN", date, 30.0, 5.0 + day))
        rows.append(outcome("TEST", date, 30.0, -20.0))

    result = threshold_stability_report(
        pl.DataFrame(rows),
        thresholds_bps=(5.0, 10.0, 25.0),
        min_train_dates=5,
        fdr_alpha=0.05,
    )

    assert result.height == 3
    assert result["train_fdr_pass"].to_list() == [True, True, True]
    assert result["stable_train_candidate"].to_list() == [True, True, True]
    assert result["test_mean_daily_net_bps"].to_list() == pytest.approx([-20.0, -20.0, -20.0])


def test_threshold_report_requires_enough_independent_train_dates() -> None:
    frame = pl.DataFrame(
        [
            outcome("TRAIN", "2026-09-01", 20.0, 10.0),
            outcome("TRAIN", "2026-09-02", 20.0, 12.0),
        ]
    )
    result = threshold_stability_report(
        frame,
        thresholds_bps=(5.0, 10.0),
        min_train_dates=5,
    )

    assert result["train_fdr_q_value"].to_list() == [None, None]
    assert result["train_fdr_pass"].to_list() == [False, False]
    assert result["stable_train_candidate"].to_list() == [False, False]


def test_threshold_report_rejects_invalid_thresholds() -> None:
    frame = pl.DataFrame(
        [outcome("TRAIN", "2026-09-01", 20.0, 10.0)]
    )
    with pytest.raises(ValueError, match="positive"):
        threshold_stability_report(frame, thresholds_bps=(0.0,))
