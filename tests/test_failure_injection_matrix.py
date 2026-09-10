"""Failure-injection matrix.

Every case injects one fault and asserts the pipeline FAILS CLOSED — an
explicit error or refusal — instead of silently recovering. Where the current
code does not yet refuse, the test asserts the DESIRED refusal and is marked
``xfail(strict=True)`` with a linked issue note; the day the guard lands, the
XPASS itself fails the suite (strict) and the marker must be removed.

Boundary: synthetic fixtures only; no held-out access, no D2-0004/D2-0005
modification, synthetic evidence never promotes to measured.
"""

from __future__ import annotations

import hashlib
import json
import sys
from dataclasses import asdict
from pathlib import Path

import jsonschema
import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ruthless_pipeline.certification import numerical_verification as nv
from ruthless_pipeline.certification.evidence import (
    EvidenceRecord,
    EvidenceType,
    require_evidence_for_state,
)
from ruthless_pipeline.certification.manifest import EvidenceState
from ruthless_pipeline.certification.objectives import cvar, mean_objective
from ruthless_pipeline.certification.provenance_graph import verify_graph
from ruthless_pipeline.certification.registry import ModelManifest, ModelRegistry
from ruthless_pipeline.certification.schema_version import (
    SchemaVersionError,
    require_schema_version,
)
from ruthless_pipeline.certification.verification import verify_certificate_bundle
from ruthless_pipeline.evidence_classes_ext import (
    SYNTHETIC_PIPELINE_VALIDATION_ONLY,
    permits_physical_efficacy_claim,
)
from ruthless_pipeline.physical_protocol import capture_rows

ISSUE_BASE = "https://github.com/ninja-ops-guy/adversarial-clothing-pipeline/issues"


def _manifest(model_id: str = "m-1") -> ModelManifest:
    return ModelManifest(
        model_id=model_id,
        architecture="fixture-arch",
        weights_id="fixture-weights",
        weights_sha256=hashlib.sha256(model_id.encode()).hexdigest(),
        framework="fixture",
        framework_version="0.0",
        preprocessing={},
        target_class="person",
        class_label=1,
        decision_threshold=0.5,
    )


# ---------------------------------------------------------------------------
# 1. missing artwork / 2. wrong artwork hash / 7. corrupt checkpoint
#    (certificate-bundle hash manifest + checkpoint integrity pin)
# ---------------------------------------------------------------------------


def _bundle(root: Path, files: dict[str, bytes], manifest: dict[str, str]) -> Path:
    """Write files + a hashes.sha256 manifest (digest<two spaces>relpath)."""
    for rel, payload in files.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
    lines = [f"{digest}  {rel}" for digest, rel in manifest.items()]
    (root / "hashes.sha256").write_text("\n".join(lines) + "\n")
    return root


def test_missing_artwork_fails_closed(tmp_path):
    digest = hashlib.sha256(b"artwork").hexdigest()
    _bundle(tmp_path, {}, {digest: "artwork/candidate.png"})
    ok, failures = verify_certificate_bundle(tmp_path)
    assert not ok
    assert any("missing artifact" in f for f in failures)


def test_wrong_artwork_hash_fails_closed(tmp_path):
    _bundle(
        tmp_path,
        {"artwork/candidate.png": b"actual-bytes"},
        {hashlib.sha256(b"attacker-bytes").hexdigest(): "artwork/candidate.png"},
    )
    ok, failures = verify_certificate_bundle(tmp_path)
    assert not ok
    assert any("hash mismatch" in f for f in failures)


def test_corrupt_checkpoint_fails_closed(tmp_path):
    payload = b"checkpoint-v1"
    path = tmp_path / "model.ckpt"
    path.write_bytes(payload)
    pin = hashlib.sha256(payload).hexdigest()
    assert nv.verify_checkpoint_integrity(path, pin) == pin  # intact: passes
    path.write_bytes(b"checkpoint-v1-tampered")
    with pytest.raises(nv.CheckpointIntegrityError):
        nv.verify_checkpoint_integrity(path, pin)


def test_missing_checkpoint_fails_closed(tmp_path):
    pin = hashlib.sha256(b"x").hexdigest()
    with pytest.raises(nv.CheckpointIntegrityError):
        nv.verify_checkpoint_integrity(tmp_path / "gone.ckpt", pin)


# ---------------------------------------------------------------------------
# 3. wrong template hash (print-alpha template manifest, frozen contract)
# ---------------------------------------------------------------------------


def _template_manifest(template_sha256: str) -> dict:
    return {
        "schema_version": "1.0",
        "manifest_id": "fixture-template",
        "template_archive_sha256": template_sha256,
        "panel_geometry": {"front": {}},
        "evidence_class": "experimental_print_specimen",
        "physical_efficacy_claimed": False,
    }


def test_wrong_template_hash_fails_closed():
    from scripts_print_alpha.validate_manifests import _TEMPLATE_SCHEMA

    # A hash that is neither a real SHA-256 nor the PENDING_USER_ACTION
    # literal must be rejected outright (fail closed), not coerced.
    bad = _template_manifest("deadbeef-not-a-sha256")
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=bad, schema=_TEMPLATE_SCHEMA)
    # sanity: a real digest validates
    jsonschema.validate(
        instance=_template_manifest(hashlib.sha256(b"tpl").hexdigest()),
        schema=_TEMPLATE_SCHEMA,
    )


# ---------------------------------------------------------------------------
# 4. invalid schema version
# ---------------------------------------------------------------------------


def test_invalid_schema_version_fails_closed():
    with pytest.raises(SchemaVersionError):
        require_schema_version({"schema_version": "99.0"}, "1.0", label="fixture")
    with pytest.raises(SchemaVersionError):
        require_schema_version({"no_version": True}, "1.0", label="fixture")
    with pytest.raises(SchemaVersionError):
        require_schema_version(["not", "a", "mapping"], "1.0", label="fixture")


# ---------------------------------------------------------------------------
# 5. missing model reference / 6. duplicate fixture
# ---------------------------------------------------------------------------


def test_missing_model_reference_fails_closed():
    registry = ModelRegistry([_manifest("m-1")])
    with pytest.raises(KeyError):
        registry.require(["m-1", "ghost-model"])
    # benchmark construction also refuses missing evaluators
    import torch  # noqa: F401

    from ruthless_pipeline.benchmark import BenchmarkConfig, ComparativeBenchmark

    with pytest.raises(ValueError, match="Missing evaluators"):
        ComparativeBenchmark(
            BenchmarkConfig(surrogate_models=("ghost",), device="cpu"), []
        )


def test_duplicate_fixture_fails_closed(tmp_path):
    # duplicate model manifests are refused at registry construction
    with pytest.raises(ValueError, match="duplicate model_id"):
        ModelRegistry([_manifest("m-1"), _manifest("m-1")])
    # duplicate trial fixtures are refused when loading the trial store
    from scripts.ingest_capture_inference import (
        P1_EVIDENCE_CLASS,
        append_trial_store,
        load_trial_store,
    )
    from ruthless_pipeline.certification.physical import PhysicalTrial

    trial = PhysicalTrial(
        trial_id="SESSION-1:still",
        condition_id="fixture",
        control_detected=True,
        candidate_detected=False,
        camera_id="cam-0",
        distance_m=5.0,
        yaw_deg=0.0,
        pitch_deg=0.0,
        pose="standing",
        lighting_id="indoor-even",
        wash_state="W0",
    )
    store = tmp_path / "trial-store.jsonl"
    prev = None
    for _ in range(2):
        record = {
            "schema_version": "1.0",
            "trial": asdict(trial),
            "trial_record": {},
            "evidence_class": P1_EVIDENCE_CLASS,
            "calibration_pass": True,
            "lineage": {},
            "prev_record_sha256": prev,
        }
        append_trial_store(store, record)
        prev = hashlib.sha256(
            store.read_text().splitlines()[-1].encode()
        ).hexdigest()
    with pytest.raises(ValueError, match="duplicate trial_id"):
        load_trial_store(store)


def test_trial_store_hash_chain_break_fails_closed(tmp_path):
    """Tampering with the cumulative store's hash chain is refused."""
    from scripts.ingest_capture_inference import append_trial_store, load_trial_store
    from ruthless_pipeline.certification.physical import PhysicalTrial

    store = tmp_path / "trial-store.jsonl"
    prev = None
    for i in range(2):
        trial = PhysicalTrial(
            trial_id=f"S{i}:still", condition_id="fixture", control_detected=True,
            candidate_detected=False, camera_id="cam-0", distance_m=5.0,
            yaw_deg=0.0, pitch_deg=0.0, pose="standing",
            lighting_id="indoor-even", wash_state="W0",
        )
        record = {
            "schema_version": "1.0", "trial": asdict(trial), "trial_record": {},
            "evidence_class": "physical_garment_p1", "calibration_pass": True,
            "lineage": {}, "prev_record_sha256": prev,
        }
        append_trial_store(store, record)
        prev = hashlib.sha256(store.read_text().splitlines()[-1].encode()).hexdigest()
    lines = store.read_text().splitlines()
    lines[0] = lines[0].replace("S0:still", "S0-tampered:still")
    store.write_text("\n".join(lines) + "\n")
    with pytest.raises(ValueError, match="hash-chain break"):
        load_trial_store(store)


# ---------------------------------------------------------------------------
# 8. NaN objective
# ---------------------------------------------------------------------------


def test_nan_objective_fails_closed():
    with pytest.raises(ValueError):
        cvar([0.2, float("nan"), 0.4], 0.5)
    with pytest.raises(ValueError):
        mean_objective([float("inf"), 0.5])
    with pytest.raises(nv.NonFiniteValueError):
        nv.require_finite([0.5, float("nan")])
    # objective telemetry path must not silently propagate NaN either
    from scripts.select_surrogate_candidate import build_objective_telemetry
    from ruthless_pipeline.certification.objectives import ObjectiveSpec

    record = {
        "candidate_id": "cand-x",
        "per_surrogate_detection_rates": {"sur-0": float("nan")},
    }
    with pytest.raises(ValueError):
        build_objective_telemetry(
            [record], objective=ObjectiveSpec(name="cvar", alpha=0.5), alpha=0.5
        )


# ---------------------------------------------------------------------------
# 9. invalid transformation distribution (frozen Barrier 1 schema)
# ---------------------------------------------------------------------------


def _distribution_manifest(dist: dict) -> dict:
    """Minimal manifest satisfying the frozen transformation-distribution
    schema, with ``dist`` stamped into every distribution slot."""
    geometry = ["scale", "camera_distance", "perspective", "yaw", "pitch", "roll", "translation"]
    imaging = ["blur", "resize_interpolation", "compression", "exposure", "contrast"]
    garment = ["stretch", "wrinkle", "fold", "bend", "partial_occlusion"]
    print_capture = ["gamut_mapping", "resolution_loss"]
    return {
        "schema_version": "1.0",
        "distribution_id": "fixture-dist",
        "seed": 1234,
        "sampling_reproducibility_note": "fixture: samples reproducible from (distribution_id, manifest, seed, index)",
        "parameter_manifest": {
            "geometry": {name: dict(dist) for name in geometry},
            "imaging": {name: dict(dist) for name in imaging},
            "garment": {name: dict(dist) for name in garment},
            "print_capture": {name: dict(dist) for name in print_capture},
        },
        "robustness_surface": {
            "grid_axes": ["scale"],
            "response_metric": "detection_rate",
            "cell_value_type": "vector",
            "scalar_only_permitted": False,
        },
    }


def test_invalid_transformation_distribution_fails_closed():
    schema = json.loads(
        (ROOT / "schemas" / "transformation_distribution.schema.json").read_text()
    )
    valid = _distribution_manifest({"type": "uniform", "params": {"min": 0.9, "max": 1.1}})
    jsonschema.validate(instance=valid, schema=schema)  # sanity: fixture is well-formed

    # unknown distribution type at every slot
    invalid = _distribution_manifest({"type": "evaporate", "params": {"min": 0, "max": 1}})
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=invalid, schema=schema)
    # unknown distribution type nested inside an otherwise valid manifest
    bad = json.loads(json.dumps(valid))
    bad["parameter_manifest"]["geometry"]["scale"] = {"type": "sideways", "params": {"x": 1}}
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=bad, schema=schema)
    # a distribution missing its params is refused
    bad2 = json.loads(json.dumps(valid))
    bad2["parameter_manifest"]["imaging"]["blur"] = {"type": "normal"}
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=bad2, schema=schema)


# ---------------------------------------------------------------------------
# 10. unknown detector family
# ---------------------------------------------------------------------------


def test_unknown_detector_family_fails_closed():
    from scripts.run_measured_benchmark import build_evaluators

    manifest = {
        "models": [
            {
                "id": "definitely_not_a_supported_detector",
                "role": "surrogate",
                "display_name": "fixture",
                "framework": "fixture",
                "model_ref": "fixture://unknown",
                "person_class": 1,
                "decision_threshold": 0.5,
            }
        ]
    }
    with pytest.raises(ValueError, match="Unsupported model id"):
        build_evaluators(manifest, roles={"surrogate"})


# ---------------------------------------------------------------------------
# 11. missing provenance edge (verify_graph on a tampered copy)
# ---------------------------------------------------------------------------


def _mini_graph(root: Path, *, target_present: bool, tamper: bool = False) -> dict:
    payload = b"attested-content"
    if target_present:
        (root / "record.json").write_bytes(b"tampered" if tamper else payload)
    return {
        "schema_id": "rac-provenance-graph",
        "schema_version": "1.0",
        "nodes": [
            {"id": "src", "type": "document"},
            {"id": "dst", "type": "inference_record", "path": "record.json"},
        ],
        "edges": [
            {
                "id": "src->dst",
                "source": "src",
                "target": "dst",
                "verify_mode": "file_hash",
                "expected_sha256": hashlib.sha256(payload).hexdigest(),
                "hash_pin_expected": True,
            }
        ],
    }


def test_missing_provenance_edge_target_detected(tmp_path):
    report = verify_graph(_mini_graph(tmp_path, target_present=False), repo_root=tmp_path)
    assert report["summary"]["MISSING"] == 1
    assert report["unexpected_edges"] == ["src->dst"]


def test_tampered_provenance_edge_detected(tmp_path):
    report = verify_graph(
        _mini_graph(tmp_path, target_present=True, tamper=True), repo_root=tmp_path
    )
    assert report["summary"]["BROKEN"] == 1
    assert report["unexpected_edges"] == ["src->dst"]
    # and the untampered copy verifies clean
    clean = verify_graph(
        _mini_graph(tmp_path, target_present=True, tamper=False), repo_root=tmp_path
    )
    assert clean["summary"]["VERIFIED"] == 1
    assert clean["unexpected_edges"] == []


def test_provenance_graph_rejects_wrong_schema(tmp_path):
    graph = _mini_graph(tmp_path, target_present=True)
    graph["schema_id"] = "forged-graph"
    with pytest.raises(ValueError):
        verify_graph(graph, repo_root=tmp_path)


# ---------------------------------------------------------------------------
# 12. synthetic evidence labeled measured (promotion guards)
# ---------------------------------------------------------------------------


def _evidence_record(rac_state, evidence_type) -> EvidenceRecord:
    return EvidenceRecord(
        rac_state=rac_state,
        evidence_type=evidence_type,
        source="fixture",
        fixture_type="fixture",
        created_at="2026-01-01T00:00:00Z",
        code_commit="0" * 40,
        configuration={},
        artifact_hashes={"fixture.json": hashlib.sha256(b"f").hexdigest()},
        model_metadata={
            "models": ["m-1"], "preprocessing": {}, "thresholds": {"m-1": 0.5}
        },
    )


def test_synthetic_labeled_measured_fails_closed():
    # a digital record presented as PHYSICAL (measured) evidence is refused
    with pytest.raises(ValueError):
        _evidence_record(EvidenceState.PHYSICAL, EvidenceType.DIGITAL).validate()
    # no physical evidence -> physical state unreachable
    with pytest.raises(ValueError):
        require_evidence_for_state(
            EvidenceState.PHYSICAL,
            [_evidence_record(EvidenceState.SURROGATE, EvidenceType.DIGITAL)],
        )
    # the synthetic class can never ground a physical efficacy claim
    assert permits_physical_efficacy_claim(SYNTHETIC_PIPELINE_VALIDATION_ONLY) is False


def test_synthetic_session_blocked_from_measured_trial_store():
    from scripts.ingest_capture_inference import enforce_promotion_gate

    with pytest.raises(ValueError, match="promotion gate"):
        enforce_promotion_gate(
            {
                "evidence_class": SYNTHETIC_PIPELINE_VALIDATION_ONLY,
                "calibration_pass": True,
            }
        )
    with pytest.raises(ValueError, match="promotion gate"):
        enforce_promotion_gate(
            {"evidence_class": "physical_garment_p1", "calibration_pass": False}
        )


# ---------------------------------------------------------------------------
# 13. candidate/control mismatch
# ---------------------------------------------------------------------------


def test_capture_rows_are_matched_pairs_by_construction():
    """The preregistered capture matrix pairs control/candidate per trial id."""
    rows = capture_rows()
    assert len(rows) == 108
    for row in rows:
        assert row["control_file"].endswith(f"{row['trial_id']}__control.jpg")
        assert row["candidate_file"].endswith(f"{row['trial_id']}__candidate.jpg")
        assert row["control_file"] != row["candidate_file"]


def test_candidate_control_mismatch_fails_closed():
    """Guard implemented in scripts_print_alpha.validate_manifests
    (validate_mapping_pairing): a concrete candidate/control collision is
    rejected with jsonschema.ValidationError. Fixture carries a valid source
    pin so the pairing collision is the sole injected fault."""
    from scripts_print_alpha.validate_manifests import validate_mapping_pairing

    mapping = {
        "schema_version": "1.0",
        "manifest_id": "fixture-mapping",
        "evidence_class": "experimental_print_specimen",
        "physical_efficacy_claimed": False,
        "source_manifest_ref": "sku-manifest.json",
        "source_manifest_sha256": "0" * 64,
        "placements": [
            {
                "placement": "front",
                "control_file": "same-file.jpg",
                "candidate_file": "same-file.jpg",
                "panel_geometry_ref": "front",
            }
        ],
    }
    with pytest.raises(jsonschema.ValidationError):
        validate_mapping_pairing(mapping)


# ---------------------------------------------------------------------------
# 14. stale production mapping
# ---------------------------------------------------------------------------


def test_stale_production_mapping_fails_closed(tmp_path):
    """Guard implemented in scripts_print_alpha.validate_manifests
    (validate_mapping_source_pin): the mapping manifest is pinned to the
    exact bytes of its source manifest; a stale pin is rejected with
    jsonschema.ValidationError. Fixture uses an otherwise-valid mapping so
    the stale pin is the sole injected fault."""
    from scripts_print_alpha.validate_manifests import validate_mapping_source_pin

    source = tmp_path / "sku-manifest.json"
    source.write_text(json.dumps({"garments": ["v1"]}))
    stale_pin = hashlib.sha256(b'{"garments": ["v0"]}').hexdigest()
    mapping = {
        "schema_version": "1.0",
        "manifest_id": "fixture-mapping",
        "evidence_class": "experimental_print_specimen",
        "physical_efficacy_claimed": False,
        "source_manifest_ref": "sku-manifest.json",
        "source_manifest_sha256": stale_pin,  # pin of a superseded source state
        "placements": [
            {
                "placement": "front",
                "control_file": "c.jpg",
                "candidate_file": "p.jpg",
                "panel_geometry_ref": "front",
            }
        ],
    }
    with pytest.raises(jsonschema.ValidationError):
        validate_mapping_source_pin(mapping, source)
