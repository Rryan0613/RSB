import json
from database import init_db, save_result
from paths import get_results_path
from validation import validate_results


def main():
    init_db()
    results_path = get_results_path()
    results = json.loads(results_path.read_text())
    validate_results(results)

    result_count = len(results["results"])
    for result in results["results"]:
        save_result(result)

    print("Saved " + str(result_count) + " results.")
    print("Next run will include these games in training if feature snapshots exist.")


if __name__ == "__main__":
    main()
