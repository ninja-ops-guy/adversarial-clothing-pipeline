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
        optimizer_version="2.1.0",
        seed=int(candidate_config["seed"]),
        master=ArtifactRef(path="pattern/master.png", sha256=master_sha, media_type="image/png"),
        protocol_id=protocol.protocol_id,
        surrogate_model_set=protocol.surrogate_model_set,
        heldout_model_set=protocol.heldout_model_set,
        evidence_state=EvidenceState.DESIGN,
        metadata={
            "pattern_type": candidate_config.get("patternType"),
            "pattern_scale": candidate_config.get("patternScale"),
            "color_palette": candidate_config.get("colorPalette"),
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
        bundle.write_json(f"manifests/models/{model_id}.json", json.loads(model_path.read_text()))
    for set_name in (protocol.surrogate_model_set, protocol.heldout_model_set):
        set_path = Path("model_sets") / f"{set_name}.json"
        if not set_path.exists():
            raise SystemExit(f"missing model set: {set_path}")
        set_payload = json.loads(set_path.read_text())
        if set_payload.get("status") != "PREREGISTERED":
            raise SystemExit(f"model set not preregistered: {set_name}")
        bundle.write_json(f"manifests/model_sets/{set_name}.json", set_payload)

    cert = issue_certificate(
        bundle=bundle,
        manifest=manifest,
        protocol=protocol,
        digital_summary=result["benchmark"]["comparative_summary"],
        requested_state=EvidenceState.DIGITAL_HELDOUT,
    )
    ok, failures = verify_certificate_bundle(bundle.root)
    status = {
        "candidate_id": candidate_id,
        "decision": cert.decision.value,
        "evidence_state": cert.evidence_state.value,
        "certificate_id": cert.certificate_id,
        "bundle_verified": ok,
        "verification_failures": failures,
        "heldout": result["benchmark"]["comparative_summary"].get("heldout", {}),
        "invalid_condition_fraction": result["benchmark"]["comparative_summary"].get("invalid_condition_fraction"),
    }
    Path("d2-latest-status.json").write_text(json.dumps(status, indent=2, sort_keys=True) + "\n")
    print(json.dumps(status, indent=2, sort_keys=True))
    if not ok:
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
