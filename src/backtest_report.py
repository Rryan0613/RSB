"""Pure backtest report. No database, filesystem, or external dependencies."""

import math

from backtest import accuracy, brier_score_binary, log_loss_binary, mean

_NOTES = [
    "Metrics are selected-outcome binary metrics, not full three-way soccer calibration.",
    "Full home/draw/away calibration requires complete probability distributions for all outcomes.",
    "The report is retrospective evaluation plumbing and does not produce betting recommendations.",
    "Passing metrics here does not mean the model is live-betting-ready.",
]


def _is_number(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _is_evaluable(row) -> bool:
    """True iff row has non-empty market/selection/actual_label and valid model_probability."""
    market = getattr(row, "market", None)
    if not isinstance(market, str) or not market:
        return False
    selection = getattr(row, "selection", None)
    if not isinstance(selection, str) or not selection:
        return False
    actual_label = getattr(row, "actual_label", None)
    if not isinstance(actual_label, str) or not actual_label:
        return False
    p = getattr(row, "model_probability", None)
    if not _is_number(p):
        return False
    pf = float(p)
    if math.isnan(pf) or math.isinf(pf):
        return False
    if not (0.0 <= pf <= 1.0):
        return False
    return True


def _compute_stats(eval_data: list) -> dict:
    """eval_data: list of (model_probability: float, correct: bool). Returns stats dict."""
    if not eval_data:
        return {
            "evaluated_rows": 0,
            "correct_count": 0,
            "accuracy": None,
            "mean_selected_brier_score": None,
            "mean_selected_log_loss": None,
        }
    correct_count = sum(1 for _, c in eval_data if c)
    brier_scores = [brier_score_binary(p, c) for p, c in eval_data]
    log_losses = [log_loss_binary(p, c) for p, c in eval_data]
    correct_bools = [c for _, c in eval_data]
    return {
        "evaluated_rows": len(eval_data),
        "correct_count": correct_count,
        "accuracy": accuracy(correct_bools),
        "mean_selected_brier_score": mean(brier_scores),
        "mean_selected_log_loss": mean(log_losses),
    }


def build_backtest_report(rows) -> dict:
    """Accept already-loaded replay rows, return an in-memory report dict.

    Pure function: no database access, no filesystem access, no external I/O.
    Rows must already be loaded by the caller (e.g. via load_replay_rows()).

    Skipped-row accounting:
    - A row with an invalid or empty market still increments overall skipped_rows.
    - It does NOT appear in by_market because there is no valid market key to group it under.
    - by_market totals therefore do not always sum to overall skipped_rows.
    """
    rows = list(rows)
    total = len(rows)
    warnings = []

    market_total: dict = {}
    market_eval: dict = {}
    overall_eval = []
    overall_skipped = 0

    for row in rows:
        market = getattr(row, "market", None)
        if isinstance(market, str) and market:
            market_total[market] = market_total.get(market, 0) + 1

        if not _is_evaluable(row):
            overall_skipped += 1
            continue

        p = float(row.model_probability)
        c = (row.selection == row.actual_label)
        overall_eval.append((p, c))

        if market not in market_eval:
            market_eval[market] = []
        market_eval[market].append((p, c))

    if overall_skipped > 0:
        warnings.append(
            f"{overall_skipped} row(s) skipped: missing or invalid market, "
            "selection, actual_label, or model_probability."
        )

    overall_stats = _compute_stats(overall_eval)
    overall = {
        "total_rows": total,
        "evaluated_rows": overall_stats["evaluated_rows"],
        "skipped_rows": overall_skipped,
        "correct_count": overall_stats["correct_count"],
        "accuracy": overall_stats["accuracy"],
        "mean_selected_brier_score": overall_stats["mean_selected_brier_score"],
        "mean_selected_log_loss": overall_stats["mean_selected_log_loss"],
    }

    by_market = {}
    for market, eval_data in market_eval.items():
        m_total = market_total.get(market, 0)
        m_stats = _compute_stats(eval_data)
        by_market[market] = {
            "market": market,
            "total_rows": m_total,
            "evaluated_rows": m_stats["evaluated_rows"],
            "skipped_rows": m_total - m_stats["evaluated_rows"],
            "correct_count": m_stats["correct_count"],
            "accuracy": m_stats["accuracy"],
            "mean_selected_brier_score": m_stats["mean_selected_brier_score"],
            "mean_selected_log_loss": m_stats["mean_selected_log_loss"],
        }
    # Markets with valid names but zero evaluable rows still appear in by_market.
    for market, m_total in market_total.items():
        if market not in by_market:
            by_market[market] = {
                "market": market,
                "total_rows": m_total,
                "evaluated_rows": 0,
                "skipped_rows": m_total,
                "correct_count": 0,
                "accuracy": None,
                "mean_selected_brier_score": None,
                "mean_selected_log_loss": None,
            }

    return {
        "total_rows": total,
        "evaluated_rows": len(overall_eval),
        "skipped_rows": overall_skipped,
        "overall": overall,
        "by_market": by_market,
        "warnings": warnings,
        "notes": list(_NOTES),
    }
