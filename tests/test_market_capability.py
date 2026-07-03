import pytest

from market_capability import (
    MarketCapabilityValidationError,
    VALID_LINE_VALUE_TYPES,
    normalize_sport,
    normalize_league,
    normalize_market_type,
    normalize_selection_type,
    build_market_capability,
    build_sport_market_profile,
)


# ---------------------------------------------------------------------------
# MarketCapabilityValidationError
# ---------------------------------------------------------------------------

def test_market_capability_validation_error_is_value_error():
    assert issubclass(MarketCapabilityValidationError, ValueError)


# ---------------------------------------------------------------------------
# VALID_LINE_VALUE_TYPES
# ---------------------------------------------------------------------------

def test_valid_line_value_types_is_frozenset():
    assert isinstance(VALID_LINE_VALUE_TYPES, frozenset)


def test_valid_line_value_types_contents():
    assert VALID_LINE_VALUE_TYPES == frozenset({"integer", "float"})


# ---------------------------------------------------------------------------
# normalize_sport
# ---------------------------------------------------------------------------

def test_normalize_sport_basic():
    assert normalize_sport("soccer") == "soccer"


def test_normalize_sport_strips_whitespace():
    assert normalize_sport("  soccer  ") == "soccer"


def test_normalize_sport_lowercases():
    assert normalize_sport("SOCCER") == "soccer"


def test_normalize_sport_spaces_to_underscores():
    assert normalize_sport("american football") == "american_football"


def test_normalize_sport_hyphens_to_underscores():
    assert normalize_sport("american-football") == "american_football"


def test_normalize_sport_returns_str():
    assert type(normalize_sport("soccer")) is str


@pytest.mark.parametrize("value", [None, 42, ["soccer"], True, 1.5])
def test_normalize_sport_rejects_non_string(value):
    with pytest.raises(MarketCapabilityValidationError):
        normalize_sport(value)


def test_normalize_sport_rejects_empty():
    with pytest.raises(MarketCapabilityValidationError):
        normalize_sport("")


def test_normalize_sport_rejects_whitespace_only():
    with pytest.raises(MarketCapabilityValidationError):
        normalize_sport("   ")


# ---------------------------------------------------------------------------
# normalize_league
# ---------------------------------------------------------------------------

def test_normalize_league_basic():
    assert normalize_league("nba") == "nba"


def test_normalize_league_strips_whitespace():
    assert normalize_league("  nba  ") == "nba"


def test_normalize_league_lowercases():
    assert normalize_league("NBA") == "nba"


def test_normalize_league_spaces_to_underscores():
    assert normalize_league("world cup") == "world_cup"


def test_normalize_league_hyphens_to_underscores():
    assert normalize_league("world-cup") == "world_cup"


def test_normalize_league_returns_str():
    assert type(normalize_league("nba")) is str


@pytest.mark.parametrize("value", [None, 0, ["nba"], True, 1.5])
def test_normalize_league_rejects_non_string(value):
    with pytest.raises(MarketCapabilityValidationError):
        normalize_league(value)


def test_normalize_league_rejects_empty():
    with pytest.raises(MarketCapabilityValidationError):
        normalize_league("")


def test_normalize_league_rejects_whitespace_only():
    with pytest.raises(MarketCapabilityValidationError):
        normalize_league("   ")


# ---------------------------------------------------------------------------
# normalize_market_type
# ---------------------------------------------------------------------------

def test_normalize_market_type_basic():
    assert normalize_market_type("player_points") == "player_points"


def test_normalize_market_type_strips_whitespace():
    assert normalize_market_type("  player_points  ") == "player_points"


def test_normalize_market_type_lowercases():
    assert normalize_market_type("PLAYER_POINTS") == "player_points"


def test_normalize_market_type_spaces_to_underscores():
    assert normalize_market_type("player points") == "player_points"


def test_normalize_market_type_hyphens_to_underscores():
    assert normalize_market_type("player-points") == "player_points"


def test_normalize_market_type_returns_str():
    assert type(normalize_market_type("player_points")) is str


@pytest.mark.parametrize("value", [None, 0, ["player_points"], True, 1.5])
def test_normalize_market_type_rejects_non_string(value):
    with pytest.raises(MarketCapabilityValidationError):
        normalize_market_type(value)


def test_normalize_market_type_rejects_empty():
    with pytest.raises(MarketCapabilityValidationError):
        normalize_market_type("")


def test_normalize_market_type_rejects_whitespace_only():
    with pytest.raises(MarketCapabilityValidationError):
        normalize_market_type("   ")


# ---------------------------------------------------------------------------
# normalize_selection_type
# ---------------------------------------------------------------------------

def test_normalize_selection_type_basic():
    assert normalize_selection_type("over_under") == "over_under"


def test_normalize_selection_type_strips_whitespace():
    assert normalize_selection_type("  over_under  ") == "over_under"


def test_normalize_selection_type_lowercases():
    assert normalize_selection_type("OVER_UNDER") == "over_under"


def test_normalize_selection_type_spaces_to_underscores():
    assert normalize_selection_type("over under") == "over_under"


def test_normalize_selection_type_hyphens_to_underscores():
    assert normalize_selection_type("over-under") == "over_under"


def test_normalize_selection_type_returns_str():
    assert type(normalize_selection_type("over_under")) is str


@pytest.mark.parametrize("value", [None, 0, ["over_under"], True, 1.5])
def test_normalize_selection_type_rejects_non_string(value):
    with pytest.raises(MarketCapabilityValidationError):
        normalize_selection_type(value)


def test_normalize_selection_type_rejects_empty():
    with pytest.raises(MarketCapabilityValidationError):
        normalize_selection_type("")


def test_normalize_selection_type_rejects_whitespace_only():
    with pytest.raises(MarketCapabilityValidationError):
        normalize_selection_type("   ")


# ---------------------------------------------------------------------------
# build_market_capability — defaults
# ---------------------------------------------------------------------------

def _base_kwargs(**overrides):
    kwargs = dict(
        sport="soccer",
        league="world_cup",
        market_type="player_points",
        selection_type="over_under",
    )
    kwargs.update(overrides)
    return kwargs


def test_build_market_capability_defaults_shape():
    result = build_market_capability(**_base_kwargs())
    assert result == {
        "sport": "soccer",
        "league": "world_cup",
        "market_type": "player_points",
        "selection_type": "over_under",
        "requires_line": False,
        "allows_line": False,
        "line_value_type": None,
        "requires_player": False,
        "requires_team": False,
        "requires_opponent": False,
        "requires_starting_status": False,
        "start_required_supported": False,
        "participation_required_supported": False,
        "void_condition_supported": False,
        "settlement_rule_required": False,
        "supported_selection_values": None,
        "required_fields": [],
        "optional_fields": [],
        "metadata": {},
    }


def test_build_market_capability_normalizes_scalar_fields():
    result = build_market_capability(
        **_base_kwargs(
            sport="  SOCCER  ",
            league="World-Cup",
            market_type="Player Points",
            selection_type="Over-Under",
        )
    )
    assert result["sport"] == "soccer"
    assert result["league"] == "world_cup"
    assert result["market_type"] == "player_points"
    assert result["selection_type"] == "over_under"


# ---------------------------------------------------------------------------
# build_market_capability — full arguments
# ---------------------------------------------------------------------------

def test_build_market_capability_full_arguments():
    result = build_market_capability(
        **_base_kwargs(
            requires_line=True,
            allows_line=True,
            line_value_type="Float",
            requires_player=True,
            requires_team=True,
            requires_opponent=True,
            requires_starting_status=True,
            start_required_supported=True,
            participation_required_supported=True,
            void_condition_supported=True,
            settlement_rule_required=True,
            supported_selection_values=["Over", "Under"],
            required_fields=["Player ID", "line"],
            optional_fields=["team-id"],
            metadata={"note": "seed"},
        )
    )
    assert result["requires_line"] is True
    assert result["allows_line"] is True
    assert result["line_value_type"] == "float"
    assert result["requires_player"] is True
    assert result["requires_team"] is True
    assert result["requires_opponent"] is True
    assert result["requires_starting_status"] is True
    assert result["start_required_supported"] is True
    assert result["participation_required_supported"] is True
    assert result["void_condition_supported"] is True
    assert result["settlement_rule_required"] is True
    assert result["supported_selection_values"] == ["over", "under"]
    assert result["required_fields"] == ["player_id", "line"]
    assert result["optional_fields"] == ["team_id"]
    assert result["metadata"] == {"note": "seed"}


# ---------------------------------------------------------------------------
# build_market_capability — bool field validation
# ---------------------------------------------------------------------------

BOOL_FIELDS = [
    "requires_line",
    "allows_line",
    "requires_player",
    "requires_team",
    "requires_opponent",
    "requires_starting_status",
    "start_required_supported",
    "participation_required_supported",
    "void_condition_supported",
    "settlement_rule_required",
]


@pytest.mark.parametrize("field", BOOL_FIELDS)
@pytest.mark.parametrize("value", [None, "true", 1, 0, 1.0])
def test_build_market_capability_bool_fields_reject_non_bool(field, value):
    with pytest.raises(MarketCapabilityValidationError):
        build_market_capability(**_base_kwargs(**{field: value}))


# ---------------------------------------------------------------------------
# build_market_capability — line semantics
# ---------------------------------------------------------------------------

def test_build_market_capability_requires_line_without_allows_line_raises():
    with pytest.raises(MarketCapabilityValidationError):
        build_market_capability(
            **_base_kwargs(requires_line=True, allows_line=False)
        )


def test_build_market_capability_allows_line_false_with_line_value_type_raises():
    with pytest.raises(MarketCapabilityValidationError):
        build_market_capability(
            **_base_kwargs(allows_line=False, line_value_type="integer")
        )


def test_build_market_capability_allows_line_true_without_line_value_type_raises():
    with pytest.raises(MarketCapabilityValidationError):
        build_market_capability(**_base_kwargs(allows_line=True))


def test_build_market_capability_invalid_line_value_type_raises():
    with pytest.raises(MarketCapabilityValidationError):
        build_market_capability(
            **_base_kwargs(allows_line=True, line_value_type="string")
        )


@pytest.mark.parametrize("value_type", ["integer", "float", "INTEGER", " Float "])
def test_build_market_capability_valid_line_value_types_normalize(value_type):
    result = build_market_capability(
        **_base_kwargs(allows_line=True, line_value_type=value_type)
    )
    assert result["line_value_type"] in VALID_LINE_VALUE_TYPES


def test_build_market_capability_requires_line_true_allows_line_true_succeeds():
    result = build_market_capability(
        **_base_kwargs(requires_line=True, allows_line=True, line_value_type="float")
    )
    assert result["requires_line"] is True
    assert result["allows_line"] is True
    assert result["line_value_type"] == "float"


# ---------------------------------------------------------------------------
# build_market_capability — supported_selection_values
# ---------------------------------------------------------------------------

def test_build_market_capability_supported_selection_values_none_returns_none():
    result = build_market_capability(**_base_kwargs(supported_selection_values=None))
    assert result["supported_selection_values"] is None


def test_build_market_capability_supported_selection_values_normalized_list():
    result = build_market_capability(
        **_base_kwargs(supported_selection_values=["Over", "UNDER"])
    )
    assert result["supported_selection_values"] == ["over", "under"]


def test_build_market_capability_supported_selection_values_empty_list_raises():
    with pytest.raises(MarketCapabilityValidationError):
        build_market_capability(**_base_kwargs(supported_selection_values=[]))


def test_build_market_capability_supported_selection_values_duplicates_raise():
    with pytest.raises(MarketCapabilityValidationError):
        build_market_capability(
            **_base_kwargs(supported_selection_values=["over", "Over"])
        )


def test_build_market_capability_supported_selection_values_non_list_raises():
    with pytest.raises(MarketCapabilityValidationError):
        build_market_capability(**_base_kwargs(supported_selection_values="over"))


def test_build_market_capability_supported_selection_values_non_string_item_raises():
    with pytest.raises(MarketCapabilityValidationError):
        build_market_capability(**_base_kwargs(supported_selection_values=["over", 1]))


def test_build_market_capability_supported_selection_values_accepts_tuple():
    result = build_market_capability(
        **_base_kwargs(supported_selection_values=("over", "under"))
    )
    assert result["supported_selection_values"] == ["over", "under"]


# ---------------------------------------------------------------------------
# build_market_capability — required_fields / optional_fields
# ---------------------------------------------------------------------------

def test_build_market_capability_required_fields_default_empty_list():
    result = build_market_capability(**_base_kwargs())
    assert result["required_fields"] == []


def test_build_market_capability_optional_fields_default_empty_list():
    result = build_market_capability(**_base_kwargs())
    assert result["optional_fields"] == []


def test_build_market_capability_required_fields_normalizes():
    result = build_market_capability(**_base_kwargs(required_fields=["Player ID"]))
    assert result["required_fields"] == ["player_id"]


def test_build_market_capability_optional_fields_normalizes():
    result = build_market_capability(**_base_kwargs(optional_fields=["Team-ID"]))
    assert result["optional_fields"] == ["team_id"]


def test_build_market_capability_required_fields_non_list_raises():
    with pytest.raises(MarketCapabilityValidationError):
        build_market_capability(**_base_kwargs(required_fields="player_id"))


def test_build_market_capability_optional_fields_non_list_raises():
    with pytest.raises(MarketCapabilityValidationError):
        build_market_capability(**_base_kwargs(optional_fields="team_id"))


def test_build_market_capability_required_fields_duplicates_raise():
    with pytest.raises(MarketCapabilityValidationError):
        build_market_capability(
            **_base_kwargs(required_fields=["player_id", "Player-ID"])
        )


def test_build_market_capability_optional_fields_duplicates_raise():
    with pytest.raises(MarketCapabilityValidationError):
        build_market_capability(
            **_base_kwargs(optional_fields=["team_id", "Team-ID"])
        )


def test_build_market_capability_required_optional_overlap_raises():
    with pytest.raises(MarketCapabilityValidationError):
        build_market_capability(
            **_base_kwargs(
                required_fields=["player_id"],
                optional_fields=["player_id"],
            )
        )


def test_build_market_capability_required_fields_empty_list_allowed():
    result = build_market_capability(**_base_kwargs(required_fields=[]))
    assert result["required_fields"] == []


def test_build_market_capability_optional_fields_empty_list_allowed():
    result = build_market_capability(**_base_kwargs(optional_fields=[]))
    assert result["optional_fields"] == []


# ---------------------------------------------------------------------------
# build_market_capability — metadata
# ---------------------------------------------------------------------------

def test_build_market_capability_metadata_defaults_to_empty_dict():
    result = build_market_capability(**_base_kwargs())
    assert result["metadata"] == {}


def test_build_market_capability_metadata_non_dict_raises():
    with pytest.raises(MarketCapabilityValidationError):
        build_market_capability(**_base_kwargs(metadata=["not", "a", "dict"]))


def test_build_market_capability_metadata_is_shallow_copied():
    source_metadata = {"note": "seed"}
    result = build_market_capability(**_base_kwargs(metadata=source_metadata))
    source_metadata["note"] = "mutated"
    assert result["metadata"] == {"note": "seed"}


# ---------------------------------------------------------------------------
# build_sport_market_profile — supported_markets shape
# ---------------------------------------------------------------------------

def _market(**overrides):
    return build_market_capability(**_base_kwargs(**overrides))


def test_build_sport_market_profile_none_supported_markets_returns_empty():
    result = build_sport_market_profile(sport="soccer", league="world_cup")
    assert result == {
        "sport": "soccer",
        "league": "world_cup",
        "supported_markets": [],
        "market_count": 0,
        "metadata": {},
    }


def test_build_sport_market_profile_empty_list_supported_markets():
    result = build_sport_market_profile(
        sport="soccer", league="world_cup", supported_markets=[]
    )
    assert result["supported_markets"] == []
    assert result["market_count"] == 0


def test_build_sport_market_profile_non_list_supported_markets_raises():
    with pytest.raises(MarketCapabilityValidationError):
        build_sport_market_profile(
            sport="soccer", league="world_cup", supported_markets="not_a_list"
        )


def test_build_sport_market_profile_non_dict_supported_market_raises_with_index():
    with pytest.raises(MarketCapabilityValidationError, match=r"\[0\]"):
        build_sport_market_profile(
            sport="soccer", league="world_cup", supported_markets=["not_a_dict"]
        )


def test_build_sport_market_profile_missing_required_key_raises():
    incomplete = _market()
    del incomplete["metadata"]
    with pytest.raises(MarketCapabilityValidationError):
        build_sport_market_profile(
            sport="soccer", league="world_cup", supported_markets=[incomplete]
        )


def test_build_sport_market_profile_extra_supported_market_key_raises():
    market = _market()
    market["unexpected"] = "value"
    with pytest.raises(MarketCapabilityValidationError):
        build_sport_market_profile(
            sport="soccer",
            league="world_cup",
            supported_markets=[market],
        )


def test_build_sport_market_profile_mismatched_sport_raises():
    mismatched = _market(sport="basketball")
    with pytest.raises(MarketCapabilityValidationError):
        build_sport_market_profile(
            sport="soccer", league="world_cup", supported_markets=[mismatched]
        )


def test_build_sport_market_profile_mismatched_league_raises():
    mismatched = _market(league="nba")
    with pytest.raises(MarketCapabilityValidationError):
        build_sport_market_profile(
            sport="soccer", league="world_cup", supported_markets=[mismatched]
        )


def test_build_sport_market_profile_duplicate_market_selection_pair_raises():
    market_one = _market(market_type="player_points", selection_type="over_under")
    market_two = _market(market_type="player_points", selection_type="over_under")
    with pytest.raises(MarketCapabilityValidationError):
        build_sport_market_profile(
            sport="soccer",
            league="world_cup",
            supported_markets=[market_one, market_two],
        )


def test_build_sport_market_profile_allows_same_market_type_different_selection_type():
    market_one = _market(market_type="player_points", selection_type="over_under")
    market_two = _market(market_type="player_points", selection_type="yes_no")
    result = build_sport_market_profile(
        sport="soccer",
        league="world_cup",
        supported_markets=[market_one, market_two],
    )
    assert result["market_count"] == 2


def test_build_sport_market_profile_multiple_entries_success():
    market_one = _market(market_type="player_points", selection_type="over_under")
    market_two = _market(market_type="moneyline", selection_type="team_result")
    result = build_sport_market_profile(
        sport="soccer",
        league="world_cup",
        supported_markets=[market_one, market_two],
    )
    assert result["market_count"] == 2
    assert len(result["supported_markets"]) == 2


def test_build_sport_market_profile_supported_markets_are_shallow_copied():
    market_one = _market()
    result = build_sport_market_profile(
        sport="soccer", league="world_cup", supported_markets=[market_one]
    )
    market_one["market_type"] = "mutated"
    assert result["supported_markets"][0]["market_type"] == "player_points"


def test_build_sport_market_profile_supported_markets_accepts_tuple():
    market_one = _market()
    result = build_sport_market_profile(
        sport="soccer", league="world_cup", supported_markets=(market_one,)
    )
    assert result["market_count"] == 1


# ---------------------------------------------------------------------------
# build_sport_market_profile — metadata
# ---------------------------------------------------------------------------

def test_build_sport_market_profile_metadata_defaults_to_empty_dict():
    result = build_sport_market_profile(sport="soccer", league="world_cup")
    assert result["metadata"] == {}


def test_build_sport_market_profile_metadata_non_dict_raises():
    with pytest.raises(MarketCapabilityValidationError):
        build_sport_market_profile(
            sport="soccer", league="world_cup", metadata=["not", "a", "dict"]
        )


def test_build_sport_market_profile_metadata_is_shallow_copied():
    source_metadata = {"note": "seed"}
    result = build_sport_market_profile(
        sport="soccer", league="world_cup", metadata=source_metadata
    )
    source_metadata["note"] = "mutated"
    assert result["metadata"] == {"note": "seed"}


def test_build_sport_market_profile_normalizes_sport_and_league():
    result = build_sport_market_profile(sport="  SOCCER  ", league="World-Cup")
    assert result["sport"] == "soccer"
    assert result["league"] == "world_cup"


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------

def test_build_market_capability_is_deterministic():
    kwargs = _base_kwargs(
        requires_line=True,
        allows_line=True,
        line_value_type="float",
        supported_selection_values=["over", "under"],
        required_fields=["player_id"],
        optional_fields=["team_id"],
        metadata={"note": "seed"},
    )
    result_one = build_market_capability(**kwargs)
    result_two = build_market_capability(**kwargs)
    assert result_one == result_two


def test_build_sport_market_profile_is_deterministic():
    market_one = _market(market_type="player_points", selection_type="over_under")
    market_two = _market(market_type="moneyline", selection_type="team_result")
    kwargs = dict(
        sport="soccer",
        league="world_cup",
        supported_markets=[market_one, market_two],
        metadata={"note": "seed"},
    )
    result_one = build_sport_market_profile(**kwargs)
    result_two = build_sport_market_profile(**kwargs)
    assert result_one == result_two
