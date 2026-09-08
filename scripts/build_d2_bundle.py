from __future__ import annotations

import argparse
import json
from pathlib import Path

from ruthless_pipeline.certification import (
    ArtifactBundle,
    ArtifactRef,
    EvidenceState,
    PatternManifest,
    hash_file,
    issue_certificate,
    load_protocol,
    verify_certificate_bundle,
)
from ruthless_pipeline.certification.experiment_status import (
    D2_STATUS_SCHEMA_VERSION,
    make_packaging_block,
    write_d2_status,
)


def _weight_reference_compatible(*, framework: str, frozen_ref: str, measured_ref: str) -> bool:
    """Accept only semantic aliases that cannot change the frozen model state.

    Torchvision's ``Weights.DEFAULT`` is an alias for a concrete enum member such
    as ``Weights.COCO_V1``. ``str(Weights.DEFAULT)`` therefore resolves to the
    concrete member at runtime even though the preregistered manifest correctly
    records ``DEFAULT``. The loaded state-dict SHA-256 remains the authoritative
    identity gate; this helper only prevents that documented alias from causing a
    false metadata mismatch.
    """
    frozen_ref = frozen_ref.strip()
    measured_ref = measured_ref.strip()
    if not frozen_ref or not measured_ref:
        return False
    if frozen_ref == measured_ref:
        return True
    if framework != "torchvision" or not frozen_ref.endswith(".DEFAULT"):
        return False
    frozen_enum = frozen_ref.rsplit(".", 1)[0]
    measured_enum = measured_ref.rsplit(".", 1)[0]
    return bool(frozen_enum) and frozen_enum == measured_enum


def verify_frozen_model_contract(model_id: str, model_manifest: dict, measured_model: dict) -> None:
    """Fail closed unless measured inference matches the preregistered model contract."""
    frozen_hash = str(model_manifest.get("weights_sha256", ""))
    measured_hash = str(measured_model.get("state_dict_sha256", ""))
    if frozen_hash != measured_hash:
        raise ValueError(f"frozen model manifest hash mismatch: {model_id}")

    if float(model_manifest.get("decision_threshold")) != float(measured_model.get("decision_threshold")):
        raise ValueError(f"frozen model threshold mismatch: {model_id}")

    framework = str(model_manifest.get("framework", ""))
    measured_framework = str(measured_model.get("framework", ""))
    if framework != measured_framework:
        raise ValueError(f"frozen model framework mismatch: {model_id}")

    frozen_version = str(model_manifest.get("framework_version", ""))
    measured_version = str(measured_model.get("framework_version", ""))
    if frozen_version != measured_version:
        raise ValueError(
            f"frozen model framework version mismatch: {model_id}: "
            f"{frozen_version} != {measured_version}"
        )

    preprocessing = model_manifest.get("preprocessing")
    if not isinstance(preprocessing, dict) or not preprocessing:
        raise ValueError(f"missing frozen preprocessing contract: {model_id}")

    frozen_ref = str(model_manifest.get("weights_id", ""))
    measured_ref = str(measured_model.get("model_ref", ""))
    if frozen_ref and not _weight_reference_compatible(
        framework=framework,
        frozen_ref=frozen_ref,
        measured_ref=measured_ref,
    ):
        raise ValueError(
            f"frozen model reference mismatch: {model_id}: {frozen_ref} != {measured_ref}"
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the first RAC-D2 evidence bundle from a locked measured benchmark.")
    parser.add_argument("--result", default="benchmark-results.json")
    parser.add_argument("--candidate", default="benchmarks/runtime/candidate.png")
    parser.add_argument("--protocol", default="protocols/RAC-PERSON-DETECT-1.0.json")
    parser.add_argument("--output", default="certification_artifacts/latest-d2")
    args = parser.parse_args()

    result_path = Path(args.result)
    candidate_path = Path(args.candidate)
    result = json.loads(result_path.read_text())
    candidate_config = result["candidate"]["config"]
    candidate_id = candidate_config.get("candidate_id")
    if not candidate_id:
        raise SystemExit("candidate_id is required for D2")
    if result.get("status") != "measured_locked" or not result.get("certification_eligible"):
        raise SystemExit("D2 blocked: detector ensemble is not preregistered and hash-matched")

    protocol = load_protocol(args.protocol)
    bundle = ArtifactBundle.create(args.output)

    master_sha = hash_file(candidate_path)
    if master_sha != result["candidate"]["sha256"]:
        raise SystemExit("candidate hash mismatch between benchmark result and exported master")

    manifest = PatternManifest(
        pattern_id=candidate_id,
        version="1.0.0",
        task="person_detection",
        source_commit=result["source_commit"],
        optimizer="PatternLabDeterministicGenerator",
        optimizer_version="3.0.0",
        seed=int(candidate_config["seed"]),
        master=ArtifactRef(path="pattern/master.png", sha256=master_sha, media_type="image/png"),
        protocol_id=protocol.protocol_id,
        surrogate_model_set=protocol.surrogate_model_set,
        heldout_model_set=protocol.heldout_model_set,
        evidence_state=EvidenceState.DESIGN,
        metadata={
            "pattern_type": candidate_config.get("patternType"),
            "pattern_family": candidate_config.get("family"),
            "pattern_scale": candidate_config.get("patternScale"),
            "color_palette": candidate_config.get("colorPalette"),
            "design_variant": candidate_config.get("design_variant"),
            "art_direction_profile": candidate_config.get("art_direction_profile"),
            "source_candidate_id": candidate_config.get("source_candidate_id"),
            "evidence_scope": result.get("evidence_scope"),
        },
    )

    (bundle.root / "pattern").mkdir(parents=True, exist_ok=True)
    (bundle.root / "pattern" / "master.png").write_bytes(candidate_path.read_bytes())
    bundle.write_json("manifests/pattern.json", json.loads(manifest.canonical_json().decode()))
    bundle.write_json("manifests/protocol.json", json.loads(Path(args.protocol).read_text()))
    bundle.write_json("digital/benchmark-results.json", result)
    bundle.write_json("digital/summary.json", result["benchmark"]["comparative_summary"])
    bundle.write_json("digital/model-lock.json", result["model_lock"])
    for model_id in result["benchmark"]["surrogate_models"] + result["benchmark"]["heldout_models"]:
        model_path = Path("model_manifests") / f"{model_id}.json"
        if not model_path.exists():
            raise SystemExit(f"missing frozen model manifest: {model_path}")
        model_manifest = json.loads(model_path.read_text())
        measured_model = result["models"][model_id]
        try:
            verify_frozen_model_contract(model_id, model_manifest, measured_model)
        except ValueError as exc:
            raise SystemExit(str(exc)) from exc
        bundle.write_json(f"manifests/models/{model_id}.json", model_manifest)

    expected_sets = {
        protocol.surrogate_model_set: list(result["benchmark"]["surrogate_models"]),
        protocol.heldout_model_set: list(result["benchmark"]["heldout_models"]),
    }
    for set_name, measured_members in expected_sets.items():
        set_path = Path("model_sets") / f"{set_name}.json"
        if not set_path.exists():
            raise SystemExit(f"missing model set: {set_path}")
        set_payload = json.loads(set_path.read_text())
        if set_payload.get("status") != "PREREGISTERED":
            raise SystemExit(f"model set not preregistered: {set_path}")
        if list(set_payload.get("models", [])) != measured_members:
            raise SystemExit(f"model-set membership mismatch for {set_name}")
        bundle.write_json(f"manifests/model_sets/{set_name}.json", set_payload)

    cert = issue_certificate(
        bundle=bundle,
        manifest=manifest,
        protocol=protocol,
        digital_summary=result["benchmark"]["comparative_summary"],
        requested_state=EvidenceState.DIGITAL_HELDOUT,
    )
    ok, failures = verify_certificate_bundle(bundle.root)
    # Scientific fields are sealed from the verified evidence FIRST. Packaging
    # is a downstream, non-scientific concern recorded in a separate block
    # (status format 1.0); a packaging failure can never overwrite the
    # decision/evidence_state below.
    status = {
        "schema_version": D2_STATUS_SCHEMA_VERSION,
        "packaging": make_packaging_block(),
        "candidate_id": candidate_id,
        "protocol_id": protocol.protocol_id,
        "protocol_version": protocol.version,
        "surrogate_model_set": protocol.surrogate_model_set,
        "heldout_model_set": protocol.heldout_model_set,
        "source_commit": result["source_commit"],
        "decision": cert.decision.value,
        "evidence_state": cert.evidence_state.value,
        "certificate_id": cert.certificate_id,
        "bundle_verified": ok,
        "verification_failures": failures,
        "heldout": result["benchmark"]["comparative_summary"].get("heldout", {}),
        "invalid_condition_fraction": result["benchmark"]["comparative_summary"].get("invalid_condition_fraction"),
    }
    write_d2_status("d2-latest-status.json", status)
    print(json.dumps(status, indent=2, sort_keys=True))
    if not ok:
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
