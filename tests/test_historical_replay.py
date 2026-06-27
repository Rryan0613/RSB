import sqlite3

import database
import historical_replay
from historical_replay import ReplayRow, load_replay_rows


def _setup_db(tmp_path, monkeypatch):
    """Isolated test DB using the established monkeypatch pattern."""
    test_db = tmp_path / "test.db"
    monkeypatch.setattr(database, "DB_PATH", test_db)
    database.init_db()
    return test_db


def _pred(match_id, selection="home_win", probability=0.65):
    return {
        "run_id": "run_test",
        "model_version": "0.1.8.8",
        "match_id": match_id,
        "market": "home_win",
        "selection": selection,
        "model_probability": probability,
        "american_odds": -186,
        "implied_probability": 0.65,
        "edge": 0.0,
        "ev_per_unit": 0.0,
        "recommendation": "pass",
    }


def _result(match_id, home_score, away_score):
    return {"match_id": match_id, "home_score": home_score, "away_score": away_score}


def test_empty_database_returns_empty_list(tmp_path, monkeypatch):
    test_db = _setup_db(tmp_path, monkeypatch)
    assert load_replay_rows(db_path=test_db) == []


def test_home_win_prediction_matched_to_home_win_result_returns_one_row(tmp_path, monkeypatch):
    test_db = _setup_db(tmp_path, monkeypatch)
    database.save_prediction(_pred("match_001"))
    database.save_result(_result("match_001", home_score=2, away_score=1))

    rows = load_replay_rows(db_path=test_db)

    assert len(rows) == 1
    row = rows[0]
    assert isinstance(row, ReplayRow)
    assert row.match_id == "match_001"
    assert row.market == "home_win"
    assert row.selection == "home_win"
    assert row.model_probability == 0.65
    assert row.actual_label == "home_win"
    assert row.correct is True
    assert row.probability_assigned_to_actual == 0.65
    assert row.model_version == "0.1.8.8"
    assert row.run_id == "run_test"


def test_actual_label_home_win(tmp_path, monkeypatch):
    test_db = _setup_db(tmp_path, monkeypatch)
    database.save_prediction(_pred("m1"))
    database.save_result(_result("m1", home_score=3, away_score=0))

    rows = load_replay_rows(db_path=test_db)
    assert rows[0].actual_label == "home_win"


def test_actual_label_draw(tmp_path, monkeypatch):
    test_db = _setup_db(tmp_path, monkeypatch)
    database.save_prediction(_pred("m2"))
    database.save_result(_result("m2", home_score=1, away_score=1))

    rows = load_replay_rows(db_path=test_db)
    assert rows[0].actual_label == "draw"


def test_actual_label_away_win(tmp_path, monkeypatch):
    test_db = _setup_db(tmp_path, monkeypatch)
    database.save_prediction(_pred("m3"))
    database.save_result(_result("m3", home_score=0, away_score=2))

    rows = load_replay_rows(db_path=test_db)
    assert rows[0].actual_label == "away_win"


def test_correct_false_and_prob_none_when_selection_misses(tmp_path, monkeypatch):
    test_db = _setup_db(tmp_path, monkeypatch)
    # Predicted home_win, actual is draw
    database.save_prediction(_pred("m4", selection="home_win", probability=0.55))
    database.save_result(_result("m4", home_score=1, away_score=1))

    rows = load_replay_rows(db_path=test_db)
    assert rows[0].correct is False
    assert rows[0].probability_assigned_to_actual is None


def test_nonmatching_prediction_and_result_ids_not_returned(tmp_path, monkeypatch):
    test_db = _setup_db(tmp_path, monkeypatch)
    database.save_prediction(_pred("pred_match"))
    database.save_result(_result("result_match", home_score=2, away_score=0))

    assert load_replay_rows(db_path=test_db) == []


def test_loader_does_not_write_to_db(tmp_path, monkeypatch):
    test_db = _setup_db(tmp_path, monkeypatch)
    database.save_prediction(_pred("m5"))
    database.save_result(_result("m5", home_score=1, away_score=0))

    mtime_before = test_db.stat().st_mtime
    size_before = test_db.stat().st_size

    load_replay_rows(db_path=test_db)

    assert test_db.stat().st_mtime == mtime_before, "loader modified DB mtime"
    assert test_db.stat().st_size == size_before, "loader changed DB size"


def test_loader_respects_explicit_db_path(tmp_path, monkeypatch):
    db_a = tmp_path / "db_a.db"
    db_b = tmp_path / "db_b.db"

    monkeypatch.setattr(database, "DB_PATH", db_a)
    database.init_db()
    database.save_prediction(_pred("in_a"))
    database.save_result(_result("in_a", home_score=1, away_score=0))

    # db_b exists but is empty
    monkeypatch.setattr(database, "DB_PATH", db_b)
    database.init_db()

    rows_a = load_replay_rows(db_path=db_a)
    rows_b = load_replay_rows(db_path=db_b)

    assert len(rows_a) == 1 and rows_a[0].match_id == "in_a"
    assert rows_b == []


def test_loader_respects_rsb_db_path_env(tmp_path, monkeypatch):
    # Build schema directly with raw sqlite3 to avoid dependency on database.DB_PATH
    test_db = tmp_path / "env_test.db"
    con = sqlite3.connect(str(test_db))
    con.execute("""CREATE TABLE predictions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_id TEXT, model_version TEXT, match_id TEXT,
        market TEXT, selection TEXT, model_probability REAL, created_at TEXT
    )""")
    con.execute("""CREATE TABLE results (
        match_id TEXT PRIMARY KEY, home_win INTEGER, draw INTEGER, away_win INTEGER
    )""")
    con.commit()
    con.close()

    monkeypatch.setenv("RSB_DB_PATH", str(test_db))
    # No explicit db_path — loader must call get_db_path() which reads RSB_DB_PATH
    rows = load_replay_rows()
    assert rows == []


def test_nonexistent_db_returns_empty_list(tmp_path):
    missing = tmp_path / "does_not_exist.db"
    assert load_replay_rows(db_path=missing) == []


def test_loader_does_not_import_banned_modules():
    banned = {"run_slate", "simulator", "odds_collector", "update_results", "model"}
    module_names = set(vars(historical_replay).keys())
    for name in banned:
        assert name not in module_names, f"historical_replay must not import {name}"
