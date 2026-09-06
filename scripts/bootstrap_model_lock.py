from __future__ import annotations

import json
import os
from pathlib import Path

from scripts.run_measured_benchmark import build_evaluators

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    manifest_path = ROOT / "benchmarks/model_manifest.json"
    manifest = json.loads(manifest_path.read_text())
    evaluators, provenance, hashes = build_evaluators(manifest)
    proposal = {
        "schema_version": "2.0",
        "generated_from_commit": os.getenv("GITHUB_SHA", "local"),
        "inference_performed": False,
        "models": {
            item["id"]: {
                "state_dict_sha256": hashes[item["id"]],
                "display_name": item["display_name"],
                "framework": item["framework"],
                "model_ref": item["model_ref"],
                "role": item["role"],
                "decision_threshold": float(item["decision_threshold"]),
                "framework_version": provenance[item["id"]]["framework_version"],
            }
            for item in manifest["models"]
        },
    }
    out = ROOT / "benchmarks/model-lock-proposal.json"
    out.write_text(json.dumps(proposal, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"output": str(out), "models": list(proposal["models"])}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
