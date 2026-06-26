# WorldCup AI v0.1

A focused World Cup +EV prediction framework.

This project is designed to:
- Store every match, feature snapshot, prediction, odds line, simulation output, and final result.
- Retrain from the local database as completed results are added.
- Estimate model probability.
- Compare model probability to sportsbook implied probability.
- Calculate edge and expected value.
- Generate structured JSON that can be pasted into Claude or ChatGPT for review.

This is not a "lock" generator. It is a disciplined sports analytics research project.

## Quick Start

```bash
python -m venv .venv
source .venv/bin/activate   # Mac/Linux
# .venv\Scripts\activate   # Windows

pip install -r requirements.txt
python src/run_slate.py
```

The first run may say there is not enough completed historical data to train. That is expected. Add historical results or use the sample bootstrap data.

## Main Workflow

1. Add upcoming matches to `data/input/slate.json`.
2. Run:

```bash
python src/run_slate.py
```

3. The model writes predictions to:

```text
data/output/latest_model_output.json
```

4. Paste that JSON into Claude with the prompt in:

```text
prompts/claude_worldcup_prompt.md
```

5. After games finish, add final results to:

```text
data/input/results.json
```

6. Run:

```bash
python src/update_results.py
```

7. Next slate run retrains using the updated database.

## Database

SQLite database path:

```text
data/worldcup_ai.db
```

The database is the model's memory.
