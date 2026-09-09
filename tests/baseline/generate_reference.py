#!/usr/bin/env python3
"""Regenerate artifacts/baseline/reference_manifest.json.

Regeneration is an explicit, audited action: the ``--regenerate`` flag is
required, and the new manifest is printed to stdout for review before/after
writing. The manifest pins (generator code sha256, seed, output sha256s);
if the current baseline chain's outputs changed unintentionally, DO NOT
regenerate — investigate the drift instead. Regenerate only after an
intentional, reviewed baseline change.

Usage:
    PYTHONPATH=. python tests/baseline/generate_reference.py --regenerate
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

REFERENCE_PATH = ROOT / "artifacts" / "baseline" / "reference_manifest.json"


def main() -> int:
    if "--regenerate" not in sys.argv[1:]:
        print(
            "refusing to regenerate without the explicit --regenerate flag; "
            "if the baseline-preservation tests fail, investigate the drift "
            "before even considering regeneration",
            file=sys.stderr,
        )
        return 2

    from tests.baseline.fixtures import collect_reference_payload

    with tempfile.TemporaryDirectory(prefix="baseline-reference-") as tmp:
        payload = collect_reference_payload(Path(tmp))

    REFERENCE_PATH.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    REFERENCE_PATH.write_text(text)
    print(f"wrote {REFERENCE_PATH}")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
