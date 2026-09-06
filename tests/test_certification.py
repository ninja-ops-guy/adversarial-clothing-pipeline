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
    (bundle.root / "master.png").write_bytes(b"pattern")
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
    (bundle.root / "master.png").write_bytes(b"pattern")
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


def test_bundle_verification_detects_certificate_tampering(tmp_path: Path):
    protocol = load_protocol("protocols/RAC-PERSON-DETECT-1.0.json")
    bundle = ArtifactBundle.create(tmp_path / "bundle-tamper")
    (bundle.root / "master.png").write_bytes(b"pattern")
    bundle.write_json(
        "digital/summary.json",
        {"heldout": {"baseline_detection_rate": 1.0, "candidate_detection_rate": 0.3}},
    )
    issue_certificate(
        bundle=bundle,
        manifest=manifest(tmp_path),
        protocol=protocol,
        digital_summary={
            "heldout": {"baseline_detection_rate": 1.0, "candidate_detection_rate": 0.3},
            "invalid_condition_fraction": 0.0,
        },
        requested_state=EvidenceState.DIGITAL_HELDOUT,
    )
    certificate_path = bundle.root / "certificate.json"
    certificate_path.write_text(certificate_path.read_text().replace('"PASS"', '"FAIL"', 1))

    ok, failures = verify_certificate_bundle(bundle.root)
    assert not ok
    assert "hash mismatch: certificate.json" in failures


def test_bundle_verification_rejects_malformed_hash_manifest(tmp_path: Path):
    root = tmp_path / "bad-bundle"
    root.mkdir()
    (root / "hashes.sha256").write_text("not-a-valid-hash-line\n")
    ok, failures = verify_certificate_bundle(root)
    assert not ok
    assert "malformed hash manifest line 1" in failures


def test_bundle_verification_rejects_path_traversal(tmp_path: Path):
    root = tmp_path / "bad-path-bundle"
    root.mkdir()
    (root / "hashes.sha256").write_text(("0" * 64) + "  ../outside.txt\n")
    ok, failures = verify_certificate_bundle(root)
    assert not ok
    assert "invalid artifact path on line 1" in failures


def test_certificate_issuance_rejects_missing_or_forged_master(tmp_path: Path):
    protocol = load_protocol("protocols/RAC-PERSON-DETECT-1.0.json")
    digital = {
        "heldout": {"baseline_detection_rate": 1.0, "candidate_detection_rate": 0.3},
        "invalid_condition_fraction": 0.0,
    }

    missing_bundle = ArtifactBundle.create(tmp_path / "missing-master")
    try:
        issue_certificate(
            bundle=missing_bundle,
            manifest=manifest(tmp_path),
            protocol=protocol,
            digital_summary=digital,
            requested_state=EvidenceState.DIGITAL_HELDOUT,
        )
    except ValueError as exc:
        assert "missing master artifact" in str(exc)
    else:
        raise AssertionError("certificate issuance must require the bundled master artifact")

    forged_bundle = ArtifactBundle.create(tmp_path / "forged-master")
    (forged_bundle.root / "master.png").write_bytes(b"forged")
    try:
        issue_certificate(
            bundle=forged_bundle,
            manifest=manifest(tmp_path),
            protocol=protocol,
            digital_summary=digital,
            requested_state=EvidenceState.DIGITAL_HELDOUT,
        )
    except ValueError as exc:
        assert "master artifact hash mismatch" in str(exc)
    else:
        raise AssertionError("certificate issuance must verify the master hash")


def test_physical_flag_alone_cannot_unlock_p1(tmp_path: Path):
    protocol = load_protocol("protocols/RAC-PERSON-DETECT-1.0.json")
    bundle = ArtifactBundle.create(tmp_path / "p1-flag-only")
    (bundle.root / "master.png").write_bytes(b"pattern")
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
            physical_evidence_present=True,
        )
    except ValueError as exc:
        assert "requires bundled physical evidence artifacts" in str(exc)
    else:
        raise AssertionError("physical boolean flag must not substitute for artifacts")


def test_manufacturing_flag_alone_cannot_unlock_m1(tmp_path: Path):
    protocol = load_protocol("protocols/RAC-PERSON-DETECT-1.0.json")
    bundle = ArtifactBundle.create(tmp_path / "m1-flag-only")
    (bundle.root / "master.png").write_bytes(b"pattern")
    (bundle.root / "physical").mkdir()
    (bundle.root / "physical" / "summary.json").write_text("{}")
    (bundle.root / "physical" / "trials.csv").write_text("trial_id\n")
    try:
        issue_certificate(
            bundle=bundle,
            manifest=manifest(tmp_path),
            protocol=protocol,
            digital_summary={
                "heldout": {"baseline_detection_rate": 1.0, "candidate_detection_rate": 0.3},
                "invalid_condition_fraction": 0.0,
            },
            requested_state=EvidenceState.GOLDEN_SAMPLE,
            physical_evidence_present=True,
            manufacturing_evidence_present=True,
        )
    except ValueError as exc:
        assert "manufacturing/golden_sample.json" in str(exc)
    else:
        raise AssertionError("manufacturing boolean flag must not substitute for artifacts")


def test_physical_trials_reject_nonfinite_and_duplicate_ids():
    import math
    from ruthless_pipeline.certification.physical import PhysicalTrial, summarize_physical_trials

    bad = [
        PhysicalTrial("T1", "C1", True, False, "CAM1", math.nan, 0, 0, "standing", "L1"),
    ]
    try:
        summarize_physical_trials(bad)
    except ValueError as exc:
        assert "must be finite" in str(exc)
    else:
        raise AssertionError("non-finite physical measurements must fail")

    dup = [
        PhysicalTrial("T1", "C1", True, False, "CAM1", 1.0, 0, 0, "standing", "L1"),
        PhysicalTrial("T1", "C2", True, False, "CAM1", 2.0, 0, 0, "walking", "L1"),
    ]
    try:
        summarize_physical_trials(dup)
    except ValueError as exc:
        assert "duplicate trial_id" in str(exc)
    else:
        raise AssertionError("duplicate physical trial ids must fail")


def test_manufacturing_rejects_nonfinite_measurements_duplicate_ids_and_bad_limits():
    import math
    from ruthless_pipeline.certification.manufacturing import (
        ConformityLimits,
        ConformityMeasurement,
        evaluate_lot_conformity,
    )

    limits = ConformityLimits(3.0, 2.0, 5.0, 2.0)
    ok, failures = evaluate_lot_conformity(
        [ConformityMeasurement("S1", math.nan, 0.0, 0.0, 0.0)],
        limits,
    )
    assert not ok
    assert "S1: non-finite measurement" in failures

    try:
        evaluate_lot_conformity(
            [
                ConformityMeasurement("S1", 1.0, 0.0, 0.0, 0.0),
                ConformityMeasurement("S1", 1.0, 0.0, 0.0, 0.0),
            ],
            limits,
        )
    except ValueError as exc:
        assert "duplicate sample_id" in str(exc)
    else:
        raise AssertionError("duplicate manufacturing sample ids must fail")

    try:
        evaluate_lot_conformity(
            [ConformityMeasurement("S2", 1.0, 0.0, 0.0, 0.0)],
            ConformityLimits(-1.0, 2.0, 5.0, 2.0),
        )
    except ValueError as exc:
        assert "finite and nonnegative" in str(exc)
    else:
        raise AssertionError("negative manufacturing limits must fail")
