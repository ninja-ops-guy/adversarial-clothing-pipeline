"""Canonical Validity Register (SW-18).

Consolidates threats-to-validity that are otherwise distributed across
``docs/papers/*`` and ``docs/*`` into structured, content-addressed records:
risk ID, category, affected experiment class, severity, mitigation, residual
risk, status and closure evidence.

Contracts:

* Papers and evidence cards reference risks by their content-addressed ID
  (``RAC-RISK-`` + sha256[:16]). :func:`find_risk_references` and
  :func:`validate_risk_references` provide the reference mechanism and its
  validation.
* Resolving (closing) a risk REQUIRES closure evidence: ``close_risk`` and the
  record validator refuse a ``closed`` status without at least one
  ``{path, sha256}`` evidence reference (fail-closed).
* Unresolved risks remain visible: ``report_markdown`` always contains an
  "Open risks" section listing every non-closed risk; there is no API that
  hides them.
* Append-only by risk ID: a risk ID, once registered, cannot be re-registered
  or removed.

Deterministic: no wall-clock; IDs derive from canonical content only.
Pure stdlib + the repo canonical helpers.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, Iterable

from ruthless_pipeline.pattern_genome.canonical import (
    _to_builtin,
    canonical_json,
    sha256_bytes,
)

SCHEMA_VERSION = "1.0"

REGISTER_SCHEMA_ID = "https://rac.local/schemas/rac_validity_risk_v1.schema.json"

RISK_ID_PATTERN = re.compile(r"RAC-RISK-[0-9a-f]{16}")


# ---------------------------------------------------------------------------
# Typed errors (fail-closed)
# ---------------------------------------------------------------------------


class ValidityRegisterError(ValueError):
    """Base error for validity-register contract violations."""


class ClosureEvidenceRequiredError(ValidityRegisterError):
    """Raised when a risk is closed without closure evidence."""


class UnknownRiskError(ValidityRegisterError):
    """Raised when referencing or resolving an unregistered risk ID."""


class RiskIntegrityError(ValidityRegisterError):
    """Raised when a serialized risk's ID does not match its content."""


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class RiskCategory(str, Enum):
    SIMULATION_GAP = "simulation_gap"
    MODEL_SELECTION = "model_selection"
    MANUFACTURING_VARIANCE = "manufacturing_variance"
    STATISTICAL_POWER = "statistical_power"
    TEMPORAL_DEPENDENCE = "temporal_dependence"
    OTHER = "other"


class RiskStatus(str, Enum):
    OPEN = "open"
    MITIGATED = "mitigated"
    CLOSED = "closed"


_CATEGORIES = {c.value for c in RiskCategory}
_STATUSES = {s.value for s in RiskStatus}
_SEVERITIES = ("low", "medium", "high", "critical")


# ---------------------------------------------------------------------------
# Record
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ClosureEvidence:
    """Content-addressed evidence supporting closure of a validity risk."""

    path: str
    sha256: str
    note: str = ""

    def validate(self) -> None:
        if not self.path:
            raise ClosureEvidenceRequiredError("closure evidence path is required")
        if (
            not isinstance(self.sha256, str)
            or len(self.sha256) != 64
            or any(c not in "0123456789abcdef" for c in self.sha256)
        ):
            raise ClosureEvidenceRequiredError(
                f"closure evidence sha256 must be lowercase 64-hex: {self.path}"
            )


@dataclass(frozen=True)
class ValidityRisk:
    """One threat-to-validity record."""

    risk_id: str  # "RAC-RISK-" + sha256[:16] of canonical content
    category: str  # RiskCategory value
    affected_experiment_class: str
    severity: str  # low | medium | high | critical
    description: str
    mitigation: str
    residual_risk: str
    status: str  # open | mitigated | closed
    closure_evidence: tuple[ClosureEvidence, ...]
    source_refs: tuple[str, ...]  # repo paths the record was extracted from
    uncertainty: str  # high | medium | low

    def validate(self) -> None:
        if self.category not in _CATEGORIES:
            raise ValidityRegisterError(f"unknown risk category: {self.category!r}")
        if self.status not in _STATUSES:
            raise ValidityRegisterError(f"unknown risk status: {self.status!r}")
        if self.severity not in _SEVERITIES:
            raise ValidityRegisterError(
                f"severity must be one of {_SEVERITIES}"
            )
        if not self.risk_id.startswith("RAC-RISK-"):
            raise ValidityRegisterError("risk_id must start with 'RAC-RISK-'")
        if not self.affected_experiment_class:
            raise ValidityRegisterError("affected_experiment_class is required")
        if not self.description:
            raise ValidityRegisterError("description is required")
        if not self.mitigation:
            raise ValidityRegisterError("mitigation is required")
        if not self.residual_risk:
            raise ValidityRegisterError("residual_risk is required")
        if not self.source_refs:
            raise ValidityRegisterError(
                "source_refs is required: validity risks must be traceable to "
                "the papers/docs they were extracted from"
            )
        for ref in self.closure_evidence:
            ref.validate()
        if self.status == RiskStatus.CLOSED.value and not self.closure_evidence:
            raise ClosureEvidenceRequiredError(
                f"risk {self.risk_id}: cannot close without closure evidence"
            )

    def _content_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload.pop("risk_id")
        return payload

    def canonical_json(self) -> bytes:
        self.validate()
        return canonical_json(self._content_dict())

    def content_sha256(self) -> str:
        return sha256_bytes(self.canonical_json())

    def expected_risk_id(self) -> str:
        return f"RAC-RISK-{self.content_sha256()[:16]}"

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        return _to_builtin(asdict(self))

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ValidityRisk":
        risk = cls(
            risk_id=data["risk_id"],
            category=data["category"],
            affected_experiment_class=data["affected_experiment_class"],
            severity=data["severity"],
            description=data["description"],
            mitigation=data["mitigation"],
            residual_risk=data["residual_risk"],
            status=data["status"],
            closure_evidence=tuple(
                ClosureEvidence(**e) for e in data.get("closure_evidence", ())
            ),
            source_refs=tuple(data.get("source_refs", ())),
            uncertainty=data.get("uncertainty", "medium"),
        )
        risk.validate()
        if risk.risk_id != risk.expected_risk_id():
            raise RiskIntegrityError(
                f"risk {risk.risk_id} does not match its content hash "
                f"({risk.expected_risk_id()}); refusing to load tampered "
                "validity-register entry"
            )
        return risk


def make_risk(
    *,
    category: RiskCategory,
    affected_experiment_class: str,
    severity: str,
    description: str,
    mitigation: str,
    residual_risk: str,
    status: RiskStatus = RiskStatus.OPEN,
    closure_evidence: Iterable[ClosureEvidence] = (),
    source_refs: Iterable[str],
    uncertainty: str = "medium",
) -> ValidityRisk:
    """Construct a risk with its content-addressed ID (fail-closed)."""
    risk = ValidityRisk(
        risk_id="RAC-RISK-pending",
        category=category.value,
        affected_experiment_class=affected_experiment_class,
        severity=severity,
        description=description,
        mitigation=mitigation,
        residual_risk=residual_risk,
        status=status.value,
        closure_evidence=tuple(closure_evidence),
        source_refs=tuple(source_refs),
        uncertainty=uncertainty,
    )
    risk.validate()
    return ValidityRisk(
        risk_id=risk.expected_risk_id(),
        category=risk.category,
        affected_experiment_class=risk.affected_experiment_class,
        severity=risk.severity,
        description=risk.description,
        mitigation=risk.mitigation,
        residual_risk=risk.residual_risk,
        status=risk.status,
        closure_evidence=risk.closure_evidence,
        source_refs=risk.source_refs,
        uncertainty=risk.uncertainty,
    )


# ---------------------------------------------------------------------------
# Register (append-only by risk ID)
# ---------------------------------------------------------------------------


class ValidityRegister:
    """Append-only register of validity risks. Risks are never deleted;
    resolution is a status transition that requires closure evidence."""

    def __init__(self, risks: Iterable[ValidityRisk] = ()) -> None:
        self._risks: list[ValidityRisk] = []
        self._by_id: dict[str, int] = {}
        self._superseded: dict[str, list[str]] = {}
        for risk in risks:
            self.add(risk)

    def add(self, risk: ValidityRisk) -> None:
        risk.validate()
        if risk.risk_id in self._by_id:
            raise ValidityRegisterError(f"duplicate risk id: {risk.risk_id}")
        if risk.risk_id != risk.expected_risk_id():
            raise RiskIntegrityError(
                f"risk id {risk.risk_id} does not match content hash"
            )
        self._by_id[risk.risk_id] = len(self._risks)
        self._risks.append(risk)

    def get(self, risk_id: str) -> ValidityRisk:
        try:
            return self._risks[self._by_id[risk_id]]
        except KeyError:
            raise UnknownRiskError(f"unknown risk id: {risk_id}") from None

    def close_risk(
        self, risk_id: str, closure_evidence: Iterable[ClosureEvidence]
    ) -> ValidityRisk:
        """Close a risk. REQUIRES closure evidence (fail-closed).

        Returns the new closed record. The register entry is replaced in place
        by its closed successor; the risk ID changes because the content
        changes, and the old ID remains listed in ``superseded_ids`` so
        historical references stay resolvable.
        """
        evidence = tuple(closure_evidence)
        if not evidence:
            raise ClosureEvidenceRequiredError(
                f"risk {risk_id}: closure requires at least one "
                "{path, sha256} closure-evidence reference"
            )
        for ref in evidence:
            ref.validate()
        current = self.get(risk_id)
        closed = make_risk(
            category=RiskCategory(current.category),
            affected_experiment_class=current.affected_experiment_class,
            severity=current.severity,
            description=current.description,
            mitigation=current.mitigation,
            residual_risk=current.residual_risk,
            status=RiskStatus.CLOSED,
            closure_evidence=evidence,
            source_refs=current.source_refs,
            uncertainty=current.uncertainty,
        )
        idx = self._by_id.pop(risk_id)
        self._risks[idx] = closed
        self._by_id[closed.risk_id] = idx
        self._superseded.setdefault(closed.risk_id, []).append(risk_id)
        return closed

    def superseded_ids(self, risk_id: str) -> tuple[str, ...]:
        """IDs superseded by the given (closed) risk; old references stay listed."""
        return tuple(self._superseded.get(risk_id, ()))

    @property
    def risks(self) -> tuple[ValidityRisk, ...]:
        return tuple(self._risks)

    def open_risks(self) -> list[ValidityRisk]:
        """Unresolved (open or mitigated) risks. These remain visible forever."""
        return [r for r in self._risks if r.status != RiskStatus.CLOSED.value]

    def by_category(self, category: str) -> list[ValidityRisk]:
        if category not in _CATEGORIES:
            raise ValidityRegisterError(f"unknown risk category: {category!r}")
        return [r for r in self._risks if r.category == category]

    # -- serialization --------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "schema": REGISTER_SCHEMA_ID,
            "risks": [r.to_dict() for r in self._risks],
        }

    def to_json(self) -> str:
        return canonical_json(self.to_dict()).decode("utf-8")

    def register_sha256(self) -> str:
        return sha256_bytes(self.to_json().encode("utf-8"))

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ValidityRegister":
        if not isinstance(data, dict) or "risks" not in data:
            raise ValidityRegisterError(
                "register payload must be an object with a 'risks' list"
            )
        if data.get("schema_version") != SCHEMA_VERSION:
            raise ValidityRegisterError(
                f"unsupported register schema_version: "
                f"{data.get('schema_version')!r}"
            )
        return cls(ValidityRisk.from_dict(r) for r in data["risks"])

    @classmethod
    def from_json(cls, text: str) -> "ValidityRegister":
        return cls.from_dict(json.loads(text))

    # -- report ---------------------------------------------------------------

    def report_markdown(self) -> str:
        """Deterministic register report. ALWAYS lists open risks."""
        lines = [
            "# Canonical Validity Register",
            "",
            f"Register sha256: `{self.register_sha256()}`",
            "",
            "## Open risks",
            "",
        ]
        open_risks = self.open_risks()
        if not open_risks:
            lines.append("_None — all registered risks are closed with evidence._")
        for risk in open_risks:
            lines.extend(
                [
                    f"### {risk.risk_id} — {risk.category} ({risk.severity})",
                    "",
                    f"- **Status:** {risk.status}",
                    f"- **Affected experiment class:** {risk.affected_experiment_class}",
                    f"- **Description:** {risk.description}",
                    f"- **Mitigation:** {risk.mitigation}",
                    f"- **Residual risk:** {risk.residual_risk}",
                    f"- **Uncertainty:** {risk.uncertainty}",
                    f"- **Sources:** {', '.join(risk.source_refs)}",
                    "",
                ]
            )
        closed = [r for r in self._risks if r.status == RiskStatus.CLOSED.value]
        lines.extend(["## Closed risks", ""])
        if not closed:
            lines.append("_None._")
        for risk in closed:
            evidence = ", ".join(
                f"{e.path} ({e.sha256[:16]}…)" for e in risk.closure_evidence
            )
            lines.extend(
                [
                    f"### {risk.risk_id} — {risk.category}",
                    "",
                    f"- **Closure evidence:** {evidence}",
                    f"- **Residual risk:** {risk.residual_risk}",
                    "",
                ]
            )
        return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Reference mechanism (papers / evidence cards reference risk IDs)
# ---------------------------------------------------------------------------


def risk_reference_token(risk_id: str) -> str:
    """Canonical token a paper or evidence card uses to reference a risk."""
    if not RISK_ID_PATTERN.fullmatch(risk_id):
        raise ValidityRegisterError(f"not a valid risk id: {risk_id!r}")
    return risk_id


def find_risk_references(text: str) -> list[str]:
    """All RAC-RISK reference tokens appearing in a document, de-duplicated."""
    return sorted(set(RISK_ID_PATTERN.findall(text)))


def validate_risk_references(text: str, register: ValidityRegister) -> list[str]:
    """Fail-closed validation of risk references in a document.

    Returns the list of referenced risk IDs; raises UnknownRiskError if any
    reference does not resolve against the register.
    """
    refs = find_risk_references(text)
    for ref in refs:
        register.get(ref)  # raises UnknownRiskError on dangling reference
    return refs


# ---------------------------------------------------------------------------
# Seed register: threats-to-validity extracted from docs/papers/*
# ---------------------------------------------------------------------------


def seed_register() -> ValidityRegister:
    """Build the seeded register from what the repo's papers/docs actually say.

    Every description/residual risk below is paraphrased from the cited
    source_refs (docs/papers/* limitations and ethics sections); nothing here
    introduces a new claim.
    """
    seeds = [
        make_risk(
            category=RiskCategory.SIMULATION_GAP,
            affected_experiment_class="digital surrogate-phase optimization and screening",
            severity="high",
            description=(
                "Simulation fidelity is bounded by available calibration; attack "
                "success on simplified synthetic evaluations can be poorly "
                "predictive of performance under realistic rendering, "
                "deformation, lighting and viewpoint (REAP/AdvReal, cited in "
                "paper 01). Digital evidence cannot be promoted to a physical "
                "claim."
            ),
            mitigation=(
                "Held-out evaluation, manufacturing-bound candidates, ISP and "
                "deformation screening, and the architectural rule that "
                "physical manufacturing and capture are evidence stages that "
                "cannot be replaced by simulation."
            ),
            residual_risk=(
                "Calibration coverage is finite; sim-to-real error remains "
                "experiment-dependent and unquantified for untested conditions."
            ),
            source_refs=(
                "docs/papers/00_RAC_SYSTEM_ARCHITECTURE.md",
                "docs/papers/01_TRANSFER_PREDICTION.md",
            ),
            uncertainty="high",
        ),
        make_risk(
            category=RiskCategory.MODEL_SELECTION,
            affected_experiment_class="held-out detector evaluation and transfer claims",
            severity="high",
            description=(
                "Model transfer cannot be inferred beyond tested model families; "
                "results are limited to named models, thresholds, fixtures and "
                "transformations and must not be generalized to arbitrary "
                "deployments. Held-out sets, once evaluated, are permanently "
                "observed, so each generation's model selection bounds every "
                "later claim."
            ),
            mitigation=(
                "Frozen model sets referenced by hash, surrogate/held-out "
                "separation enforced in code, and permanent-observation "
                "bookkeeping across generations."
            ),
            residual_risk=(
                "Conclusions remain conditional on the selected architectures; "
                "untested families are an open threat."
            ),
            source_refs=(
                "docs/papers/00_RAC_SYSTEM_ARCHITECTURE.md",
                "docs/papers/01_TRANSFER_PREDICTION.md",
            ),
            uncertainty="medium",
        ),
        make_risk(
            category=RiskCategory.MANUFACTURING_VARIANCE,
            affected_experiment_class="physical manufacturing and print calibration",
            severity="medium",
            description=(
                "Print and textile manufacturing introduce uncontrolled or only "
                "partially controlled variation; the learned calibration "
                "profile is not universal — provider, substrate, fulfillment "
                "region, printer, garment construction, camera, software "
                "processing and environment may all change the transfer "
                "function."
            ),
            mitigation=(
                "Manufacturing calibration protocol (paper 02), delta-E and "
                "scale-error tolerances in the failure taxonomy, and "
                "manufacturing-bound candidate artifacts."
            ),
            residual_risk=(
                "Calibration is provider/substrate-specific; re-calibration is "
                "required whenever any manufacturing parameter changes."
            ),
            source_refs=(
                "docs/papers/00_RAC_SYSTEM_ARCHITECTURE.md",
                "docs/papers/02_MANUFACTURING_CALIBRATION.md",
            ),
            uncertainty="medium",
        ),
        make_risk(
            category=RiskCategory.STATISTICAL_POWER,
            affected_experiment_class="longitudinal generation comparisons and hypothesis tests",
            severity="medium",
            description=(
                "A first serious predictor analysis requires at least three "
                "comparable closed generations, and that threshold is an "
                "analysis-start rule rather than a claim that three generations "
                "provide definitive statistical power. Wide Wilson intervals "
                "with consistent effect direction are classified as "
                "statistical_inconclusive, not as effects."
            ),
            mitigation=(
                "Preregistered analysis-start thresholds, Wilson interval "
                "reporting, and the statistical_inconclusive failure category "
                "that prevents over-claiming underpowered results."
            ),
            residual_risk=(
                "Small generation counts leave all current comparisons "
                "underpowered; negative and inconclusive results dominate "
                "until more closed generations accumulate."
            ),
            source_refs=(
                "docs/papers/01_TRANSFER_PREDICTION.md",
            ),
            uncertainty="high",
        ),
        make_risk(
            category=RiskCategory.TEMPORAL_DEPENDENCE,
            affected_experiment_class="longitudinal and aging studies",
            severity="medium",
            description=(
                "Physical artifacts age (wear, laundering, color shift) while "
                "the model ecosystem drifts (new architectures, weights, "
                "preprocessing, thresholds). Once a model generation is "
                "observed it is never unseen again, so repeated measurements "
                "are temporally dependent and technological aging must be "
                "evaluated on the same frozen physical artifact."
            ),
            mitigation=(
                "Longitudinal aging design (paper 04) separating physical and "
                "technological aging, frozen garments across W0/W1/W5/W10 "
                "states, and permanent-observation bookkeeping of evaluated "
                "model generations."
            ),
            residual_risk=(
                "Drift between measurement waves is uncontrolled; aging "
                "conclusions remain cohort- and time-bound."
            ),
            source_refs=(
                "docs/papers/04_AGING.md",
                "docs/papers/01_TRANSFER_PREDICTION.md",
            ),
            uncertainty="medium",
        ),
    ]
    return ValidityRegister(seeds)
