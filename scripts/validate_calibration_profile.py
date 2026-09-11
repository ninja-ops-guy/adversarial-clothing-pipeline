from __future__ import annotations

import argparse
import json
from pathlib import Path

from ruthless_pipeline.certification.p1_calibration_binding import (
    canonical_receipt,
    evaluate_profile_payload,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate a measured P1 PrintCameraProfile and emit a hash-bound acceptance receipt."
    )
    parser.add_argument("profile_json")
    parser.add_argument("--phase", choices=("pre", "post"), required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    profile_path = Path(args.profile_json)
    output_path = Path(args.output)
    try:
        payload = json.loads(profile_path.read_text())
        receipt = evaluate_profile_payload(payload, args.phase)
    except (ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        print(json.dumps({"accepted": False, "error": str(exc)}, indent=2, sort_keys=True))
        return 2

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(canonical_receipt(receipt))
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0 if receipt["accepted"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
