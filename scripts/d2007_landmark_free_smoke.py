from __future__ import annotations

"""Execute the preregistered D2-0007 Stage-0 landmark-free wiring smoke test.

This is a wiring/rehearsal command, not motif screening and not evidence
promotion.  It generates one deterministic FeatureCollage PATTERNS candidate,
passes it through the existing PERSON-SUR-v3 benchmark stack, and writes a
hash-bound telemetry receipt.  Held-out evaluators are never constructed.
"""

import argparse
import json
from pathlib import Path
import sys
import tempfile

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ruthless_pipeline.patterns.d2007_smoke import (  # noqa: E402
    SURROGATE_MODEL_SET_ID,
    SurrogateScoreResult,
    run_landmark_free_smoke,
)
from scripts.run_measured_benchmark import build_evaluators  # noqa: E402
from scripts.select_surrogate_candidate import (  # noqa: E402
    evaluate_candidate,
    make_config,
)


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _surrogate_ids(model_set: dict) -> tuple[str, ...]:
    if model_set.get("model_set_id") != SURROGATE_MODEL_SET_ID:
        raise SystemExit(
            f"D2-0007 Stage 0 requires {SURROGATE_MODEL_SET_ID}; "
            f"got {model_set.get('model_set_id')!r}"
        )
    if model_set.get("role") != "surrogate":
        raise SystemExit("D2-0007 Stage 0 model set must have role=surrogate")
    ids = tuple(str(v) for v in model_set.get("models", ()))
    if not ids:
        raise SystemExit("surrogate model set is empty")
    return ids


def _build_score_adapter(*, manifest: dict, surrogate_ids: tuple[str, ...], runtime: Path):
    # Critical boundary: only surrogate-role evaluators are constructed here.
    evaluators, _provenance, _state_hashes = build_evaluators(manifest, roles={"surrogate"})
    configured = tuple(
        item["id"] for item in manifest["models"] if item.get("role") == "surrogate"
    )
    if set(configured) != set(surrogate_ids):
        raise SystemExit(
            "PERSON-SUR-v3 membership disagrees with benchmark manifest; refuse Stage-0 run"
        )

    nominal = {
        "brightness": [1.0],
        "scale": [1.0],
        "blur_sigma": [0.0],
        "rotation_deg": [0.0],
    }
    config = make_config(manifest, surrogate_ids, nominal)

    def score_candidate(image: np.ndarray, candidate: dict) -> SurrogateScoreResult:
        with tempfile.TemporaryDirectory(prefix="rac-d2007-stage0-") as temp_dir:
            pool_dir = Path(temp_dir)
            png_name = "landmark-free-pattern.png"
            Image.fromarray(image.astype(np.uint8), "RGB").save(pool_dir / png_name)
            item = dict(candidate)
            item["png"] = png_name
            record = evaluate_candidate(
                item,
                pool_dir=pool_dir,
                manifest=manifest,
                output_dir=runtime,
                config=config,
                evaluators=evaluators,
                include_per_surrogate=True,
            )
        return SurrogateScoreResult(
            model_set_id=SURROGATE_MODEL_SET_ID,
            per_surrogate_detection_rates=record["per_surrogate_detection_rates"],
            invalid_condition_fraction=float(record["invalid_condition_fraction"]),
            heldout_access=False,
        )

    return score_candidate


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run D2-0007 Stage-0 landmark-free PATTERNS/surrogate wiring smoke test."
    )
    parser.add_argument("--manifest", default="benchmarks/model_manifest.json")
    parser.add_argument("--model-set", default="model_sets/PERSON-SUR-v3.json")
    parser.add_argument(
        "--output",
        default="benchmarks/runtime/d2-0007/stage0-landmark-free-smoke.json",
    )
    args = parser.parse_args()

    manifest_path = Path(args.manifest)
    model_set_path = Path(args.model_set)
    output_path = Path(args.output)
    manifest = _load_json(manifest_path)
    model_set = _load_json(model_set_path)
    surrogate_ids = _surrogate_ids(model_set)

    runtime = output_path.parent / "benchmark"
    runtime.mkdir(parents=True, exist_ok=True)
    scorer = _build_score_adapter(
        manifest=manifest,
        surrogate_ids=surrogate_ids,
        runtime=runtime,
    )
    telemetry = run_landmark_free_smoke(
        score_candidate=scorer,
        expected_surrogate_ids=surrogate_ids,
    )
    telemetry["inputs"] = {
        "manifest": str(manifest_path),
        "model_set": str(model_set_path),
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(telemetry, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": telemetry["status"],
        "generation_id": telemetry["generation_id"],
        "candidate_id": telemetry["candidate_id"],
        "telemetry_sha256": telemetry["telemetry_sha256"],
        "output": str(output_path),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
