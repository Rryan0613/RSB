import pytest

from stage_market import (
    StageMarketValidationError,
    VALID_STAGES,
    VALID_MARKET_TYPES,
    DRAW_ALLOWED_MARKET_TYPES,
    normalize_stage,
    normalize_market_type,
    allows_draw,
    validate_stage_market,
)


# --- normalize_stage ---

def test_normalize_stage_all_canonical_values():
    canonical = ["group", "round_of_32", "round_of_16", "quarterfinal", "semifinal", "final", "league"]
    for stage in canonical:
        assert normalize_stage(stage) == stage


def test_normalize_stage_mixed_case():
    assert normalize_stage("Group") == "group"
    assert normalize_stage("Round_Of_16") == "round_of_16"
    assert normalize_stage("FINAL") == "final"


def test_normalize_stage_strips_whitespace():
    assert normalize_stage("  group  ") == "group"
    assert normalize_stage("  final  ") == "final"


def test_normalize_stage_space_separated():
    assert normalize_stage("round of 16") == "round_of_16"
    assert normalize_stage("round of 32") == "round_of_32"


def test_normalize_stage_hyphenated():
    assert normalize_stage("round-of-16") == "round_of_16"
    assert normalize_stage("round-of-32") == "round_of_32"


def test_normalize_stage_unknown_raises():
    with pytest.raises(StageMarketValidationError):
        normalize_stage("knockout")


def test_normalize_stage_empty_raises():
    with pytest.raises(StageMarketValidationError):
        normalize_stage("")


# --- normalize_market_type ---

def test_normalize_market_type_canonical_values():
    assert normalize_market_type("regulation_result") == "regulation_result"
    assert normalize_market_type("to_advance") == "to_advance"


def test_normalize_market_type_mixed_case():
    assert normalize_market_type("Regulation_Result") == "regulation_result"
    assert normalize_market_type("TO_ADVANCE") == "to_advance"


def test_normalize_market_type_strips_whitespace():
    assert normalize_market_type("  to_advance  ") == "to_advance"


def test_normalize_market_type_unknown_raises():
    with pytest.raises(StageMarketValidationError):
        normalize_market_type("moneyline")


def test_normalize_market_type_empty_raises():
    with pytest.raises(StageMarketValidationError):
        normalize_market_type("")


# --- allows_draw ---

def test_allows_draw_regulation_result_is_true():
    assert allows_draw("regulation_result") is True


def test_allows_draw_to_advance_is_false():
    assert allows_draw("to_advance") is False


def test_allows_draw_mixed_case_regulation_result():
    assert allows_draw("Regulation_Result") is True


def test_allows_draw_unknown_market_type_raises():
    with pytest.raises(StageMarketValidationError):
        allows_draw("draw_no_bet")


def test_allows_draw_is_not_stage_based():
    # regulation_result allows draw regardless of knockout stage
    assert allows_draw("regulation_result") is True
    # to_advance disallows draw regardless of stage — verified via validate_stage_market
    result_group = validate_stage_market("group", "to_advance")
    result_final = validate_stage_market("final", "to_advance")
    assert result_group["allows_draw"] is False
    assert result_final["allows_draw"] is False


# --- validate_stage_market ---

def test_validate_stage_market_returns_exactly_three_keys():
    result = validate_stage_market("group", "regulation_result")
    assert set(result.keys()) == {"stage", "market_type", "allows_draw"}


def test_validate_stage_market_group_regulation_result_allows_draw():
    result = validate_stage_market("group", "regulation_result")
    assert result["stage"] == "group"
    assert result["market_type"] == "regulation_result"
    assert result["allows_draw"] is True


def test_validate_stage_market_knockout_regulation_result_allows_draw():
    for stage in ["round_of_32", "round_of_16", "quarterfinal", "semifinal", "final"]:
        result = validate_stage_market(stage, "regulation_result")
        assert result["allows_draw"] is True, f"Expected allows_draw True for {stage} + regulation_result"


def test_validate_stage_market_to_advance_disallows_draw():
    for stage in ["round_of_32", "round_of_16", "quarterfinal", "semifinal", "final"]:
        result = validate_stage_market(stage, "to_advance")
        assert result["allows_draw"] is False, f"Expected allows_draw False for {stage} + to_advance"


def test_validate_stage_market_invalid_stage_raises():
    with pytest.raises(StageMarketValidationError):
        validate_stage_market("elimination", "regulation_result")


def test_validate_stage_market_invalid_market_type_raises():
    with pytest.raises(StageMarketValidationError):
        validate_stage_market("group", "h2h")


def test_validate_stage_market_normalizes_inputs():
    result = validate_stage_market("Round-Of-16", "Regulation_Result")
    assert result["stage"] == "round_of_16"
    assert result["market_type"] == "regulation_result"
    assert result["allows_draw"] is True


# --- banned imports ---

def test_stage_market_has_no_banned_imports():
    import ast
    import pathlib
    src = pathlib.Path(__file__).resolve().parents[1] / "src" / "stage_market.py"
    tree = ast.parse(src.read_text())
    banned = {"sqlite3", "database", "json", "subprocess", "pathlib"}
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imported.add(node.module.split(".")[0])
    assert imported.isdisjoint(banned), f"Banned imports found: {imported & banned}"
