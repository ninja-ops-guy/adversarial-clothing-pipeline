#!/usr/bin/env python3
"""Deterministic export of the RAC-PRINT-ALPHA-001 trial sheet.

Exports the 108 matched control/candidate capture rows from
ruthless_pipeline.physical_protocol.capture_rows() to
print-alpha/CAPTURE/trial-sheet.csv and prints the file's sha256.

Determinism contract: same repo state -> byte-identical CSV. Row order is the
preregistered loop order of capture_rows(); floats are rendered with repr-free
fixed formatting; the file ends with a trailing newline and uses \\n line
endings regardless of platform.

Usage:
    PYTHONPATH=. python3 scripts_print_alpha/export_trial_sheet.py [output_path]
"""

from __future__ import annotations

import csv
import hashlib
import io
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ruthless_pipeline.physical_protocol import capture_rows  # noqa: E402

DEFAULT_OUTPUT = REPO_ROOT / "print-alpha" / "CAPTURE" / "trial-sheet.csv"

FIELDNAMES = [
    "trial_id",
    "condition_id",
    "repeat",
    "distance_m",
    "yaw_deg",
    "pitch_deg",
    "pose",
    "lighting_id",
    "wash_state",
    "control_file",
    "candidate_file",
]


def render_csv() -> bytes:
    """Render the trial sheet to deterministic bytes."""
    buf = io.StringIO(newline="")
    writer = csv.DictWriter(buf, fieldnames=FIELDNAMES, lineterminator="\n")
    writer.writeheader()
    rows = capture_rows()
    if len(rows) != 108:
        raise RuntimeError(f"capture_rows() returned {len(rows)} rows, expected 108")
    for row in rows:
        out = dict(row)
        for key in ("distance_m", "yaw_deg", "pitch_deg"):
            out[key] = f"{row[key]:.1f}"
        writer.writerow(out)
    return buf.getvalue().encode("utf-8")


def main() -> int:
    output = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_OUTPUT
    payload = render_csv()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(payload)
    digest = hashlib.sha256(payload).hexdigest()
    print(f"wrote {output} ({len(payload)} bytes)")
    print(f"sha256 {digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
