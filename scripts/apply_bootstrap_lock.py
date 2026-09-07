from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _is_sha256(value: str) -> bool:
    if len(value) != 64:
        return False
    try:
        int(value, 16)
    except ValueError:
        return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Apply a no-inference detector lock proposal to the current preregistered generation."
    )
    parser.add_argument("--proposal", default="benchmarks/model-lock-proposal.json")
    parser.add_argument("--manifest", default="benchmarks/model_manifest.json")
    args = parser.parse_args()

    proposal_path = ROOT / args.proposal
    manifest_path = ROOT / args.manifest
    proposal = json.loads(proposal_path.read_text())
    manifest = json.loads(manifest_path.read_text())

    if proposal.get("inference_performed") is not False:
        raise SystemExit("lock proposal must certify inference_performed=false")

    proposed = proposal.get("models", {})
    model_ids = [item["id"] for item in manifest["models"]]
    if set(model_ids) != set(proposed):
        raise SystemExit("proposal model set does not match current manifest")

    for item in manifest["models"]:
        locked = proposed[item["id"]]
        for field in ("model_ref", "framework", "role"):
            if str(item.get(field)) != str(locked.get(field)):
                raise SystemExit(f"{item['id']}: proposal {field} mismatch")
        if float(item["decision_threshold"]) != float(locked["decision_threshold"]):
            raise SystemExit(f"{item['id']}: proposal threshold mismatch")
        digest = str(locked["state_dict_sha256"]).lower()
        if not _is_sha256(digest):
            raise SystemExit(f"{item['id']}: invalid state_dict_sha256")
        item["state_dict_sha256"] = digest

    source_commit = str(proposal.get("generated_from_commit") or "")
    if not source_commit:
        raise SystemExit("proposal missing generated_from_commit")

    manifest["lock_status"] = "PREREGISTERED"
    manifest["lock_source_commit"] = source_commit
    manifest["lock_inference_performed"] = False
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")

    set_names = (manifest.get("surrogate_model_set"), manifest.get("heldout_model_set"))
    for set_name in set_names:
        if not set_name:
            raise SystemExit("manifest missing model-set identifiers")
        set_path = ROOT / "model_sets" / f"{set_name}.json"
        payload = json.loads(set_path.read_text())
        payload["status"] = "PREREGISTERED"
        payload["lock_source_commit"] = source_commit
        if payload.get("role") == "heldout":
            payload["candidate_inference_performed"] = False
        set_path.write_text(json.dumps(payload, indent=2) + "\n")

    for item in manifest["models"]:
        locked = proposed[item["id"]]
        out = ROOT / "model_manifests" / f"{item['id']}.json"
        existing = json.loads(out.read_text()) if out.exists() else {}
        payload = {
            "model_id": item["id"],
            "architecture": item["display_name"],
            "weights_id": item["model_ref"],
            "weights_sha256": item["state_dict_sha256"],
            "framework": item["framework"],
            "framework_version": locked["framework_version"],
            "preprocessing": existing.get(
                "preprocessing",
                {
                    "source": "model runtime internal transform",
                    "input": "float32 RGB tensors [0,1]",
                    "device": "cpu",
                },
            ),
            "target_class": "person",
            "class_label": item["person_class"],
            "decision_threshold": float(item["decision_threshold"]),
            "nms_threshold": existing.get("nms_threshold"),
            "metadata": {
                **existing.get("metadata", {}),
                "hash_scope": "loaded_state_dict",
                "lock_source_commit": source_commit,
                "generation_id": manifest.get("generation_id"),
                "role_source": "model_sets/*; role is generation-specific",
                "candidate_inference_performed_during_lock": False,
            },
        }
        out.write_text(json.dumps(payload, indent=2) + "\n")

    print(
        json.dumps(
            {
                "generation_id": manifest.get("generation_id"),
                "lock_source_commit": source_commit,
                "surrogate_model_set": manifest.get("surrogate_model_set"),
                "heldout_model_set": manifest.get("heldout_model_set"),
                "models": model_ids,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
