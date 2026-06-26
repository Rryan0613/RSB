import sqlite3
import json
from datetime import datetime, timezone

from paths import DEFAULT_DB_PATH

DB_PATH = DEFAULT_DB_PATH


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(DB_PATH)


def _column_exists(cur, table_name, column_name):
    columns = cur.execute(f"PRAGMA table_info({table_name})").fetchall()
    return any(row[1] == column_name for row in columns)


def _add_column_if_missing(cur, table_name, column_name, column_definition):
    if not _column_exists(cur, table_name, column_name):
        cur.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_definition}")


def init_db():
    con = connect()
    cur = con.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS matches (
        match_id TEXT PRIMARY KEY,
        date TEXT,
        competition TEXT,
        stage TEXT,
        neutral_site INTEGER,
        home_team TEXT,
        away_team TEXT,
        raw_json TEXT,
        created_at TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS feature_snapshots (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_id TEXT,
        match_id TEXT,
        model_version TEXT,
        features_json TEXT,
        created_at TEXT,
        UNIQUE(run_id, match_id)
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS predictions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_id TEXT,
        model_version TEXT,
        match_id TEXT,
        market TEXT,
        selection TEXT,
        model_probability REAL,
        american_odds INTEGER,
        implied_probability REAL,
        edge REAL,
        ev_per_unit REAL,
        recommendation TEXT,
        technical_recommendation TEXT,
        data_quality TEXT,
        actionable INTEGER,
        recommendation_guardrail TEXT,
        do_not_bet_real_money INTEGER,
        prediction_json TEXT,
        created_at TEXT
    )
    """)

    for column_name, column_definition in [
        ("technical_recommendation", "TEXT"),
        ("data_quality", "TEXT"),
        ("actionable", "INTEGER"),
        ("recommendation_guardrail", "TEXT"),
        ("do_not_bet_real_money", "INTEGER"),
        ("prediction_json", "TEXT"),
    ]:
        _add_column_if_missing(cur, "predictions", column_name, column_definition)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS simulation_outputs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_id TEXT,
        match_id TEXT,
        simulations INTEGER,
        output_json TEXT,
        created_at TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS odds_snapshots (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_id TEXT,
        match_id TEXT,
        sportsbook TEXT,
        market TEXT,
        selection TEXT,
        american_odds INTEGER,
        implied_probability REAL,
        captured_at TEXT,
        provider TEXT,
        provider_event_id TEXT,
        sport_key TEXT,
        home_team TEXT,
        away_team TEXT,
        commence_time TEXT,
        raw_json TEXT
    )
    """)

    for column_name, column_definition in [
        ("provider", "TEXT"),
        ("provider_event_id", "TEXT"),
        ("sport_key", "TEXT"),
        ("home_team", "TEXT"),
        ("away_team", "TEXT"),
        ("commence_time", "TEXT"),
        ("raw_json", "TEXT"),
    ]:
        _add_column_if_missing(cur, "odds_snapshots", column_name, column_definition)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS results (
        match_id TEXT PRIMARY KEY,
        home_score INTEGER,
        away_score INTEGER,
        home_win INTEGER,
        draw INTEGER,
        away_win INTEGER,
        btts INTEGER,
        over_25 INTEGER,
        result_json TEXT,
        updated_at TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS model_runs (
        run_id TEXT PRIMARY KEY,
        model_version TEXT,
        run_type TEXT,
        trained_on_matches INTEGER,
        notes TEXT,
        created_at TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS review_notes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_id TEXT,
        note_type TEXT,
        note_json TEXT,
        created_at TEXT
    )
    """)

    con.commit()
    con.close()


def save_match(match):
    con = connect()
    cur = con.cursor()
    cur.execute("""
    INSERT OR REPLACE INTO matches
    (match_id, date, competition, stage, neutral_site, home_team, away_team, raw_json, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        match["match_id"],
        match.get("date"),
        match.get("competition", "World Cup"),
        match.get("stage"),
        int(match.get("neutral_site", True)),
        match.get("home_team"),
        match.get("away_team"),
        json.dumps(match),
        utc_now()
    ))
    con.commit()
    con.close()


def save_features(run_id, model_version, match_id, features):
    con = connect()
    cur = con.cursor()
    cur.execute("""
    INSERT OR REPLACE INTO feature_snapshots
    (run_id, match_id, model_version, features_json, created_at)
    VALUES (?, ?, ?, ?, ?)
    """, (run_id, match_id, model_version, json.dumps(features), utc_now()))
    con.commit()
    con.close()


def save_prediction(pred):
    con = connect()
    cur = con.cursor()
    cur.execute("""
    INSERT INTO predictions
    (run_id, model_version, match_id, market, selection, model_probability,
     american_odds, implied_probability, edge, ev_per_unit, recommendation,
     technical_recommendation, data_quality, actionable, recommendation_guardrail,
     do_not_bet_real_money, prediction_json, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        pred["run_id"],
        pred["model_version"],
        pred["match_id"],
        pred["market"],
        pred["selection"],
        pred["model_probability"],
        pred["american_odds"],
        pred["implied_probability"],
        pred["edge"],
        pred["ev_per_unit"],
        pred["recommendation"],
        pred.get("technical_recommendation"),
        pred.get("data_quality"),
        int(bool(pred.get("actionable", False))),
        pred.get("recommendation_guardrail"),
        int(bool(pred.get("do_not_bet_real_money", False))),
        json.dumps(pred),
        utc_now()
    ))
    con.commit()
    con.close()


def save_simulation(run_id, match_id, simulations, output):
    con = connect()
    cur = con.cursor()
    cur.execute("""
    INSERT INTO simulation_outputs
    (run_id, match_id, simulations, output_json, created_at)
    VALUES (?, ?, ?, ?, ?)
    """, (run_id, match_id, simulations, json.dumps(output), utc_now()))
    con.commit()
    con.close()


def save_odds_snapshot(
    run_id,
    match_id,
    sportsbook,
    market,
    selection,
    american_odds,
    implied_probability,
    provider=None,
    provider_event_id=None,
    sport_key=None,
    home_team=None,
    away_team=None,
    commence_time=None,
    raw_json=None,
):
    con = connect()
    cur = con.cursor()
    cur.execute("""
    INSERT INTO odds_snapshots
    (run_id, match_id, sportsbook, market, selection, american_odds, implied_probability,
     captured_at, provider, provider_event_id, sport_key, home_team, away_team, commence_time, raw_json)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        run_id,
        match_id,
        sportsbook,
        market,
        selection,
        int(american_odds),
        float(implied_probability),
        utc_now(),
        provider,
        provider_event_id,
        sport_key,
        home_team,
        away_team,
        commence_time,
        json.dumps(raw_json) if raw_json is not None else None,
    ))
    con.commit()
    con.close()


def save_odds_lines(run_id, odds_lines):
    for line in odds_lines:
        save_odds_snapshot(
            run_id=run_id,
            match_id=line["match_id"],
            sportsbook=line["sportsbook"],
            market=line["market"],
            selection=line["selection"],
            american_odds=line["american_odds"],
            implied_probability=line["implied_probability"],
            provider=line.get("provider"),
            provider_event_id=line.get("provider_event_id"),
            sport_key=line.get("sport_key"),
            home_team=line.get("home_team"),
            away_team=line.get("away_team"),
            commence_time=line.get("commence_time"),
            raw_json=line.get("raw_json"),
        )


def save_result(result):
    home_score = int(result["home_score"])
    away_score = int(result["away_score"])

    con = connect()
    cur = con.cursor()
    cur.execute("""
    INSERT OR REPLACE INTO results
    (match_id, home_score, away_score, home_win, draw, away_win, btts, over_25, result_json, updated_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        result["match_id"],
        home_score,
        away_score,
        int(home_score > away_score),
        int(home_score == away_score),
        int(home_score < away_score),
        int(home_score > 0 and away_score > 0),
        int(home_score + away_score > 2.5),
        json.dumps(result),
        utc_now()
    ))
    con.commit()
    con.close()


def load_training_rows(target_market="home_win"):
    allowed_targets = {"home_win", "draw", "away_win", "btts", "over_25"}
    if target_market not in allowed_targets:
        raise ValueError(f"Unsupported target_market: {target_market}. Allowed: {sorted(allowed_targets)}")

    con = connect()
    query = f"""
    SELECT fs.match_id, fs.features_json, r.{target_market} AS target
    FROM feature_snapshots fs
    JOIN results r ON r.match_id = fs.match_id
    WHERE fs.id IN (
        SELECT MAX(id)
        FROM feature_snapshots
        GROUP BY match_id
    )
    """
    rows = con.execute(query).fetchall()
    con.close()

    training_rows = []
    for match_id, features_json, target in rows:
        features = json.loads(features_json)
        features["match_id"] = match_id
        features["target"] = int(target)
        training_rows.append(features)

    return training_rows


def save_model_run(run_id, model_version, run_type, trained_on_matches, notes=""):
    con = connect()
    cur = con.cursor()
    cur.execute("""
    INSERT OR REPLACE INTO model_runs
    (run_id, model_version, run_type, trained_on_matches, notes, created_at)
    VALUES (?, ?, ?, ?, ?, ?)
    """, (run_id, model_version, run_type, trained_on_matches, notes, utc_now()))
    con.commit()
    con.close()


def save_review_note(run_id, note_type, note):
    con = connect()
    cur = con.cursor()
    cur.execute("""
    INSERT INTO review_notes
    (run_id, note_type, note_json, created_at)
    VALUES (?, ?, ?, ?)
    """, (run_id, note_type, json.dumps(note), utc_now()))
    con.commit()
    con.close()
