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
