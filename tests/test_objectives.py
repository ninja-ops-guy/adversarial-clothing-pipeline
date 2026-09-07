"""Unit tests for the preregistered D2-0005 selection objectives.

CVaR validation matrix against docs/PREREGISTRATION_D2-0005.md: exact worst-k
tail selection (including unsorted input orderings), deterministic tie
handling at the tail boundary, odd ensemble sizes, ordering determinism, and
input validation rejections. Gradients are not applicable: the selector is an
argmin over a discrete candidate set, so no smoothness/autodiff properties
are tested here.
"""

import math

import pytest

from ruthless_pipeline.certification.objectives import (
    ObjectiveSpec,
    cvar,
    cvar_tail_size,
    mean_objective,
    worst_tail_members,
)


SIX_RATES = [0.10, 0.20, 0.30, 0.40, 0.50, 0.60]


def test_cvar_half_is_worst_three_of_six():
    # Preregistered Arm C: alpha = 0.5 over the 6-surrogate ensemble averages
    # exactly the 3 highest per-surrogate rates.
    assert cvar(SIX_RATES, 0.5) == pytest.approx((0.40 + 0.50 + 0.60) / 3)


def test_cvar_is_order_invariant():
    shuffled = [0.60, 0.10, 0.50, 0.20, 0.40, 0.30]
    assert cvar(shuffled, 0.5) == pytest.approx(cvar(SIX_RATES, 0.5))


def test_cvar_alpha_one_is_max():
    # alpha -> 1 approaches the single-worst-surrogate (minimax) objective.
    assert cvar(SIX_RATES, 1.0) == pytest.approx(0.60)


def test_cvar_small_alpha_collapses_to_mean_with_ceil_rule():
    # k = max(1, ceil((1 - alpha) * n)): alpha = 0.1, n = 6 -> k = 6 -> the mean.
    assert cvar(SIX_RATES, 0.1) == pytest.approx(sum(SIX_RATES) / 6)
    # alpha = 0.9, n = 6 -> k = ceil(0.6) = 1 -> the worst single rate.
    assert cvar(SIX_RATES, 0.9) == pytest.approx(0.60)
    # alpha = 0.75, n = 6 -> k = ceil(1.5) = 2 -> mean of the two worst.
    assert cvar(SIX_RATES, 0.75) == pytest.approx((0.50 + 0.60) / 2)


def test_cvar_single_rate():
    assert cvar([0.42], 0.5) == pytest.approx(0.42)


@pytest.mark.parametrize("alpha", [0.0, -0.1, 1.1, float("nan"), float("inf")])
def test_cvar_rejects_alpha_outside_open_closed_unit(alpha):
    with pytest.raises(ValueError):
        cvar(SIX_RATES, alpha)


def test_cvar_rejects_empty_rates():
    with pytest.raises(ValueError):
        cvar([], 0.5)


@pytest.mark.parametrize("bad", [-0.01, 1.01, float("nan"), float("inf")])
def test_cvar_rejects_non_unit_interval_rates(bad):
    rates = [0.1, 0.2, 0.3, 0.4, 0.5, bad]
    with pytest.raises(ValueError):
        cvar(rates, 0.5)


def test_mean_objective():
    assert mean_objective(SIX_RATES) == pytest.approx(sum(SIX_RATES) / 6)
    with pytest.raises(ValueError):
        mean_objective([])
    with pytest.raises(ValueError):
        mean_objective([0.5, float("nan")])


def test_objective_spec_validation():
    ObjectiveSpec(name="mean").validate()
    ObjectiveSpec(name="cvar", alpha=0.5).validate()
    with pytest.raises(ValueError):
        ObjectiveSpec(name="cvar").validate()  # alpha required
    with pytest.raises(ValueError):
        ObjectiveSpec(name="mean", alpha=0.5).validate()  # alpha forbidden
    with pytest.raises(ValueError):
        ObjectiveSpec(name="median").validate()
    with pytest.raises(ValueError):
        ObjectiveSpec(name="cvar", alpha=0.0).validate()


def test_objective_spec_is_frozen():
    spec = ObjectiveSpec(name="cvar", alpha=0.5)
    with pytest.raises(Exception):
        spec.alpha = 0.7


def test_objective_spec_dispatch():
    rates = {f"m{i}": r for i, r in enumerate(SIX_RATES)}
    mean_spec = ObjectiveSpec(name="mean")
    cvar_spec = ObjectiveSpec(name="cvar", alpha=0.5)
    assert mean_spec.objective_key(rates) == pytest.approx(mean_objective(SIX_RATES))
    assert cvar_spec.objective_key(rates) == pytest.approx(cvar(SIX_RATES, 0.5))


def test_objective_spec_dispatch_is_deterministic_under_dict_ordering():
    forward = {f"m{i}": r for i, r in enumerate(SIX_RATES)}
    reversed_rates = dict(reversed(list(forward.items())))
    spec = ObjectiveSpec(name="cvar", alpha=0.5)
    assert spec.objective_key(forward) == spec.objective_key(reversed_rates)
    assert math.isfinite(spec.objective_key(forward))


def test_objective_spec_rejects_empty_rate_vector():
    with pytest.raises(ValueError):
        ObjectiveSpec(name="mean").objective_key({})


# --- CVaR validation matrix (PREREGISTRATION_D2-0005.md) ---------------------

RATES_BY_ID = {f"sur-{i}": r for i, r in enumerate(SIX_RATES)}


def test_tail_size_rule_odd_and_even_ensembles():
    # k = max(1, ceil((1 - alpha) * n)) at alpha = 0.5.
    assert {n: cvar_tail_size(n, 0.5) for n in (1, 3, 5, 6, 7)} == {1: 1, 3: 2, 5: 3, 6: 3, 7: 4}
    # alpha = 1.0 is always the single worst model; small alpha approaches n.
    assert all(cvar_tail_size(n, 1.0) == 1 for n in (1, 3, 5, 6, 7))
    assert cvar_tail_size(6, 0.1) == 6


@pytest.mark.parametrize("n", [1, 3, 5, 7])
def test_cvar_odd_ensemble_sizes(n):
    rates = [round(0.1 * (i + 1), 1) for i in range(n)]
    k = cvar_tail_size(n, 0.5)
    expected = sum(sorted(rates, reverse=True)[:k]) / k
    assert cvar(rates, 0.5) == pytest.approx(expected)


def test_exact_tail_membership():
    assert worst_tail_members(RATES_BY_ID, 0.5) == ("sur-5", "sur-4", "sur-3")
    assert worst_tail_members(RATES_BY_ID, 1.0) == ("sur-5",)


def test_tail_membership_invariant_to_input_ordering():
    shuffled = dict(reversed(list(RATES_BY_ID.items())))
    assert worst_tail_members(shuffled, 0.5) == worst_tail_members(RATES_BY_ID, 0.5)
    spec = ObjectiveSpec(name="cvar", alpha=0.5)
    assert spec.objective_key(shuffled) == spec.objective_key(RATES_BY_ID)


def test_tail_boundary_ties_are_deterministic():
    # Tie exactly at the k = 3 boundary: sur-b and sur-c both rate 0.50.
    rates = {"sur-a": 0.60, "sur-b": 0.50, "sur-c": 0.50, "sur-d": 0.10, "sur-e": 0.10, "sur-f": 0.10}
    # Documented behavior: boundary ties broken by canonical model id ascending.
    assert worst_tail_members(rates, 0.5) == ("sur-a", "sur-b", "sur-c")
    rates2 = {"sur-c": 0.50, "sur-a": 0.60, "sur-b": 0.50, "sur-f": 0.10, "sur-e": 0.10, "sur-d": 0.10}
    assert worst_tail_members(rates2, 0.5) == ("sur-a", "sur-b", "sur-c")
    # A tie spanning the k boundary (k = 2 at alpha = 0.75): sur-b is included
    # and sur-c excluded, deterministically, regardless of dict ordering.
    assert worst_tail_members(rates, 0.75) == ("sur-a", "sur-b")
    assert worst_tail_members(rates2, 0.75) == ("sur-a", "sur-b")
    # The objective value itself is tie-insensitive.
    assert cvar(list(rates.values()), 0.5) == pytest.approx((0.60 + 0.50 + 0.50) / 3)


def test_worst_tail_members_validation():
    with pytest.raises(ValueError):
        worst_tail_members({}, 0.5)
    with pytest.raises(ValueError):
        worst_tail_members({"a": float("nan")}, 0.5)
    with pytest.raises(ValueError):
        worst_tail_members({"a": 1.5}, 0.5)
    with pytest.raises(ValueError):
        worst_tail_members({"a": 0.5}, 0.0)


def test_cvar_tail_size_validation():
    for bad_n in (0, -1, 2.5):
        with pytest.raises(ValueError):
            cvar_tail_size(bad_n, 0.5)
    for bad_alpha in (0.0, 1.01, float("nan")):
        with pytest.raises(ValueError):
            cvar_tail_size(6, bad_alpha)
