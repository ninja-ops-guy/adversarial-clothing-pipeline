"""SPEC-8 + SPEC-14 — Genome v2 candidate register (register ONLY).

Pattern Genome v1 stays frozen.  This module maintains the deferred v2
*candidate register*: invariance-class features that v1 cannot express,
each entry carrying a feature definition, an invariance claim (under the
deformation group / the coarsening operator / both), a computability cost,
and an explicit dependence on SPEC-7's sealed outcome.

Hard rules (fail closed with :class:`GenomeV2RegisterError`):

- NOTHING in this module reads, writes, or mutates any Pattern Genome v1
  surface (``ruthless_pipeline/pattern_genome/**``).  The register is a
  side artifact; v1 hashing/measurement code is untouched by construction.
- A feature family that SPEC-7 legally rejected (``legally_rejected``
  disposition in a verified decision artifact) is DROPPED from the register
  and can never be promoted to ``v2_candidate`` — rejection by the sealed
  kill-gate is terminal for that family's v2 path.
- Promotion of any registered candidate to ``v2_candidate`` requires a
  verified SPEC-7 decision artifact; silent entry into Genome v2
  implementation without the gate is structurally impossible.
- Every promotion/demotion re-seals the register hash; the register is
  content-addressed and deterministic.

SPEC-14 contributes four FR-adjacency candidates (region-placement
descriptors, symmetry-enforcement deltas, landmark-region density
targeting, template-margin geometry), each tagged with its source paper,
its measured effect, and its SPEC-7 kill-gate dependence.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping

import jsonschema

from ..pattern_genome.canonical import canonical_json, sha256_bytes
from .errors import CTMBridgeError
from .retro_mining import PREDICTOR_FAMILIES, verify_decision

_SCHEMA_PATH = (
    Path(__file__).resolve().parents[2]
    / "schemas"
    / "ctm_genome_v2_register_v1.schema.json"
)

GENOME_V2_REGISTER_SCHEMA_VERSION = "rac-ctm-genome-v2-register/1.0"

#: Candidate families: four SPEC-8 invariance-class + four SPEC-14
#: FR-adjacency families.
CANDIDATE_FAMILIES = frozenset({
    "persistence_landscape_norms",
    "self_similarity_criticality",
    "harmonic_order_energy_curves",
    "description_length_proxies",
    "region_placement_descriptors",
    "symmetry_enforcement_deltas",
    "landmark_region_density_targeting",
    "template_margin_geometry",
})

ENTRY_STATUSES = frozenset({"registered", "v2_candidate", "dropped"})

_TERMINAL_DROP_DISPOSITION = "legally_rejected"


class GenomeV2RegisterError(CTMBridgeError):
    """Genome v2 candidate-register contract violated (SPEC-8/14).
    Fail closed."""


def _require_nonempty(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise GenomeV2RegisterError(
            f"{name} must be a non-empty string (fail closed)"
        )
    return value


# ---------------------------------------------------------------------------
# Candidate entries
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class GenomeV2Candidate:
    """One register entry: a v1-inexpressible invariance-class feature."""

    family: str
    feature_definition: str
    invariance_claim: Mapping[str, Any]
    computability_cost: str
    spec7_family_ref: str | None
    spec7_dependence: str
    source_paper: str | None = None
    measured_effect: str | None = None
    status: str = "registered"

    def __post_init__(self) -> None:
        if self.family not in CANDIDATE_FAMILIES:
            raise GenomeV2RegisterError(
                f"unknown candidate family {self.family!r}; allowed: "
                f"{sorted(CANDIDATE_FAMILIES)} (fail closed)"
            )
        _require_nonempty(self.feature_definition, "feature_definition")
        _require_nonempty(self.computability_cost, "computability_cost")
        _require_nonempty(self.spec7_dependence, "spec7_dependence")
        claim = self.invariance_claim
        if not isinstance(claim, Mapping):
            raise GenomeV2RegisterError(
                "invariance_claim must be a mapping (fail closed)"
            )
        for key in ("deformation_group", "coarsening_operator"):
            if not isinstance(claim.get(key), bool):
                raise GenomeV2RegisterError(
                    f"invariance_claim.{key} must be a boolean (fail closed)"
                )
        _require_nonempty(claim.get("statement"), "invariance_claim.statement")
        if self.spec7_family_ref is not None and (
            self.spec7_family_ref not in PREDICTOR_FAMILIES
        ):
            raise GenomeV2RegisterError(
                f"spec7_family_ref {self.spec7_family_ref!r} is not a "
                f"preregistered SPEC-7 family {sorted(PREDICTOR_FAMILIES)}: "
                "the register may only bind to the sealed predictor families "
                "(fail closed)"
            )
        if self.status not in ENTRY_STATUSES:
            raise GenomeV2RegisterError(
                f"unknown entry status {self.status!r}; allowed: "
                f"{sorted(ENTRY_STATUSES)} (fail closed)"
            )

    def _body(self) -> dict[str, Any]:
        body: dict[str, Any] = {
            "family": self.family,
            "feature_definition": self.feature_definition,
            "invariance_claim": {
                "deformation_group": bool(
                    self.invariance_claim["deformation_group"]
                ),
                "coarsening_operator": bool(
                    self.invariance_claim["coarsening_operator"]
                ),
                "statement": str(self.invariance_claim["statement"]),
            },
            "computability_cost": self.computability_cost,
            "spec7_family_ref": self.spec7_family_ref,
            "spec7_dependence": self.spec7_dependence,
            "status": self.status,
        }
        if self.source_paper is not None:
            body["source_paper"] = self.source_paper
        if self.measured_effect is not None:
            body["measured_effect"] = self.measured_effect
        return body

    @property
    def candidate_id(self) -> str:
        return "RAC-CTM-GV2-" + sha256_bytes(canonical_json(self._body()))[:16]

    def to_dict(self) -> dict[str, Any]:
        body = self._body()
        body["candidate_id"] = self.candidate_id
        return body

    def with_status(self, status: str) -> "GenomeV2Candidate":
        if status not in ENTRY_STATUSES:
            raise GenomeV2RegisterError(
                f"unknown entry status {status!r}; allowed: "
                f"{sorted(ENTRY_STATUSES)} (fail closed)"
            )
        return GenomeV2Candidate(
            family=self.family,
            feature_definition=self.feature_definition,
            invariance_claim=self.invariance_claim,
            computability_cost=self.computability_cost,
            spec7_family_ref=self.spec7_family_ref,
            spec7_dependence=self.spec7_dependence,
            source_paper=self.source_paper,
            measured_effect=self.measured_effect,
            status=status,
        )


# ---------------------------------------------------------------------------
# Default register content (SPEC-8 four + SPEC-14 four)
# ---------------------------------------------------------------------------


def build_default_candidates() -> list[GenomeV2Candidate]:
    """The seed register: SPEC-8 invariance-class candidates plus the four
    SPEC-14 FR-adjacency candidates with their evidence bases."""
    return [
        GenomeV2Candidate(
            family="persistence_landscape_norms",
            feature_definition=(
                "Norms of persistence landscapes computed over the pattern's "
                "intensity/gradient filtration, summarizing multiscale "
                "topological structure that Genome v1's scalar summaries "
                "cannot express."
            ),
            invariance_claim={
                "deformation_group": True,
                "coarsening_operator": True,
                "statement": (
                    "Persistence-landscape norms are stable under the "
                    "print/capture deformation group and under resolution "
                    "coarsening, up to the landscape stability bound."
                ),
            },
            computability_cost=(
                "high: persistent homology over a deformation sweep; "
                "superlinear in pixel count per deformation sample"
            ),
            spec7_family_ref="persistence_summary",
            spec7_dependence=(
                "Gated by SPEC-7: if the persistence_summary predictor "
                "family is legally rejected by the sealed kill-gate, this "
                "candidate is dropped from the v2 register."
            ),
        ),
        GenomeV2Candidate(
            family="self_similarity_criticality",
            feature_definition=(
                "Multi-scale energy decay exponents (self-similarity / "
                "criticality estimators) of the pattern's spatial power "
                "spectrum across octaves."
            ),
            invariance_claim={
                "deformation_group": True,
                "coarsening_operator": True,
                "statement": (
                    "Decay exponents are defined across scales and are "
                    "invariant to coarsening by construction; deformation "
                    "invariance is claimed only for the exponent, not the "
                    "per-scale energies."
                ),
            },
            computability_cost=(
                "low: log-log regression on octave-aggregated spectral "
                "energy"
            ),
            spec7_family_ref=None,
            spec7_dependence=(
                "Indirect: no dedicated SPEC-7 family. Continuation depends "
                "on the SPEC-7 decision not rejecting the parent "
                "invariance-research families; entry remains registered "
                "(not promotable) until a preregistered family binds it."
            ),
        ),
        GenomeV2Candidate(
            family="harmonic_order_energy_curves",
            feature_definition=(
                "Energy of the pattern's angular Fourier decomposition as a "
                "function of harmonic order, describing rotational "
                "structure that v1's quadrant energies cannot express."
            ),
            invariance_claim={
                "deformation_group": True,
                "coarsening_operator": False,
                "statement": (
                    "Harmonic-order curves are stable under the deformation "
                    "group's mild warps; coarsening invariance is NOT "
                    "claimed beyond the Nyquist order of the coarsest grid."
                ),
            },
            computability_cost=(
                "low: one polar FFT per pattern; linearithmic in pixel count"
            ),
            spec7_family_ref="harmonic_energy_curve",
            spec7_dependence=(
                "Gated by SPEC-7: if the harmonic_energy_curve predictor "
                "family is legally rejected by the sealed kill-gate, this "
                "candidate is dropped from the v2 register."
            ),
        ),
        GenomeV2Candidate(
            family="description_length_proxies",
            feature_definition=(
                "Algorithmic-complexity proxies (compressed length under a "
                "fixed codec, dictionary-model codelength) of the canonical "
                "pattern representation."
            ),
            invariance_claim={
                "deformation_group": False,
                "coarsening_operator": True,
                "statement": (
                    "Description-length proxies are stable under resolution "
                    "coarsening when computed on the canonicalized "
                    "representation; deformation-group invariance is NOT "
                    "claimed (compression is sensitive to local warps)."
                ),
            },
            computability_cost=(
                "low: single pass of a fixed compressor / dictionary model"
            ),
            spec7_family_ref="description_length",
            spec7_dependence=(
                "Gated by SPEC-7: if the description_length predictor "
                "family is legally rejected by the sealed kill-gate, this "
                "candidate is dropped from the v2 register."
            ),
        ),
        # ---- SPEC-14 FR-adjacency candidates ----
        GenomeV2Candidate(
            family="region_placement_descriptors",
            feature_definition=(
                "Placement-relative-to-landmark features: distance of "
                "adversarial mass to anatomical landmarks (eyes, nose "
                "bridge, brow, jaw for faces; shoulders/hem for garments), "
                "normalized by garment geometry. v1's center_of_mass / "
                "quadrant_energy are garment-relative, not landmark-relative."
            ),
            invariance_claim={
                "deformation_group": True,
                "coarsening_operator": False,
                "statement": (
                    "Landmark-relative placement is stable under the "
                    "deformation group when landmarks are re-estimated "
                    "post-deformation; coarsening invariance is limited by "
                    "landmark localization accuracy."
                ),
            },
            computability_cost=(
                "medium: landmark detector plus masked moment computation"
            ),
            spec7_family_ref=None,
            spec7_dependence=(
                "Deferred until SPEC-7 outcome: enters the v2 implementation "
                "path only after the sealed decision clarifies which parent "
                "property families survive; no direct SPEC-7 family binding."
            ),
            source_paper="Sharif et al. 2016 (AdvHat)",
            measured_effect=(
                "Patch position/size dominate physical success: an "
                "adversarial accessory is really adversarial region "
                "placement."
            ),
        ),
        GenomeV2Candidate(
            family="symmetry_enforcement_deltas",
            feature_definition=(
                "Symmetry-enforcement deltas: the genome of a pattern versus "
                "its symmetrized twin, making the symmetry constraint itself "
                "a first-class experimental factor (and a natural "
                "matched-property null axis for SPEC-1)."
            ),
            invariance_claim={
                "deformation_group": True,
                "coarsening_operator": True,
                "statement": (
                    "The symmetrized-twin delta is defined on the "
                    "canonicalized pattern and is stable under the "
                    "deformation group and coarsening applied identically "
                    "to both twins."
                ),
            },
            computability_cost=(
                "low: one symmetrization plus a differential v1 genome pass"
            ),
            spec7_family_ref=None,
            spec7_dependence=(
                "Deferred until SPEC-7 outcome: strongest published causal "
                "evidence among the candidates, but v2 entry still waits "
                "for the sealed decision on parent property families."
            ),
            source_paper="GaP (bilateral-symmetry enforcement)",
            measured_effect=(
                "Enforcing bilateral symmetry raised physical ASR from "
                "65.4% to 80.7% — the strongest published evidence that a "
                "topological constraint causally affects attack success."
            ),
        ),
        GenomeV2Candidate(
            family="landmark_region_density_targeting",
            feature_definition=(
                "Adversarial energy density within anatomical landmark "
                "masks versus outside them (a masked energy ratio), "
                "capturing deliberate subtle targeting of high-density "
                "landmark regions."
            ),
            invariance_claim={
                "deformation_group": True,
                "coarsening_operator": True,
                "statement": (
                    "The masked energy ratio is stable under the "
                    "deformation group and coarsening when the landmark "
                    "mask is transformed identically."
                ),
            },
            computability_cost=(
                "low: a masked energy ratio; directly testable in the "
                "digital tier"
            ),
            spec7_family_ref=None,
            spec7_dependence=(
                "Deferred until SPEC-7 outcome: no direct SPEC-7 family "
                "binding; digital-tier testable after the sealed decision."
            ),
            source_paper="DiffAM / PeopleTec",
            measured_effect=(
                "Subtle darkening of high-density landmark regions "
                "produces measured physical recognition degradation."
            ),
        ),
        GenomeV2Candidate(
            family="template_margin_geometry",
            feature_definition=(
                "Similarity-margin shift features for FR-adjacent targets: "
                "the continuous cosine-similarity margin movement, not just "
                "binary threshold crossing — the honest effect size that "
                "binary ASR hides."
            ),
            invariance_claim={
                "deformation_group": True,
                "coarsening_operator": False,
                "statement": (
                    "Margin shift is a property of the (pattern, template) "
                    "pair under deformation; coarsening invariance is NOT "
                    "claimed (resolution affects the embedding itself)."
                ),
            },
            computability_cost=(
                "medium: requires template embeddings per condition"
            ),
            spec7_family_ref=None,
            spec7_dependence=(
                "Deferred until SPEC-7 outcome: reframes the outcome cell "
                "(margin shift, not binary crossing) rather than adding a "
                "pattern property; enters the v2 discussion only after the "
                "sealed decision."
            ),
            source_paper="FR margin-attack reframing (anti-surveillance corpus)",
            measured_effect=(
                "Attacks shift the median similarity toward the threshold "
                "without always crossing it; binary ASR hides exactly the "
                "partial effects that predict robustness."
            ),
        ),
    ]


# ---------------------------------------------------------------------------
# Register artifact (content-addressed, deterministic)
# ---------------------------------------------------------------------------


def seal_register(candidates: Iterable[GenomeV2Candidate]) -> dict[str, Any]:
    """Seal candidate entries into a content-addressed register artifact."""
    candidates = list(candidates)
    if not candidates:
        raise GenomeV2RegisterError(
            "cannot seal an empty register (fail closed)"
        )
    families = [c.family for c in candidates]
    if len(set(families)) != len(families):
        raise GenomeV2RegisterError(
            "duplicate candidate family in the register (fail closed)"
        )
    entries = [
        c.to_dict() for c in sorted(candidates, key=lambda c: c.family)
    ]
    body: dict[str, Any] = {
        "schema_version": GENOME_V2_REGISTER_SCHEMA_VERSION,
        "genome_v1_frozen": True,
        "entries": entries,
    }
    artifact = dict(body)
    artifact["register_sha256"] = sha256_bytes(canonical_json(body))
    artifact["register_id"] = (
        "RAC-CTM-GV2-REGISTER-" + artifact["register_sha256"][:16]
    )
    return artifact


def verify_register(artifact: Mapping[str, Any]) -> None:
    """Fail-closed verification of a sealed register artifact: schema,
    derived hash, and per-entry candidate-id re-derivation."""
    if not isinstance(artifact, Mapping):
        raise GenomeV2RegisterError("register artifact must be an object")
    schema = json.loads(_SCHEMA_PATH.read_text())
    try:
        jsonschema.validate(dict(artifact), schema)
    except jsonschema.ValidationError as exc:
        raise GenomeV2RegisterError(
            f"register artifact fails ctm_genome_v2_register_v1 schema: "
            f"{exc.message}"
        ) from exc
    body = {
        k: v
        for k, v in artifact.items()
        if k not in ("register_sha256", "register_id")
    }
    if sha256_bytes(canonical_json(body)) != artifact["register_sha256"]:
        raise GenomeV2RegisterError(
            "register_sha256 does not re-derive: the register was tampered "
            "with or asserted (fail closed)"
        )
    if artifact["register_id"] != (
        "RAC-CTM-GV2-REGISTER-" + artifact["register_sha256"][:16]
    ):
        raise GenomeV2RegisterError(
            "register_id does not match register_sha256 (fail closed)"
        )
    for entry in artifact["entries"]:
        candidate = GenomeV2Candidate(
            family=entry["family"],
            feature_definition=entry["feature_definition"],
            invariance_claim=entry["invariance_claim"],
            computability_cost=entry["computability_cost"],
            spec7_family_ref=entry.get("spec7_family_ref"),
            spec7_dependence=entry["spec7_dependence"],
            source_paper=entry.get("source_paper"),
            measured_effect=entry.get("measured_effect"),
            status=entry["status"],
        )
        if candidate.candidate_id != entry["candidate_id"]:
            raise GenomeV2RegisterError(
                f"candidate_id of family {entry['family']!r} does not "
                "re-derive from its body (fail closed)"
            )


# ---------------------------------------------------------------------------
# SPEC-7 kill-gate coupling
# ---------------------------------------------------------------------------


def _rejected_families(decision_artifact: Mapping[str, Any]) -> frozenset:
    """Verified SPEC-7 decision -> set of legally rejected families."""
    verify_decision(dict(decision_artifact))
    dispositions = decision_artifact["family_dispositions"]
    return frozenset(
        family
        for family, disposition in dispositions.items()
        if disposition == _TERMINAL_DROP_DISPOSITION
    )


def apply_spec7_gate(
    register_artifact: Mapping[str, Any],
    decision_artifact: Mapping[str, Any],
) -> dict[str, Any]:
    """Apply a verified SPEC-7 sealed decision to the register.

    Every entry whose ``spec7_family_ref`` was legally rejected by the
    kill-gate is DROPPED.  Returns a newly sealed register artifact.
    """
    verify_register(register_artifact)
    rejected = _rejected_families(decision_artifact)
    candidates = []
    for entry in register_artifact["entries"]:
        candidate = GenomeV2Candidate(
            family=entry["family"],
            feature_definition=entry["feature_definition"],
            invariance_claim=entry["invariance_claim"],
            computability_cost=entry["computability_cost"],
            spec7_family_ref=entry.get("spec7_family_ref"),
            spec7_dependence=entry["spec7_dependence"],
            source_paper=entry.get("source_paper"),
            measured_effect=entry.get("measured_effect"),
            status=entry["status"],
        )
        if (
            candidate.spec7_family_ref is not None
            and candidate.spec7_family_ref in rejected
        ):
            candidate = candidate.with_status("dropped")
        candidates.append(candidate)
    return seal_register(candidates)


def require_promotion_legal(
    entry: Mapping[str, Any],
    decision_artifact: Mapping[str, Any],
) -> None:
    """Fail-closed promotion gate: a candidate may enter the Genome v2
    implementation path (status ``v2_candidate``) ONLY if a verified SPEC-7
    decision exists and did not legally reject the entry's family.

    A family rejected by the sealed kill-gate can never silently enter
    Genome v2 implementation.
    """
    if entry.get("status") != "registered":
        raise GenomeV2RegisterError(
            f"only 'registered' entries can be promoted; found status "
            f"{entry.get('status')!r} (fail closed)"
        )
    rejected = _rejected_families(decision_artifact)
    family_ref = entry.get("spec7_family_ref")
    if family_ref is not None and family_ref in rejected:
        raise GenomeV2RegisterError(
            f"family {family_ref!r} was legally rejected by the sealed "
            "SPEC-7 kill-gate: this candidate can never enter Genome v2 "
            "implementation (fail closed)"
        )


def promote_candidate(
    register_artifact: Mapping[str, Any],
    family: str,
    decision_artifact: Mapping[str, Any],
) -> dict[str, Any]:
    """Promote one registered candidate to ``v2_candidate`` under the
    SPEC-7 gate.  Returns a newly sealed register artifact."""
    verify_register(register_artifact)
    rejected = _rejected_families(decision_artifact)
    found = False
    candidates = []
    for entry in register_artifact["entries"]:
        candidate = GenomeV2Candidate(
            family=entry["family"],
            feature_definition=entry["feature_definition"],
            invariance_claim=entry["invariance_claim"],
            computability_cost=entry["computability_cost"],
            spec7_family_ref=entry.get("spec7_family_ref"),
            spec7_dependence=entry["spec7_dependence"],
            source_paper=entry.get("source_paper"),
            measured_effect=entry.get("measured_effect"),
            status=entry["status"],
        )
        if candidate.family == family:
            found = True
            require_promotion_legal(entry, decision_artifact)
            candidate = candidate.with_status("v2_candidate")
        candidates.append(candidate)
    if not found:
        raise GenomeV2RegisterError(
            f"no register entry for family {family!r} (fail closed)"
        )
    return seal_register(candidates)
