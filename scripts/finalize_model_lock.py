from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # import-safe CLI entrypoint (E2)

import argparse
import json


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply a measured model-lock proposal to the preregistered benchmark manifest.")
    parser.add_argument("--proposal", required=True)
    parser.add_argument("--manifest", default="benchmarks/model_manifest.json")
    parser.add_argument("--surrogate-set", default="model_sets/PERSON-SUR-v1.json")
    parser.add_argument("--heldout-set", default="model_sets/PERSON-HO-v1.json")
    args = parser.parse_args()

    proposal_path = Path(args.proposal)
    manifest_path = Path(args.manifest)
    manifest = json.loads(manifest_path.read_text())
    proposal = json.loads(proposal_path.read_text())
    proposal_models = proposal.get("models", {})
    if not proposal_models:
        raise SystemExit("proposal contains no models")

    ids = {item["id"] for item in manifest["models"]}
    if ids != set(proposal_models):
        raise SystemExit("proposal model set does not match manifest")

    for item in manifest["models"]:
        locked = proposal_models[item["id"]]
        for field in ("model_ref", "framework", "role"):
            if str(item[field]) != str(locked[field]):
                raise SystemExit(f"{item['id']}: proposal {field} does not match manifest")
        threshold = float(locked["decision_threshold"])
        if float(item["decision_threshold"]) != threshold:
            raise SystemExit(f"{item['id']}: proposal threshold does not match manifest")
        digest = str(locked["state_dict_sha256"]).lower()
        if len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest):
            raise SystemExit(f"{item['id']}: invalid state_dict_sha256")
        item["state_dict_sha256"] = digest

    manifest["lock_source_commit"] = proposal.get("generated_from_commit")
    manifest["lock_status"] = "PREREGISTERED"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")

    for set_path in (Path(args.surrogate_set), Path(args.heldout_set)):
        payload = json.loads(set_path.read_text())
        payload["status"] = "PREREGISTERED"
        payload["lock_source_commit"] = proposal.get("generated_from_commit")
        set_path.write_text(json.dumps(payload, indent=2) + "\n")

    print("Model lock applied. Commit these files before running a D2 candidate benchmark.")
    print("Do not use the same candidate result that generated this proposal as certification evidence.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
