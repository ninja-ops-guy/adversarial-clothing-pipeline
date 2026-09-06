from __future__ import annotations

import hashlib
from pathlib import Path


def verify_certificate_bundle(root: str | Path) -> tuple[bool, list[str]]:
    root = Path(root)
    hashes_path = root / "hashes.sha256"
    if not hashes_path.exists():
        return False, ["missing hashes.sha256"]
    failures: list[str] = []
    for line in hashes_path.read_text().splitlines():
        if not line.strip():
            continue
        digest, rel = line.split("  ", 1)
        path = root / rel
        if not path.exists():
            failures.append(f"missing artifact: {rel}")
            continue
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != digest:
            failures.append(f"hash mismatch: {rel}")
    return not failures, failures
