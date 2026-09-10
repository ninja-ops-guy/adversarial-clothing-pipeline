"""Additive RAC evidence-class registry (Barrier 1).

This module is an ADDITIVE extension of the evidence taxonomy. It does not
modify ``ruthless_pipeline/certification/evidence.py`` in any way; governance
ratification of the new class into the certification core is a separate
handoff item for the governance swarm.

Newly registered class:
    ``experimental_print_specimen`` — a physical print-alpha manufacturing
    specimen. It is NOT evidence of physical-world adversarial efficacy, and
    any manifest carrying this class must keep
    ``physical_efficacy_claimed = false``. Unresolved vendor fields on such
    specimens are fail-closed via the literal string ``PENDING_USER_ACTION``.

Pure stdlib; no repo imports.
"""

from __future__ import annotations

from typing import Dict, FrozenSet

SCHEMA_VERSION = "1.0"

# Existing classes (preserved unchanged from the pre-Barrier-1 taxonomy).
SYNTHETIC_PIPELINE_VALIDATION_ONLY = "synthetic_pipeline_validation_only"
GENERATED_DIGITAL_REFERENCE = "generated_digital_reference"
LOG_ATTESTED = "log_attested"
SCENARIO_ASSUMPTION = "scenario_assumption"

# Newly registered class (additive).
EXPERIMENTAL_PRINT_SPECIMEN = "experimental_print_specimen"
DERIVED_DIGITAL_MEASUREMENT = "derived_digital_measurement"

EVIDENCE_CLASSES: FrozenSet[str] = frozenset(
    {
        SYNTHETIC_PIPELINE_VALIDATION_ONLY,
        GENERATED_DIGITAL_REFERENCE,
        LOG_ATTESTED,
        SCENARIO_ASSUMPTION,
        EXPERIMENTAL_PRINT_SPECIMEN,
        DERIVED_DIGITAL_MEASUREMENT,
    }
)

PENDING_USER_ACTION = "PENDING_USER_ACTION"

# Classes whose artifacts may never be cited as physical-world efficacy
# evidence. (Currently all registered classes: physical efficacy requires
# measured captures that do not exist yet.)
NON_EFFICACY_CLASSES: FrozenSet[str] = frozenset(EVIDENCE_CLASSES)

# Classes that fail-closed on outstanding user actions when fields are
# unresolved (e.g. vendor fields on a print specimen).
_USER_ACTION_GATED: FrozenSet[str] = frozenset({EXPERIMENTAL_PRINT_SPECIMEN})

# Human-readable description of each class, for audit/journal rendering.
DESCRIPTIONS: Dict[str, str] = {
    SYNTHETIC_PIPELINE_VALIDATION_ONLY: (
        "Synthetic pipeline output usable solely for validating the "
        "pipeline itself; never evidence of detector evasion efficacy."
    ),
    GENERATED_DIGITAL_REFERENCE: (
        "Generated digital reference artifact (e.g. rendered mockup); "
        "not a measured physical observation."
    ),
    LOG_ATTESTED: (
        "Claim attested only by experiment logs/journals; not independently "
        "verified against a measured capture."
    ),
    SCENARIO_ASSUMPTION: (
        "Assumption made for scenario construction; must not be treated "
        "as an observed fact."
    ),
    EXPERIMENTAL_PRINT_SPECIMEN: (
        "Physical print-alpha manufacturing specimen. Asserts print "
        "provenance only; physical_efficacy_claimed must remain false. "
        "Unresolved vendor fields are fail-closed as 'PENDING_USER_ACTION'."
    ),
    DERIVED_DIGITAL_MEASUREMENT: (
        "Deterministic measurement derived from a digital candidate artifact. "
        "May describe intrinsic pattern properties but never constitutes "
        "physical-world efficacy evidence."
    ),
}


def is_valid(cls: str) -> bool:
    """Return True iff ``cls`` is a registered evidence class."""
    return cls in EVIDENCE_CLASSES


def requires_user_action(cls: str) -> bool:
    """Return True iff artifacts of this class fail-closed on user actions.

    Raises KeyError for unregistered classes (fail-closed on typos).
    """
    if not is_valid(cls):
        raise KeyError(f"unregistered evidence class: {cls!r}")
    return cls in _USER_ACTION_GATED


def permits_physical_efficacy_claim(cls: str) -> bool:
    """Return True iff this class may carry a physical-efficacy claim.

    Always False for every currently registered class.
    """
    if not is_valid(cls):
        raise KeyError(f"unregistered evidence class: {cls!r}")
    return cls not in NON_EFFICACY_CLASSES


def describe(cls: str) -> str:
    """Return the audit description for a registered class."""
    if not is_valid(cls):
        raise KeyError(f"unregistered evidence class: {cls!r}")
    return DESCRIPTIONS[cls]
