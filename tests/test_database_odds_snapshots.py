import json
import sqlite3

import database


def test_save_odds_lines_persists_provider_metadata(tmp_path, monkeypatch):
    test_db_path = tmp_path / "test_worldcup_ai.db"
    monkeypatch.setattr(database, "DB_PATH", test_db_path)
    database.init_db()

    line = {
        "provider": "mock",
        "provider_event_id": "event_1",
        "sport_key": "soccer_fifa_world_cup",
        "match_id": "2026-06-26_canada_france",
        "sportsbook": "fanduel",
        "market": "h2h",
        "selection": "home_win",
        "american_odds": 225,
        "implied_probability": 0.3076923077,
        "home_team": "Canada",
        "away_team": "France",
        "commence_time": "2026-06-26T20:00:00Z",
        "raw_json": {"source": "test"},
    }

    database.save_odds_lines("run_1", [line])

    con = sqlite3.connect(test_db_path)
    row = con.execute(
        "SELECT provider, provider_event_id, sport_key, sportsbook, market, selection FROM odds_snapshots"
    ).fetchone()
    con.close()

    assert row == ("mock", "event_1", "soccer_fifa_world_cup", "fanduel", "h2h", "home_win")


def test_save_prediction_persists_full_payload(tmp_path, monkeypatch):
    test_db_path = tmp_path / "test_worldcup_ai.db"
    monkeypatch.setattr(database, "DB_PATH", test_db_path)
    database.init_db()

    pred = {
        "run_id": "run_1",
        "model_version": "0.1.8.1",
        "match_id": "2026-06-26_canada_france",
        "market": "h2h",
        "selection": "Canada home win",
        "model_probability": 0.31,
        "american_odds": 230,
        "implied_probability": 0.303,
        "edge": 0.007,
        "ev_per_unit": 0.02,
        "technical_recommendation": "pass",
        "recommendation": "pass",
        "data_quality": "weak",
        "actionable": False,
        "recommendation_guardrail": "blocked",
        "do_not_bet_real_money": True,
        "quality_warnings": [{"code": "simulation_only_bootstrap"}],
    }

    database.save_prediction(pred)

    con = sqlite3.connect(test_db_path)
    row = con.execute(
        "SELECT technical_recommendation, data_quality, actionable, recommendation_guardrail, do_not_bet_real_money, prediction_json FROM predictions"
    ).fetchone()
    con.close()

    saved_json = json.loads(row[5])
    assert row[:5] == ("pass", "weak", 0, "blocked", 1)
    assert saved_json["quality_warnings"] == [{"code": "simulation_only_bootstrap"}]
