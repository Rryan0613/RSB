import pytest

from odds_snapshot import (
    OddsSnapshotValidationError,
    VALID_ODDS_FORMATS,
    normalize_provider,
    normalize_sportsbook,
    normalize_market_type,
    normalize_selection,
    normalize_odds_format,
    build_odds_snapshot,
)


# ---------------------------------------------------------------------------
# OddsSnapshotValidationError
# ---------------------------------------------------------------------------

def test_odds_snapshot_validation_error_is_value_error():
    assert issubclass(OddsSnapshotValidationError, ValueError)


# ---------------------------------------------------------------------------
# VALID_ODDS_FORMATS
# ---------------------------------------------------------------------------

def test_valid_odds_formats_is_frozenset():
    assert isinstance(VALID_ODDS_FORMATS, frozenset)


def test_valid_odds_formats_contains_american_and_decimal():
    assert VALID_ODDS_FORMATS == frozenset({"american", "decimal"})


# ---------------------------------------------------------------------------
# normalize_provider
# ---------------------------------------------------------------------------

def test_normalize_provider_basic():
    assert normalize_provider("the_odds_api") == "the_odds_api"


def test_normalize_provider_strips_whitespace():
    assert normalize_provider("  the_odds_api  ") == "the_odds_api"


def test_normalize_provider_lowercases():
    assert normalize_provider("THE_ODDS_API") == "the_odds_api"


def test_normalize_provider_spaces_to_underscores():
    assert normalize_provider("the odds api") == "the_odds_api"


def test_normalize_provider_hyphens_to_underscores():
    assert normalize_provider("the-odds-api") == "the_odds_api"


def test_normalize_provider_returns_str():
    assert type(normalize_provider("the_odds_api")) is str


@pytest.mark.parametrize("value", [None, 42, ["the_odds_api"]])
def test_normalize_provider_rejects_non_string(value):
    with pytest.raises(OddsSnapshotValidationError):
        normalize_provider(value)


def test_normalize_provider_rejects_empty():
    with pytest.raises(OddsSnapshotValidationError):
        normalize_provider("")


def test_normalize_provider_rejects_whitespace_only():
    with pytest.raises(OddsSnapshotValidationError):
        normalize_provider("   ")


# ---------------------------------------------------------------------------
# normalize_sportsbook
# ---------------------------------------------------------------------------

def test_normalize_sportsbook_basic():
    assert normalize_sportsbook("draftkings") == "draftkings"


def test_normalize_sportsbook_strips_whitespace():
    assert normalize_sportsbook("  draftkings  ") == "draftkings"


def test_normalize_sportsbook_lowercases():
    assert normalize_sportsbook("DraftKings") == "draftkings"


def test_normalize_sportsbook_spaces_to_underscores():
    assert normalize_sportsbook("draft kings") == "draft_kings"


def test_normalize_sportsbook_hyphens_to_underscores():
    assert normalize_sportsbook("fan-duel") == "fan_duel"


def test_normalize_sportsbook_returns_str():
    assert type(normalize_sportsbook("draftkings")) is str


@pytest.mark.parametrize("value", [None, 0, ["draftkings"]])
def test_normalize_sportsbook_rejects_non_string(value):
    with pytest.raises(OddsSnapshotValidationError):
        normalize_sportsbook(value)


def test_normalize_sportsbook_rejects_empty():
    with pytest.raises(OddsSnapshotValidationError):
        normalize_sportsbook("")


def test_normalize_sportsbook_rejects_whitespace_only():
    with pytest.raises(OddsSnapshotValidationError):
        normalize_sportsbook("   ")


# ---------------------------------------------------------------------------
# normalize_market_type
# ---------------------------------------------------------------------------

def test_normalize_market_type_basic():
    assert normalize_market_type("player_points") == "player_points"


def test_normalize_market_type_strips():
    assert normalize_market_type("  player_points  ") == "player_points"


def test_normalize_market_type_lowercases():
    assert normalize_market_type("PLAYER_POINTS") == "player_points"


def test_normalize_market_type_spaces_to_underscores():
    assert normalize_market_type("player points") == "player_points"


def test_normalize_market_type_hyphens_to_underscores():
    assert normalize_market_type("player-points") == "player_points"


def test_normalize_market_type_returns_str():
    assert type(normalize_market_type("player_points")) is str


@pytest.mark.parametrize("value", [None, 0, ["player_points"]])
def test_normalize_market_type_rejects_non_string(value):
    with pytest.raises(OddsSnapshotValidationError):
        normalize_market_type(value)


def test_normalize_market_type_rejects_empty():
    with pytest.raises(OddsSnapshotValidationError):
        normalize_market_type("")


def test_normalize_market_type_rejects_whitespace_only():
    with pytest.raises(OddsSnapshotValidationError):
        normalize_market_type("   ")


# ---------------------------------------------------------------------------
# normalize_selection
# ---------------------------------------------------------------------------

def test_normalize_selection_basic():
    assert normalize_selection("over") == "over"


def test_normalize_selection_strips():
    assert normalize_selection("  over  ") == "over"


def test_normalize_selection_lowercases():
    assert normalize_selection("OVER") == "over"


def test_normalize_selection_spaces_to_underscores():
    assert normalize_selection("home win") == "home_win"


def test_normalize_selection_hyphens_to_underscores():
    assert normalize_selection("home-win") == "home_win"


def test_normalize_selection_returns_str():
    assert type(normalize_selection("over")) is str


@pytest.mark.parametrize("value", [None, 1, ["over"]])
def test_normalize_selection_rejects_non_string(value):
    with pytest.raises(OddsSnapshotValidationError):
        normalize_selection(value)


def test_normalize_selection_rejects_empty():
    with pytest.raises(OddsSnapshotValidationError):
        normalize_selection("")


def test_normalize_selection_rejects_whitespace_only():
    with pytest.raises(OddsSnapshotValidationError):
        normalize_selection("   ")


# ---------------------------------------------------------------------------
# normalize_odds_format
# ---------------------------------------------------------------------------

def test_normalize_odds_format_american():
    assert normalize_odds_format("american") == "american"


def test_normalize_odds_format_decimal():
    assert normalize_odds_format("decimal") == "decimal"


def test_normalize_odds_format_lowercases():
    assert normalize_odds_format("AMERICAN") == "american"


def test_normalize_odds_format_strips_whitespace():
    assert normalize_odds_format("  decimal  ") == "decimal"


def test_normalize_odds_format_returns_str():
    assert type(normalize_odds_format("american")) is str


def test_normalize_odds_format_rejects_fractional():
    with pytest.raises(OddsSnapshotValidationError):
        normalize_odds_format("fractional")


def test_normalize_odds_format_rejects_unknown():
    with pytest.raises(OddsSnapshotValidationError):
        normalize_odds_format("moneyline")


def test_normalize_odds_format_rejects_empty():
    with pytest.raises(OddsSnapshotValidationError):
        normalize_odds_format("")


def test_normalize_odds_format_rejects_whitespace_only():
    with pytest.raises(OddsSnapshotValidationError):
        normalize_odds_format("   ")


@pytest.mark.parametrize("value", [None, 42, ["american"]])
def test_normalize_odds_format_rejects_non_string(value):
    with pytest.raises(OddsSnapshotValidationError):
        normalize_odds_format(value)


# ---------------------------------------------------------------------------
# build_odds_snapshot — return shape
# ---------------------------------------------------------------------------

EXPECTED_KEYS = {
    "provider", "sportsbook", "event_id", "market_type", "selection",
    "line", "odds", "odds_format", "odds_found_at", "source", "metadata",
}


def test_build_odds_snapshot_returns_exactly_11_keys():
    result = build_odds_snapshot(
        "the_odds_api", "draftkings", "WC2026_G42", "player_points", "over",
        -110, "american", "2026-06-29T10:00:00Z",
    )
    assert set(result.keys()) == EXPECTED_KEYS
    assert len(result) == 11


def test_build_odds_snapshot_returns_plain_dict():
    result = build_odds_snapshot(
        "the_odds_api", "draftkings", "WC2026_G42", "player_points", "over",
        -110, "american", "2026-06-29T10:00:00Z",
    )
    assert type(result) is dict


def test_build_odds_snapshot_all_keys_always_present():
    result = build_odds_snapshot(
        "the_odds_api", "draftkings", "WC2026_G42", "player_points", "over",
        -110, "american", "2026-06-29T10:00:00Z",
    )
    for key in EXPECTED_KEYS:
        assert key in result


# ---------------------------------------------------------------------------
# build_odds_snapshot — canonical example (all fields)
# ---------------------------------------------------------------------------

def test_build_odds_snapshot_full_canonical_american():
    result = build_odds_snapshot(
        "the_odds_api",
        "draftkings",
        "WC2026_G42",
        "player_shots_on_target",
        "over",
        -110,
        "american",
        "2026-06-29T10:00:00Z",
        line=2.5,
        source="api_pull",
        metadata={"batch_id": "b001"},
    )
    assert result["provider"] == "the_odds_api"
    assert result["sportsbook"] == "draftkings"
    assert result["event_id"] == "WC2026_G42"
    assert result["market_type"] == "player_shots_on_target"
    assert result["selection"] == "over"
    assert result["line"] == pytest.approx(2.5)
    assert result["odds"] == pytest.approx(-110.0)
    assert result["odds_format"] == "american"
    assert result["odds_found_at"] == "2026-06-29T10:00:00Z"
    assert result["source"] == "api_pull"
    assert result["metadata"] == {"batch_id": "b001"}


def test_build_odds_snapshot_full_canonical_decimal():
    result = build_odds_snapshot(
        "pinnacle",
        "fanduel",
        "WC2026_G42",
        "player_points",
        "under",
        1.91,
        "decimal",
        "2026-06-29T11:00:00Z",
        line=3.5,
        source="scrape",
        metadata={"region": "us"},
    )
    assert result["provider"] == "pinnacle"
    assert result["sportsbook"] == "fanduel"
    assert result["event_id"] == "WC2026_G42"
    assert result["market_type"] == "player_points"
    assert result["selection"] == "under"
    assert result["line"] == pytest.approx(3.5)
    assert result["odds"] == pytest.approx(1.91)
    assert result["odds_format"] == "decimal"
    assert result["odds_found_at"] == "2026-06-29T11:00:00Z"
    assert result["source"] == "scrape"
    assert result["metadata"] == {"region": "us"}


# ---------------------------------------------------------------------------
# build_odds_snapshot — minimal required fields / optional defaults
# ---------------------------------------------------------------------------

def test_build_odds_snapshot_minimal_required_only():
    result = build_odds_snapshot(
        "the_odds_api", "draftkings", "WC2026_G42", "player_points", "over",
        -110, "american", "2026-06-29T10:00:00Z",
    )
    assert result["provider"] == "the_odds_api"
    assert result["sportsbook"] == "draftkings"
    assert result["event_id"] == "WC2026_G42"
    assert result["market_type"] == "player_points"
    assert result["selection"] == "over"
    assert result["line"] is None
    assert result["odds"] == pytest.approx(-110.0)
    assert result["odds_format"] == "american"
    assert result["odds_found_at"] == "2026-06-29T10:00:00Z"
    assert result["source"] is None
    assert result["metadata"] == {}


# ---------------------------------------------------------------------------
# build_odds_snapshot — required field validation (provider)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("value", [None, 42, ["the_odds_api"]])
def test_build_odds_snapshot_provider_rejects_non_string(value):
    with pytest.raises(OddsSnapshotValidationError):
        build_odds_snapshot(
            value, "draftkings", "WC2026_G42", "player_points", "over",
            -110, "american", "2026-06-29T10:00:00Z",
        )


def test_build_odds_snapshot_provider_rejects_empty():
    with pytest.raises(OddsSnapshotValidationError):
        build_odds_snapshot(
            "", "draftkings", "WC2026_G42", "player_points", "over",
            -110, "american", "2026-06-29T10:00:00Z",
        )


def test_build_odds_snapshot_provider_rejects_whitespace_only():
    with pytest.raises(OddsSnapshotValidationError):
        build_odds_snapshot(
            "   ", "draftkings", "WC2026_G42", "player_points", "over",
            -110, "american", "2026-06-29T10:00:00Z",
        )


# ---------------------------------------------------------------------------
# build_odds_snapshot — required field validation (sportsbook)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("value", [None, 42, ["draftkings"]])
def test_build_odds_snapshot_sportsbook_rejects_non_string(value):
    with pytest.raises(OddsSnapshotValidationError):
        build_odds_snapshot(
            "the_odds_api", value, "WC2026_G42", "player_points", "over",
            -110, "american", "2026-06-29T10:00:00Z",
        )


def test_build_odds_snapshot_sportsbook_rejects_empty():
    with pytest.raises(OddsSnapshotValidationError):
        build_odds_snapshot(
            "the_odds_api", "", "WC2026_G42", "player_points", "over",
            -110, "american", "2026-06-29T10:00:00Z",
        )


def test_build_odds_snapshot_sportsbook_rejects_whitespace_only():
    with pytest.raises(OddsSnapshotValidationError):
        build_odds_snapshot(
            "the_odds_api", "   ", "WC2026_G42", "player_points", "over",
            -110, "american", "2026-06-29T10:00:00Z",
        )


# ---------------------------------------------------------------------------
# build_odds_snapshot — required field validation (event_id)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("value", [None, 42, ["WC2026_G42"]])
def test_build_odds_snapshot_event_id_rejects_non_string(value):
    with pytest.raises(OddsSnapshotValidationError):
        build_odds_snapshot(
            "the_odds_api", "draftkings", value, "player_points", "over",
            -110, "american", "2026-06-29T10:00:00Z",
        )


def test_build_odds_snapshot_event_id_rejects_empty():
    with pytest.raises(OddsSnapshotValidationError):
        build_odds_snapshot(
            "the_odds_api", "draftkings", "", "player_points", "over",
            -110, "american", "2026-06-29T10:00:00Z",
        )


def test_build_odds_snapshot_event_id_rejects_whitespace_only():
    with pytest.raises(OddsSnapshotValidationError):
        build_odds_snapshot(
            "the_odds_api", "draftkings", "   ", "player_points", "over",
            -110, "american", "2026-06-29T10:00:00Z",
        )


# ---------------------------------------------------------------------------
# build_odds_snapshot — required field validation (market_type)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("value", [None, 42, ["player_points"]])
def test_build_odds_snapshot_market_type_rejects_non_string(value):
    with pytest.raises(OddsSnapshotValidationError):
        build_odds_snapshot(
            "the_odds_api", "draftkings", "WC2026_G42", value, "over",
            -110, "american", "2026-06-29T10:00:00Z",
        )


def test_build_odds_snapshot_market_type_rejects_empty():
    with pytest.raises(OddsSnapshotValidationError):
        build_odds_snapshot(
            "the_odds_api", "draftkings", "WC2026_G42", "", "over",
            -110, "american", "2026-06-29T10:00:00Z",
        )


def test_build_odds_snapshot_market_type_rejects_whitespace_only():
    with pytest.raises(OddsSnapshotValidationError):
        build_odds_snapshot(
            "the_odds_api", "draftkings", "WC2026_G42", "   ", "over",
            -110, "american", "2026-06-29T10:00:00Z",
        )


# ---------------------------------------------------------------------------
# build_odds_snapshot — required field validation (selection)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("value", [None, 42, ["over"]])
def test_build_odds_snapshot_selection_rejects_non_string(value):
    with pytest.raises(OddsSnapshotValidationError):
        build_odds_snapshot(
            "the_odds_api", "draftkings", "WC2026_G42", "player_points", value,
            -110, "american", "2026-06-29T10:00:00Z",
        )


def test_build_odds_snapshot_selection_rejects_empty():
    with pytest.raises(OddsSnapshotValidationError):
        build_odds_snapshot(
            "the_odds_api", "draftkings", "WC2026_G42", "player_points", "",
            -110, "american", "2026-06-29T10:00:00Z",
        )


def test_build_odds_snapshot_selection_rejects_whitespace_only():
    with pytest.raises(OddsSnapshotValidationError):
        build_odds_snapshot(
            "the_odds_api", "draftkings", "WC2026_G42", "player_points", "   ",
            -110, "american", "2026-06-29T10:00:00Z",
        )


# ---------------------------------------------------------------------------
# build_odds_snapshot — event_id case preservation
# ---------------------------------------------------------------------------

def test_build_odds_snapshot_event_id_preserves_case():
    result = build_odds_snapshot(
        "the_odds_api", "draftkings", "WC2026_G42", "player_points", "over",
        -110, "american", "2026-06-29T10:00:00Z",
    )
    assert result["event_id"] == "WC2026_G42"


def test_build_odds_snapshot_event_id_strips_whitespace():
    result = build_odds_snapshot(
        "the_odds_api", "draftkings", "  WC2026_G42  ", "player_points", "over",
        -110, "american", "2026-06-29T10:00:00Z",
    )
    assert result["event_id"] == "WC2026_G42"


def test_build_odds_snapshot_event_id_not_lowercased():
    result = build_odds_snapshot(
        "the_odds_api", "draftkings", "WC2026-GroupA-G42", "player_points", "over",
        -110, "american", "2026-06-29T10:00:00Z",
    )
    assert result["event_id"] == "WC2026-GroupA-G42"


# ---------------------------------------------------------------------------
# build_odds_snapshot — odds_format validation
# ---------------------------------------------------------------------------

def test_build_odds_snapshot_odds_format_american_accepted():
    result = build_odds_snapshot(
        "the_odds_api", "draftkings", "WC2026_G42", "player_points", "over",
        -110, "american", "2026-06-29T10:00:00Z",
    )
    assert result["odds_format"] == "american"


def test_build_odds_snapshot_odds_format_decimal_accepted():
    result = build_odds_snapshot(
        "the_odds_api", "draftkings", "WC2026_G42", "player_points", "over",
        1.91, "decimal", "2026-06-29T10:00:00Z",
    )
    assert result["odds_format"] == "decimal"


def test_build_odds_snapshot_odds_format_normalized_in_output():
    result = build_odds_snapshot(
        "the_odds_api", "draftkings", "WC2026_G42", "player_points", "over",
        -110, "AMERICAN", "2026-06-29T10:00:00Z",
    )
    assert result["odds_format"] == "american"


def test_build_odds_snapshot_odds_format_rejects_unknown():
    with pytest.raises(OddsSnapshotValidationError):
        build_odds_snapshot(
            "the_odds_api", "draftkings", "WC2026_G42", "player_points", "over",
            -110, "fractional", "2026-06-29T10:00:00Z",
        )


def test_build_odds_snapshot_odds_format_rejects_empty():
    with pytest.raises(OddsSnapshotValidationError):
        build_odds_snapshot(
            "the_odds_api", "draftkings", "WC2026_G42", "player_points", "over",
            -110, "", "2026-06-29T10:00:00Z",
        )


@pytest.mark.parametrize("value", [None, 42, ["american"]])
def test_build_odds_snapshot_odds_format_rejects_non_string(value):
    with pytest.raises(OddsSnapshotValidationError):
        build_odds_snapshot(
            "the_odds_api", "draftkings", "WC2026_G42", "player_points", "over",
            -110, value, "2026-06-29T10:00:00Z",
        )


# ---------------------------------------------------------------------------
# build_odds_snapshot — odds validation (American format)
# ---------------------------------------------------------------------------

def test_build_odds_snapshot_american_negative_odds_valid():
    result = build_odds_snapshot(
        "the_odds_api", "draftkings", "WC2026_G42", "player_points", "over",
        -110, "american", "2026-06-29T10:00:00Z",
    )
    assert result["odds"] == pytest.approx(-110.0)


def test_build_odds_snapshot_american_positive_odds_valid():
    result = build_odds_snapshot(
        "the_odds_api", "draftkings", "WC2026_G42", "player_points", "over",
        +150, "american", "2026-06-29T10:00:00Z",
    )
    assert result["odds"] == pytest.approx(150.0)


def test_build_odds_snapshot_american_odds_returns_float():
    result = build_odds_snapshot(
        "the_odds_api", "draftkings", "WC2026_G42", "player_points", "over",
        -110, "american", "2026-06-29T10:00:00Z",
    )
    assert type(result["odds"]) is float


def test_build_odds_snapshot_american_int_odds_returns_float():
    result = build_odds_snapshot(
        "the_odds_api", "draftkings", "WC2026_G42", "player_points", "over",
        200, "american", "2026-06-29T10:00:00Z",
    )
    assert result["odds"] == pytest.approx(200.0)
    assert type(result["odds"]) is float


def test_build_odds_snapshot_american_rejects_zero():
    with pytest.raises(OddsSnapshotValidationError):
        build_odds_snapshot(
            "the_odds_api", "draftkings", "WC2026_G42", "player_points", "over",
            0, "american", "2026-06-29T10:00:00Z",
        )


@pytest.mark.parametrize("value", [True, False])
def test_build_odds_snapshot_american_rejects_bool(value):
    with pytest.raises(OddsSnapshotValidationError):
        build_odds_snapshot(
            "the_odds_api", "draftkings", "WC2026_G42", "player_points", "over",
            value, "american", "2026-06-29T10:00:00Z",
        )


@pytest.mark.parametrize("value", ["-110", None, [-110]])
def test_build_odds_snapshot_american_rejects_non_numeric(value):
    with pytest.raises(OddsSnapshotValidationError):
        build_odds_snapshot(
            "the_odds_api", "draftkings", "WC2026_G42", "player_points", "over",
            value, "american", "2026-06-29T10:00:00Z",
        )


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_build_odds_snapshot_american_rejects_nan_and_inf(value):
    with pytest.raises(OddsSnapshotValidationError):
        build_odds_snapshot(
            "the_odds_api", "draftkings", "WC2026_G42", "player_points", "over",
            value, "american", "2026-06-29T10:00:00Z",
        )


# ---------------------------------------------------------------------------
# build_odds_snapshot — odds validation (decimal format)
# ---------------------------------------------------------------------------

def test_build_odds_snapshot_decimal_odds_valid():
    result = build_odds_snapshot(
        "the_odds_api", "draftkings", "WC2026_G42", "player_points", "over",
        2.5, "decimal", "2026-06-29T10:00:00Z",
    )
    assert result["odds"] == pytest.approx(2.5)


def test_build_odds_snapshot_decimal_odds_just_above_one_valid():
    result = build_odds_snapshot(
        "the_odds_api", "draftkings", "WC2026_G42", "player_points", "over",
        1.01, "decimal", "2026-06-29T10:00:00Z",
    )
    assert result["odds"] == pytest.approx(1.01)


def test_build_odds_snapshot_decimal_odds_returns_float():
    result = build_odds_snapshot(
        "the_odds_api", "draftkings", "WC2026_G42", "player_points", "over",
        2.5, "decimal", "2026-06-29T10:00:00Z",
    )
    assert type(result["odds"]) is float


def test_build_odds_snapshot_decimal_rejects_exactly_one():
    with pytest.raises(OddsSnapshotValidationError):
        build_odds_snapshot(
            "the_odds_api", "draftkings", "WC2026_G42", "player_points", "over",
            1.0, "decimal", "2026-06-29T10:00:00Z",
        )


@pytest.mark.parametrize("value", [0.5, 0.0, -1.0, -110.0])
def test_build_odds_snapshot_decimal_rejects_lte_one(value):
    with pytest.raises(OddsSnapshotValidationError):
        build_odds_snapshot(
            "the_odds_api", "draftkings", "WC2026_G42", "player_points", "over",
            value, "decimal", "2026-06-29T10:00:00Z",
        )


@pytest.mark.parametrize("value", [True, False])
def test_build_odds_snapshot_decimal_rejects_bool(value):
    with pytest.raises(OddsSnapshotValidationError):
        build_odds_snapshot(
            "the_odds_api", "draftkings", "WC2026_G42", "player_points", "over",
            value, "decimal", "2026-06-29T10:00:00Z",
        )


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_build_odds_snapshot_decimal_rejects_nan_and_inf(value):
    with pytest.raises(OddsSnapshotValidationError):
        build_odds_snapshot(
            "the_odds_api", "draftkings", "WC2026_G42", "player_points", "over",
            value, "decimal", "2026-06-29T10:00:00Z",
        )


# ---------------------------------------------------------------------------
# build_odds_snapshot — odds_found_at validation
# ---------------------------------------------------------------------------

def test_build_odds_snapshot_odds_found_at_valid():
    result = build_odds_snapshot(
        "the_odds_api", "draftkings", "WC2026_G42", "player_points", "over",
        -110, "american", "2026-06-29T10:00:00Z",
    )
    assert result["odds_found_at"] == "2026-06-29T10:00:00Z"


def test_build_odds_snapshot_odds_found_at_strips_whitespace():
    result = build_odds_snapshot(
        "the_odds_api", "draftkings", "WC2026_G42", "player_points", "over",
        -110, "american", "  2026-06-29T10:00:00Z  ",
    )
    assert result["odds_found_at"] == "2026-06-29T10:00:00Z"


def test_build_odds_snapshot_odds_found_at_preserves_case():
    result = build_odds_snapshot(
        "the_odds_api", "draftkings", "WC2026_G42", "player_points", "over",
        -110, "american", "2026-06-29T10:00:00Z",
    )
    assert result["odds_found_at"] == "2026-06-29T10:00:00Z"


@pytest.mark.parametrize("value", [None, 20260629, ["2026-06-29"]])
def test_build_odds_snapshot_odds_found_at_rejects_non_string(value):
    with pytest.raises(OddsSnapshotValidationError):
        build_odds_snapshot(
            "the_odds_api", "draftkings", "WC2026_G42", "player_points", "over",
            -110, "american", value,
        )


def test_build_odds_snapshot_odds_found_at_rejects_empty():
    with pytest.raises(OddsSnapshotValidationError):
        build_odds_snapshot(
            "the_odds_api", "draftkings", "WC2026_G42", "player_points", "over",
            -110, "american", "",
        )


def test_build_odds_snapshot_odds_found_at_rejects_whitespace_only():
    with pytest.raises(OddsSnapshotValidationError):
        build_odds_snapshot(
            "the_odds_api", "draftkings", "WC2026_G42", "player_points", "over",
            -110, "american", "   ",
        )


# ---------------------------------------------------------------------------
# build_odds_snapshot — line validation
# ---------------------------------------------------------------------------

def test_build_odds_snapshot_line_none():
    result = build_odds_snapshot(
        "the_odds_api", "draftkings", "WC2026_G42", "player_points", "over",
        -110, "american", "2026-06-29T10:00:00Z",
    )
    assert result["line"] is None


def test_build_odds_snapshot_line_float():
    result = build_odds_snapshot(
        "the_odds_api", "draftkings", "WC2026_G42", "player_points", "over",
        -110, "american", "2026-06-29T10:00:00Z",
        line=2.5,
    )
    assert result["line"] == pytest.approx(2.5)


def test_build_odds_snapshot_line_int_returns_float():
    result = build_odds_snapshot(
        "the_odds_api", "draftkings", "WC2026_G42", "player_points", "over",
        -110, "american", "2026-06-29T10:00:00Z",
        line=2,
    )
    assert result["line"] == pytest.approx(2.0)
    assert type(result["line"]) is float


def test_build_odds_snapshot_line_negative():
    result = build_odds_snapshot(
        "the_odds_api", "draftkings", "WC2026_G42", "spread", "home",
        -110, "american", "2026-06-29T10:00:00Z",
        line=-3.5,
    )
    assert result["line"] == pytest.approx(-3.5)


def test_build_odds_snapshot_line_zero():
    result = build_odds_snapshot(
        "the_odds_api", "draftkings", "WC2026_G42", "spread", "home",
        -110, "american", "2026-06-29T10:00:00Z",
        line=0,
    )
    assert result["line"] == pytest.approx(0.0)
    assert type(result["line"]) is float


@pytest.mark.parametrize("value", [True, False])
def test_build_odds_snapshot_line_rejects_bool(value):
    with pytest.raises(OddsSnapshotValidationError):
        build_odds_snapshot(
            "the_odds_api", "draftkings", "WC2026_G42", "player_points", "over",
            -110, "american", "2026-06-29T10:00:00Z",
            line=value,
        )


@pytest.mark.parametrize("value", ["2.5", [2.5]])
def test_build_odds_snapshot_line_rejects_non_numeric(value):
    with pytest.raises(OddsSnapshotValidationError):
        build_odds_snapshot(
            "the_odds_api", "draftkings", "WC2026_G42", "player_points", "over",
            -110, "american", "2026-06-29T10:00:00Z",
            line=value,
        )


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_build_odds_snapshot_line_rejects_nan_and_inf(value):
    with pytest.raises(OddsSnapshotValidationError):
        build_odds_snapshot(
            "the_odds_api", "draftkings", "WC2026_G42", "player_points", "over",
            -110, "american", "2026-06-29T10:00:00Z",
            line=value,
        )


# ---------------------------------------------------------------------------
# build_odds_snapshot — source validation
# ---------------------------------------------------------------------------

def test_build_odds_snapshot_source_none():
    result = build_odds_snapshot(
        "the_odds_api", "draftkings", "WC2026_G42", "player_points", "over",
        -110, "american", "2026-06-29T10:00:00Z",
    )
    assert result["source"] is None


def test_build_odds_snapshot_source_valid_string():
    result = build_odds_snapshot(
        "the_odds_api", "draftkings", "WC2026_G42", "player_points", "over",
        -110, "american", "2026-06-29T10:00:00Z",
        source="api_pull",
    )
    assert result["source"] == "api_pull"


def test_build_odds_snapshot_source_strips_whitespace():
    result = build_odds_snapshot(
        "the_odds_api", "draftkings", "WC2026_G42", "player_points", "over",
        -110, "american", "2026-06-29T10:00:00Z",
        source="  api_pull  ",
    )
    assert result["source"] == "api_pull"


def test_build_odds_snapshot_source_preserves_case():
    result = build_odds_snapshot(
        "the_odds_api", "draftkings", "WC2026_G42", "player_points", "over",
        -110, "american", "2026-06-29T10:00:00Z",
        source="API_Pull",
    )
    assert result["source"] == "API_Pull"


def test_build_odds_snapshot_source_rejects_empty():
    with pytest.raises(OddsSnapshotValidationError):
        build_odds_snapshot(
            "the_odds_api", "draftkings", "WC2026_G42", "player_points", "over",
            -110, "american", "2026-06-29T10:00:00Z",
            source="",
        )


def test_build_odds_snapshot_source_rejects_whitespace_only():
    with pytest.raises(OddsSnapshotValidationError):
        build_odds_snapshot(
            "the_odds_api", "draftkings", "WC2026_G42", "player_points", "over",
            -110, "american", "2026-06-29T10:00:00Z",
            source="   ",
        )


def test_build_odds_snapshot_source_rejects_non_string():
    with pytest.raises(OddsSnapshotValidationError):
        build_odds_snapshot(
            "the_odds_api", "draftkings", "WC2026_G42", "player_points", "over",
            -110, "american", "2026-06-29T10:00:00Z",
            source=42,
        )


# ---------------------------------------------------------------------------
# build_odds_snapshot — metadata validation
# ---------------------------------------------------------------------------

def test_build_odds_snapshot_metadata_none_returns_empty_dict():
    result = build_odds_snapshot(
        "the_odds_api", "draftkings", "WC2026_G42", "player_points", "over",
        -110, "american", "2026-06-29T10:00:00Z",
    )
    assert result["metadata"] == {}
    assert type(result["metadata"]) is dict


def test_build_odds_snapshot_metadata_passed_dict():
    result = build_odds_snapshot(
        "the_odds_api", "draftkings", "WC2026_G42", "player_points", "over",
        -110, "american", "2026-06-29T10:00:00Z",
        metadata={"batch_id": "b001"},
    )
    assert result["metadata"] == {"batch_id": "b001"}


def test_build_odds_snapshot_metadata_is_plain_dict():
    result = build_odds_snapshot(
        "the_odds_api", "draftkings", "WC2026_G42", "player_points", "over",
        -110, "american", "2026-06-29T10:00:00Z",
        metadata={"batch_id": "b001"},
    )
    assert type(result["metadata"]) is dict


def test_build_odds_snapshot_metadata_mutation_isolation():
    caller_meta = {"batch_id": "b001"}
    result = build_odds_snapshot(
        "the_odds_api", "draftkings", "WC2026_G42", "player_points", "over",
        -110, "american", "2026-06-29T10:00:00Z",
        metadata=caller_meta,
    )
    result["metadata"]["extra"] = "injected"
    assert "extra" not in caller_meta


def test_build_odds_snapshot_metadata_rejects_non_dict():
    with pytest.raises(OddsSnapshotValidationError):
        build_odds_snapshot(
            "the_odds_api", "draftkings", "WC2026_G42", "player_points", "over",
            -110, "american", "2026-06-29T10:00:00Z",
            metadata=["batch_id"],
        )


def test_build_odds_snapshot_metadata_rejects_string():
    with pytest.raises(OddsSnapshotValidationError):
        build_odds_snapshot(
            "the_odds_api", "draftkings", "WC2026_G42", "player_points", "over",
            -110, "american", "2026-06-29T10:00:00Z",
            metadata="batch_id",
        )


# ---------------------------------------------------------------------------
# build_odds_snapshot — normalization applied in output
# ---------------------------------------------------------------------------

def test_build_odds_snapshot_provider_normalized_in_output():
    result = build_odds_snapshot(
        "  THE-ODDS-API  ", "draftkings", "WC2026_G42", "player_points", "over",
        -110, "american", "2026-06-29T10:00:00Z",
    )
    assert result["provider"] == "the_odds_api"


def test_build_odds_snapshot_sportsbook_normalized_in_output():
    result = build_odds_snapshot(
        "the_odds_api", "Draft Kings", "WC2026_G42", "player_points", "over",
        -110, "american", "2026-06-29T10:00:00Z",
    )
    assert result["sportsbook"] == "draft_kings"


def test_build_odds_snapshot_market_type_normalized_in_output():
    result = build_odds_snapshot(
        "the_odds_api", "draftkings", "WC2026_G42", "Player-Points", "over",
        -110, "american", "2026-06-29T10:00:00Z",
    )
    assert result["market_type"] == "player_points"


def test_build_odds_snapshot_selection_normalized_in_output():
    result = build_odds_snapshot(
        "the_odds_api", "draftkings", "WC2026_G42", "player_points", "  OVER  ",
        -110, "american", "2026-06-29T10:00:00Z",
    )
    assert result["selection"] == "over"


def test_build_odds_snapshot_event_id_not_lowercased_in_output():
    result = build_odds_snapshot(
        "the_odds_api", "draftkings", "WC2026_G42", "player_points", "over",
        -110, "american", "2026-06-29T10:00:00Z",
    )
    assert result["event_id"] == "WC2026_G42"


# ---------------------------------------------------------------------------
# build_odds_snapshot — operation order
# ---------------------------------------------------------------------------

def test_build_odds_snapshot_bad_provider_raises_before_odds_format_check():
    with pytest.raises(OddsSnapshotValidationError):
        build_odds_snapshot(
            None, "draftkings", "WC2026_G42", "player_points", "over",
            -110, "fractional", "2026-06-29T10:00:00Z",
        )


def test_build_odds_snapshot_bad_odds_format_raises_before_odds_check():
    with pytest.raises(OddsSnapshotValidationError):
        build_odds_snapshot(
            "the_odds_api", "draftkings", "WC2026_G42", "player_points", "over",
            0, "fractional", "2026-06-29T10:00:00Z",
        )


def test_build_odds_snapshot_bad_line_raises_before_odds_format_check():
    with pytest.raises(OddsSnapshotValidationError):
        build_odds_snapshot(
            "the_odds_api", "draftkings", "WC2026_G42", "player_points", "over",
            -110, "fractional", "2026-06-29T10:00:00Z",
            line=True,
        )


# ---------------------------------------------------------------------------
# banned imports
# ---------------------------------------------------------------------------

def test_odds_snapshot_has_no_banned_imports():
    import ast
    import pathlib
    src = pathlib.Path(__file__).resolve().parents[1] / "src" / "odds_snapshot.py"
    tree = ast.parse(src.read_text())
    banned = {
        "sqlite3", "database", "json", "subprocess", "pathlib",
        "odds", "ev", "edge", "candidate_evaluation", "backtest_review",
        "review_taxonomy", "review_notes", "prop_candidate",
    }
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imported.add(node.module.split(".")[0])
    assert imported.isdisjoint(banned), f"Banned imports found: {imported & banned}"
