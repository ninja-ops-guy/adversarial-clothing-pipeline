"""Additive model-family sidecar registry.

Maps the architectures locked in ``model_manifests/`` (read-only) to detector
families. The registry is validated against the manifests at runtime: every
manifest must be covered, and every sidecar entry must match the locked
architecture. Unknown models fail closed with ``UnknownFamilyError``.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, Optional

_REPO_ROOT = Path(__file__).resolve().parents[2]
REGISTRY_PATH = Path(__file__).resolve().parent / "data" / "model_families.json"
MANIFEST_DIR = _REPO_ROOT / "model_manifests"

DEFAULT_CONCENTRATION_THRESHOLD = 0.5
DEFAULT_MIN_DISTINCT_FAMILIES = 3


class UnknownFamilyError(KeyError):
    """Raised when a model has no family assignment (fail-closed)."""


def load_registry(registry_path: Optional[Path] = None) -> dict:
    """Load the sidecar family registry (fail-closed on malformed content)."""
    path = Path(registry_path) if registry_path else REGISTRY_PATH
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data.get("models"), dict) or not isinstance(data.get("families"), dict):
        raise ValueError("model family registry malformed: need 'models' and 'families'")
    for model_id, entry in data["models"].items():
        if entry.get("family") not in data["families"]:
            raise ValueError(
                f"registry entry {model_id!r} references unknown family {entry.get('family')!r}"
            )
    return data


def _load_manifests(manifest_dir: Optional[Path] = None) -> dict:
    """Read model manifests at runtime (read-only)."""
    directory = Path(manifest_dir) if manifest_dir else MANIFEST_DIR
    manifests = {}
    for path in sorted(directory.glob("*.json")):
        with open(path, "r", encoding="utf-8") as fh:
            manifest = json.load(fh)
        manifests[manifest["model_id"]] = manifest
    return manifests


def validate_coverage(
    registry: Optional[dict] = None,
    manifest_dir: Optional[Path] = None,
) -> dict:
    """Ensure every manifest is covered and architecture strings match.

    Returns the registry. Raises ValueError on any mismatch (fail-closed).
    """
    registry = registry if registry is not None else load_registry()
    manifests = _load_manifests(manifest_dir)
    models = registry["models"]
    missing = sorted(set(manifests) - set(models))
    if missing:
        raise ValueError(f"family registry missing manifests: {missing}")
    stale = sorted(set(models) - set(manifests))
    if stale:
        raise ValueError(f"family registry has entries without manifests: {stale}")
    for model_id, manifest in manifests.items():
        locked = manifest.get("architecture")
        sidecar = models[model_id].get("architecture")
        if locked != sidecar:
            raise ValueError(
                f"architecture mismatch for {model_id!r}: manifest={locked!r} sidecar={sidecar!r}"
            )
    return registry


def family_for_model(
    model_id: str,
    registry: Optional[dict] = None,
    manifest_dir: Optional[Path] = None,
) -> str:
    """Return the family for a model; unknown model fails closed."""
    registry = validate_coverage(registry, manifest_dir)
    try:
        return registry["models"][model_id]["family"]
    except KeyError:
        raise UnknownFamilyError(f"no family assignment for model {model_id!r}") from None


def concentration_report(
    model_set: Iterable[str],
    *,
    registry: Optional[dict] = None,
    manifest_dir: Optional[Path] = None,
    threshold: float = DEFAULT_CONCENTRATION_THRESHOLD,
    min_distinct_families: int = DEFAULT_MIN_DISTINCT_FAMILIES,
) -> dict:
    """Family shares over a model set plus an architecture-concentration warning.

    The warning flag is set when any family's share is >= ``threshold``
    (default 0.5) or the number of distinct families is below
    ``min_distinct_families`` (default 3). Empty model sets fail closed.
    """
    model_ids = list(model_set)
    if not model_ids:
        raise ValueError("concentration_report requires a non-empty model set")
    registry = validate_coverage(registry, manifest_dir)
    counts: dict[str, int] = {}
    for model_id in model_ids:
        family = family_for_model(model_id, registry, manifest_dir)
        counts[family] = counts.get(family, 0) + 1
    total = len(model_ids)
    shares = {fam: counts[fam] / total for fam in sorted(counts)}
    max_family = max(shares, key=lambda f: (shares[f], f))
    max_share = shares[max_family]
    distinct = len(shares)
    dominant = max_share >= threshold
    too_few = distinct < min_distinct_families
    reasons = []
    if dominant:
        reasons.append(
            f"family {max_family!r} share {max_share:.3f} >= threshold {threshold:.3f}"
        )
    if too_few:
        reasons.append(
            f"distinct families {distinct} < minimum {min_distinct_families}"
        )
    return {
        "model_count": total,
        "family_counts": {fam: counts[fam] for fam in sorted(counts)},
        "family_shares": shares,
        "max_family": max_family,
        "max_family_share": max_share,
        "distinct_families": distinct,
        "threshold": threshold,
        "min_distinct_families": min_distinct_families,
        "warning": bool(dominant or too_few),
        "warning_reasons": reasons,
    }
