"""
Tests for database.load_training_rows() training-data leakage guard (v0.1.8.9).

All tests use isolated temporary SQLite databases via monkeypatch/tmp_path.
Real data/worldcup_ai.db is never touched.
"""

import json
import sqlite3

import database


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _setup_db(tmp_path, monkeypatch):
    """Isolated test DB using the established monkeypatch pattern."""
    test_db = tmp_path / "test.db"
    monkeypatch.setattr(database, "DB_PATH", test_db)
    database.init_db()
    return test_db


def _insert_snapshot(test_db, match_id, features, created_at="2025-01-01T10:00:00+00:00"):
    """Insert a feature snapshot directly, allowing control of created_at."""
    con = sqlite3.connect(str(test_db))
    con.execute(
        "INSERT INTO feature_snapshots "
        "(run_id, match_id, model_version, features_json, created_at) "
        "VALUES (?, ?, ?, ?, ?)",
        ("run_test", match_id, "0.1.8.9", json.dumps(features), created_at),
    )
    con.commit()
    con.close()


def _insert_snapshot_raw(test_db, match_id, features_json_str, created_at="2025-01-01T10:00:00+00:00"):
    """Insert a feature snapshot with a raw features_json string (for edge-case tests)."""
    con = sqlite3.connect(str(test_db))
    con.execute(
        "INSERT INTO feature_snapshots "
        "(run_id, match_id, model_version, features_json, created_at) "
        "VALUES (?, ?, ?, ?, ?)",
        ("run_test", match_id, "0.1.8.9", features_json_str, created_at),
    )
    con.commit()
    con.close()


def _insert_result(test_db, match_id, home_score, away_score, updated_at="2025-01-01T22:00:00+00:00"):
    """Insert a result row directly, allowing control of updated_at."""
    home_win = int(home_score > away_score)
    draw = int(home_score == away_score)
    away_win = int(home_score < away_score)
    btts = int(home_score > 0 and away_score > 0)
    over_25 = int(home_score + away_score > 2.5)
    con = sqlite3.connect(str(test_db))
    con.execute(
        "INSERT OR REPLACE INTO results "
        "(match_id, home_score, away_score, home_win, draw, away_win, "
        "btts, over_25, result_json, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            match_id, home_score, away_score, home_win, draw, away_win,
            btts, over_25, json.dumps({}), updated_at,
        ),
    )
    con.commit()
    con.close()


_SAMPLE_FEATURES = {"home_elo": 1800.0, "away_elo": 1700.0, "neutral_site": 0}


# ---------------------------------------------------------------------------
# Core join behaviour
# ---------------------------------------------------------------------------

def test_empty_db_returns_empty_list(tmp_path, monkeypatch):
    _setup_db(tmp_path, monkeypatch)
    assert database.load_training_rows("home_win") == []


def test_returns_row_when_both_snapshot_and_result_exist(tmp_path, monkeypatch):
    test_db = _setup_db(tmp_path, monkeypatch)
    _insert_snapshot(test_db, "m1", _SAMPLE_FEATURES)
    _insert_result(test_db, "m1", home_score=2, away_score=1)

    rows = database.load_training_rows("home_win")

    assert len(rows) == 1
    assert rows[0]["match_id"] == "m1"
    assert rows[0]["target"] == 1


def test_snapshot_without_result_is_excluded(tmp_path, monkeypatch):
    test_db = _setup_db(tmp_path, monkeypatch)
    _insert_snapshot(test_db, "no_result", _SAMPLE_FEATURES)

    assert database.load_training_rows("home_win") == []


def test_result_without_snapshot_is_excluded(tmp_path, monkeypatch):
    test_db = _setup_db(tmp_path, monkeypatch)
    _insert_result(test_db, "no_snapshot", home_score=1, away_score=0)

    assert database.load_training_rows("home_win") == []


# ---------------------------------------------------------------------------
# Target market mapping
# ---------------------------------------------------------------------------

def test_home_win_target_maps_to_home_win_column(tmp_path, monkeypatch):
    test_db = _setup_db(tmp_path, monkeypatch)
    _insert_snapshot(test_db, "m_hw", _SAMPLE_FEATURES)
    _insert_result(test_db, "m_hw", home_score=2, away_score=0)

    rows = database.load_training_rows("home_win")
    assert rows[0]["target"] == 1


def test_draw_target_maps_to_draw_column(tmp_path, monkeypatch):
    test_db = _setup_db(tmp_path, monkeypatch)
    _insert_snapshot(test_db, "m_draw", _SAMPLE_FEATURES)
    _insert_result(test_db, "m_draw", home_score=1, away_score=1)

    rows = database.load_training_rows("draw")
    assert rows[0]["target"] == 1


def test_away_win_target_maps_to_away_win_column(tmp_path, monkeypatch):
    test_db = _setup_db(tmp_path, monkeypatch)
    _insert_snapshot(test_db, "m_aw", _SAMPLE_FEATURES)
    _insert_result(test_db, "m_aw", home_score=0, away_score=3)

    rows = database.load_training_rows("away_win")
    assert rows[0]["target"] == 1


def test_draw_target_is_zero_for_home_win_result(tmp_path, monkeypatch):
    test_db = _setup_db(tmp_path, monkeypatch)
    _insert_snapshot(test_db, "m_hw2", _SAMPLE_FEATURES)
    _insert_result(test_db, "m_hw2", home_score=1, away_score=0)

    rows = database.load_training_rows("draw")
    assert rows[0]["target"] == 0


def test_btts_target_is_valid_market(tmp_path, monkeypatch):
    test_db = _setup_db(tmp_path, monkeypatch)
    _insert_snapshot(test_db, "m_btts", _SAMPLE_FEATURES)
    _insert_result(test_db, "m_btts", home_score=1, away_score=2)

    rows = database.load_training_rows("btts")
    assert rows[0]["target"] == 1


def test_over_25_target_is_valid_market(tmp_path, monkeypatch):
    test_db = _setup_db(tmp_path, monkeypatch)
    _insert_snapshot(test_db, "m_o25", _SAMPLE_FEATURES)
    _insert_result(test_db, "m_o25", home_score=2, away_score=1)

    rows = database.load_training_rows("over_25")
    assert rows[0]["target"] == 1


def test_unsupported_target_market_raises_value_error(tmp_path, monkeypatch):
    _setup_db(tmp_path, monkeypatch)
    import pytest
    with pytest.raises(ValueError, match="Unsupported target_market"):
        database.load_training_rows("fake_market")


# ---------------------------------------------------------------------------
# JSON validity guards
# ---------------------------------------------------------------------------

def test_malformed_features_json_is_excluded_not_raised(tmp_path, monkeypatch):
    test_db = _setup_db(tmp_path, monkeypatch)
    _insert_snapshot_raw(test_db, "m_bad_json", "{not valid json}")
    _insert_result(test_db, "m_bad_json", home_score=1, away_score=0)

    # Must not raise — malformed rows are silently excluded.
    rows = database.load_training_rows("home_win")
    assert rows == []


def test_null_features_json_is_excluded(tmp_path, monkeypatch):
    test_db = _setup_db(tmp_path, monkeypatch)
    _insert_snapshot_raw(test_db, "m_null_json", None)
    _insert_result(test_db, "m_null_json", home_score=1, away_score=0)

    assert database.load_training_rows("home_win") == []


def test_empty_features_json_is_excluded(tmp_path, monkeypatch):
    test_db = _setup_db(tmp_path, monkeypatch)
    _insert_snapshot_raw(test_db, "m_empty_json", "")
    _insert_result(test_db, "m_empty_json", home_score=1, away_score=0)

    assert database.load_training_rows("home_win") == []


def test_non_dict_features_json_is_excluded(tmp_path, monkeypatch):
    # Valid JSON but not an object — should be excluded.
    test_db = _setup_db(tmp_path, monkeypatch)
    _insert_snapshot_raw(test_db, "m_array_json", json.dumps([1, 2, 3]))
    _insert_result(test_db, "m_array_json", home_score=1, away_score=0)

    assert database.load_training_rows("home_win") == []


# ---------------------------------------------------------------------------
# NULL target guard
# ---------------------------------------------------------------------------

def test_null_target_column_is_excluded(tmp_path, monkeypatch):
    # Insert result with NULL home_win to simulate partial/corrupt result data.
    test_db = _setup_db(tmp_path, monkeypatch)
    _insert_snapshot(test_db, "m_null_target", _SAMPLE_FEATURES)
    con = sqlite3.connect(str(test_db))
    con.execute(
        "INSERT OR REPLACE INTO results "
        "(match_id, home_score, away_score, home_win, draw, away_win, "
        "btts, over_25, result_json, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        ("m_null_target", 1, 0, None, 0, 0, 0, 0, "{}", "2025-01-01T22:00:00+00:00"),
    )
    con.commit()
    con.close()

    rows = database.load_training_rows("home_win")
    assert rows == []


# ---------------------------------------------------------------------------
# Timestamp leakage guard
# ---------------------------------------------------------------------------

def test_snapshot_created_before_result_is_included(tmp_path, monkeypatch):
    test_db = _setup_db(tmp_path, monkeypatch)
    _insert_snapshot(test_db, "m_ts_ok", _SAMPLE_FEATURES,
                     created_at="2025-06-01T10:00:00+00:00")
    _insert_result(test_db, "m_ts_ok", home_score=1, away_score=0,
                   updated_at="2025-06-01T22:00:00+00:00")

    rows = database.load_training_rows("home_win")
    assert len(rows) == 1


def test_snapshot_created_after_result_is_excluded(tmp_path, monkeypatch):
    # Snapshot created_at AFTER result updated_at — potential post-result leakage.
    test_db = _setup_db(tmp_path, monkeypatch)
    _insert_snapshot(test_db, "m_ts_leak", _SAMPLE_FEATURES,
                     created_at="2025-06-01T23:00:00+00:00")
    _insert_result(test_db, "m_ts_leak", home_score=1, away_score=0,
                   updated_at="2025-06-01T22:00:00+00:00")

    rows = database.load_training_rows("home_win")
    assert rows == []


def test_snapshot_null_created_at_passes_through(tmp_path, monkeypatch):
    # NULL timestamps pass through as a legacy-compatible fallback for pre-existing data without timestamps.
    test_db = _setup_db(tmp_path, monkeypatch)
    con = sqlite3.connect(str(test_db))
    con.execute(
        "INSERT INTO feature_snapshots "
        "(run_id, match_id, model_version, features_json, created_at) "
        "VALUES (?, ?, ?, ?, ?)",
        ("run_test", "m_null_ts", "0.1.8.9", json.dumps(_SAMPLE_FEATURES), None),
    )
    con.commit()
    con.close()
    _insert_result(test_db, "m_null_ts", home_score=1, away_score=0,
                   updated_at="2025-06-01T22:00:00+00:00")

    rows = database.load_training_rows("home_win")
    assert len(rows) == 1


# ---------------------------------------------------------------------------
# Output shape — no leakage of prediction / odds / result-score fields
# ---------------------------------------------------------------------------

def test_output_does_not_include_prediction_fields(tmp_path, monkeypatch):
    test_db = _setup_db(tmp_path, monkeypatch)
    _insert_snapshot(test_db, "m_shape", _SAMPLE_FEATURES)
    _insert_result(test_db, "m_shape", home_score=2, away_score=0)

    row = database.load_training_rows("home_win")[0]
    prediction_fields = {"model_probability", "recommendation", "ev_per_unit",
                         "american_odds", "implied_probability", "edge",
                         "actionable", "do_not_bet_real_money", "run_id",
                         "technical_recommendation", "prediction_json"}
    assert prediction_fields.isdisjoint(row.keys()), (
        f"Prediction fields leaked into training row: {prediction_fields & row.keys()}"
    )


def test_output_does_not_include_odds_snapshot_fields(tmp_path, monkeypatch):
    test_db = _setup_db(tmp_path, monkeypatch)
    _insert_snapshot(test_db, "m_odds", _SAMPLE_FEATURES)
    _insert_result(test_db, "m_odds", home_score=2, away_score=0)

    row = database.load_training_rows("home_win")[0]
    odds_fields = {"sportsbook", "captured_at", "provider", "provider_event_id",
                   "sport_key", "commence_time", "raw_json"}
    assert odds_fields.isdisjoint(row.keys()), (
        f"Odds snapshot fields leaked into training row: {odds_fields & row.keys()}"
    )


def test_output_does_not_include_result_scores(tmp_path, monkeypatch):
    # home_score and away_score from results table must not appear in training rows.
    test_db = _setup_db(tmp_path, monkeypatch)
    _insert_snapshot(test_db, "m_scores", _SAMPLE_FEATURES)
    _insert_result(test_db, "m_scores", home_score=3, away_score=1)

    row = database.load_training_rows("home_win")[0]
    assert "home_score" not in row
    assert "away_score" not in row


def test_output_contains_match_id_and_target(tmp_path, monkeypatch):
    test_db = _setup_db(tmp_path, monkeypatch)
    _insert_snapshot(test_db, "m_out", {"feat_a": 1.0})
    _insert_result(test_db, "m_out", home_score=1, away_score=0)

    row = database.load_training_rows("home_win")[0]
    assert row["match_id"] == "m_out"
    assert row["target"] == 1
    assert row["feat_a"] == 1.0


# ---------------------------------------------------------------------------
# Write-safety
# ---------------------------------------------------------------------------

def test_loader_does_not_write_to_db(tmp_path, monkeypatch):
    test_db = _setup_db(tmp_path, monkeypatch)
    _insert_snapshot(test_db, "m_rw", _SAMPLE_FEATURES)
    _insert_result(test_db, "m_rw", home_score=1, away_score=0)

    mtime_before = test_db.stat().st_mtime
    size_before = test_db.stat().st_size

    database.load_training_rows("home_win")

    assert test_db.stat().st_size == size_before, "loader changed DB size"
    assert test_db.stat().st_mtime == mtime_before, "loader modified DB mtime"


def test_loader_does_not_change_schema(tmp_path, monkeypatch):
    test_db = _setup_db(tmp_path, monkeypatch)

    def _schema(db_path):
        con = sqlite3.connect(str(db_path))
        rows = con.execute(
            "SELECT name, sql FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()
        con.close()
        return rows

    before = _schema(test_db)
    database.load_training_rows("home_win")
    after = _schema(test_db)

    assert before == after, "Schema changed during load_training_rows call"


# ---------------------------------------------------------------------------
# Import boundary — historical_replay must not be imported by database
# ---------------------------------------------------------------------------

def test_database_does_not_import_historical_replay():
    banned = {"historical_replay"}
    module_names = set(vars(database).keys())
    for name in banned:
        assert name not in module_names, (
            f"database.py must not import {name}"
        )
