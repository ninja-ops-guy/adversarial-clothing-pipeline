from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


class RACAuthorityLoader:
    """Derive P1 authority from frozen repository bytes and parsed mappings."""

    @staticmethod
    def hash_file(path: str | Path) -> str:
        h = hashlib.sha256()
        with Path(path).open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()

    @classmethod
    def generate_manifest(cls, schedule_path: str | Path, contract_path: str | Path, freeze_path: str | Path) -> dict[str, str]:
        return {
            "schedule_sha256": cls.hash_file(schedule_path),
            "pairing_contract_sha256": cls.hash_file(contract_path),
            "readiness_freeze_sha256": cls.hash_file(freeze_path),
        }

    @staticmethod
    def _walk(value: Any):
        if isinstance(value, dict):
            yield value
            for child in value.values():
                yield from RACAuthorityLoader._walk(child)
        elif isinstance(value, list):
            for child in value:
                yield from RACAuthorityLoader._walk(child)

    @classmethod
    def parse_trial_contract(cls, schedule_path: str | Path, contract_path: str | Path) -> dict[str, dict[str, str]]:
        schedule = json.loads(Path(schedule_path).read_text(encoding="utf-8"))
        contract = json.loads(Path(contract_path).read_text(encoding="utf-8"))
        lookup: dict[str, dict[str, str]] = {}
        for node in list(cls._walk(schedule)) + list(cls._walk(contract)):
            trial_id = node.get("trial_id")
            pair_id = node.get("pair_id") or node.get("pairing_id")
            condition_id = node.get("condition_id")
            if trial_id and pair_id and condition_id:
                mapping = {"pair_id": str(pair_id), "condition_id": str(condition_id)}
                previous = lookup.get(str(trial_id))
                if previous is not None and previous != mapping:
                    raise ValueError(f"conflicting frozen mapping for trial {trial_id}")
                lookup[str(trial_id)] = mapping
        if not lookup:
            raise ValueError("no trial/pair/condition mappings found in frozen P1 authorities")
        return lookup
