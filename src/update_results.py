import json
from pathlib import Path
from database import init_db, save_result

def main():
    init_db()
    results_path = Path("data/input/results.json")
    results = json.loads(results_path.read_text())

    for result in results["results"]:
        save_result(result)

    print(f"Saved {len(results['results'])} results.")
    print("Next run will include these games in training if feature snapshots exist.")

if __name__ == "__main__":
    main()
