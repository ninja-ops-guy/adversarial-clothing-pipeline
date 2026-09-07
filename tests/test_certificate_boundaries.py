from pathlib import Path

import pytest

from ruthless_pipeline.certification import (
    ArtifactBundle,
    ArtifactRef,
    EvidenceState,
    PatternManifest,
    load_protocol,
)
from ruthless_pipeline.certification.certificate import CertificateDecision, issue_certificate
from ruthless_pipeline.certification.manifest import hash_file


def _manifest(tmp_path: Path) -> PatternManifest:
    master = tmp_path / "master.png"
    master.write_bytes(b"pattern")
    return PatternManifest(
        pattern_id="RAC-BOUNDARY-0001",
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


def _summary() -> dict:
    return {
        "heldout": {
            "baseline_detection_rate": 1.0,
            "candidate_detection_rate": 0.3,
        },
        "invalid_condition_fraction": 0.0,
    }


def _bundle_with_master(tmp_path: Path, name: str) -> ArtifactBundle:
    bundle = ArtifactBundle.create(tmp_path / name)
    (bundle.root / "master.png").write_bytes(b"pattern")
    return bundle


def _write_physical(bundle: ArtifactBundle, *, candidate_rate: float) -> None:
    bundle.write_json(
        "physical/summary.json",
        {
            "total_trials": 100,
            "valid_trials": 100,
            "invalid_trials": 0,
            "control_detection_rate": 1.0,
            "candidate_detection_rate": candidate_rate,
        },
    )
    trials = bundle.root / "physical" / "trials.csv"
    trials.parent.mkdir(parents=True, exist_ok=True)
    trials.write_text("trial_id,condition_id\nT1,C1\n")


def test_physical_boolean_cannot_issue_manufacturing_state(tmp_path: Path) -> None:
    protocol = load_protocol("protocols/RAC-PERSON-DETECT-1.0.json")
    bundle = _bundle_with_master(tmp_path, "m1-no-manufacturing")

    with pytest.raises(ValueError, match="requires manufacturing evidence"):
        issue_certificate(
            bundle=bundle,
            manifest=_manifest(tmp_path),
            protocol=protocol,
            digital_summary=_summary(),
            requested_state=EvidenceState.GOLDEN_SAMPLE,
            physical_evidence_present=True,
            manufacturing_evidence_present=False,
        )


def test_m2_requires_manufacturing_evidence(tmp_path: Path) -> None:
    protocol = load_protocol("protocols/RAC-PERSON-DETECT-1.0.json")
    bundle = _bundle_with_master(tmp_path, "m2-no-manufacturing")

    with pytest.raises(ValueError, match="requires manufacturing evidence"):
        issue_certificate(
            bundle=bundle,
            manifest=_manifest(tmp_path),
            protocol=protocol,
            digital_summary=_summary(),
            requested_state=EvidenceState.LOT_CONFORMITY,
            physical_evidence_present=True,
            manufacturing_evidence_present=False,
        )


def test_physical_failure_cannot_be_overridden_by_strong_digital_result(tmp_path: Path) -> None:
    protocol = load_protocol("protocols/RAC-PERSON-DETECT-1.0.json")
    bundle = _bundle_with_master(tmp_path, "p1-physical-fail")
    _write_physical(bundle, candidate_rate=0.9)

    cert = issue_certificate(
        bundle=bundle,
        manifest=_manifest(tmp_path),
        protocol=protocol,
        digital_summary=_summary(),
        requested_state=EvidenceState.PHYSICAL,
        physical_evidence_present=True,
    )
    assert cert.decision is CertificateDecision.FAIL
    assert cert.evidence_state is EvidenceState.DESIGN
    assert cert.limitations[0] == "Decision basis: physical evidence under the frozen protocol."


def test_physical_pass_uses_bundled_physical_measurements(tmp_path: Path) -> None:
    protocol = load_protocol("protocols/RAC-PERSON-DETECT-1.0.json")
    bundle = _bundle_with_master(tmp_path, "p1-physical-pass")
    _write_physical(bundle, candidate_rate=0.2)

    cert = issue_certificate(
        bundle=bundle,
        manifest=_manifest(tmp_path),
        protocol=protocol,
        digital_summary={
            "heldout": {"baseline_detection_rate": 1.0, "candidate_detection_rate": 0.95},
            "invalid_condition_fraction": 0.0,
        },
        requested_state=EvidenceState.PHYSICAL,
        physical_evidence_present=True,
    )
    assert cert.decision is CertificateDecision.PASS
    assert cert.evidence_state is EvidenceState.PHYSICAL
