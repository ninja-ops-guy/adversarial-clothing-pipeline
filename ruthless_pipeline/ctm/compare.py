"""Deterministic genome comparison. Pure functions; no outcome data.

claim_state is HARD-SET to "EXPLORATORY" (documented): a comparison is a
measurement, never evidence of a heuristic. physical_efficacy_claimed is
always False. evidence_tier is a caller-supplied label restricted to
"DIGITAL" (default) or "SYNTHETIC".

Distance metrics (documented, deliberately simple):
  per family (spectral/topology/color/geometry) all numeric leaf values are
  collected in sorted-key, deterministic order into feature vectors; we report
    - l1: mean absolute difference
    - l2: euclidean distance
    - max_abs: maximum absolute difference
  overall_distance: sum of per-family l2 distances.
"""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field, is_dataclass

from .errors import ComparisonError

FAMILIES = ("spectral", "topology", "color", "geometry")
VALID_EVIDENCE_TIERS = frozenset({"DIGITAL", "SYNTHETIC"})
CLAIM_STATE = "EXPLORATORY"


@dataclass(frozen=True)
class FamilyDistance:
    l1: float
    l2: float
    max_abs: float
    feature_count: int


@dataclass(frozen=True)
class ComparisonReport:
    families: dict = field(default_factory=dict)
    overall_distance: float = 0.0
    identical: bool = True
    evidence_tier: str = "DIGITAL"
    claim_state: str = CLAIM_STATE
    physical_efficacy_claimed: bool = False

    def to_dict(self) -> dict:
        d = asdict(self)
        d["families"] = {k: d["families"][k] for k in sorted(d["families"])}
        return d


def _to_dict(genome) -> dict:
    if is_dataclass(genome):
        return asdict(genome)
    if isinstance(genome, dict):
        return genome
    raise ComparisonError(f"unsupported genome type: {type(genome).__name__}")


def _numeric_leaves(node, path: str = ""):
    """Yield (path, value) for numeric leaves in deterministic sorted-key order."""
    if isinstance(node, dict):
        for key in sorted(node, key=str):
            yield from _numeric_leaves(node[key], f"{path}.{key}" if path else str(key))
    elif isinstance(node, (list, tuple)):
        for i, v in enumerate(node):
            yield from _numeric_leaves(v, f"{path}[{i}]")
    elif isinstance(node, bool):
        return
    elif isinstance(node, (int, float)):
        yield path, float(node)


def _family_leaves(genome_dict: dict, family: str) -> dict:
    if family not in genome_dict:
        raise ComparisonError(f"genome is missing family {family!r}")
    return dict(_numeric_leaves(genome_dict[family]))


def _family_distance(a: dict, b: dict) -> FamilyDistance:
    """Diff over the sorted union of feature paths; a feature present in only
    one genome contributes its absolute value (documented union rule)."""
    paths = sorted(set(a) | set(b))
    if not paths:
        return FamilyDistance(l1=0.0, l2=0.0, max_abs=0.0, feature_count=0)
    diffs = [abs(a.get(p, 0.0) - b.get(p, 0.0)) for p in paths]
    l1 = sum(diffs) / len(diffs)
    l2 = math.sqrt(sum(d * d for d in diffs))
    return FamilyDistance(l1=l1, l2=l2, max_abs=max(diffs), feature_count=len(paths))


def compare_genomes(genome_a, genome_b, *, evidence_tier: str = "DIGITAL") -> ComparisonReport:
    if evidence_tier not in VALID_EVIDENCE_TIERS:
        raise ComparisonError(
            f"evidence_tier must be one of {sorted(VALID_EVIDENCE_TIERS)}, got {evidence_tier!r}")
    da, db = _to_dict(genome_a), _to_dict(genome_b)
    families = {}
    overall = 0.0
    for family in FAMILIES:
        dist = _family_distance(_family_leaves(da, family), _family_leaves(db, family))
        families[family] = asdict(dist)
        overall += dist.l2
    return ComparisonReport(
        families=families,
        overall_distance=overall,
        identical=(overall == 0.0),
        evidence_tier=evidence_tier,
        claim_state=CLAIM_STATE,
        physical_efficacy_claimed=False,
    )
