import pytest

from review_taxonomy import ReviewTaxonomyValidationError
from review_notes import (
    ReviewNoteValidationError,
    build_review_note,
)


# --- return shape ---

def test_build_review_note_returns_exactly_five_keys():
    result = build_review_note("variance", "low", "strong", "Some summary")
    assert set(result.keys()) == {"review_category", "severity", "data_quality", "summary", "evidence"}


def test_build_review_note_canonical_inputs():
    result = build_review_note("variance", "low", "strong", "Sample summary")
    assert result["review_category"] == "variance"
    assert result["severity"] == "low"
    assert result["data_quality"] == "strong"
    assert result["summary"] == "Sample summary"
    assert result["evidence"] == []


def test_build_review_note_return_is_plain_dict():
    result = build_review_note("variance", "low", "strong", "Sample summary")
    assert type(result) is dict


# --- taxonomy normalization ---

def test_build_review_note_normalizes_taxonomy_inputs():
    result = build_review_note("Data-Quality", "HIGH", "Weak", "Sample summary")
    assert result["review_category"] == "data_quality"
    assert result["severity"] == "high"
    assert result["data_quality"] == "weak"


# --- taxonomy errors propagate ---

def test_build_review_note_invalid_category_raises_taxonomy_error():
    with pytest.raises(ReviewTaxonomyValidationError):
        build_review_note("match_result", "low", "strong", "Sample summary")


def test_build_review_note_invalid_severity_raises_taxonomy_error():
    with pytest.raises(ReviewTaxonomyValidationError):
        build_review_note("variance", "urgent", "strong", "Sample summary")


def test_build_review_note_invalid_data_quality_raises_taxonomy_error():
    with pytest.raises(ReviewTaxonomyValidationError):
        build_review_note("variance", "low", "excellent", "Sample summary")


def test_taxonomy_error_not_wrapped_as_review_note_error():
    try:
        build_review_note("bad_category", "low", "strong", "Sample summary")
    except ReviewNoteValidationError:
        pytest.fail("Taxonomy error must not be wrapped as ReviewNoteValidationError")
    except ReviewTaxonomyValidationError:
        pass


# --- summary validation ---

def test_build_review_note_summary_not_a_string_raises():
    with pytest.raises(ReviewNoteValidationError):
        build_review_note("variance", "low", "strong", 42)


def test_build_review_note_summary_empty_string_raises():
    with pytest.raises(ReviewNoteValidationError):
        build_review_note("variance", "low", "strong", "")


def test_build_review_note_summary_whitespace_only_raises():
    with pytest.raises(ReviewNoteValidationError):
        build_review_note("variance", "low", "strong", "   ")


def test_build_review_note_summary_is_stripped():
    result = build_review_note("variance", "low", "strong", "  valid summary  ")
    assert result["summary"] == "valid summary"


def test_build_review_note_summary_internal_whitespace_preserved():
    result = build_review_note("variance", "low", "strong", "xG better  than expected")
    assert result["summary"] == "xG better  than expected"


# --- evidence validation ---

def test_build_review_note_evidence_none_returns_empty_list():
    result = build_review_note("variance", "low", "strong", "Sample summary", evidence=None)
    assert result["evidence"] == []


def test_build_review_note_evidence_empty_list_returns_empty_list():
    result = build_review_note("variance", "low", "strong", "Sample summary", evidence=[])
    assert result["evidence"] == []


def test_build_review_note_evidence_valid_list_strips_items():
    result = build_review_note(
        "variance", "low", "strong", "Sample summary",
        evidence=["  item one  ", "item two"],
    )
    assert result["evidence"] == ["item one", "item two"]


def test_build_review_note_evidence_tuple_accepted():
    result = build_review_note("variance", "low", "strong", "Sample summary", evidence=("a", "b"))
    assert result["evidence"] == ["a", "b"]


def test_build_review_note_evidence_order_preserved():
    result = build_review_note(
        "variance", "low", "strong", "Sample summary",
        evidence=["first", "second", "third"],
    )
    assert result["evidence"] == ["first", "second", "third"]


def test_build_review_note_multiple_evidence_items():
    items = ["xG 1.8 vs 0.4", "Opponent missing two defenders", "Home pressing efficiency top 5"]
    result = build_review_note("model_calibration", "medium", "okay", "Strong attacking edge", evidence=items)
    assert result["evidence"] == items


def test_build_review_note_evidence_empty_string_item_raises():
    with pytest.raises(ReviewNoteValidationError):
        build_review_note("variance", "low", "strong", "Sample summary", evidence=[""])


def test_build_review_note_evidence_whitespace_only_item_raises():
    with pytest.raises(ReviewNoteValidationError):
        build_review_note("variance", "low", "strong", "Sample summary", evidence=["   "])


def test_build_review_note_evidence_non_string_item_raises():
    with pytest.raises(ReviewNoteValidationError):
        build_review_note("variance", "low", "strong", "Sample summary", evidence=[123])


def test_build_review_note_evidence_non_list_tuple_raises():
    with pytest.raises(ReviewNoteValidationError):
        build_review_note("variance", "low", "strong", "Sample summary", evidence="single string")


# --- exception distinctness ---

def test_review_note_validation_error_is_distinct_from_taxonomy_error():
    assert not issubclass(ReviewNoteValidationError, ReviewTaxonomyValidationError)
    assert not issubclass(ReviewTaxonomyValidationError, ReviewNoteValidationError)


# --- banned imports ---

def test_review_notes_has_no_banned_imports():
    import ast
    import pathlib
    src = pathlib.Path(__file__).resolve().parents[1] / "src" / "review_notes.py"
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
