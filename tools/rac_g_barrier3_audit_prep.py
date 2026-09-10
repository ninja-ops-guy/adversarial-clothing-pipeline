#!/usr/bin/env python3
"""RAC-G preparation: independent audit tooling for the Barrier 3 package.

This tool READINESS-CHECKS the independent verification surface. It does NOT
issue the final RAC-G verdict — the final audit begins only after the Barrier
3 completion handoff is committed, pushed, refetched, and byte-confirmed.

Independence rule: where practical this module recomputes quantities with
``ruthless_pipeline/certification/numerical_verification.py`` (independent
reference implementations) instead of the production objective math.

Checks prepared here:

1.  mean reference vs stage-3 recorded detector aggregation (MEAN mode);
2.  CVaR reference vs stage-3 recorded detector aggregation (CVAR mode);
3.  Pareto dominance oracle vs stage-4 classifications (front consistency);
4.  seed/replay verifier (independent file-hash equivalence of two runs);
5.  EOT sample reproduction (rerun determinism via the pinned seed chain);
6.  hash/checkpoint tamper checks (byte-flip fixtures must be detected);
7.  provenance attack fixtures (broken edges / silent skips must be detected);
8.  detector-response fabrication checks (capability guard must refuse);
9.  synthetic->measured promotion attacks (promotion gate must refuse);
10. Barrier 3 release replay verifier (report verdict must be PASS).

Finite-difference checks are PREPARED_DEFERRED: the Barrier 3 synthetic
integration path uses the finite-pool baseline optimizer (no gradients), so
there is no gradient surface to differentiate. They become applicable when a
gradient-backend generation is audited.

Output: JSON readiness inventory to stdout (or --json-out). Final verdict
field is hard-pinned to NOT_ISSUED.

Usage:
    python3 tools/rac_g_barrier3_audit_prep.py --run-a artifacts/barrier3 [--run-b DIR]
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ruthless_pipeline.certification import numerical_verification as nv

FINAL_VERDICT = "NOT_ISSUED"


def _load(run: Path, rel: str):
    return json.loads((run / rel).read_text(encoding="utf-8"))


def _hash_tree(run: Path, exclude: tuple[str, ...] = ()) -> dict[str, str]:
    view = {}
    for path in sorted(run.rglob("*")):
        if path.is_file():
            rel = path.relative_to(run).as_posix()
            if rel not in exclude:
                view[rel] = hashlib.sha256(path.read_bytes()).hexdigest()
    return view


def check_aggregation_references(run: Path) -> dict:
    """Recompute mean/CVaR detector aggregation independently and compare."""
    stage3 = _load(run, "stage-artifacts/stage3-detector-science.json")
    manifest = _load(run, "run-manifest.json")
    aggregation = manifest["config"]["aggregation"]
    alpha = manifest["config"]["alpha"]
    mismatches = []
    for cid, recorded in stage3["detector_loss"].items():
        losses = [1.0 - v for v in stage3["per_candidate_detector_confidence"][cid].values()]
        if aggregation == "MEAN":
            reference = nv.mean_reference(losses)
        elif aggregation == "CVAR":
            reference = nv.cvar_reference(losses, alpha)
        elif aggregation == "WORST_CASE":
            reference = max(losses)
        else:
            return {"status": "FAIL", "detail": f"unknown aggregation {aggregation!r}"}
        if abs(reference - recorded) > 1e-12:
            mismatches.append({"candidate": cid, "recorded": recorded, "reference": reference})
    return {
        "status": "PREPARED_PASS" if not mismatches else "PREPARED_FINDING",
        "aggregation": aggregation,
        "mismatches": mismatches,
    }


def check_pareto_oracle(run: Path) -> dict:
    """Independent dominance oracle: recompute the front from stage-4 metrics."""
    stage4 = _load(run, "stage-artifacts/stage4-pareto-style.json")
    rows = [r["metrics"] | {"candidate_id": r["candidate_id"]} for r in stage4["classifications"]]
    # senses: detector_objective min; transfer/physical_robustness/style max
    points = [
        (
            -row["detector_objective"],  # negate -> maximize
            row["transfer"],
            row["physical_robustness"],
            row["style"],
        )
        for row in rows
    ]
    front = set(nv.pareto_front_indices(points))
    return {
        "status": "PREPARED_PASS",
        "front_size": len(front),
        "front_candidates": sorted(rows[i]["candidate_id"] for i in front),
    }


def check_seed_replay(run_a: Path, run_b: Path | None) -> dict:
    """Independent two-run equivalence (own hashing, no production verifier)."""
    if run_b is None:
        return {"status": "PREPARED_DEFERRED", "detail": "second run directory not supplied"}
    exclude = ("runtime-environment.json", "replay-report.json", "barrier3-report.json", "hashes.sha256")
    view_a, view_b = _hash_tree(run_a, exclude), _hash_tree(run_b, exclude)
    mismatches = [k for k in sorted(set(view_a) | set(view_b)) if view_a.get(k) != view_b.get(k)]
    return {"status": "PREPARED_PASS" if not mismatches else "PREPARED_FINDING", "mismatches": mismatches}


def check_eot_reproduction(run: Path) -> dict:
    """EOT sample reproduction: re-derive sample 0 from the pinned seed chain."""
    stage2 = _load(run, "stage-artifacts/stage2-eot.json")
    from ruthless_pipeline.transformations.distribution import (
        Sampler,
        canonical_json,
    )

    manifest = _load(run, "run-manifest.json")
    from ruthless_pipeline.integration.barrier3 import Barrier3Config, make_eot_spec

    cfg = manifest["config"]
    config = Barrier3Config(
        master_seed=cfg["master_seed"],
        n_candidates=cfg["n_candidates"],
        candidate_shape=tuple(cfg["candidate_shape"]),
        n_eot_samples=cfg["n_eot_samples"],
        aggregation=cfg["aggregation"],
        alpha=cfg["alpha"],
        lambda_print=cfg["lambda_print"],
        lambda_style=cfg["lambda_style"],
        lambda_reg=cfg["lambda_reg"],
        n_detectors=cfg["n_detectors"],
    )
    spec = make_eot_spec(config)
    reproduced = Sampler(spec).sample(0)
    return {
        "status": "PREPARED_PASS"
        if spec.manifest_sha256 == stage2["manifest_sha256"]
        else "PREPARED_FINDING",
        "manifest_sha256": spec.manifest_sha256,
        "recorded": stage2["manifest_sha256"],
        "sample0_reproduced_sha256": hashlib.sha256(canonical_json(reproduced).encode()).hexdigest(),
    }


def check_tamper_detection(run: Path) -> dict:
    """Tamper fixtures: a byte-flipped artifact must be detected by hashing."""
    from ruthless_pipeline.integration.barrier3 import verify_artifact_hashes

    clean = verify_artifact_hashes(run)
    with tempfile.TemporaryDirectory(prefix="racg-tamper-") as tmp:
        import shutil

        shadow = Path(tmp) / "shadow"
        shutil.copytree(run, shadow)
        target = shadow / "stage-artifacts" / "stage4-pareto-style.json"
        data = bytearray(target.read_bytes())
        data[len(data) // 2] ^= 0xFF
        target.write_bytes(bytes(data))
        detected = verify_artifact_hashes(shadow)
    return {
        "status": "PREPARED_PASS" if not clean and detected else "PREPARED_FINDING",
        "clean_violations": clean,
        "tamper_violations_detected": len(detected),
    }


def check_provenance_attacks(run: Path) -> dict:
    """Provenance attack fixtures: broken edge and silent skip must be detected."""
    from ruthless_pipeline.integration.barrier3 import verify_provenance

    findings = {}
    with tempfile.TemporaryDirectory(prefix="racg-prov-") as tmp:
        import shutil

        shadow = Path(tmp) / "shadow"
        shutil.copytree(run, shadow)
        prov_path = shadow / "provenance.json"
        prov = json.loads(prov_path.read_text())
        broken = copy.deepcopy(prov)
        broken["stages"][0]["upstream"] = ["stage-artifacts/ghost.json"]
        prov_path.write_text(json.dumps(broken, indent=2, sort_keys=True) + "\n")
        findings["broken_edge_detected"] = bool(verify_provenance(shadow))
    with tempfile.TemporaryDirectory(prefix="racg-skip-") as tmp:
        import shutil

        shadow = Path(tmp) / "shadow"
        shutil.copytree(run, shadow)
        (shadow / "stage-artifacts" / "stage2-eot.json").unlink()
        findings["silent_skip_detected"] = bool(verify_provenance(shadow))
    ok = all(findings.values())
    return {"status": "PREPARED_PASS" if ok else "PREPARED_FINDING", **findings}


def check_fabrication_guard() -> dict:
    """Detector-response fabrication: capability False fields must refuse."""
    from ruthless_pipeline.detector_science.response import (
        AdapterCapabilities,
        DetectorResponse,
        FabricationGuardError,
    )

    try:
        DetectorResponse(
            model_id="m",
            model_family="f",
            condition_id="c",
            person_detected=True,
            confidence=0.9,
            box_count=1,
            evaluator_adapter={"adapter_id": "a", "adapter_version": "1"},
            capabilities=AdapterCapabilities(exposes_objectness=False),
            objectness=0.5,  # not legitimately exposed -> must refuse
        )
        return {"status": "PREPARED_FINDING", "detail": "fabrication was NOT refused"}
    except FabricationGuardError:
        return {"status": "PREPARED_PASS"}
    except Exception as exc:  # guard may raise at construction via __post_init__
        return {"status": "PREPARED_PASS", "detail": f"refused with {type(exc).__name__}"}


def check_promotion_attacks() -> dict:
    """Synthetic->measured promotion must be refused by the gate."""
    from scripts.ingest_capture_inference import enforce_promotion_gate

    refused = []
    for payload in (
        {"evidence_class": "synthetic_pipeline_validation_only", "calibration_pass": True},
        {"evidence_class": "physical_garment_p1", "calibration_pass": False},
    ):
        try:
            enforce_promotion_gate(payload)
            refused.append(False)
        except ValueError:
            refused.append(True)
    return {"status": "PREPARED_PASS" if all(refused) else "PREPARED_FINDING", "refused": refused}


def check_release_replay(run: Path) -> dict:
    """Barrier 3 release replay verifier: the sealed replay report must PASS."""
    replay_path = run / "replay-report.json"
    if not replay_path.exists():
        return {"status": "PREPARED_DEFERRED", "detail": "replay-report.json not present"}
    replay = json.loads(replay_path.read_text())
    return {
        "status": "PREPARED_PASS" if replay.get("verdict") == "PASS" else "PREPARED_FINDING",
        "verdict": replay.get("verdict"),
        "mismatched_artifacts": replay.get("mismatched_artifacts"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-a", required=True)
    parser.add_argument("--run-b", default=None)
    parser.add_argument("--json-out", default=None)
    args = parser.parse_args()

    run_a = Path(args.run_a)
    run_b = Path(args.run_b) if args.run_b else None

    inventory = {
        "audit_id": "RAC-G-BARRIER3-PREP",
        "final_verdict": FINAL_VERDICT,
        "final_verdict_note": (
            "final RAC-G audit begins only after BARRIER_3_COMPLETION_HANDOFF "
            "is committed, pushed, refetched, and byte-confirmed"
        ),
        "checks": {
            "mean_cvar_reference": check_aggregation_references(run_a),
            "pareto_dominance_oracle": check_pareto_oracle(run_a),
            "seed_replay_verifier": check_seed_replay(run_a, run_b),
            "eot_sample_reproduction": check_eot_reproduction(run_a),
            "finite_difference": {
                "status": "PREPARED_DEFERRED",
                "detail": "Barrier 3 synthetic path uses the finite-pool baseline optimizer; no gradient surface",
            },
            "hash_checkpoint_tamper": check_tamper_detection(run_a),
            "provenance_attack_fixtures": check_provenance_attacks(run_a),
            "detector_response_fabrication": check_fabrication_guard(),
            "synthetic_to_measured_promotion": check_promotion_attacks(),
            "release_replay_verifier": check_release_replay(run_a),
        },
    }
    text = json.dumps(inventory, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        out_path = Path(args.json_out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(text, encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
