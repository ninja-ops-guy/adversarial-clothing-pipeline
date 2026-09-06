from __future__ import annotations

import hashlib
from pathlib import Path


def verify_certificate_bundle(root: str | Path) -> tuple[bool, list[str]]:
    root = Path(root)
    hashes_path = root / "hashes.sha256"
    if not hashes_path.exists():
        return False, ["missing hashes.sha256"]
    failures: list[str] = []
    for line_number, line in enumerate(hashes_path.read_text().splitlines(), start=1):
        if not line.strip():
            continue
        if "  " not in line:
            failures.append(f"malformed hash manifest line {line_number}")
            continue
        digest, rel = line.split("  ", 1)
        if len(digest) != 64 or any(ch not in "0123456789abcdefABCDEF" for ch in digest):
            failures.append(f"invalid sha256 on line {line_number}")
            continue
        if not rel or rel.startswith("/") or ".." in Path(rel).parts:
            failures.append(f"invalid artifact path on line {line_number}")
            continue
        path = root / rel
        if not path.exists():
            failures.append(f"missing artifact: {rel}")
            continue
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != digest:
            failures.append(f"hash mismatch: {rel}")
    return not failures, failures
