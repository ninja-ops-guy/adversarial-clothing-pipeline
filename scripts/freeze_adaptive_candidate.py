from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Freeze the surrogate-only adaptive winner as the next D2 candidate."
    )
    parser.add_argument(
        "--adaptive",
        default="benchmarks/runtime/adaptive/adaptive-selection.json",
    )
    parser.add_argument("--output-dir", default="benchmarks/runtime")
    parser.add_argument("--pool", default="benchmarks/runtime/pool/pool.json")
    parser.add_argument("--candidate-id", default="RAC-PER-D2-0004")
    args = parser.parse_args()

    adaptive_path = Path(args.adaptive)
    adaptive = json.loads(adaptive_path.read_text())
    if adaptive.get("stage") != "environment_adaptive_surrogate_only":
        raise SystemExit("adaptive report has unexpected stage")
    if adaptive.get("heldout_models_loaded") != []:
        raise SystemExit("adaptive report indicates held-out models were loaded")
    if adaptive.get("heldout_feedback_used") is not False:
        raise SystemExit("adaptive report indicates held-out feedback was used")

    winner = adaptive.get("winner") or {}
    if not winner:
        raise SystemExit("adaptive report has no winner")

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    winner_path = adaptive_path.parent / winner["png"]
    if not winner_path.is_file():
        raise SystemExit(f"adaptive winner PNG missing: {winner_path}")

    pool = json.loads(Path(args.pool).read_text())
    pool_by_id = {item["candidate_id"]: item for item in pool.get("candidates", [])}
    source = pool_by_id.get(winner["source_candidate_id"])
    if source is None:
        raise SystemExit("adaptive source candidate missing from preregistered pool")

    candidate_path = output_dir / "candidate.png"
    shutil.copyfile(winner_path, candidate_path)

    config = {
        "schema_version": "4.0",
        "candidate_id": args.candidate_id,
        "source_candidate_id": winner["candidate_id"],
        "pre_adaptation_candidate_id": winner["source_candidate_id"],
        "family": winner["family"],
        "patternType": source["patternType"],
        "product": winner["product"],
        "seed": winner["seed"],
        "patternScale": source["patternScale"],
        "colorVariance": source["colorVariance"],
        "edgeIntensity": source["edgeIntensity"],
        "symmetry": source.get("symmetry", 0),
        "colorPalette": source.get("colorPalette"),
        "variationPreset": source.get("variationPreset", "original"),
        "featureMotifs": source.get("featureMotifs", []),
        "design_variant": source.get("design_variant"),
        "art_direction_profile": source.get("art_direction_profile"),
        "reference_fidelity_score": winner.get("reference_fidelity_score"),
        "reference_fidelity_subscores": source.get("reference_fidelity_subscores"),
        "environment_colors": winner["environment_colors"],
        "temperature": winner["temperature"],
        "blend": winner["blend"],
        "frozen_candidate_png": str(candidate_path),
        "source": "surrogate-only reference-ranked + environment-adaptive candidate selection",
        "selection_boundary": "SURROGATE_ONLY",
        "heldout_models_loaded": [],
        "heldout_feedback_used": False,
        "adaptive_report": str(adaptive_path),
        "design_profile_sha256": pool.get("design_profile_sha256"),
    }
    (output_dir / "candidate-config.json").write_text(
        json.dumps(config, indent=2, sort_keys=True) + "\n"
    )
    print(json.dumps(config, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
