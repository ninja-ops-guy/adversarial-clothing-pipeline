from __future__ import annotations

"""Aggregate the eight fixed D2-0007 Stage-1 generator results.

No detector model is loaded here.  The aggregator verifies the eight partials,
reconstructs exactly 64 observations, applies the frozen survivor/admission
rule, and emits a hash-bound surrogate-only screening result.
"""

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ruthless_pipeline.patterns.d2007_screening import (  # noqa: E402
    D2007ScreeningError,
    ScreeningObservation,
    close_screening,
    load_json,
    validate_execution_spec,
)


def _observation(row: dict) -> ScreeningObservation:
    return ScreeningObservation(
        generator_index=int(row["generator_index"]),
        generator=str(row["generator"]),
        composition_index=int(row["composition_index"]),
        derived_seed=int(row["derived_seed"]),
        screening_candidate_id=str(row["screening_candidate_id"]),
        pattern_sha256=str(row["pattern_sha256"]),
        baseline_detection_rates=row["baseline_detection_rates"],
        candidate_detection_rates=row["candidate_detection_rates"],
        invalid_condition_fraction=float(row["invalid_condition_fraction"]),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Aggregate all D2-0007 Stage-1 generator screening partials.")
    parser.add_argument("--spec", default="configs/d2007_stage1_screening_v1.json")
    parser.add_argument("--partials-dir", required=True)
    parser.add_argument("--output", default="benchmarks/runtime/d2-0007/stage1/screening-result.json")
    args = parser.parse_args()

    spec = load_json(ROOT / args.spec)
    validate_execution_spec(spec, repo_root=ROOT)
    partial_root = Path(args.partials_dir)
    files = sorted(partial_root.rglob("generator-*.json"))
    if len(files) != 8:
        raise SystemExit(f"expected exactly eight generator partials; found {len(files)}")

    by_index: dict[int, dict] = {}
    observations: list[ScreeningObservation] = []
    state_hash_reference: dict | None = None
    for path in files:
        partial = load_json(path)
        if partial.get("schema_version") != "rac-d2007-stage1-generator-result/1.0":
            raise SystemExit(f"unexpected partial schema: {path}")
        if partial.get("generation_id") != "RAC-PER-D2-0007" or partial.get("stage") != "STAGE_1_MOTIF_SCREENING":
            raise SystemExit(f"partial outside D2-0007 Stage 1: {path}")
        if partial.get("status") != "GENERATOR_COMPLETE":
            raise SystemExit(f"incomplete generator result: {path}")
        if partial.get("model_set_id") != "PERSON-SUR-v3" or partial.get("heldout_access") is not False:
            raise SystemExit(f"partial violates surrogate-only boundary: {path}")
        for guard in (
            "body_garment_anchor_support_built",
            "optimization_opened",
            "candidate_freeze_created",
            "alpha_002_promoted",
        ):
            if partial.get(guard) is not False:
                raise SystemExit(f"partial unexpectedly advanced {guard}: {path}")
        generator_index = int(partial["generator_index"])
        if generator_index in by_index:
            raise SystemExit(f"duplicate generator index {generator_index}")
        if not 0 <= generator_index < 8:
            raise SystemExit(f"generator index outside frozen range: {generator_index}")
        if partial.get("generator_class") != spec["generator_order"][generator_index]:
            raise SystemExit(f"generator identity/order drift in {path}")
        if len(partial.get("observations", ())) != 8:
            raise SystemExit(f"generator {generator_index} did not produce exactly eight observations")
        hashes = partial.get("surrogate_state_hashes")
        if state_hash_reference is None:
            state_hash_reference = hashes
        elif hashes != state_hash_reference:
            raise SystemExit("surrogate model state hashes differ across Stage-1 generator jobs")
        by_index[generator_index] = partial
        observations.extend(_observation(row) for row in partial["observations"])

    if set(by_index) != set(range(8)):
        raise SystemExit("Stage-1 partial set does not cover generator indices 0..7 exactly")
    try:
        result = close_screening(spec, observations)
    except D2007ScreeningError as exc:
        raise SystemExit(str(exc)) from exc
    result["surrogate_state_hashes"] = state_hash_reference
    result["partial_files"] = [str(path) for path in files]
    canonical = json.dumps(result, sort_keys=True, separators=(",", ":")).encode("utf-8")
    result["result_sha256"] = hashlib.sha256(canonical).hexdigest()

    output_path = ROOT / args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": result["status"],
        "survivor_count": result["survivor_count"],
        "admitted_count": result["admitted_count"],
        "heldout_access": result["heldout_access"],
        "result_sha256": result["result_sha256"],
        "output": str(output_path),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
