"""Tests for ruthless_pipeline.certification.numerical_verification.

All fixtures are analytically solvable by hand so the expected values are
known a priori — the reference implementations are checked against arithmetic,
not against themselves. Cross-checks against the pipeline's own
``objectives`` module are included to catch shared-code drift in *both*
directions (the references here are implemented independently).
"""

from __future__ import annotations

import hashlib
import math
import random
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ruthless_pipeline.certification import numerical_verification as nv
from ruthless_pipeline.certification import objectives


# ---------------------------------------------------------------------------
# finite-value / NaN / Inf rejection
# ---------------------------------------------------------------------------


def test_require_finite_accepts_plain_values():
    assert nv.require_finite([0, 1, -2.5, 1e308]) == [0.0, 1.0, -2.5, 1e308]


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), float("-inf")])
def test_require_finite_rejects_nonfinite(bad):
    with pytest.raises(nv.NonFiniteValueError):
        nv.require_finite([0.5, bad, 0.25])


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), -0.1, 1.1])
def test_require_rates_rejects_out_of_domain(bad):
    with pytest.raises(nv.VerificationError):
        nv.require_rates([0.5, bad])


def test_require_rates_rejects_empty():
    with pytest.raises(nv.VerificationError):
        nv.require_rates([])


# ---------------------------------------------------------------------------
# mean / CVaR references (analytically solvable fixtures)
# ---------------------------------------------------------------------------


def test_mean_reference_exact():
    # sum = 1.0 over 4 values -> 0.25 exactly (binary-representable)
    assert nv.mean_reference([0.1, 0.2, 0.3, 0.4]) == pytest.approx(0.25)
    # exactly representable case: 0.25 + 0.5 + 0.125 = 0.875 over 3
    assert nv.mean_reference([0.25, 0.5, 0.125]) == 0.875 / 3


def test_cvar_reference_analytic_alpha_half():
    # n = 6, alpha = 0.5 -> k = ceil(0.5*6) = 3 worst: 0.9, 0.5, 0.4 -> 0.6
    rates = [0.1, 0.2, 0.3, 0.4, 0.5, 0.9]
    assert nv.cvar_tail_size_reference(6, 0.5) == 3
    assert nv.cvar_reference(rates, 0.5) == pytest.approx(0.6)


def test_cvar_reference_alpha_one_is_single_worst():
    assert nv.cvar_tail_size_reference(5, 1.0) == 1
    assert nv.cvar_reference([0.1, 0.9, 0.3], 1.0) == pytest.approx(0.9)


def test_cvar_reference_small_alpha_approaches_mean():
    rates = [0.2, 0.4, 0.6, 0.8]
    # alpha -> 0 collapses to the mean; alpha = 1/n already takes k = n-... check:
    # alpha = 0.25, n = 4 -> k = ceil(0.75*4) = 3; worst 3 of 4 -> (0.8+0.6+0.4)/3
    assert nv.cvar_reference(rates, 0.25) == pytest.approx(1.8 / 3)
    # alpha tiny -> k = n -> exactly the mean
    assert nv.cvar_reference(rates, 1e-9) == pytest.approx(nv.mean_reference(rates))


def test_cvar_tail_size_ceil_boundary_uses_exact_arithmetic():
    # 1 - 0.7 = 0.3; 0.3 * 3 = 0.9 -> ceil = 1. In binary floating point
    # 0.30000000000000004 * 3 = 0.90000000000000002; naive math.ceil still
    # yields 1, but (1 - 0.1) * 3 = 2.7000000000000002 -> naive ceil = 3
    # where exact arithmetic gives ceil(2.7) = 3 as well... use 0.6*5:
    # 1 - 0.6 = 0.4; 0.4 * 5 = 2.0 exactly in decimal; float gives
    # 0.4000000000000001 * 5 = 2.0000000000000004 -> naive ceil = 3 (wrong).
    assert nv.cvar_tail_size_reference(5, 0.6) == 2


def test_cvar_reference_rejects_bad_alpha():
    for bad in (0.0, -0.5, 1.5, float("nan")):
        with pytest.raises(nv.VerificationError):
            nv.cvar_reference([0.5], bad)


def test_references_agree_with_pipeline_objectives_on_random_rates():
    """Cross-check: independent references vs pipeline objectives.

    Agreement is required; a mismatch means one of the two implementations
    drifted — either way it must surface loudly.
    """
    rng = random.Random(20240101)
    for _ in range(50):
        n = rng.randint(1, 9)
        rates = [rng.random() for _ in range(n)]
        alpha = rng.choice([0.1, 0.25, 0.5, 0.75, 0.9, 1.0])
        assert nv.mean_reference(rates) == pytest.approx(
            objectives.mean_objective(rates), rel=0, abs=1e-12
        )
        assert nv.cvar_reference(rates, alpha) == pytest.approx(
            objectives.cvar(rates, alpha), rel=0, abs=1e-12
        )


# ---------------------------------------------------------------------------
# Pareto dominance reference
# ---------------------------------------------------------------------------


def test_pareto_dominates_minimization():
    assert nv.pareto_dominates((1.0, 1.0), (2.0, 2.0))
    assert nv.pareto_dominates((1.0, 2.0), (2.0, 2.0))  # strictly better in one
    assert not nv.pareto_dominates((1.0, 3.0), (2.0, 2.0))  # trade-off
    assert not nv.pareto_dominates((2.0, 2.0), (2.0, 2.0))  # equal != dominates


def test_pareto_dominates_maximization():
    senses = ("max", "max")
    assert nv.pareto_dominates((0.9, 0.9), (0.8, 0.9), senses=senses)
    assert not nv.pareto_dominates((0.7, 0.9), (0.8, 0.9), senses=senses)


def test_pareto_front_indices_reference():
    # 2-D minimization; hand-computed front: points 0, 1, 2
    points = [
        (1.0, 5.0),  # front
        (2.0, 3.0),  # front
        (4.0, 1.0),  # front
        (3.0, 4.0),  # dominated by (2,3)
        (5.0, 5.0),  # dominated by everything
    ]
    assert nv.pareto_front_indices(points) == (0, 1, 2)


def test_pareto_front_rejects_nonfinite_and_bad_senses():
    with pytest.raises(nv.DominanceError):
        nv.pareto_dominates((float("nan"), 1.0), (1.0, 1.0))
    with pytest.raises(nv.DominanceError):
        nv.pareto_dominates((1.0,), (1.0, 2.0))
    with pytest.raises(nv.DominanceError):
        nv.pareto_dominates((1.0, 1.0), (2.0, 2.0), senses=("min", "sideways"))


# ---------------------------------------------------------------------------
# objective decomposition
# ---------------------------------------------------------------------------


def test_verify_objective_decomposition_exact():
    # exactly representable in binary floating point
    assert nv.verify_objective_decomposition(0.75, [0.25, 0.5]) == 0.0
    # within-tolerance non-exact case
    assert nv.verify_objective_decomposition(0.9, [0.3, 0.6]) < 1e-12


def test_verify_objective_decomposition_weighted():
    # 0.25*0.8 + 0.75*0.4 = 0.5
    nv.verify_objective_decomposition(0.5, [0.8, 0.4], weights=[0.25, 0.75])


def test_verify_objective_decomposition_fails_closed_on_mismatch():
    with pytest.raises(nv.DecompositionError):
        nv.verify_objective_decomposition(1.0, [0.3, 0.6])


def test_verify_objective_decomposition_rejects_nan():
    with pytest.raises(nv.DecompositionError):
        nv.verify_objective_decomposition(float("nan"), [0.3])
    with pytest.raises(nv.NonFiniteValueError):
        nv.verify_objective_decomposition(0.3, [float("inf")])


# ---------------------------------------------------------------------------
# deterministic rerun / seed reproducibility
# ---------------------------------------------------------------------------


def test_deterministic_rerun_accepts_pure_function():
    def pure(x):
        return {"square": x * x, "values": [x, x + 1]}

    assert nv.check_deterministic_rerun(pure, 7, runs=3)["square"] == 49


def test_deterministic_rerun_catches_stateful_function():
    state = {"calls": 0}

    def impure():
        state["calls"] += 1
        return {"calls": state["calls"]}

    with pytest.raises(nv.NondeterminismError):
        nv.check_deterministic_rerun(impure, runs=2)


def test_deterministic_rerun_catches_nonfinite_result():
    with pytest.raises(nv.NonFiniteValueError):
        nv.check_deterministic_rerun(lambda: {"loss": float("nan")})


def test_seed_reproducibility_accepts_seeded_rng():
    def seeded(seed):
        return random.Random(seed).random()

    assert nv.check_seed_reproducibility(seeded, 42, other_seed=43) == pytest.approx(
        random.Random(42).random()
    )


def test_seed_reproducibility_catches_seed_ignoring_function():
    with pytest.raises(nv.SeedReproducibilityError):
        nv.check_seed_reproducibility(lambda seed: 0.5, 42, other_seed=43)


# ---------------------------------------------------------------------------
# transformation-seed reproduction
# ---------------------------------------------------------------------------


def test_transformation_seed_reproduction_stateless_sampler():
    def factory(seed):
        def sample(index):
            # stateless: sample depends only on (seed, index)
            return hashlib.sha256(f"{seed}:{index}".encode()).hexdigest()

        return sample

    nv.check_transformation_seed_reproduction(factory, 99, 3, runs=3)


def test_transformation_seed_reproduction_catches_stream_sampler():
    def factory(seed):
        rng = random.Random(seed)
        return lambda index: rng.random()  # stream: value depends on draw order

    with pytest.raises(nv.SeedReproducibilityError):
        nv.check_transformation_seed_reproduction(factory, 99, 3, runs=2)


def test_transformation_seed_reproduction_catches_nondeterministic_sampler():
    def factory(seed):
        return lambda index: random.random()  # unseeded

    with pytest.raises(nv.NondeterminismError):
        nv.check_transformation_seed_reproduction(factory, 99, 3, runs=2)


# ---------------------------------------------------------------------------
# hash / checkpoint integrity
# ---------------------------------------------------------------------------


def test_checkpoint_integrity_roundtrip(tmp_path):
    payload = b"fake-checkpoint-bytes" * 100
    path = tmp_path / "ckpt.bin"
    path.write_bytes(payload)
    digest = hashlib.sha256(payload).hexdigest()
    assert nv.verify_checkpoint_integrity(path, digest) == digest
    assert nv.checkpoint_sha256(path) == digest


def test_checkpoint_integrity_fails_closed_on_corruption(tmp_path):
    path = tmp_path / "ckpt.bin"
    path.write_bytes(b"original")
    digest = hashlib.sha256(b"original").hexdigest()
    path.write_bytes(b"tampered")
    with pytest.raises(nv.CheckpointIntegrityError):
        nv.verify_checkpoint_integrity(path, digest)


def test_checkpoint_integrity_fails_closed_on_missing_and_malformed(tmp_path):
    digest = hashlib.sha256(b"x").hexdigest()
    with pytest.raises(nv.CheckpointIntegrityError):
        nv.verify_checkpoint_integrity(tmp_path / "absent.bin", digest)
    with pytest.raises(nv.CheckpointIntegrityError):
        nv.verify_checkpoint_integrity(tmp_path / "absent.bin", "not-a-digest")


def test_canonical_sha256_is_order_insensitive_and_stable():
    a = {"x": 1, "y": [1, 2, {"z": 0.5}]}
    b = {"y": [1, 2, {"z": 0.5}], "x": 1}
    assert nv.canonical_sha256(a) == nv.canonical_sha256(b)
    assert nv.canonical_json(a) == b'{"x":1,"y":[1,2,{"z":0.5}]}'


def test_module_exports_no_pipeline_math_imports():
    """The harness must stay independent of the pipeline's math modules."""
    source = (ROOT / "ruthless_pipeline" / "certification" / "numerical_verification.py").read_text()
    assert "from .objectives import" not in source
    assert "import objectives" not in source
    assert "ruthless_pipeline.optimization" not in source
