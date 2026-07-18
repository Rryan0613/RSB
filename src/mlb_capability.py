from market_capability import build_market_capability, build_sport_market_profile

MLB_SPORT = "baseball"
MLB_LEAGUE = "mlb"

_OVER_UNDER_SELECTION_VALUES = ["over", "under"]
_TEAM_SELECTION_VALUES = ["home", "away"]

_GAME_MARKETS = (
    {
        "market_type": "moneyline",
        "selection_type": "team",
        "requires_line": False,
        "allows_line": False,
        "line_value_type": None,
        "supported_selection_values": _TEAM_SELECTION_VALUES,
    },
    {
        "market_type": "run_line",
        "selection_type": "team",
        "requires_line": True,
        "allows_line": True,
        "line_value_type": "float",
        "supported_selection_values": _TEAM_SELECTION_VALUES,
    },
    {
        "market_type": "total_runs",
        "selection_type": "over_under",
        "requires_line": True,
        "allows_line": True,
        "line_value_type": "float",
        "supported_selection_values": _OVER_UNDER_SELECTION_VALUES,
    },
    {
        "market_type": "team_total_runs",
        "selection_type": "over_under",
        "requires_line": True,
        "allows_line": True,
        "line_value_type": "float",
        "supported_selection_values": _OVER_UNDER_SELECTION_VALUES,
    },
)

_BATTER_MARKETS = (
    "player_hits",
    "player_total_bases",
    "player_home_runs",
    "player_rbis",
    "player_runs",
    "player_stolen_bases",
)

_PITCHER_MARKETS = (
    "pitcher_strikeouts",
    "pitcher_outs_recorded",
    "pitcher_hits_allowed",
    "pitcher_walks_allowed",
    "pitcher_earned_runs_allowed",
)


def _required_fields(*, requires_player, requires_team, requires_opponent, requires_line):
    fields = []
    if requires_player:
        fields.append("player")
    if requires_team:
        fields.append("team")
    if requires_opponent:
        fields.append("opponent")
    if requires_line:
        fields.append("line")
    return fields


def _build_game_market(spec) -> dict:
    requires_line = spec["requires_line"]
    return build_market_capability(
        sport=MLB_SPORT,
        league=MLB_LEAGUE,
        market_type=spec["market_type"],
        selection_type=spec["selection_type"],
        requires_line=requires_line,
        allows_line=spec["allows_line"],
        line_value_type=spec["line_value_type"],
        requires_player=False,
        requires_team=True,
        requires_opponent=True,
        requires_starting_status=False,
        start_required_supported=False,
        participation_required_supported=False,
        void_condition_supported=False,
        settlement_rule_required=True,
        supported_selection_values=spec["supported_selection_values"],
        required_fields=_required_fields(
            requires_player=False,
            requires_team=True,
            requires_opponent=True,
            requires_line=requires_line,
        ),
        optional_fields=[],
        metadata={},
    )


def _build_batter_market(market_type: str) -> dict:
    return build_market_capability(
        sport=MLB_SPORT,
        league=MLB_LEAGUE,
        market_type=market_type,
        selection_type="over_under",
        requires_line=True,
        allows_line=True,
        line_value_type="float",
        requires_player=True,
        requires_team=True,
        requires_opponent=True,
        requires_starting_status=False,
        start_required_supported=False,
        participation_required_supported=True,
        void_condition_supported=True,
        settlement_rule_required=True,
        supported_selection_values=_OVER_UNDER_SELECTION_VALUES,
        required_fields=_required_fields(
            requires_player=True,
            requires_team=True,
            requires_opponent=True,
            requires_line=True,
        ),
        optional_fields=[],
        metadata={},
    )


def _build_pitcher_market(market_type: str) -> dict:
    return build_market_capability(
        sport=MLB_SPORT,
        league=MLB_LEAGUE,
        market_type=market_type,
        selection_type="over_under",
        requires_line=True,
        allows_line=True,
        line_value_type="float",
        requires_player=True,
        requires_team=True,
        requires_opponent=True,
        requires_starting_status=True,
        start_required_supported=True,
        participation_required_supported=True,
        void_condition_supported=True,
        settlement_rule_required=True,
        supported_selection_values=_OVER_UNDER_SELECTION_VALUES,
        required_fields=_required_fields(
            requires_player=True,
            requires_team=True,
            requires_opponent=True,
            requires_line=True,
        ),
        optional_fields=[],
        metadata={},
    )


def build_mlb_capability_profile() -> dict:
    supported_markets = (
        [_build_game_market(spec) for spec in _GAME_MARKETS]
        + [_build_batter_market(market_type) for market_type in _BATTER_MARKETS]
        + [_build_pitcher_market(market_type) for market_type in _PITCHER_MARKETS]
    )
    return build_sport_market_profile(
        sport=MLB_SPORT,
        league=MLB_LEAGUE,
        supported_markets=supported_markets,
        metadata={"profile_type": "mlb_capability_seed"},
    )
