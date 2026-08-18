"""Pure MLB plate-appearance probability primitives.

Turns v0.3.2's leakage-safe prior batter/pitcher/league outcome counts into a
single coherent categorical probability distribution over RATE_CATEGORIES.

No filesystem, database, network, or non-stdlib dependency. See
docs/MLB_PLATE_APPEARANCE_PROBABILITY_CONTRACT.md.
"""

import math

from .plate_appearance import PLATE_APPEARANCE_SCHEMA_VERSION, RATE_CATEGORIES
from .plate_appearance_rates import RATE_ENRICHED_FIELD_ORDER


class PlateAppearanceProbabilityValidationError(ValueError):
    pass


class PitcherAttributionUnavailableError(PlateAppearanceProbabilityValidationError):
    """A pitcher-dependent method was requested for a PA whose pitcher-of-record
    attribution is ambiguous.

    Subclasses the module error so a broad `except` still catches it, while
    callers that want to skip such records rather than abort can catch this
    specific type.
    """


PLATE_APPEARANCE_PROBABILITY_SCHEMA_VERSION = "1"

# Versions the hyperparameter set itself, separately from the record shape.
# Two artifacts both labelled "matchup_combination" must never be silently
# incomparable because they were generated under different prior strengths.
PROBABILITY_MODEL_CONFIG_VERSION = "1"

# Provisional v0.3.3 baseline hyperparameters. These are NOT empirically
# optimized stabilization estimates — they are deterministic starting values
# subject to comparative walk-forward evaluation in v0.3.4. The league strength
# exists primarily to guarantee strict positivity (see
# build_league_baseline_distribution), not to assert that one pseudo-plate-
# appearance is baseball-optimal.
DEFAULT_LEAGUE_PRIOR_STRENGTH = 1.0
DEFAULT_BATTER_PRIOR_STRENGTH = 100.0
DEFAULT_PITCHER_PRIOR_STRENGTH = 100.0

MODEL_METHODS = (
    "league_only",
    "batter_shrinkage",
    "pitcher_shrinkage",
    "matchup_combination",
)

# Methods that consume prior_pitcher_* state, and are therefore unavailable
# when pitcher-of-record attribution is ambiguous (see
# _require_pitcher_attribution).
PITCHER_DEPENDENT_METHODS = (
    "pitcher_shrinkage",
    "matchup_combination",
)

_BATTER_DEPENDENT_METHODS = (
    "batter_shrinkage",
    "matchup_combination",
)

PROBABILITY_SUM_TOLERANCE = 1e-9

PROBABILITY_FIELD_ORDER = (
    "rsb_pa_id",
    "source_game_id",
    "at_bat_number",
    "batter_id",
    "pitcher_id",
    "pitcher_rate_eligible",
    "model_method",
    "model_config_version",
    "probabilities",
    "league_pa_count_used",
    "batter_pa_count_used",
    "pitcher_pa_count_used",
    "league_prior_strength",
    "batter_prior_strength",
    "pitcher_prior_strength",
    "normalized_pa_probability_schema_version",
)

# The leakage boundary. Every field the probability math is allowed to see.
# Internal: this is implementation machinery, not package-root API.
#
# Deliberately excluded: pa_status, pa_outcome_detailed, pa_outcome_category,
# and terminal_pa_event_raw — a predictor must never condition on how the PA
# actually resolved, nor on whether it resolved at all. Also excluded are the
# prior_*_outcome_rates fields: this module re-derives smoothed rates from the
# raw counts, so the precomputed unsmoothed rates (which carry None for
# no-history entities) are not needed and are kept outside the boundary.
_PRIOR_CONTEXT_FIELD_ORDER = (
    "rsb_pa_id",
    "source_game_id",
    "at_bat_number",
    "batter_id",
    "pitcher_id",
    "pitcher_rate_eligible",
    "prior_batter_pa_count",
    "prior_batter_outcome_counts",
    "prior_pitcher_pa_count",
    "prior_pitcher_outcome_counts",
    "prior_league_pa_count",
    "prior_league_outcome_counts",
)

_EXPECTED_INPUT_FIELDS = frozenset(RATE_ENRICHED_FIELD_ORDER)
_EXPECTED_PRIOR_CONTEXT_FIELDS = frozenset(_PRIOR_CONTEXT_FIELD_ORDER)

assert _EXPECTED_PRIOR_CONTEXT_FIELDS <= _EXPECTED_INPUT_FIELDS
assert set(PITCHER_DEPENDENT_METHODS) <= set(MODEL_METHODS)
assert set(_BATTER_DEPENDENT_METHODS) <= set(MODEL_METHODS)


def _is_number(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _validate_prior_strength(value, name: str) -> float:
    if not _is_number(value):
        raise PlateAppearanceProbabilityValidationError(
            f"{name} must be numeric, got {type(value).__name__!r}"
        )
    number = float(value)
    if not math.isfinite(number):
        raise PlateAppearanceProbabilityValidationError(
            f"{name} must be finite, got {value!r}"
        )
    if number <= 0.0:
        raise PlateAppearanceProbabilityValidationError(
            f"{name} must be strictly positive, got {value!r}"
        )
    return number


def _validate_pa_count(value, name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise PlateAppearanceProbabilityValidationError(
            f"{name} must be an int, got {type(value).__name__!r}"
        )
    if value < 0:
        raise PlateAppearanceProbabilityValidationError(
            f"{name} must be non-negative, got {value!r}"
        )
    return value


def _validate_outcome_counts(counts, pa_count, name: str) -> dict:
    if not isinstance(counts, dict):
        raise PlateAppearanceProbabilityValidationError(
            f"{name} must be a dict, got {type(counts).__name__!r}"
        )
    actual = set(counts)
    expected = set(RATE_CATEGORIES)
    if actual != expected:
        missing = expected - actual
        extra = actual - expected
        raise PlateAppearanceProbabilityValidationError(
            f"{name} must be keyed by exactly RATE_CATEGORIES; "
            f"missing={sorted(missing)} extra={sorted(extra)}"
        )

    _validate_pa_count(pa_count, f"{name} pa_count")

    total = 0
    for category in RATE_CATEGORIES:
        value = counts[category]
        if not isinstance(value, int) or isinstance(value, bool):
            raise PlateAppearanceProbabilityValidationError(
                f"{name}[{category!r}] must be an int, got {type(value).__name__!r}"
            )
        if value < 0:
            raise PlateAppearanceProbabilityValidationError(
                f"{name}[{category!r}] must be non-negative, got {value!r}"
            )
        total += value

    # v0.3.2 increments pa_count and counts[category] together on every
    # completed PA, so a disagreement here means the record was not produced
    # by attach_prior_outcome_rates and must not be modeled.
    if total != pa_count:
        raise PlateAppearanceProbabilityValidationError(
            f"{name} counts sum to {total} but pa_count is {pa_count}"
        )
    return counts


def _validate_distribution(distribution, name: str) -> dict:
    if not isinstance(distribution, dict):
        raise PlateAppearanceProbabilityValidationError(
            f"{name} must be a dict, got {type(distribution).__name__!r}"
        )
    actual = set(distribution)
    expected = set(RATE_CATEGORIES)
    if actual != expected:
        missing = expected - actual
        extra = actual - expected
        raise PlateAppearanceProbabilityValidationError(
            f"{name} must be keyed by exactly RATE_CATEGORIES; "
            f"missing={sorted(missing)} extra={sorted(extra)}"
        )

    values = []
    for category in RATE_CATEGORIES:
        value = distribution[category]
        if not _is_number(value):
            raise PlateAppearanceProbabilityValidationError(
                f"{name}[{category!r}] must be numeric, got {type(value).__name__!r}"
            )
        number = float(value)
        if not math.isfinite(number):
            raise PlateAppearanceProbabilityValidationError(
                f"{name}[{category!r}] must be finite, got {value!r}"
            )
        # Strict positivity is guaranteed by construction whenever the league
        # prior strength is positive; asserting it turns any future positivity
        # regression into an immediate failure.
        if number <= 0.0:
            raise PlateAppearanceProbabilityValidationError(
                f"{name}[{category!r}] must be strictly positive, got {value!r}"
            )
        if number > 1.0:
            raise PlateAppearanceProbabilityValidationError(
                f"{name}[{category!r}] must be <= 1, got {value!r}"
            )
        values.append(number)

    total = math.fsum(values)
    if abs(total - 1.0) > PROBABILITY_SUM_TOLERANCE:
        raise PlateAppearanceProbabilityValidationError(
            f"{name} must sum to 1 within {PROBABILITY_SUM_TOLERANCE}, got {total!r}"
        )
    return distribution


def _validate_prior_context(prior_context) -> dict:
    if not isinstance(prior_context, dict):
        raise PlateAppearanceProbabilityValidationError(
            f"prior_context must be a dict, got {type(prior_context).__name__!r}"
        )
    actual = set(prior_context)
    if actual != _EXPECTED_PRIOR_CONTEXT_FIELDS:
        missing = _EXPECTED_PRIOR_CONTEXT_FIELDS - actual
        extra = actual - _EXPECTED_PRIOR_CONTEXT_FIELDS
        raise PlateAppearanceProbabilityValidationError(
            f"prior_context does not match the prior-context field set; "
            f"missing={sorted(missing)} extra={sorted(extra)}"
        )
    if not isinstance(prior_context["pitcher_rate_eligible"], bool):
        raise PlateAppearanceProbabilityValidationError(
            "prior_context pitcher_rate_eligible must be a bool, got "
            f"{type(prior_context['pitcher_rate_eligible']).__name__!r}"
        )

    _validate_outcome_counts(
        prior_context["prior_batter_outcome_counts"],
        prior_context["prior_batter_pa_count"],
        "prior_batter_outcome_counts",
    )
    _validate_outcome_counts(
        prior_context["prior_pitcher_outcome_counts"],
        prior_context["prior_pitcher_pa_count"],
        "prior_pitcher_outcome_counts",
    )
    _validate_outcome_counts(
        prior_context["prior_league_outcome_counts"],
        prior_context["prior_league_pa_count"],
        "prior_league_outcome_counts",
    )
    return prior_context


def _extract_prior_context(pa_record) -> dict:
    """Strip a rate-enriched PA record down to the leakage-safe modeling inputs.

    This is the module's leakage boundary: every probability function operates
    on the result of this call, never on the original record, so no realized
    outcome or completion-status field can reach the math. See
    _PRIOR_CONTEXT_FIELD_ORDER.
    """
    if not isinstance(pa_record, dict):
        raise PlateAppearanceProbabilityValidationError(
            f"pa_record must be a dict, got {type(pa_record).__name__!r}"
        )
    actual = set(pa_record)
    if actual != _EXPECTED_INPUT_FIELDS:
        missing = _EXPECTED_INPUT_FIELDS - actual
        extra = actual - _EXPECTED_INPUT_FIELDS
        raise PlateAppearanceProbabilityValidationError(
            f"pa_record does not match the rate-enriched plate appearance "
            f"contract; missing={sorted(missing)} extra={sorted(extra)}"
        )

    # Upstream schema guard. A record shaped like v0.3.2 but declaring an
    # incompatible PA schema version must not be modeled, so this is checked
    # before the field is stripped away. Schema metadata is not a realized PA
    # outcome, so consulting it does not weaken the leakage boundary.
    if pa_record["normalized_pa_schema_version"] != PLATE_APPEARANCE_SCHEMA_VERSION:
        raise PlateAppearanceProbabilityValidationError(
            f"pa_record normalized_pa_schema_version must be "
            f"{PLATE_APPEARANCE_SCHEMA_VERSION!r}, got "
            f"{pa_record['normalized_pa_schema_version']!r}"
        )

    context = {field: pa_record[field] for field in _PRIOR_CONTEXT_FIELD_ORDER}
    return _validate_prior_context(context)


def _require_pitcher_attribution(prior_context) -> None:
    if not prior_context["pitcher_rate_eligible"]:
        raise PitcherAttributionUnavailableError(
            f"plate appearance {prior_context['rsb_pa_id']!r} has ambiguous "
            "pitcher-of-record attribution (pitcher_rate_eligible=False); its "
            "prior_pitcher_* state describes the terminal pitcher, who was not "
            "known before the plate appearance began. Pitcher-dependent methods "
            "are unavailable for this record."
        )


def build_league_baseline_distribution(
    prior_context,
    *,
    league_prior_strength=DEFAULT_LEAGUE_PRIOR_STRENGTH,
) -> dict:
    """League outcome distribution, smoothed toward uniform.

        L[k] = (c_L[k] + alpha/K) / (n_L + alpha)

    `alpha` is the *total* prior strength, spread uniformly across the K
    categories. Because alpha > 0, every category keeps strictly positive
    support even when it has never been observed, which is what makes the
    downstream shrinkage and matchup steps well defined without any epsilon
    clamping. At n_L == 0 this reduces algebraically to the uniform
    distribution, so no separate no-history fallback branch is required.
    """
    context = _validate_prior_context(prior_context)
    alpha = _validate_prior_strength(league_prior_strength, "league_prior_strength")

    counts = context["prior_league_outcome_counts"]
    pa_count = context["prior_league_pa_count"]

    uniform_mass = alpha / len(RATE_CATEGORIES)
    denominator = pa_count + alpha
    return {
        category: (counts[category] + uniform_mass) / denominator
        for category in RATE_CATEGORIES
    }


def shrink_entity_distribution(
    entity_counts,
    entity_pa_count,
    league_distribution,
    prior_strength,
) -> dict:
    """Dirichlet-multinomial posterior mean for one entity.

        p[k] = (c[k] + kappa * L[k]) / (n + kappa)

    Entity-agnostic on purpose — batters and pitchers share this one
    implementation. Normalization is automatic rather than imposed: the
    numerators sum to n + kappa because the counts sum to n and the league
    distribution sums to 1. At n == 0 the result is exactly the league
    distribution, so unseen entities need no special case; as n grows the
    result approaches the raw empirical rate.
    """
    _validate_outcome_counts(entity_counts, entity_pa_count, "entity_counts")
    _validate_distribution(league_distribution, "league_distribution")
    kappa = _validate_prior_strength(prior_strength, "prior_strength")

    denominator = entity_pa_count + kappa
    return {
        category: (entity_counts[category] + kappa * league_distribution[category])
        / denominator
        for category in RATE_CATEGORIES
    }


def build_batter_shrinkage_distribution(
    prior_context,
    *,
    league_prior_strength=DEFAULT_LEAGUE_PRIOR_STRENGTH,
    batter_prior_strength=DEFAULT_BATTER_PRIOR_STRENGTH,
) -> dict:
    """Batter's prior outcome history, shrunk toward the league baseline."""
    context = _validate_prior_context(prior_context)
    league = build_league_baseline_distribution(
        context, league_prior_strength=league_prior_strength
    )
    return shrink_entity_distribution(
        context["prior_batter_outcome_counts"],
        context["prior_batter_pa_count"],
        league,
        batter_prior_strength,
    )


def build_pitcher_shrinkage_distribution(
    prior_context,
    *,
    league_prior_strength=DEFAULT_LEAGUE_PRIOR_STRENGTH,
    pitcher_prior_strength=DEFAULT_PITCHER_PRIOR_STRENGTH,
) -> dict:
    """Pitcher's prior outcome history, shrunk toward the league baseline.

    Raises PitcherAttributionUnavailableError when the PA's pitcher-of-record
    attribution is ambiguous.
    """
    context = _validate_prior_context(prior_context)
    _require_pitcher_attribution(context)
    league = build_league_baseline_distribution(
        context, league_prior_strength=league_prior_strength
    )
    return shrink_entity_distribution(
        context["prior_pitcher_outcome_counts"],
        context["prior_pitcher_pa_count"],
        league,
        pitcher_prior_strength,
    )


def combine_matchup_distribution(
    prior_context,
    *,
    league_prior_strength=DEFAULT_LEAGUE_PRIOR_STRENGTH,
    batter_prior_strength=DEFAULT_BATTER_PRIOR_STRENGTH,
    pitcher_prior_strength=DEFAULT_PITCHER_PRIOR_STRENGTH,
) -> dict:
    """Multiplicative relative-likelihood categorical matchup baseline.

        r[k] = b[k] * q[k] / L[k]
        P[k] = r[k] / sum_j r[j]

    Equivalent to classical log5 in the binary case. Computed in log space
    with max-subtraction for numerical stability; every input is strictly
    positive, so all logs are finite.

    This form assumes no interaction beyond the additive log-space
    contribution of each side, and can be overconfident because it compounds
    both entities' deviations from league. Upstream shrinkage damps that;
    quantifying what remains is v0.3.4 calibration work.

    Limiting behavior, exact rather than approximate: if the pitcher sits at
    the league baseline the result is the batter distribution; if the batter
    does, the result is the pitcher distribution; if both do, the result is
    the league distribution.

    Raises PitcherAttributionUnavailableError when the PA's pitcher-of-record
    attribution is ambiguous.
    """
    context = _validate_prior_context(prior_context)
    _require_pitcher_attribution(context)

    league = build_league_baseline_distribution(
        context, league_prior_strength=league_prior_strength
    )
    batter = shrink_entity_distribution(
        context["prior_batter_outcome_counts"],
        context["prior_batter_pa_count"],
        league,
        batter_prior_strength,
    )
    pitcher = shrink_entity_distribution(
        context["prior_pitcher_outcome_counts"],
        context["prior_pitcher_pa_count"],
        league,
        pitcher_prior_strength,
    )

    log_scores = [
        math.log(batter[category])
        + math.log(pitcher[category])
        - math.log(league[category])
        for category in RATE_CATEGORIES
    ]
    max_log_score = max(log_scores)
    weights = [math.exp(score - max_log_score) for score in log_scores]
    total = math.fsum(weights)
    return {
        category: weight / total
        for category, weight in zip(RATE_CATEGORIES, weights)
    }


def supported_methods_for(pa_record) -> tuple:
    """Methods that can legitimately be generated for this PA record.

    Lets callers select records up front instead of using exceptions for
    control flow. Note that pitcher eligibility is itself known only after the
    fact, so any sample selected on it is not a random sample of plate
    appearances — v0.3.4 must compare methods on the intersection of records
    all methods support.
    """
    context = _extract_prior_context(pa_record)
    if context["pitcher_rate_eligible"]:
        return MODEL_METHODS
    return tuple(
        method for method in MODEL_METHODS if method not in PITCHER_DEPENDENT_METHODS
    )


def _validate_optional_pa_count(value, name: str, *, required: bool) -> None:
    if required:
        _validate_pa_count(value, name)
    elif value is not None:
        raise PlateAppearanceProbabilityValidationError(
            f"{name} must be None for this model_method, got {value!r}"
        )


def _validate_optional_strength(value, name: str, *, required: bool) -> None:
    if required:
        _validate_prior_strength(value, name)
    elif value is not None:
        raise PlateAppearanceProbabilityValidationError(
            f"{name} must be None for this model_method, got {value!r}"
        )


def validate_pa_probability_distribution(record) -> dict:
    """Whole-record validator for a PA probability distribution.

    Returns the record unchanged when valid; never repairs or renormalizes.
    """
    if not isinstance(record, dict):
        raise PlateAppearanceProbabilityValidationError(
            f"record must be a dict, got {type(record).__name__!r}"
        )
    actual = set(record)
    expected = set(PROBABILITY_FIELD_ORDER)
    if actual != expected:
        missing = expected - actual
        extra = actual - expected
        raise PlateAppearanceProbabilityValidationError(
            f"record does not match PROBABILITY_FIELD_ORDER; "
            f"missing={sorted(missing)} extra={sorted(extra)}"
        )

    method = record["model_method"]
    if method not in MODEL_METHODS:
        raise PlateAppearanceProbabilityValidationError(
            f"model_method must be one of {list(MODEL_METHODS)}, got {method!r}"
        )
    if record["model_config_version"] != PROBABILITY_MODEL_CONFIG_VERSION:
        raise PlateAppearanceProbabilityValidationError(
            f"model_config_version must be {PROBABILITY_MODEL_CONFIG_VERSION!r}, "
            f"got {record['model_config_version']!r}"
        )
    if (
        record["normalized_pa_probability_schema_version"]
        != PLATE_APPEARANCE_PROBABILITY_SCHEMA_VERSION
    ):
        raise PlateAppearanceProbabilityValidationError(
            "normalized_pa_probability_schema_version must be "
            f"{PLATE_APPEARANCE_PROBABILITY_SCHEMA_VERSION!r}, got "
            f"{record['normalized_pa_probability_schema_version']!r}"
        )

    if not isinstance(record["pitcher_rate_eligible"], bool):
        raise PlateAppearanceProbabilityValidationError(
            "pitcher_rate_eligible must be a bool, got "
            f"{type(record['pitcher_rate_eligible']).__name__!r}"
        )
    if method in PITCHER_DEPENDENT_METHODS and not record["pitcher_rate_eligible"]:
        raise PlateAppearanceProbabilityValidationError(
            f"model_method {method!r} requires pitcher_rate_eligible to be True"
        )

    # A record for an ineligible PA must not carry the terminal pitcher's
    # identity: that pitcher was not known before the plate appearance began,
    # so embedding it would put future information into an artifact that is
    # framed as pre-PA. Eligible records have a start pitcher identical to the
    # terminal one, so the identity is legitimate there.
    if record["pitcher_rate_eligible"]:
        if record["pitcher_id"] is None:
            raise PlateAppearanceProbabilityValidationError(
                "pitcher_id must be present when pitcher_rate_eligible is True"
            )
    elif record["pitcher_id"] is not None:
        raise PlateAppearanceProbabilityValidationError(
            "pitcher_id must be None when pitcher_rate_eligible is False; the "
            "terminal pitcher was not known before the plate appearance began"
        )

    # Semantic validity only: an equivalent mapping with the same categories
    # and values is the same distribution regardless of insertion order.
    # Canonical RATE_CATEGORIES ordering is a guarantee of the builder (see
    # build_pa_probability_distribution), not a condition of validity.
    _validate_distribution(record["probabilities"], "probabilities")

    uses_batter = method in _BATTER_DEPENDENT_METHODS
    uses_pitcher = method in PITCHER_DEPENDENT_METHODS

    _validate_pa_count(record["league_pa_count_used"], "league_pa_count_used")
    _validate_optional_pa_count(
        record["batter_pa_count_used"], "batter_pa_count_used", required=uses_batter
    )
    _validate_optional_pa_count(
        record["pitcher_pa_count_used"], "pitcher_pa_count_used", required=uses_pitcher
    )

    _validate_prior_strength(record["league_prior_strength"], "league_prior_strength")
    _validate_optional_strength(
        record["batter_prior_strength"], "batter_prior_strength", required=uses_batter
    )
    _validate_optional_strength(
        record["pitcher_prior_strength"], "pitcher_prior_strength", required=uses_pitcher
    )

    return record


def build_pa_probability_distribution(
    pa_record,
    *,
    method,
    league_prior_strength=DEFAULT_LEAGUE_PRIOR_STRENGTH,
    batter_prior_strength=DEFAULT_BATTER_PRIOR_STRENGTH,
    pitcher_prior_strength=DEFAULT_PITCHER_PRIOR_STRENGTH,
) -> dict:
    """Build one validated categorical probability distribution for a PA.

    `method` is required and has no default so the most complex method can
    never be selected by accident.

    The distribution is conditional on the plate appearance completing:
    P(outcome category | PA completes). Whether a given historical PA actually
    completed is deliberately not consulted — an incomplete or truncated PA
    still has a well-defined pre-PA conditional distribution. Deciding which
    records carry a scorable target is v0.3.4 evaluation work.

    `probabilities` is always emitted in canonical RATE_CATEGORIES order, which
    keeps serialization and float summation bit-reproducible across runs.
    """
    context = _extract_prior_context(pa_record)

    if method not in MODEL_METHODS:
        raise PlateAppearanceProbabilityValidationError(
            f"method must be one of {list(MODEL_METHODS)}, got {method!r}"
        )

    alpha = _validate_prior_strength(league_prior_strength, "league_prior_strength")
    kappa_batter = _validate_prior_strength(
        batter_prior_strength, "batter_prior_strength"
    )
    kappa_pitcher = _validate_prior_strength(
        pitcher_prior_strength, "pitcher_prior_strength"
    )

    if method in PITCHER_DEPENDENT_METHODS:
        _require_pitcher_attribution(context)

    if method == "league_only":
        probabilities = build_league_baseline_distribution(
            context, league_prior_strength=alpha
        )
    elif method == "batter_shrinkage":
        probabilities = build_batter_shrinkage_distribution(
            context,
            league_prior_strength=alpha,
            batter_prior_strength=kappa_batter,
        )
    elif method == "pitcher_shrinkage":
        probabilities = build_pitcher_shrinkage_distribution(
            context,
            league_prior_strength=alpha,
            pitcher_prior_strength=kappa_pitcher,
        )
    else:
        probabilities = combine_matchup_distribution(
            context,
            league_prior_strength=alpha,
            batter_prior_strength=kappa_batter,
            pitcher_prior_strength=kappa_pitcher,
        )

    uses_batter = method in _BATTER_DEPENDENT_METHODS
    uses_pitcher = method in PITCHER_DEPENDENT_METHODS

    # Withhold the terminal pitcher's identity for ineligible PAs. The
    # league/batter probabilities are legitimate for such records, but the
    # pitcher who finished the PA was not known before it began, so that
    # identity must not travel in a pre-PA artifact. pitcher_rate_eligible is
    # retained as retrospective metadata v0.3.4 needs to build its
    # intersection sample.
    emitted_pitcher_id = (
        context["pitcher_id"] if context["pitcher_rate_eligible"] else None
    )

    values = {
        "rsb_pa_id": context["rsb_pa_id"],
        "source_game_id": context["source_game_id"],
        "at_bat_number": context["at_bat_number"],
        "batter_id": context["batter_id"],
        "pitcher_id": emitted_pitcher_id,
        "pitcher_rate_eligible": context["pitcher_rate_eligible"],
        "model_method": method,
        "model_config_version": PROBABILITY_MODEL_CONFIG_VERSION,
        "probabilities": probabilities,
        "league_pa_count_used": context["prior_league_pa_count"],
        "batter_pa_count_used": (
            context["prior_batter_pa_count"] if uses_batter else None
        ),
        "pitcher_pa_count_used": (
            context["prior_pitcher_pa_count"] if uses_pitcher else None
        ),
        "league_prior_strength": alpha,
        "batter_prior_strength": kappa_batter if uses_batter else None,
        "pitcher_prior_strength": kappa_pitcher if uses_pitcher else None,
        "normalized_pa_probability_schema_version": (
            PLATE_APPEARANCE_PROBABILITY_SCHEMA_VERSION
        ),
    }
    record = {field: values[field] for field in PROBABILITY_FIELD_ORDER}
    return validate_pa_probability_distribution(record)
