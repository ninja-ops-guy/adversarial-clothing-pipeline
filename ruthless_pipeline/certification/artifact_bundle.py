from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .manifest import hash_file, sha256_bytes


@dataclass
class ArtifactBundle:
    root: Path

    @classmethod
    def create(cls, root: str | Path) -> "ArtifactBundle":
        path = Path(root)
        path.mkdir(parents=True, exist_ok=True)
        return cls(path)

    def resolve_path(self, relative_path: str | Path) -> Path:
        relative = Path(relative_path)
        if not str(relative) or relative.is_absolute() or ".." in relative.parts:
            raise ValueError("artifact path must be a safe relative path")
        root = self.root.resolve()
        path = (root / relative).resolve()
        if path != root and root not in path.parents:
            raise ValueError("artifact path escapes bundle root")
        return path

    def write_json(self, relative_path: str, payload: dict) -> Path:
        path = self.resolve_path(relative_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
        return path

    def hash_manifest(self, exclude: tuple[str, ...] = ("hashes.sha256", "certificate.json")) -> dict[str, str]:
        hashes: dict[str, str] = {}
        for path in sorted(p for p in self.root.rglob("*") if p.is_file()):
            rel = path.relative_to(self.root).as_posix()
            if rel in exclude:
                continue
            hashes[rel] = hash_file(path)
        return hashes

    def seal(self, exclude: tuple[str, ...] = ("hashes.sha256", "certificate.json")) -> tuple[Path, str]:
        hashes = self.hash_manifest(exclude=exclude)
        body = "".join(f"{digest}  {path}\n" for path, digest in sorted(hashes.items()))
        hashes_path = self.root / "hashes.sha256"
        hashes_path.write_text(body)
        return hashes_path, sha256_bytes(body.encode())
