import json
from pathlib import Path
from database import init_db, save_review_note

def main():
    init_db()
    review_path = Path("data/input/claude_review.json")
    review = json.loads(review_path.read_text())

    run_id = review.get("run_summary", {}).get("run_id") or review.get("run_id", "unknown")
    save_review_note(run_id, "claude_review", review)

    print("Claude review saved.")
    print("Send this file to ChatGPT so the framework can be updated if the model missed something.")

if __name__ == "__main__":
    main()
