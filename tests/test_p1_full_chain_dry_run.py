"""End-to-end checks for scripts/p1_full_chain_dry_run.py.

Covers: chain completion, byte-identity across two runs, synthetic evidence
class on every emitted artifact, release verification, and the promotion gate
(synthetic output can never be certified as physical/RAC evidence).
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

from ruthless_pipeline.certification import (
    ArtifactBundle,
    ArtifactRef,
    EvidenceState,
    PatternManifest,
    load_protocol,
)
from ruthless_pipeline.certification.certificate import issue_certificate
from ruthless_pipeline.certification.experiment import ExperimentArtifact
from ruthless_pipeline.certification.manifest import hash_file
from ruthless_pipeline.certification.release_format import verify_release

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.p1_full_chain_dry_run import (  # noqa: E402
    EVIDENCE_CLASS,
    EXPERIMENT_ID,
    RELEASE_EXCLUDE,
    RESULT_LINE,
    run_chain,
)

# Strict-format hash indexes that cannot carry the label fields by design.
UNLABELLED_FORMAT_FILES = {"MANIFEST.json"}


def _tree_bytes(root: Path) -> dict[str, bytes]:
    return {
        p.relative_to(root).as_posix(): p.read_bytes()
        for p in sorted(root.rglob("*"))
        if p.is_file()
    }


def _emitted_artifacts(root: Path) -> list[Path]:
    return [
        p
        for p in sorted(root.rglob("*.json"))
        if p.name not in UNLABELLED_FORMAT_FILES
    ]


def test_chain_completes(tmp_path: Path) -> None:
    out = tmp_path / "run"
    summary = run_chain(out)
    assert summary["evidence_class"] == EVIDENCE_CLASS
    assert summary["rac_evidence_eligible"] is False
    assert summary["calibration_accepted"] is True
    assert summary["cumulative_trial_count"] == 2  # still + motion-spec trials
    assert summary["release_verified"] is True
    for name, digest in summary["artifacts"].items():
        path = out / name
        assert path.is_file(), name
        assert len(digest) == 64
    assert (out / "p1-full-chain-dry-run.json").is_file()


def test_cli_final_line_is_the_result_contract(tmp_path: Path) -> None:
    proc = subprocess.run(
        [sys.executable, "scripts/p1_full_chain_dry_run.py", "--output-dir", str(tmp_path / "cli")],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    assert proc.stdout.rstrip("\n").splitlines()[-1] == RESULT_LINE
    assert "synthetic_pipeline_validation_only" in RESULT_LINE


def test_determinism_byte_identity(tmp_path: Path) -> None:
    run_chain(tmp_path / "a")
    run_chain(tmp_path / "b")
    tree_a = _tree_bytes(tmp_path / "a")
    tree_b = _tree_bytes(tmp_path / "b")
    assert tree_a == tree_b


def test_every_emitted_artifact_is_synthetic_only(tmp_path: Path) -> None:
    out = tmp_path / "run"
    run_chain(out)
    artifacts = _emitted_artifacts(out)
    assert len(artifacts) >= 10
    for path in artifacts:
        payload = json.loads(path.read_text())
        assert payload.get("evidence_class") == EVIDENCE_CLASS, path
        assert payload.get("rac_evidence_eligible") is False, path


def test_release_verification_passes(tmp_path: Path) -> None:
    out = tmp_path / "run"
    run_chain(out)
    result = verify_release(out / "release" / EXPERIMENT_ID, exclude=RELEASE_EXCLUDE)
    assert result.ok


def test_release_verification_detects_tampering(tmp_path: Path) -> None:
    out = tmp_path / "run"
    run_chain(out)
    release_dir = out / "release" / EXPERIMENT_ID
    target = release_dir / "statistics.json"
    target.write_bytes(target.read_bytes() + b" ")
    result = verify_release(release_dir, exclude=RELEASE_EXCLUDE)
    assert not result.ok
    assert "statistics.json" in result.tampered


def test_simulated_inference_substitution_is_documented(tmp_path: Path) -> None:
    out = tmp_path / "run"
    run_chain(out)
    inference = json.loads((out / "inference-result.json").read_text())
    assert inference["status"] == "simulated_inference_fixture"
    assert inference["simulated_inference"]["substituted"] is True
    assert inference["simulated_inference"]["reason"]
    assert inference["motion"]["spec_level_only"] is True


def test_experiment_artifact_is_not_promotable(tmp_path: Path) -> None:
    out = tmp_path / "run"
    run_chain(out)
    payload = json.loads((out / "experiment-artifact.json").read_text())
    artifact = ExperimentArtifact.from_dict(payload["experiment"])
    # Not measured evidence: the registry entry is a scenario assumption only.
    assert artifact.evidence_label == "scenario_assumption"
    assert artifact.evidence_label != "internally_measured"
    assert artifact.validity_flags["rac_evidence_eligible"] is False
    assert artifact.validity_flags["evidence_class"] == EVIDENCE_CLASS


def test_promotion_gate_rejects_synthetic_chain(tmp_path: Path) -> None:
    """The certification gate cannot be crossed by synthetic dry-run output.

    Requesting a physical evidence state without physical evidence must fail;
    the synthetic chain produces physical_evidence_present=False by contract.
    """
    master = tmp_path / "master.png"
    master.write_bytes(b"pattern")
    manifest = PatternManifest(
        pattern_id="RAC-BOUNDARY-DR",
        version="1.0.0",
        task="person_detection",
        source_commit="a" * 40,
        optimizer="test",
        optimizer_version="1",
        seed=42,
        master=ArtifactRef(
            path="master.png",
            sha256=hash_file(master),
            media_type="image/png",
        ),
        protocol_id="RAC-PERSON-DETECT",
        surrogate_model_set="PERSON-SUR-v1",
        heldout_model_set="PERSON-HO-v1",
    )
    protocol = load_protocol("protocols/RAC-PERSON-DETECT-1.0.json")
    bundle = ArtifactBundle.create(tmp_path / "bundle")
    (bundle.root / "master.png").write_bytes(b"pattern")

    with pytest.raises(ValueError, match="requires physical evidence"):
        issue_certificate(
            bundle=bundle,
            manifest=manifest,
            protocol=protocol,
            digital_summary={
                "heldout": {
                    "baseline_detection_rate": 1.0,
                    "candidate_detection_rate": 0.3,
                },
                "invalid_condition_fraction": 0.0,
            },
            requested_state=EvidenceState.PHYSICAL,
            physical_evidence_present=False,
        )
