"""SPEC-5 — Imposed-structure provenance (CTM-B adapter extension).

Lesson L4: the genome extractor measures REALIZED structure; the optimizer's
IMPOSED constraints (TV/NPS regularizers, tileability, palette fixing,
symmetry enforcement) are a separate causal channel that Genome v1 does not
record — and Genome v1 stays frozen, so this provenance lives OUTSIDE the
genome schema, in candidate provenance.

Core rule: two patterns in the same genome cell produced under different
imposed constraints are DIFFERENT experimental units for attribution.
:func:`experimental_unit_id` therefore derives identity from BOTH the genome
content hash and the optimizer-constraints hash — identical genomes under
different constraints are mechanically distinguishable.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ruthless_pipeline.pattern_genome.canonical import canonical_json, sha256_bytes

from .errors import OptimizerConstraintsError
from .ids import genome_content_sha256

OPTIMIZER_CONSTRAINTS_SCHEMA_VERSION = "rac-ctm-optimizer-constraints/1.0"

EXPERIMENTAL_UNIT_PREFIX = "RAC-CTM-UNIT-"

#: Recognized imposed-structure channels. Unknown names are legal only when
#: they carry explicit parameters; this prevents an ad-hoc label from looking
#: equivalent to a specified optimizer intervention.
KNOWN_REGULARIZERS = frozenset({"total_variation", "nps", "laplacian", "entropy"})
KNOWN_STRUCTURAL_CONSTRAINTS = frozenset({
    "tileability",
    "palette_fixing",
    "symmetry_enforcement",
    "region_masking",
})


def _validate_named_block(
    block: dict[str, Any],
    kind: str,
    known_names: frozenset[str],
) -> None:
    if not isinstance(block, dict):
        raise OptimizerConstraintsError(f"{kind} entries must be objects")
    name = block.get("name")
    if not isinstance(name, str) or not name:
        raise OptimizerConstraintsError(f"{kind} entry requires a non-empty 'name'")
    params = block.get("parameters", {})
    if not isinstance(params, dict):
        raise OptimizerConstraintsError(
            f"{kind} entry {name!r}: 'parameters' must be an object"
        )
    if name not in known_names and not params:
        raise OptimizerConstraintsError(
            f"unknown {kind} {name!r} requires explicit non-empty parameters; "
            "an ad-hoc name without a parameterization is not reproducible"
        )


@dataclass(frozen=True)
class OptimizerConstraints:
    """Immutable provenance block recording IMPOSED structure, stored outside
    Genome v1 (candidate provenance), content-addressable via sha256."""

    regularizers: tuple[dict[str, Any], ...] = ()
    structural_constraints: tuple[dict[str, Any], ...] = ()
    schema_version: str = OPTIMIZER_CONSTRAINTS_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != OPTIMIZER_CONSTRAINTS_SCHEMA_VERSION:
            raise OptimizerConstraintsError(
                f"unsupported optimizer_constraints schema_version: "
                f"{self.schema_version!r}"
            )
        for block in self.regularizers:
            _validate_named_block(block, "regularizer", KNOWN_REGULARIZERS)
        for block in self.structural_constraints:
            _validate_named_block(
                block, "structural_constraint", KNOWN_STRUCTURAL_CONSTRAINTS
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "regularizers": [dict(b) for b in self.regularizers],
            "structural_constraints": [dict(b) for b in self.structural_constraints],
        }

    def canonical_bytes(self) -> bytes:
        return canonical_json(self.to_dict())

    def constraints_sha256(self) -> str:
        """Content hash of the imposed-constraint set. This is the value a
        SPEC-1 swap_validity record pins as ``constraint_set_ref``."""
        return sha256_bytes(self.canonical_bytes())

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "OptimizerConstraints":
        if not isinstance(payload, dict):
            raise OptimizerConstraintsError(
                "optimizer_constraints payload must be an object"
            )
        return cls(
            regularizers=tuple(dict(b) for b in payload.get("regularizers", ())),
            structural_constraints=tuple(
                dict(b) for b in payload.get("structural_constraints", ())
            ),
            schema_version=payload.get("schema_version", ""),
        )


def experimental_unit_id(
    genome,
    constraints: OptimizerConstraints | None,
) -> str:
    """Derive the experimental-unit identity for attribution.

    unit = f(genome content, imposed constraints). Two patterns with
    byte-identical genomes but different optimizer constraints get DIFFERENT
    unit ids — they are different experimental units (SPEC-5). ``None``
    constraints (no imposed structure recorded) is a distinct, explicit unit
    class, never silently equal to an empty-constraints unit.
    """
    genome_hash = genome_content_sha256(genome)
    if constraints is None:
        constraints_hash = "none"
    else:
        constraints_hash = constraints.constraints_sha256()
    material = (
        genome_hash.encode("utf-8")
        + b"|"
        + constraints_hash.encode("utf-8")
        + b"|"
        + OPTIMIZER_CONSTRAINTS_SCHEMA_VERSION.encode("utf-8")
    )
    return EXPERIMENTAL_UNIT_PREFIX + sha256_bytes(material)[:16].lower()


def same_experimental_unit(
    genome_a,
    constraints_a: OptimizerConstraints | None,
    genome_b,
    constraints_b: OptimizerConstraints | None,
) -> bool:
    """Identity comparison honoring imposed-structure provenance."""
    return experimental_unit_id(genome_a, constraints_a) == experimental_unit_id(
        genome_b, constraints_b
    )
