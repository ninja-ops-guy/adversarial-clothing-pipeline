"""Base interface for the RAC Pattern Generator Library.

Adapted from noRecognition v0.9.8 (spec section 3) with evidence-integrity
adaptations:

* provenance_hash is sha256 of canonical JSON of {generator name, version,
  sorted params (including mask_geometry), code schema version} using
  ``ruthless_pipeline.pattern_genome.canonical``.
* Every generate() is fully deterministic given (seed, params); only
  ``np.random.default_rng(seed)`` randomness is permitted. No wall-clock,
  no os.urandom, no unseeded randomness anywhere in this package.
* Fail-closed typed errors instead of bare ValueError/KeyError.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Sequence, Tuple

import jsonschema
import numpy as np

from ruthless_pipeline.pattern_genome.canonical import canonical_json, sha256_bytes

CODE_SCHEMA_VERSION = "1.0"


# ---------------------------------------------------------------------------
# Typed errors (fail closed)
# ---------------------------------------------------------------------------

class PatternGeneratorError(Exception):
    """Base class for all pattern-library errors."""


class PatternParamError(PatternGeneratorError):
    """Parameters failed validation against the generator's JSON schema."""


class MissingLandmarksError(PatternGeneratorError):
    """mask_geometry is missing landmarks/bboxes the generator requires."""


class PatternNondeterminismError(PatternGeneratorError):
    """A generator produced different output for identical (seed, params)."""


class ProvenanceMismatchError(PatternGeneratorError):
    """Recomputed provenance hash does not match the recorded one."""


class PatternNotImplementedError(PatternGeneratorError):
    """Generator is registered but not yet implemented (P1/P2 stub)."""


class PatternCompositionError(PatternGeneratorError):
    """Invalid composition request (e.g. unknown blend mode)."""


class GeneratorRegistrationError(PatternGeneratorError):
    """Registry conflict or refused registration (e.g. deferred P3)."""


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class GeneratorParams:
    """Base parameters for all generators (spec section 3)."""
    seed: int
    mask_geometry: Dict[str, Any]
    output_size: Tuple[int, int]
    color_space: str = "RGB"
    params: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "seed": self.seed,
            "mask_geometry": self.mask_geometry,
            "output_size": list(self.output_size),
            "color_space": self.color_space,
            "params": self.params,
        }


@dataclass
class GeneratedPattern:
    """Output of a pattern generator (spec section 3)."""
    image: np.ndarray
    params: GeneratorParams
    generator_version: str
    provenance_hash: str
    generator_name: str = ""

    def to_candidate(self) -> Dict[str, Any]:
        """Convert to a RAC candidate artifact (evidence-integrity adaptation).

        Returns a plain dict; claim_state is EXPLORATORY and
        physical_efficacy_claimed is False, always.
        """
        pattern_sha = sha256_bytes(self.image.tobytes())
        candidate_id = "RAC-PAT-CAND-" + pattern_sha[:16]
        return {
            "candidate_id": candidate_id,
            "pattern_sha256": pattern_sha,
            "generator": self.generator_name,
            "generator_version": self.generator_version,
            "provenance_hash": self.provenance_hash,
            "params": self.params.to_dict(),
            "evidence_class": "digital_candidate",
            "physical_efficacy_claimed": False,
            "claim_state": "EXPLORATORY",
        }


# ---------------------------------------------------------------------------
# Schema helpers
# ---------------------------------------------------------------------------

def base_param_schema(extra_properties: Optional[Dict[str, Any]] = None,
                      extra_required: Optional[Sequence[str]] = None
                      ) -> Dict[str, Any]:
    """JSON schema covering base GeneratorParams plus generator extras."""
    properties: Dict[str, Any] = {
        "seed": {"type": "integer"},
        "mask_geometry": {"type": "object"},
        "output_size": {
            "type": "array",
            "items": {"type": "integer", "minimum": 1},
            "minItems": 2,
            "maxItems": 2,
        },
        "color_space": {"type": "string", "enum": ["RGB"]},
    }
    if extra_properties:
        properties.update(extra_properties)
    required = ["seed", "mask_geometry", "output_size"]
    if extra_required:
        required.extend(extra_required)
    return {
        "type": "object",
        "properties": properties,
        "required": required,
        "additionalProperties": True,
    }


def landmarks_of(params: GeneratorParams) -> Dict[str, Any]:
    """Return mask_geometry['landmarks'] as a name -> {'position': [x, y]} dict.

    A list-of-dicts form ([{'type': ..., 'position': ...}]) is also accepted
    and normalised. Missing/empty landmarks raise MissingLandmarksError.
    """
    lm = params.mask_geometry.get("landmarks")
    if not lm:
        raise MissingLandmarksError(
            "mask_geometry.landmarks is required and must be non-empty")
    if isinstance(lm, list):
        out = {}
        for entry in lm:
            out[entry.get("type")] = {"position": entry.get("position")}
        lm = out
    if not isinstance(lm, dict):
        raise MissingLandmarksError(
            "mask_geometry.landmarks must be a dict or list of typed entries")
    return lm


def require_landmarks(params: GeneratorParams, names: Sequence[str]) -> Dict[str, Any]:
    """Fail closed unless all `names` are present in mask_geometry.landmarks."""
    lm = landmarks_of(params)
    missing = [n for n in names if n not in lm or lm[n].get("position") is None]
    if missing:
        raise MissingLandmarksError(
            f"missing required landmarks: {sorted(missing)}")
    return lm


def require_bboxes(params: GeneratorParams, names: Sequence[str]) -> Dict[str, Any]:
    """Fail closed unless all `names` are present in mask_geometry.bboxes."""
    bb = params.mask_geometry.get("bboxes")
    if not isinstance(bb, dict) or not bb:
        raise MissingLandmarksError(
            "mask_geometry.bboxes is required and must be a non-empty dict")
    missing = [n for n in names if n not in bb]
    if missing:
        raise MissingLandmarksError(f"missing required bboxes: {sorted(missing)}")
    return bb


# ---------------------------------------------------------------------------
# Abstract base
# ---------------------------------------------------------------------------

class PatternGenerator(ABC):
    """Abstract base for all pattern generators (spec section 3)."""

    name: str = ""
    version: str = "1.0.0"
    category: str = ""
    priority: str = ""

    @abstractmethod
    def generate(self, params: GeneratorParams) -> GeneratedPattern:
        """Generate pattern from parameters (deterministic given seed+params)."""

    @abstractmethod
    def get_param_schema(self) -> Dict[str, Any]:
        """Return JSON schema for valid parameters."""

    # -- shared helpers -----------------------------------------------------

    def validate_params(self, params: GeneratorParams) -> None:
        """Validate params against get_param_schema(); fail closed on error."""
        instance = params.to_dict()
        flat = dict(instance)
        flat.update(instance.pop("params"))
        try:
            jsonschema.validate(flat, self.get_param_schema())
        except jsonschema.ValidationError as exc:
            raise PatternParamError(
                f"{self.name}: invalid params: {exc.message}") from exc

    def compute_provenance_hash(self, params: GeneratorParams) -> str:
        """sha256 of canonical JSON of name/version/sorted params/schema version."""
        payload = {
            "generator": self.name,
            "version": self.version,
            "params": params.to_dict(),
            "code_schema_version": CODE_SCHEMA_VERSION,
        }
        return sha256_bytes(canonical_json(payload))

    def _finalize(self, params: GeneratorParams, image: np.ndarray) -> GeneratedPattern:
        """Build the provenance-tracked output artifact."""
        return GeneratedPattern(
            image=image,
            params=params,
            generator_version=self.version,
            provenance_hash=self.compute_provenance_hash(params),
            generator_name=self.name,
        )

    def verify_provenance(self, pattern: GeneratedPattern) -> bool:
        """Verify a pattern's provenance hash by recomputation."""
        return pattern.provenance_hash == self.compute_provenance_hash(pattern.params)

    def verify_provenance_strict(self, pattern: GeneratedPattern) -> None:
        """Fail-closed variant: raises ProvenanceMismatchError on mismatch."""
        if not self.verify_provenance(pattern):
            raise ProvenanceMismatchError(
                f"{self.name}: provenance hash mismatch (tampering suspected)")

    def assert_deterministic(self, params: GeneratorParams) -> None:
        """Run generate() twice; raise if image bytes or hashes differ."""
        a = self.generate(params)
        b = self.generate(params)
        if a.image.tobytes() != b.image.tobytes():
            raise PatternNondeterminismError(
                f"{self.name}: image bytes differ for identical (seed, params)")
        if a.provenance_hash != b.provenance_hash:
            raise PatternNondeterminismError(
                f"{self.name}: provenance hash differs for identical (seed, params)")


class StubPatternGenerator(PatternGenerator):
    """Registered-but-unimplemented generator (P1/P2 skeleton)."""

    stub_notes: str = ""

    def generate(self, params: GeneratorParams) -> GeneratedPattern:
        raise PatternNotImplementedError(
            f"{self.name} is a {self.priority} stub; not implemented in P0 scope")

    def get_param_schema(self) -> Dict[str, Any]:
        return base_param_schema()
