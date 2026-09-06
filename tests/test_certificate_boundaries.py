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
