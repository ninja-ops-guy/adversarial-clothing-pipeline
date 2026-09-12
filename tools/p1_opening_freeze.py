from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from rac_prc.authority import RACAuthorityLoader
from rac_prc.canonical import RACCanonicalSerializer

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCHEDULE = REPO_ROOT / "physical/p1/P1_CAPTURE_SCHEDULE.json"
DEFAULT_PAIRING = REPO_ROOT / "physical/p1/PAIRING_RANDOMIZATION_CONTRACT.json"
DEFAULT_READINESS = REPO_ROOT / "physical/p1/P1_READINESS_FREEZE.json"
DEFAULT_ALPHA_RECEIPT = REPO_ROOT / "evidence/p1/alpha001-source-recovery.json"


def _git_head() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, text=True).strip()


def _load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _prediction_payload(prediction_path: Path | None) -> tuple[dict | None, str | None]:
    if prediction_path is None:
        return None, None
    payload = _load_json(prediction_path)
    return payload, RACCanonicalSerializer.compute_sha256(payload)


def main() -> int:
    parser = argparse.ArgumentParser(description="Create the prospective P1 opening receipt before outcome access.")
    parser.add_argument("--output", required=True)
    parser.add_argument("--prediction", help="Workspace/repository prediction-freeze JSON prepared before P1.")
    parser.add_argument("--operator", default="local-operator")
    args = parser.parse_args()

    output = Path(args.output).resolve()
    prediction_path = Path(args.prediction).resolve() if args.prediction else None
    authorities = RACAuthorityLoader.generate_manifest(DEFAULT_SCHEDULE, DEFAULT_PAIRING, DEFAULT_READINESS)
    trial_lookup = RACAuthorityLoader.parse_trial_contract(DEFAULT_SCHEDULE, DEFAULT_PAIRING)
    schedule_json = _load_json(DEFAULT_SCHEDULE)
    prediction, prediction_sha = _prediction_payload(prediction_path)

    if prediction is None:
        raise SystemExit("prediction freeze is required before P1 opening")

    alpha_sha = RACAuthorityLoader.hash_file(DEFAULT_ALPHA_RECEIPT) if DEFAULT_ALPHA_RECEIPT.exists() else None
    receipt = {
        "schema": "rac.p1-execution-opening-receipt.v1",
        "state": "P1_READY_PREDICTIONS_FROZEN",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "operator": args.operator,
        "repository_commit": _git_head(),
        "canonicalization_version": RACCanonicalSerializer.VERSION,
        "authority": authorities,
        "trial_contract": {
            "parsed_trial_mappings": len(trial_lookup),
            "schedule_record_sha256": RACCanonicalSerializer.compute_sha256(schedule_json),
        },
        "alpha001_source_recovery_sha256": alpha_sha,
        "prediction_freeze": {
            "path": str(prediction_path),
            "canonical_sha256": prediction_sha,
        },
        "scientific_lock": {
            "outcome_bearing_changes_prohibited": True,
            "allowed_after_opening": ["documented operational corrections permitted by frozen P1 authority"],
        },
    }
    receipt["opening_receipt_sha256"] = RACCanonicalSerializer.compute_sha256(receipt)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": receipt["state"], "opening_receipt_sha256": receipt["opening_receipt_sha256"], "output": str(output)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
