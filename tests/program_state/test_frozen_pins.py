"""Frozen-surface pinning: the files SW-01 reads but must never modify.

Hashes were pinned from HEAD bytes at branch creation. If this test fails,
a frozen artifact changed and the change must be reverted or re-reviewed
through the owning governance lane — never absorbed silently.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

FROZEN_PINS = {
    "generations/RAC-PER-D2-0004.json":
        "f1abcf77bf746d536f95089c415c0ae9b6352a63ebb46ba988ddc48e87937dc7",
    "generations/RAC-PER-D2-0005.json":
        "d54e1d7d49acef53d1ce20c2b09a4592af83b5a8e70d7e7ad7ca4754d03d0e8d",
    "generations/RAC-PER-D2-0007.json":
        "3efd0ddd6ca00c9a9f4ee15ef233eac2d8733cf235ef669927dc8665d072efef",
    "docs/D2-0005_FREEZE_CANDIDATE.json":
        "ae505bb0d57db1c98a04f7b7ef1259877040ce0e0c7968f6cdfe619864ab411c",
    "docs/PREREGISTRATION_D2-0005.md":
        "5a26c0839f49d5bb8feedaa77027e9d778ac5ed40edd96651266f83b24e3a0a3",
    "d2-latest-status.json":
        "d761fd947342cca722e6820e9beed0f78b925638e02389c4487e4061f59db4b9",
    "benchmarks/runtime_lock.json":
        "3c7ca4696a8066f3485e2141bab46570ab3265f591ffc87cd3a44795cd361186",
    "benchmarks/frozen_surface_sha256.json":
        "e9c5181e531dd1ea4e8bf4e66f6b3122e08e4d3cfe69916b7fb2bc1c9df9b718",
    "releases/RAC-EXP-2026-001/RELEASE.json":
        "c08df2ceb24970529ff672f4fe32749c1b4c83de52091b07ec4eb673a84d6e53",
    "artifacts/barrier3/barrier3-report.json":
        "cd93886cba33bbb891d7d55ec357c62e454439cdcdc595b5fc648791d1dc24c2",
    "physical/p1/P1_READINESS_FREEZE.json":
        "05b9453168da4d5739f33c7c13307ca09595462ead577bebfadbe486650963b3",
    "artifacts/print-alpha/readiness.json":
        "a7c9486bd6519ad4becfc21fffeb90b95a2e8673578c133c6a050da1d7b7b5b5",
}


def test_frozen_surfaces_unchanged() -> None:
    for rel, expected in sorted(FROZEN_PINS.items()):
        path = ROOT / rel
        assert path.is_file(), f"frozen file missing: {rel}"
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        assert actual == expected, f"frozen file drifted: {rel}"


def test_thresholds_not_touched() -> None:
    """Spot-check the frozen scientific thresholds in the pinned records."""
    import json

    gen5 = json.loads(
        (ROOT / "generations" / "RAC-PER-D2-0005.json").read_text()
    )
    assert gen5["lock_status"] == "PREREGISTERED"
    assert gen5.get("armed") is not True
    assert gen5["heldout_feedback_allowed"] is False
