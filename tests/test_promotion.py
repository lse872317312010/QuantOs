import polars as pl
import pytest

from bstocks_alpha.promotion import research_promotion_gate


def threshold_row(threshold: float, stable: bool = True) -> dict[str, object]:
    return {
        "horizon_s": 5,
        "market_session": "REGULAR",
        "preferred_side": "LONG",
        "threshold_bps": threshold,
        "stable_train_candidate": stable,
        "train_market_dates": 20,
        "train_mean_daily_net_bps": 3.0,
        "train_fdr_q_value": 0.01,
    }


def walk_row(
    threshold: float,
    *,
    folds: int = 4,
    dates: int = 20,
    mean_bps: float = 2.0,
    positive_rate: float = 0.75,
) -> dict[str, object]:
    return {
        "horizon_s": 5,
        "market_session": "REGULAR",
        "preferred_side": "LONG",
        "threshold_bps": threshold,
        "selected_folds": folds,
        "test_market_dates": dates,
        "mean_oos_daily_net_bps": mean_bps,
        "median_oos_daily_net_bps": mean_bps,
        "positive_oos_fold_rate": positive_rate,
    }


def test_promotion_gate_marks_research_candidate_only_after_oos_gates() -> None:
    threshold = pl.DataFrame([threshold_row(10.0), threshold_row(25.0)])
    walk = pl.DataFrame(
        [
            walk_row(10.0),
            walk_row(25.0, folds=2, dates=8, mean_bps=5.0, positive_rate=1.0),
        ]
    )

    result = research_promotion_gate(threshold, walk).sort("threshold_bps")
    assert result["research_state"].to_list() == [
        "RESEARCH_CANDIDATE",
        "INSUFFICIENT_OOS_HISTORY",
    ]


def test_promotion_gate_never_promotes_train_rejected_candidate() -> None:
    threshold = pl.DataFrame([threshold_row(10.0, stable=False)])
    walk = pl.DataFrame([walk_row(10.0, mean_bps=100.0, positive_rate=1.0)])

    result = research_promotion_gate(threshold, walk).to_dicts()[0]
    assert result["research_state"] == "REJECTED_TRAIN"


def test_promotion_gate_marks_missing_walk_forward_history() -> None:
    threshold = pl.DataFrame([threshold_row(10.0)])
    result = research_promotion_gate(threshold, pl.DataFrame()).to_dicts()[0]
    assert result["research_state"] == "INSUFFICIENT_WALK_FORWARD"


def test_promotion_gate_validates_probability_threshold() -> None:
    threshold = pl.DataFrame([threshold_row(10.0)])
    with pytest.raises(ValueError, match="between 0 and 1"):
        research_promotion_gate(
            threshold,
            pl.DataFrame(),
            min_positive_oos_fold_rate=1.1,
        )


def test_promotion_gate_allows_empty_early_research_history() -> None:
    assert research_promotion_gate(pl.DataFrame(), pl.DataFrame()).is_empty()
