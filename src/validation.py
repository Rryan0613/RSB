class SlateValidationError(ValueError):
    pass

class ResultsValidationError(ValueError):
    pass

REQUIRED_MATCH_FIELDS = [
    "match_id",
    "date",
    "home_team",
    "away_team",
    "home",
    "away",
    "odds",
]

REQUIRED_RESULT_FIELDS = [
    "match_id",
    "home_score",
    "away_score",
]

def _is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)

def validate_slate(data):
    if not isinstance(data, dict):
        raise SlateValidationError(f"slate.json must be a JSON object, got {type(data).__name__}.")

    if "matches" not in data:
        raise SlateValidationError('slate.json is missing top-level "matches" key.')

    if not isinstance(data["matches"], list):
        raise SlateValidationError(f'"matches" must be a list, got {type(data["matches"]).__name__}.')

    for index, match in enumerate(data["matches"]):
        validate_match(match, index)

def validate_match(match, index=0):
    if not isinstance(match, dict):
        raise SlateValidationError(f"matches[{index}] must be an object, got {type(match).__name__}.")

    for field in REQUIRED_MATCH_FIELDS:
        if field not in match:
            match_id = match.get("match_id", f"<index {index}>")
            raise SlateValidationError(f'Match "{match_id}" is missing required field "{field}".')

    for team_key in ["home", "away"]:
        if not isinstance(match[team_key], dict):
            match_id = match.get("match_id", f"<index {index}>")
            raise SlateValidationError(f'Match "{match_id}" field "{team_key}" must be an object of team metrics.')

    odds = match["odds"]
    if not isinstance(odds, dict):
        match_id = match.get("match_id", f"<index {index}>")
        raise SlateValidationError(f'Match "{match_id}" field "odds" must be an object.')

    if "home_win" not in odds:
        match_id = match.get("match_id", f"<index {index}>")
        raise SlateValidationError(f'Match "{match_id}" odds are missing required key "home_win".')

    if not _is_number(odds["home_win"]) or odds["home_win"] == 0:
        match_id = match.get("match_id", f"<index {index}>")
        raise SlateValidationError(f'Match "{match_id}" odds.home_win must be a non-zero number.')

    if "simulations" in match:
        simulations = match["simulations"]
        if not isinstance(simulations, int) or isinstance(simulations, bool) or simulations <= 0:
            match_id = match.get("match_id", f"<index {index}>")
            raise SlateValidationError(f'Match "{match_id}" simulations must be a positive integer.')

def validate_results(data):
    if not isinstance(data, dict):
        raise ResultsValidationError(f"results.json must be a JSON object, got {type(data).__name__}.")

    if "results" not in data:
        raise ResultsValidationError('results.json is missing top-level "results" key.')

    if not isinstance(data["results"], list):
        raise ResultsValidationError(f'"results" must be a list, got {type(data["results"]).__name__}.')

    for index, result in enumerate(data["results"]):
        validate_result(result, index)

def validate_result(result, index=0):
    if not isinstance(result, dict):
        raise ResultsValidationError(f"results[{index}] must be an object, got {type(result).__name__}.")

    for field in REQUIRED_RESULT_FIELDS:
        if field not in result:
            match_id = result.get("match_id", f"<index {index}>")
            raise ResultsValidationError(f'Result "{match_id}" is missing required field "{field}".')

    for score_field in ["home_score", "away_score"]:
        score = result[score_field]
        if not isinstance(score, int) or isinstance(score, bool) or score < 0:
            match_id = result.get("match_id", f"<index {index}>")
            raise ResultsValidationError(f'Result "{match_id}" field "{score_field}" must be a non-negative integer.')
