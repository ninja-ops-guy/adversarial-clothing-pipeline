"""D2-0005 non-held-out rehearsal tests (queue step 6).

Repeatable pytest coverage for the rehearsal harness
(ruthless_pipeline/certification/rehearsal_d20005.py): end-to-end chain over
synthetic inputs for BOTH arms, fail-closed failure injection, the A5.5 ICC
<= 0.25 gate (one probe above, one below), crash recovery, promotion refusal,
and rerun determinism. All artifacts are synthetic_pipeline_validation_only;
no real fixture, model, held-out set, or generation record is touched.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from ruthless_pipeline.certification import rehearsal_d20005 as rehearsal
from ruthless_pipeline.certification.cluster_paired_arm_statistics import (
    ABSOLUTE_MIN_CLUSTERS,
    to_canonical_json,
)
from ruthless_pipeline.certification.release_format import verify_release
from ruthless_pipeline.certification.schema_version import (
    SchemaVersionError,
    require_schema_version,
)

EVIDENCE_CLASS = "synthetic_pipeline_validation_only"


def _sha256_path(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture(scope="module")
def chain(tmp_path_factory) -> Path:
    """One full end-to-end rehearsal run, shared by the chain tests."""
    output = tmp_path_factory.mktemp("d20005-rehearsal-chain")
    rehearsal.run_rehearsal(output)
    return output


# ---------------------------------------------------------------------------
# End-to-end chain, both arms
# ---------------------------------------------------------------------------

def test_full_chain_completes_all_stages(chain: Path):
    summary = json.loads((chain / "rehearsal-summary.json").read_text())
    assert summary["stages_completed"] == list(rehearsal.STAGES)
    assert summary["release_verified"] is True
    assert summary["evidence_class"] == EVIDENCE_CLASS
    assert summary["rac_evidence_eligible"] is False


def test_fixture_manifest_is_synthetic_and_hash_pinned(chain: Path):
    manifest = json.loads((chain / "fixture-manifest.json").read_text())
    require_schema_version(manifest, "1.0", label="fixture manifest")
    assert manifest["schema_id"] == "d2-0005-fixture-manifest"
    assert manifest["evidence_class"] == EVIDENCE_CLASS
    assert manifest["synthetic"] is True
    assert manifest["cluster_count"] >= 8
    for image in manifest["images"]:
        path = chain / "fixture_images" / image["path"]
        assert _sha256_path(path) == image["sha256"]


def test_selection_arm_uses_frozen_seed_and_mock_adapter(chain: Path):
    selection = json.loads((chain / "selection-report.json").read_text())
    assert selection["arm"] == "surrogate_selection"
    assert selection["candidate_pool_seed"] == 1337
    assert selection["objective"] == {"name": "cvar", "alpha": 0.5}
    assert selection["mock_adapter"] is True
    assert len(selection["winner_candidate_sha256"]) == 64


def test_frozen_telemetry_records_no_heldout_access(chain: Path):
    telemetry = json.loads((chain / "frozen-telemetry.json").read_text())
    assert telemetry["heldout_model_set_id"] == "PERSON-HO-v3"
    assert "NONE" in telemetry["heldout_access"]
    assert len(telemetry["frozen_sha256"]) == 64


def test_analysis_uses_pinned_cluster_module_params(chain: Path):
    sealed = json.loads((chain / "sealed-evidence.json").read_text())
    params = sealed["parameters"]
    assert params == {
        "z": 1.959963984540054,
        "bootstrap_seed": 20260907,
        "bootstrap_resamples": 10000,
        "width_gate": 0.2,
        "min_clusters": 8,
    }
    result = sealed["result"]
    assert result["clusters"] >= 8
    assert result["observation_units"] == result["clusters"] * 36
    assert result["decision"] in {"success", "negative", "null", "inconclusive"}
    # Sealed hash binds the canonical result of the pinned module.
    canonical = to_canonical_json(
        rehearsal.run_cluster_analysis(
            {
                cid: {u: (bool(m), bool(c)) for u, (m, c) in members.items()}
                for cid, members in json.loads(
                    (chain / "cluster-outcomes.json").read_text()
                )["cluster_outcomes"].items()
            }
        )
    )
    assert hashlib.sha256(canonical.encode()).hexdigest() == sealed["canonical_result_sha256"]


def test_release_object_verifies(chain: Path):
    result = rehearsal.verify_release_dir(chain / "release" / rehearsal.RELEASE_ID)
    assert result.ok, result
    release = json.loads(
        (chain / "release" / rehearsal.RELEASE_ID / "RELEASE.json").read_text()
    )
    assert release["evidence_class"] == EVIDENCE_CLASS
    assert release["rac_evidence_eligible"] is False


def test_manuscript_export_row_written_to_scratch_only(chain: Path):
    export_dir = chain / "export_synthetic"
    csv_path = export_dir / "paper5_arms_rehearsal_synthetic.csv"
    assert csv_path.is_file()
    wrapper = json.loads((export_dir / "export-row.json").read_text())
    assert wrapper["evidence_class"] == EVIDENCE_CLASS
    assert len(wrapper["rows"]) == 2  # both arms
    arm_ids = {row["arm_id"] for row in wrapper["rows"]}
    assert arm_ids == {"arm_m_surrogate_selection_synthetic", "arm_c_control_synthetic"}
    for row in wrapper["rows"]:
        assert int(row["observation_units"]) == 8 * 36
    # The committed manuscript outputs are never touched by the exporter here.
    assert "manuscript" not in str(export_dir.resolve())
    with pytest.raises(ValueError, match="manuscript"):
        rehearsal.export_manuscript_rows(
            Path("manuscript/exports") / "rehearsal",
            {},
            winner_candidate_sha256="0" * 64,
            telemetry_sha256="0" * 64,
        )


# ---------------------------------------------------------------------------
# Failure injection: fail-CLOSED behavior
# ---------------------------------------------------------------------------

def test_injection_fewer_than_8_clusters_raises(tmp_path):
    fixture = rehearsal.build_synthetic_fixture(tmp_path / "images", k=ABSOLUTE_MIN_CLUSTERS - 1)
    outcomes = rehearsal.mock_heldout_cluster_outcomes(fixture)
    assert len(outcomes) == 7
    with pytest.raises(ValueError, match="at least 8 clusters"):
        rehearsal.run_cluster_analysis(outcomes)


def test_injection_min_clusters_floor_cannot_be_lowered(tmp_path):
    fixture = rehearsal.build_synthetic_fixture(tmp_path / "images", k=7)
    outcomes = rehearsal.mock_heldout_cluster_outcomes(fixture)
    with pytest.raises(ValueError, match="ABSOLUTE_MIN_CLUSTERS"):
        rehearsal.run_cluster_analysis(outcomes, min_clusters=4)


def test_injection_tampered_evidence_detected_post_seal(chain: Path, tmp_path):
    import shutil

    src = chain / "release" / rehearsal.RELEASE_ID
    dst = tmp_path / "tampered-release"
    shutil.copytree(src, dst)
    assert rehearsal.verify_release_dir(dst).ok
    # Tamper with the sealed evidence after sealing.
    sealed_path = dst / "sealed-evidence.json"
    payload = json.loads(sealed_path.read_text())
    payload["result"]["decision"] = "success" if payload["result"]["decision"] != "success" else "null"
    sealed_path.write_text(json.dumps(payload))
    result = rehearsal.verify_release_dir(dst)
    assert not result.ok
    assert "sealed-evidence.json" in result.tampered


def test_injection_schema_version_mismatch_raises(chain: Path):
    sealed = json.loads((chain / "sealed-evidence.json").read_text())
    sealed["schema_version"] = "2.0"
    with pytest.raises(SchemaVersionError):
        require_schema_version(sealed, "1.0", label="sealed evidence")
    del sealed["schema_version"]
    with pytest.raises(SchemaVersionError):
        require_schema_version(sealed, "1.0", label="sealed evidence")


def test_injection_mid_pipeline_crash_recovery_no_double_emit(tmp_path):
    crashed = tmp_path / "crashed"
    with pytest.raises(rehearsal.RehearsalCrash):
        rehearsal.run_rehearsal(crashed, crash_after="seal")
    journal = json.loads((crashed / "rehearsal_journal.json").read_text())
    assert journal["completed_stages"] == list(rehearsal.STAGES[:5])
    # Partial results are not a release: the release stage never ran.
    assert not (crashed / "release").exists()
    # Recovery completes the chain without duplicating any stage.
    summary = rehearsal.run_rehearsal(crashed)
    journal = json.loads((crashed / "rehearsal_journal.json").read_text())
    assert journal["completed_stages"] == list(rehearsal.STAGES)
    assert len(journal["completed_stages"]) == len(set(journal["completed_stages"]))
    # A clean run into a fresh directory produces byte-identical artifacts:
    # recovery emits exactly what an uninterrupted run would emit.
    clean = tmp_path / "clean"
    clean_summary = rehearsal.run_rehearsal(clean)
    assert summary["artifact_hashes"] == clean_summary["artifact_hashes"]
    assert summary["summary_sha256"] == clean_summary["summary_sha256"]


def test_injection_resume_detects_tampered_prior_stage(tmp_path):
    crashed = tmp_path / "crashed"
    with pytest.raises(rehearsal.RehearsalCrash):
        rehearsal.run_rehearsal(crashed, crash_after="selection")
    # Tamper with an already-journaled stage artifact before resuming.
    (crashed / "selection-report.json").write_text("{}")
    with pytest.raises(ValueError, match="hash-mismatched"):
        rehearsal.run_rehearsal(crashed)


def test_injection_promotion_to_rac_p1_refused(chain: Path):
    with pytest.raises(rehearsal.PromotionRefusedError, match="REFUSED"):
        rehearsal.promote_to_rac_p1(chain / "release" / rehearsal.RELEASE_ID)


def test_injection_promotion_refused_on_tampered_release(chain: Path, tmp_path):
    import shutil

    dst = tmp_path / "tampered"
    shutil.copytree(chain / "release" / rehearsal.RELEASE_ID, dst)
    (dst / "analysis.json").write_text("{}")
    with pytest.raises(rehearsal.PromotionRefusedError, match="verification failed"):
        rehearsal.promote_to_rac_p1(dst)


def test_rerun_determinism_identical_hashes(tmp_path):
    run_a = tmp_path / "run-a"
    run_b = tmp_path / "run-b"
    summary_a = rehearsal.run_rehearsal(run_a)
    summary_b = rehearsal.run_rehearsal(run_b)
    assert summary_a["summary_sha256"] == summary_b["summary_sha256"]
    assert summary_a["artifact_hashes"] == summary_b["artifact_hashes"]
    # Byte-level comparison of every emitted artifact across the two runs.
    files_a = sorted(p.relative_to(run_a).as_posix() for p in run_a.rglob("*") if p.is_file())
    files_b = sorted(p.relative_to(run_b).as_posix() for p in run_b.rglob("*") if p.is_file())
    assert files_a == files_b
    for rel in files_a:
        assert _sha256_path(run_a / rel) == _sha256_path(run_b / rel), rel


# ---------------------------------------------------------------------------
# A5.5 rehearsal ICC gate: one probe above, one below the 0.25 gate
# ---------------------------------------------------------------------------

def test_icc_gate_passes_below_gate():
    probe = rehearsal.make_icc_probe_clusters("low")
    rho, design_effect, n_eff = rehearsal.realized_icc(probe)
    assert rho is not None and rho <= rehearsal.ICC_GATE_MAX
    decision = rehearsal.icc_gate_decision(rho)
    assert decision["gate_passed"] is True
    assert "permit arming" in decision["arming_effect"]


def test_icc_gate_blocks_above_gate():
    probe = rehearsal.make_icc_probe_clusters("high")
    rho, design_effect, n_eff = rehearsal.realized_icc(probe)
    assert rho is not None and rho > rehearsal.ICC_GATE_MAX
    decision = rehearsal.icc_gate_decision(rho)
    assert decision["gate_passed"] is False
    assert "BLOCKS arming" in decision["arming_effect"]


def test_icc_gate_blocks_on_na_zero_variance():
    # Zero total variance: rho is NA (None), never 0 — and NA must not arm.
    outcomes = {
        f"cluster-{c:03d}": {f"m|t{i:02d}": (True, False) for i in range(36)}
        for c in range(8)
    }
    rho, _, _ = rehearsal.realized_icc(outcomes)
    assert rho is None
    assert rehearsal.icc_gate_decision(rho)["gate_passed"] is False


# ---------------------------------------------------------------------------
# Synthetic-only invariants
# ---------------------------------------------------------------------------

def test_all_emitted_artifacts_labelled_synthetic(chain: Path):
    for name in (
        "fixture-manifest.json",
        "selection-report.json",
        "frozen-telemetry.json",
        "analysis.json",
        "cluster-outcomes.json",
        "sealed-evidence.json",
        "rehearsal-summary.json",
        "rehearsal_journal.json",
        "export_synthetic/export-row.json",
        f"release/{rehearsal.RELEASE_ID}/RELEASE.json",
    ):
        payload = json.loads((chain / name).read_text())
        assert payload["evidence_class"] == EVIDENCE_CLASS, name
        assert payload["rac_evidence_eligible"] is False, name


def test_freeze_candidate_remains_not_armed():
    freeze = json.loads(
        Path("docs/D2-0005_FREEZE_CANDIDATE.json").read_text()
    )
    assert freeze["status"] == "FREEZE_CANDIDATE_NOT_ARMED_PENDING_REHEARSAL_AND_AUDIT"
    assert freeze["arming"]["armed"] is False
