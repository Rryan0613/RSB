import os

from check_odds_provider import api_key_status, build_diagnostics, mask_secret


def test_mask_secret_hides_full_value():
    assert mask_secret(None) is None
    assert mask_secret("short") == "***"
    assert mask_secret("abcdefghijklmnop") == "abcd...mnop"


def test_api_key_status_does_not_expose_full_secret(monkeypatch):
    monkeypatch.setenv("ODDS_API_KEY", "abcdefghijklmnop")
    status = api_key_status()

    assert status["present"] is True
    assert status["masked"] == "abcd...mnop"
    assert status["masked"] != os.getenv("ODDS_API_KEY")


def test_api_key_status_missing(monkeypatch):
    monkeypatch.delenv("ODDS_API_KEY", raising=False)
    status = api_key_status()

    assert status["present"] is False
    assert status["masked"] is None


def test_mock_diagnostics_runs_without_api_key(monkeypatch):
    monkeypatch.delenv("ODDS_API_KEY", raising=False)
    report = build_diagnostics("mock")

    assert report["diagnostics_summary"]["provider"] == "mock"
    assert report["api_key_status"]["present"] is False
    assert report["provider_result"]["connection_status"] == "ok"
    assert report["provider_result"]["odds_lines_collected"] == 9


def test_live_diagnostics_missing_key_is_safe(monkeypatch):
    monkeypatch.delenv("ODDS_API_KEY", raising=False)
    report = build_diagnostics("the_odds_api", list_sports=False)

    assert report["diagnostics_summary"]["provider"] == "the_odds_api"
    assert report["api_key_status"]["present"] is False
    assert report["provider_result"]["connection_status"] == "error"
    assert "ODDS_API_KEY" in report["provider_result"]["error_message"]
