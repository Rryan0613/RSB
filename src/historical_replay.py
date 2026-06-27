import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from paths import get_db_path


@dataclass
class ReplayRow:
    match_id: str
    market: str
    selection: str
    model_probability: float
    actual_label: str        # "home_win" | "draw" | "away_win"
    correct: bool
    # None when selection != actual_label: only one probability per prediction row is
    # stored. Full 3-way probability assignment requires future schema work.
    probability_assigned_to_actual: Optional[float]
    model_version: Optional[str]
    run_id: Optional[str]
    predicted_at: Optional[str]


def _derive_actual_label(home_win: int, draw: int) -> str:
    if home_win:
        return "home_win"
    if draw:
        return "draw"
    return "away_win"


def load_replay_rows(db_path=None) -> list[ReplayRow]:
    """Return stored predictions joined to actual results as in-memory replay rows.

    Read-only evaluation plumbing only. Does not solve training leakage —
    that guard (load_training_rows SQL review) is v0.1.8.9. Do not use
    these rows to retrain the model before the leakage guard is implemented.

    Opens the database in SQLite read-only URI mode. Does not call init_db(),
    create tables, or write anything.
    """
    resolved = Path(db_path) if db_path is not None else get_db_path()

    if not resolved.exists():
        return []

    uri = f"file:{resolved.resolve()}?mode=ro"
    try:
        con = sqlite3.connect(uri, uri=True)
    except sqlite3.OperationalError:
        return []

    try:
        rows = con.execute("""
            SELECT
                p.match_id,
                p.market,
                p.selection,
                p.model_probability,
                p.model_version,
                p.run_id,
                p.created_at,
                r.home_win,
                r.draw
            FROM predictions p
            JOIN results r ON r.match_id = p.match_id
            ORDER BY p.id
        """).fetchall()
    except sqlite3.OperationalError:
        # Tables do not exist yet (pre-init or unrelated DB file).
        return []
    finally:
        con.close()

    replay_rows = []
    for (match_id, market, selection, model_probability, model_version,
         run_id, predicted_at, home_win, draw) in rows:
        actual_label = _derive_actual_label(home_win, draw)
        correct = (selection == actual_label)
        prob_assigned = model_probability if correct else None
        replay_rows.append(ReplayRow(
            match_id=match_id,
            market=market,
            selection=selection,
            model_probability=model_probability,
            actual_label=actual_label,
            correct=correct,
            probability_assigned_to_actual=prob_assigned,
            model_version=model_version,
            run_id=run_id,
            predicted_at=predicted_at,
        ))

    return replay_rows
