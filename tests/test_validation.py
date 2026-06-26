import pytest

from validation import (
    validate_slate,
    validate_results,
    SlateValidationError,
    ResultsValidationError,
)

VALID_MATCH = {
    "match_id": "test_match",
    "date": "2026-06-26",
    "home_team": "Alpha FC",
    "away_team": "Beta FC",
    "home": {},
    "away": {},
    "odds": {"home_win": -120}
}


def test_empty_slate_is_valid():
    validate_slate({"matches": []})


def test_valid_slate_is_valid():
    validate_slate({"matches": [VALID_MATCH]})


def test_slate_missing_matches_fails():
    with pytest.raises(SlateValidationError):
        validate_slate({})


def test_match_missing_home_win_odds_fails():
    invalid = {**VALID_MATCH, "odds": {"away_win": 200}}
    with pytest.raises(SlateValidationError):
        validate_slate({"matches": [invalid]})


def test_empty_results_is_valid():
    validate_results({"results": []})


def test_valid_results_is_valid():
    validate_results({"results": [{"match_id": "test_match", "home_score": 2, "away_score": 1}]})


def test_results_missing_score_fails():
    with pytest.raises(ResultsValidationError):
        validate_results({"results": [{"match_id": "test_match", "home_score": 2}]})
