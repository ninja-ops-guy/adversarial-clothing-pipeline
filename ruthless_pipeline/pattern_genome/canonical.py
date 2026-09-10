from __future__ import annotations
import hashlib, json
from pathlib import Path
from .schema import PatternGenome

def _payload(genome: PatternGenome | dict) -> dict:
    if isinstance(genome, PatternGenome):
        data = genome.to_dict()
    else:
        data = dict(genome)
    return data

def canonical_json(genome: PatternGenome | dict, *, blank_genome_id: bool = False) -> bytes:
    data = _payload(genome)
    if blank_genome_id:
        data["genome_id"] = ""
    return json.dumps(data, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")

def genome_sha256(genome: PatternGenome | dict) -> str:
    return hashlib.sha256(canonical_json(genome, blank_genome_id=True)).hexdigest()

def write_genome(path: str | Path, genome: PatternGenome) -> None:
    Path(path).write_text(json.dumps(genome.to_dict(), sort_keys=True, indent=2, allow_nan=False) + "\n")
