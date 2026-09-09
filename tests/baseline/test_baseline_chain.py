"""Baseline preservation characterization tests.

These tests pin the deterministic outputs of the CURRENT baseline selection
chain — Product Studio candidate pool (schema 3.0 contract) -> surrogate
scoring (ComparativeBenchmark) -> two-stage mean / CVaR_0.5 selection via
scripts/select_surrogate_candidate.py — on hash-seeded synthetic fixtures
(tests/baseline/fixtures.py). If a future engine change silently alters the
historical baseline behavior, the pinned hashes in
artifacts/baseline/reference_manifest.json stop matching and these tests
fail.

Regeneration of the reference is an explicit, audited action:
``python tests/baseline/generate_reference.py --regenerate``.

Boundary: synthetic fixtures only. No real detector weights, no held-out
models, no measured evidence; nothing here optimizes against held-out
results or touches D2-0004/D2-0005 selection rules.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ruthless_pipeline.certification.numerical_verification import canonical_sha256
from scripts import select_surrogate_candidate as ssc
from tests.baseline import fixtures as fx

REFERENCE_PATH = ROOT / "artifacts" / "baseline" / "reference_manifest.json"


@pytest.fixture(scope="module")
def reference() -> dict:
    assert REFERENCE_PATH.is_file(), (
        "reference manifest missing; regenerate with: "
        "PYTHONPATH=. python tests/baseline/generate_reference.py --regenerate"
    )
    return json.loads(REFERENCE_PATH.read_text())


@pytest.fixture(scope="module")
def current(tmp_path_factory) -> dict:
    work = tmp_path_factory.mktemp("baseline-chain")
    return fx.collect_reference_payload(work)


def test_reference_pins_generator_code_and_seed(reference):
    """The manifest pins the generator code hash and seed of the fixtures."""
    assert reference["seed"] == fx.FIXTURE_SEED
    assert reference["fixture_version"] == fx.FIXTURE_VERSION
    assert reference["generator"]["path"] == "tests/baseline/fixtures.py"
    assert reference["generator"]["sha256"] == fx.generator_code_sha256(), (
        "tests/baseline/fixtures.py changed after the reference was pinned; "
        "if this change is intentional and reviewed, regenerate the reference "
        "with --regenerate"
    )


def test_chain_outputs_match_reference(reference, current):
    """Every pinned output digest of the baseline chain must match exactly."""
    ref_entries = reference["entries"]
    cur_entries = current["entries"]
    assert set(cur_entries) == set(ref_entries)
    mismatches = {
        key: (ref_entries[key], cur_entries[key])
        for key in ref_entries
        if ref_entries[key] != cur_entries[key]
    }
    assert not mismatches, (
        "baseline chain outputs drifted from the pinned reference "
        "(investigate before considering regeneration): "
        + json.dumps(mismatches, indent=2, sort_keys=True)
    )


def test_selection_boundary_is_surrogate_only(current):
    """The characterized chain never touches held-out models or feedback."""
    assert fx.build_pool()["heldout_feedback_allowed"] is False
    assert all(m["role"] == "surrogate" for m in fx.build_manifest()["models"])


def test_deterministic_rerun_same_output(tmp_path):
    """Running the chain twice from scratch yields byte-identical digests."""
    first = fx.collect_reference_payload(tmp_path / "run1")
    second = fx.collect_reference_payload(tmp_path / "run2")
    assert first["entries"] == second["entries"]


# ---------------------------------------------------------------------------
# Unit-level characterization of the selection semantics (crafted, analytic)
# ---------------------------------------------------------------------------




def test_mean_and_cvar_arms_rank_differently_on_crafted_tail():
    """Pin the baseline's defining property: the CVaR arm ranks by the
    per-surrogate worst-tail, not the ensemble mean.

    cand-a: low mean, one left-behind surrogate (0.9); cand-b: flat 0.4.
    Mean arm prefers cand-b (0.4 > 0.3167); CVaR_0.5 (worst 3 of 6) prefers
    cand-b too (0.4 < 0.4333 as a *loss*... both keys are losses, lower is
    better): mean losses a=0.3167? No — rates are losses where *lower* is
    better (detection *suppression*): cand-a mean = 0.3167 beats cand-b 0.4;
    CVaR_0.5: cand-a worst-3 mean = 0.4333 loses to cand-b 0.4.
    """
    record_a, record_b = fx.crafted_stage_b()

    mean_spec = ssc.ObjectiveSpec(name="mean")
    cvar_spec = ssc.ObjectiveSpec(name="cvar", alpha=0.5)
    mean_spec.validate()
    cvar_spec.validate()

    # Mean arm: cand-a wins (lower mean loss).
    assert min([record_a, record_b], key=ssc.sort_key) is record_a
    # CVaR arm: cand-b wins (lower worst-tail loss).
    assert (
        min([record_a, record_b], key=lambda r: ssc.objective_sort_key(r, cvar_spec))
        is record_b
    )


def test_objective_telemetry_shape_characterized():
    """Pin the deterministic structure of per-checkpoint objective telemetry."""
    telemetry = fx.crafted_telemetry()
    assert telemetry["schema_version"] == "1.0"
    assert telemetry["objective"] == {"name": "cvar", "alpha": 0.5}
    assert len(telemetry["checkpoints"]) == 2
    first, second = telemetry["checkpoints"]
    # cand-a tail at alpha=0.5: the 3 highest rates {sur-5, plus two 0.2s by id order}
    assert first["cvar_tail"]["k"] == 3
    assert first["cvar_tail"]["member_ids"][0] == "sur-5"
    assert first["losses"]["cvar"] == pytest.approx((0.9 + 0.2 + 0.2) / 3)
    assert first["losses"]["mean"] == pytest.approx((0.2 * 5 + 0.9) / 6)
    # second checkpoint knows both candidates; ranks pinned
    assert second["candidate_ranks"]["cand-a"]["mean_rank"] == 1
    assert second["candidate_ranks"]["cand-a"]["cvar_rank"] == 2
    assert second["candidate_ranks"]["cand-b"]["mean_rank"] == 2
    assert second["candidate_ranks"]["cand-b"]["cvar_rank"] == 1
    # tail turnover between checkpoints is pinned: cand-a's tail
    # {sur-5, sur-0, sur-1} rotates to cand-b's flat tail {sur-0, sur-1, sur-2}
    assert first["cvar_tail"]["member_ids"] == ["sur-5", "sur-0", "sur-1"]
    assert second["cvar_tail"]["member_ids"] == ["sur-0", "sur-1", "sur-2"]
    assert second["tail_turnover"]["entered"] == ["sur-2"]
    assert second["tail_turnover"]["left"] == ["sur-5"]


def test_telemetry_canonical_hash_pinned():
    """Pin the exact canonical digest of the crafted telemetry document."""
    telemetry = fx.crafted_telemetry()
    expected = json.loads(REFERENCE_PATH.read_text())["entries"].get(
        "crafted_telemetry_sha256"
    )
    if expected is None:
        pytest.fail(
            "reference manifest lacks crafted_telemetry_sha256; regenerate with --regenerate"
        )
    assert canonical_sha256(telemetry) == expected


# ---------------------------------------------------------------------------
# Pool-contract guards (fail-closed invariants of the baseline chain)
# ---------------------------------------------------------------------------


def _run_with_pool(tmp_path: Path, mutate, expected_exc=SystemExit) -> int:
    pool = fx.build_pool()
    mutate(pool)
    pool_dir = tmp_path / "pool"
    pool_dir.mkdir(parents=True, exist_ok=True)
    for candidate_id in fx.CANDIDATE_IDS:
        (pool_dir / f"{candidate_id}.png").write_bytes(fx.candidate_png_bytes(candidate_id))
    pool_path = pool_dir / "pool.json"
    pool_path.write_text(json.dumps(pool, indent=2, sort_keys=True) + "\n")
    manifest_path = pool_dir / "model_manifest.json"
    manifest_path.write_text(json.dumps(fx.build_manifest(), indent=2, sort_keys=True) + "\n")

    ssc.build_evaluators = lambda manifest, roles=None: (fx.make_mock_evaluators(), {}, {})
    ssc.prepare_fixture = fx.fake_prepare_fixture
    argv = [
        "select_surrogate_candidate.py",
        "--manifest", str(manifest_path),
        "--pool", str(pool_path),
        "--output-dir", str(tmp_path / "out"),
    ]
    old_argv = sys.argv
    try:
        sys.argv = argv
        with pytest.raises(expected_exc):
            ssc.main()
    finally:
        sys.argv = old_argv
    return 0


def test_pool_rejects_heldout_feedback(tmp_path):
    _run_with_pool(tmp_path, lambda pool: pool.update(heldout_feedback_allowed=True))


def test_pool_rejects_count_mismatch(tmp_path):
    _run_with_pool(tmp_path, lambda pool: pool.update(candidate_count=99))


def test_pool_rejects_missing_design_profile_hash(tmp_path):
    _run_with_pool(tmp_path, lambda pool: pool.update(design_profile_sha256=""))


def test_pool_rejects_wrong_schema_version(tmp_path):
    from ruthless_pipeline.certification.schema_version import SchemaVersionError

    _run_with_pool(
        tmp_path,
        lambda pool: pool.update(schema_version="2.0"),
        expected_exc=SchemaVersionError,
    )
