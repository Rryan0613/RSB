from odds_collector import build_report, collect_odds, select_best_prices, summarize_bookmakers


def runtime_config():
    return {
        "model_config": {"version": "0.1.2", "odds_collection": {"provider": "mock"}},
        "sports_config": {},
        "active_sport": "worldcup",
        "sport_profile": {
            "label": "FIFA World Cup",
            "provider_sport_key": "soccer_fifa_world_cup",
            "bookmakers": ["fanduel", "draftkings", "betmgm"],
            "markets": ["h2h"],
        },
        "odds_config": {
            "provider": "mock",
            "regions": "us",
            "bookmakers": ["fanduel", "draftkings", "betmgm"],
            "markets": ["h2h"],
            "odds_format": "american",
        },
    }


def test_collect_odds_with_mock_provider():
    lines = collect_odds(runtime_config())

    assert len(lines) == 9
    assert {line["sportsbook"] for line in lines} == {"fanduel", "draftkings", "betmgm"}
    assert {line["selection"] for line in lines} == {"home_win", "draw", "away_win"}


def test_select_best_prices_keeps_best_sportsbook_line():
    lines = collect_odds(runtime_config())
    best = select_best_prices(lines)

    assert len(best) == 3
    home_win = [line for line in best if line["selection"] == "home_win"][0]
    assert home_win["sportsbook"] == "betmgm"
    assert home_win["american_odds"] == 230


def test_summarize_bookmakers_tracks_missing_books():
    lines = collect_odds(runtime_config())
    summary = summarize_bookmakers(lines, ["fanduel", "draftkings", "betmgm", "caesars"])

    assert summary["line_counts_by_bookmaker"]["fanduel"] == 3
    assert "caesars" in summary["missing_expected_bookmakers"]


def test_build_report_contains_foundation_metadata():
    lines = collect_odds(runtime_config())
    report = build_report("test_run", runtime_config(), lines)

    assert report["run_summary"]["active_sport"] == "worldcup"
    assert report["run_summary"]["provider"] == "mock"
    assert report["run_summary"]["odds_lines_collected"] == 9
    assert len(report["best_prices"]) == 3
