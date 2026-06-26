import sqlite3
import json
from pathlib import Path
from datetime import datetime, timezone

DB_PATH = Path("data/worldcup_ai.db")

def utc_now():
    return datetime.now(timezone.utc).isoformat()

def connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(DB_PATH)

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
        created_at TEXT
    )
    """)

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
     american_odds, implied_probability, edge, ev_per_unit, recommendation, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
