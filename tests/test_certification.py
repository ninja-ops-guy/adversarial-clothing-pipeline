from pathlib import Path

from ruthless_pipeline.certification import (
    ArtifactBundle,
    ArtifactRef,
    EvidenceState,
    PatternManifest,
    load_protocol,
    verify_certificate_bundle,
)
from ruthless_pipeline.certification.certificate import CertificateDecision, issue_certificate


def manifest(tmp_path: Path) -> PatternManifest:
    master = tmp_path / "master.png"
    master.write_bytes(b"pattern")
    import hashlib
    digest = hashlib.sha256(master.read_bytes()).hexdigest()
    return PatternManifest(
        pattern_id="RAC-PER-0001",
        version="1.0.0",
        task="person_detection",
        source_commit="a" * 40,
        optimizer="test",
        optimizer_version="1",
        seed=1,
        master=ArtifactRef(path="master.png", sha256=digest, media_type="image/png"),
        protocol_id="RAC-PERSON-DETECT",
        surrogate_model_set="PERSON-SUR-v1",
        heldout_model_set="PERSON-HO-v1",
    )


def test_digital_certificate_passes_and_bundle_verifies(tmp_path: Path):
    protocol = load_protocol("protocols/RAC-PERSON-DETECT-1.0.json")
    bundle = ArtifactBundle.create(tmp_path / "bundle")
    bundle.write_json("digital/summary.json", {"heldout": {"baseline_detection_rate": 1.0, "candidate_detection_rate": 0.3}})
    cert = issue_certificate(
        bundle=bundle,
        manifest=manifest(tmp_path),
        protocol=protocol,
        digital_summary={
            "heldout": {"baseline_detection_rate": 1.0, "candidate_detection_rate": 0.3},
            "invalid_condition_fraction": 0.0,
        },
        requested_state=EvidenceState.DIGITAL_HELDOUT,
    )
    assert cert.decision == CertificateDecision.PASS
    ok, failures = verify_certificate_bundle(bundle.root)
    assert ok, failures


def test_physical_state_fails_closed_without_physical_evidence(tmp_path: Path):
    protocol = load_protocol("protocols/RAC-PERSON-DETECT-1.0.json")
    bundle = ArtifactBundle.create(tmp_path / "bundle")
    try:
        issue_certificate(
            bundle=bundle,
            manifest=manifest(tmp_path),
            protocol=protocol,
            digital_summary={
                "heldout": {"baseline_detection_rate": 1.0, "candidate_detection_rate": 0.3},
                "invalid_condition_fraction": 0.0,
            },
            requested_state=EvidenceState.PHYSICAL,
        )
    except ValueError as exc:
        assert "requires physical evidence" in str(exc)
    else:
        raise AssertionError("physical certificate must fail closed")


def test_physical_baseline_qualification_and_lot_conformity():
    from ruthless_pipeline.certification.physical import PhysicalTrial, summarize_physical_trials
    from ruthless_pipeline.certification.manufacturing import (
        ConformityLimits,
        ConformityMeasurement,
        evaluate_lot_conformity,
    )

    trials = [
        PhysicalTrial("T1", "C1", True, False, "CAM1", 3.0, 0, 0, "standing", "L1"),
        PhysicalTrial("T2", "C2", False, False, "CAM1", 8.0, 45, 0, "walking", "L1"),
    ]
    summary = summarize_physical_trials(trials)
    assert summary.valid_trials == 1
    assert summary.invalid_trials == 1
    assert summary.candidate_detection_rate == 0.0

    limits = ConformityLimits(3.0, 2.0, 5.0, 2.0)
    ok, failures = evaluate_lot_conformity(
        [ConformityMeasurement("S1", 1.0, 1.0, 2.0, 1.0)],
        limits,
    )
    assert ok
    assert failures == []
