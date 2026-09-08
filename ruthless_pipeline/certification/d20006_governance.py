"""Outcome-independent D2-0006 infrastructure: branch router, template
validation, and readiness gating.

This module implements tooling for the D2-0006 interpretation policy
(``docs/PREREGISTRATION_D2-0006_DRAFT.md``). It is deliberately
outcome-independent infrastructure:

- It never creates a D2-0006 generation file, directional hypothesis, or
  trigger path.
- The branch router consumes ONLY a sealed research release (per
  ``docs/RESEARCH_RELEASE_FORMAT.md``) plus the frozen interpretation-policy
  document, and emits a deterministic branch-selection memo. Every factual
  slot in the memo rationale is filled from the sealed artifacts; the router
  never invents numbers.
- All entry points fail closed: missing, tampered, or ambiguous inputs
  produce an error, never a guessed branch and never a "ready" verdict.

Branch mapping (frozen tree, policy §2):

- 2.1 SUCCESS            -> directional replication of CVaR superiority
- 2.2 NULL               -> equivalence / minimum-effect (SESOI) framing
- 2.3 NEGATIVE           -> reversal investigation with telemetry endpoints
- 2.4 INCONCLUSIVE       -> design-amended generation from OC evidence
- 2.5 INFRASTRUCTURE FAILURE -> amendment-authorized exactly-one re-run
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from ruthless_pipeline.certification.release_format import verify_release

REPO_ROOT = Path(__file__).resolve().parents[2]

DEFAULT_POLICY_PATH = REPO_ROOT / "docs" / "PREREGISTRATION_D2-0006_DRAFT.md"
DEFAULT_TEMPLATE_PATH = (
    REPO_ROOT / "docs" / "templates" / "PREREGISTRATION_D2-0006_TEMPLATE.md"
)

D20005_GENERATION_ID = "RAC-PER-D2-0005"
D20006_GENERATION_ID = "RAC-PER-D2-0006"

#: Decision regions preregistered for D2-0005 (§4 of PREREGISTRATION_D2-0005),
#: mapped to the interpretation-policy branch that fires on each region.
DECISION_REGION_BRANCHES = {
    "SUCCESS": "2.1",
    "NULL": "2.2",
    "NEGATIVE": "2.3",
    "INCONCLUSIVE": "2.4",
}

INFRASTRUCTURE_FAILURE_BRANCH = "2.5"

#: FAILURE.json classification category that marks a TRUE infrastructure
#: failure (no outcome produced). A scientific failure classification (e.g.
#: D2-0004's cross_architecture_transfer_failure, where an outcome WAS
#: observed) must NEVER route to branch 2.5.
INFRASTRUCTURE_FAILURE_CATEGORY = "infrastructure_failure"

BRANCH_NAMES = {
    "2.1": "SUCCESS replication (fresh-generation CVaR-superiority replication)",
    "2.2": "NULL equivalence / minimum-effect (SESOI) framing",
    "2.3": "NEGATIVE reversal investigation with objective-telemetry endpoints",
    "2.4": "INCONCLUSIVE design-amended generation informed by OC evidence",
    "2.5": "INFRASTRUCTURE FAILURE amendment-authorized re-run policy",
}

#: Markers that must be present in the document offered as the interpretation
#: policy, so the router fails closed if handed the wrong (or a truncated)
#: document. These identify the frozen five-branch tree only; they carry no
#: outcome information.
POLICY_REQUIRED_MARKERS = (
    "### 2.1 If D2-0005 closes as SUCCESS",
    "### 2.2 If D2-0005 closes as NULL",
    "### 2.3 If D2-0005 closes as NEGATIVE",
    "### 2.4 If D2-0005 closes as INCONCLUSIVE",
    "INFRASTRUCTURE FAILURE",
    "BLOCKED until D2-0005 closes",
)

#: Rationale text templates. Slots are filled EXCLUSIVELY from sealed release
#: artifacts and the policy document hash. No slot ever carries a number that
#: is not byte-present in a sealed input.
RATIONALE_TEMPLATES = {
    "2.1": (
        "Sealed release {release_id} (content_hash {content_hash}, source_commit "
        "{source_commit}) closed in decision region SUCCESS. Per the frozen "
        "interpretation-policy tree (policy sha256 {policy_sha256}, branch 2.1), "
        "D2-0006 is a directional replication of CVaR superiority on a FRESH "
        "generation: fresh candidate pool (new seed), fresh held-out conditions "
        "disjoint from PERSON-HO-v3, same RAC-PERSON-DETECT protocol lineage. "
        "The exact directional hypothesis and replication region are written at "
        "D2-0006 preregistration time, anchored on the D2-0005 observed interval "
        "as sealed in {release_id}, never on desired outcomes."
    ),
    "2.2": (
        "Sealed release {release_id} (content_hash {content_hash}, source_commit "
        "{source_commit}) closed in decision region NULL (informative null). Per "
        "the frozen interpretation-policy tree (policy sha256 {policy_sha256}, "
        "branch 2.2), D2-0006 tests a bounds/equivalence claim against a "
        "smallest effect size of interest (SESOI) fixed at D2-0006 "
        "preregistration time, justified from the closed interval in "
        "{release_id} — never tuned to guarantee equivalence passes. Fresh "
        "candidate pool and fresh held-out conditions apply."
    ),
    "2.3": (
        "Sealed release {release_id} (content_hash {content_hash}, source_commit "
        "{source_commit}) closed in decision region NEGATIVE (reversal: the mean "
        "objective transferred better than CVaR). Per the frozen "
        "interpretation-policy tree (policy sha256 {policy_sha256}, branch 2.3), "
        "D2-0006 confirms the reversal on a fresh generation with a directional "
        "hypothesis of the reversed sign, plus mechanistic secondary endpoints "
        "from the sealed objective telemetry (labeled speculative_open). The "
        "no-silent-abandonment rule applies: discontinuation of the CVaR line "
        "would itself require a written governance decision."
    ),
    "2.4": (
        "Sealed release {release_id} (content_hash {content_hash}, source_commit "
        "{source_commit}) closed in decision region INCONCLUSIVE. Per the frozen "
        "interpretation-policy tree (policy sha256 {policy_sha256}, branch 2.4), "
        "D2-0006 is a design-amended generation sized from the pre-arming "
        "operating-characteristic evidence (labeled scenario_assumption), with "
        "every amendment documented and traceable to that evidence — never to a "
        "desired sign or magnitude of effect. The inconclusive D2-0005 remains "
        "a published closed datapoint and is never re-run silently."
    ),
    "2.5": (
        "Sealed release {release_id} (content_hash {content_hash}, source_commit "
        "{source_commit}) records an INFRASTRUCTURE FAILURE at stage "
        "{failure_stage} (FAILURE.json sha256 {failure_json_sha256}): no outcome "
        "was produced, and the sealed bundle contains no held-out outcome "
        "artifacts. Per the frozen interpretation-policy tree (policy sha256 "
        "{policy_sha256}, branch 2.5), the policy is an amendment-authorized "
        "re-run following the AMENDMENT_D2-0004-INFRA-001 pattern: "
        "outcome-never-observed criterion, exactly ONE re-run per failure "
        "event, no scientific parameter changes, recorded root cause, and "
        "published failure disclosure. Failure reason as sealed: "
        "{failure_reason}"
    ),
}


class GovernanceError(Exception):
    """Raised on any missing, invalid, or ambiguous governance input."""


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _load_json(path: Path, what: str) -> Any:
    try:
        text = path.read_text()
    except OSError as exc:
        raise GovernanceError(f"{what} unreadable: {path}: {exc}") from exc
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise GovernanceError(f"{what} is not valid JSON: {path}: {exc}") from exc


def load_policy_document(policy_path: Path) -> dict[str, Any]:
    """Load the interpretation-policy document and verify its frozen markers.

    Fails closed if the document is missing or lacks the five-branch tree
    markers, so the router can never run against the wrong policy text.
    Returns the document path, sha256, and text.
    """
    policy_path = Path(policy_path)
    if not policy_path.is_file():
        raise GovernanceError(f"policy document not found: {policy_path}")
    text = policy_path.read_text()
    missing = [m for m in POLICY_REQUIRED_MARKERS if m not in text]
    if missing:
        raise GovernanceError(
            "policy document is missing required frozen-tree markers "
            f"(refusing to route against an unrecognized policy): {missing}"
        )
    return {
        "path": str(policy_path),
        "sha256": _sha256_bytes(text.encode("utf-8")),
        "text": text,
    }


def classify_release_closure(
    release_dir: Path, expect_generation_id: str | None = D20005_GENERATION_ID
) -> dict[str, Any]:
    """Classify a sealed release's closure for branch routing.

    Returns a closure record with either a ``decision_region`` (one of the
    preregistered D2-0005 regions) or ``infrastructure_failure: True``.

    Fail-closed rules:
    - the release must verify per ``docs/RESEARCH_RELEASE_FORMAT.md`` §6
      (no tampered/missing/extra files), and ``RELEASE.json`` must carry a
      well-formed 64-hex ``content_hash``;
    - when ``expect_generation_id`` is set, the release's ``generation_id``
      must equal it (the router routes a SPECIFIC generation's closure);
    - an outcome-based closure requires exactly one outcome artifact under
      ``stages/optimization_telemetry/outcome/`` declaring a preregistered
      ``decision_region``;
    - an infrastructure-failure closure requires ``FAILURE.json`` with
      ``classification.category == "infrastructure_failure"`` AND the total
      absence of held-out outcome artifacts (the artifact-level shadow of
      the outcome-never-observed criterion). A FAILURE.json recording a
      SCIENTIFIC failure (an observed outcome that falsified the hypothesis)
      is not infrastructure failure and is rejected;
    - a release with BOTH outcome artifacts and any FAILURE.json is
      ambiguous and rejected;
    - anything else is unclassifiable and rejected.
    """
    release_dir = Path(release_dir)
    if not release_dir.is_dir():
        raise GovernanceError(f"release directory not found: {release_dir}")

    try:
        result = verify_release(release_dir)
    except ValueError as exc:
        raise GovernanceError(f"release is not verifiable: {exc}") from exc
    if not result.ok:
        raise GovernanceError(
            "release fails verification per RESEARCH_RELEASE_FORMAT §6 "
            f"(tampered={result.tampered}, missing={result.missing}, "
            f"extra={result.extra}); an unverifiable release MUST NOT be "
            "cited as evidence and cannot drive branch selection"
        )

    experiment = _load_json(release_dir / "experiment.json", "experiment.json")
    generation_id = experiment.get("generation_id")
    experiment_id = experiment.get("experiment_id")
    if not isinstance(generation_id, str) or not generation_id:
        raise GovernanceError("experiment.json lacks a generation_id")
    if expect_generation_id is not None and generation_id != expect_generation_id:
        raise GovernanceError(
            f"release generation_id {generation_id!r} does not match the "
            f"generation being routed ({expect_generation_id!r}); refusing to "
            "route the wrong generation's closure"
        )
    if experiment_id != release_dir.name:
        raise GovernanceError(
            f"experiment_id {experiment_id!r} does not match release "
            f"directory name {release_dir.name!r}"
        )

    release_meta = _load_json(release_dir / "RELEASE.json", "RELEASE.json")
    content_hash = release_meta.get("content_hash")
    if not (isinstance(content_hash, str) and re.fullmatch(r"[0-9a-f]{64}", content_hash)):
        raise GovernanceError(
            "RELEASE.json content_hash is not a 64-hex SHA-256 digest"
        )

    outcome_dir = release_dir / "stages" / "optimization_telemetry" / "outcome"
    outcome_files = (
        sorted(p for p in outcome_dir.iterdir() if p.is_file())
        if outcome_dir.is_dir()
        else []
    )
    failure_path = release_dir / "FAILURE.json"

    base = {
        "release_dir": str(release_dir),
        "release_id": experiment_id,
        "generation_id": generation_id,
        "content_hash": content_hash,
        "source_commit": release_meta.get("source_commit"),
        "created_utc": release_meta.get("created_utc"),
    }

    if failure_path.is_file():
        failure = _load_json(failure_path, "FAILURE.json")
        for field in ("failure_stage", "failure_reason", "detected_utc", "invalidates"):
            if field not in failure:
                raise GovernanceError(
                    f"FAILURE.json missing required field {field!r} "
                    "(RESEARCH_RELEASE_FORMAT §2.4)"
                )
        if outcome_files:
            raise GovernanceError(
                "release carries BOTH FAILURE.json and held-out outcome "
                "artifacts: the outcome-never-observed criterion of policy "
                "§2.5 cannot be established from the sealed artifacts, and no "
                "decision region is attested. Refusing to classify (fail "
                "closed). If the outcome was observed, close under the "
                "§2.1–§2.4 outcome semantics via a decision-region artifact."
            )
        category = (failure.get("classification") or {}).get("category")
        if category != INFRASTRUCTURE_FAILURE_CATEGORY:
            raise GovernanceError(
                f"FAILURE.json classification category {category!r} is not "
                f"{INFRASTRUCTURE_FAILURE_CATEGORY!r}: a scientific failure "
                "record (an observed outcome) is not an infrastructure "
                "failure and cannot route to branch 2.5. No decision-region "
                "artifact is present either, so this release is "
                "unclassifiable for D2-0006 routing (fail closed)."
            )
        base.update(
            {
                "infrastructure_failure": True,
                "failure_stage": failure["failure_stage"],
                "failure_reason": failure["failure_reason"],
                "failure_json_sha256": _sha256_file(failure_path),
            }
        )
        return base

    if not outcome_files:
        raise GovernanceError(
            "release has neither a decision-region outcome artifact under "
            "stages/optimization_telemetry/outcome/ nor FAILURE.json: closure "
            "is unclassifiable (fail closed)"
        )
    if len(outcome_files) != 1:
        raise GovernanceError(
            f"expected exactly one decision-region outcome artifact, found "
            f"{len(outcome_files)}: refusing to pick among them (fail closed)"
        )

    outcome_file = outcome_files[0]
    outcome = _load_json(outcome_file, "decision-region outcome artifact")
    region = outcome.get("decision_region")
    if region not in DECISION_REGION_BRANCHES:
        raise GovernanceError(
            f"decision_region {region!r} is not one of the preregistered "
            f"regions {sorted(DECISION_REGION_BRANCHES)} (fail closed)"
        )
    base.update(
        {
            "infrastructure_failure": False,
            "decision_region": region,
            "outcome_artifact": outcome_file.name,
            "outcome_artifact_sha256": _sha256_file(outcome_file),
        }
    )
    return base


def build_branch_memo(closure: dict[str, Any], policy: dict[str, Any]) -> dict[str, Any]:
    """Build the deterministic branch-selection memo from a closure record.

    The memo is deterministic: it contains no wall-clock timestamps and no
    values other than those byte-present in the sealed inputs. Sorting keys
    and re-serializing yields byte-identical output for identical inputs.
    """
    if closure.get("infrastructure_failure"):
        branch = INFRASTRUCTURE_FAILURE_BRANCH
        slots = {
            "failure_stage": closure["failure_stage"],
            "failure_reason": closure["failure_reason"],
            "failure_json_sha256": closure["failure_json_sha256"],
        }
        evidence = {
            "release_content_hash": closure["content_hash"],
            "failure_json_sha256": closure["failure_json_sha256"],
            "outcome_artifact_sha256": None,
        }
        trigger = {
            "kind": "infrastructure_failure",
            "failure_stage": closure["failure_stage"],
        }
    else:
        region = closure.get("decision_region")
        if region not in DECISION_REGION_BRANCHES:
            raise GovernanceError(f"closure record has no valid decision region: {region!r}")
        branch = DECISION_REGION_BRANCHES[region]
        slots = {}
        evidence = {
            "release_content_hash": closure["content_hash"],
            "failure_json_sha256": None,
            "outcome_artifact_sha256": closure["outcome_artifact_sha256"],
        }
        trigger = {"kind": "decision_region", "decision_region": region}

    rationale = RATIONALE_TEMPLATES[branch].format(
        release_id=closure["release_id"],
        content_hash=closure["content_hash"],
        source_commit=closure["source_commit"],
        policy_sha256=policy["sha256"],
        **slots,
    )

    memo = {
        "memo_type": "d20006_branch_selection",
        "memo_schema_version": "1.0",
        "branch_id": branch,
        "branch_name": BRANCH_NAMES[branch],
        "policy_document": {
            "path": policy["path"],
            "sha256": policy["sha256"],
        },
        "sealed_release": {
            "release_id": closure["release_id"],
            "generation_id": closure["generation_id"],
            "content_hash": closure["content_hash"],
            "source_commit": closure["source_commit"],
            "created_utc": closure["created_utc"],
        },
        "trigger": trigger,
        "triggering_evidence": evidence,
        "rationale": rationale,
        "outcome_independence_attestation": (
            "This memo is a mechanical lookup of the frozen interpretation-"
            "policy tree against a sealed, verified release. It selects only "
            "the FORM of a future D2-0006 preregistration. It contains no "
            "directional hypothesis, no effect-size region, no budget, no "
            "generation skeleton, and no trigger path, and it arms nothing."
        ),
    }
    return memo


def memo_to_json(memo: dict[str, Any]) -> str:
    """Deterministic memo serialization (canonical JSON + trailing newline)."""
    return json.dumps(memo, indent=2, sort_keys=True) + "\n"


# --------------------------------------------------------------------------
# D2-0006 preregistration template validation
# --------------------------------------------------------------------------

#: Mandatory slots of the D2-0006 preregistration template. A document is
#: "complete" only when every slot has been replaced by real content.
MANDATORY_SLOTS = (
    "HYPOTHESIS",
    "PROTOCOL_VERSION",
    "SURROGATE_MODEL_SET",
    "HELDOUT_MODEL_SET",
    "POOL_SEED",
    "DECISION_REGIONS",
    "RUNTIME_LOCK_REFERENCE",
    "SELECTED_BRANCH",
    "BRANCH_MEMO_SHA256",
    "BUDGET_CAPS",
    "TREE_COMMIT_SHA",
)

#: Section labels that must survive in the COMPLETED document, so a mandatory
#: slot cannot be "filled" by silently deleting the field.
REQUIRED_SECTION_LABELS = (
    "Selected interpretation-policy branch",
    "Directional hypothesis",
    "Protocol:",
    "Surrogate model set",
    "Held-out model set",
    "Fresh candidate pool seed",
    "Decision regions",
    "Budget caps",
    "Runtime lock reference",
    "Infrastructure-failure clause",
    "Timing disclosure",
)

_SLOT_PATTERN = re.compile(r"\{\{([A-Z0-9_]+)\}\}")

#: The infra-failure clause marker: policy §2.5 requires the D2-0006
#: preregistration to adopt the infrastructure-failure policy BY REFERENCE.
INFRA_CLAUSE_MARKERS = ("infrastructure-failure clause", "§2.5")

#: Phrases that indicate a still-open (outcome-dependent) field.
OPEN_FIELD_MARKERS = ("TBD", "BLOCKED until D2-0005 closes")


def validate_preregistration_document(text: str) -> list[str]:
    """Validate a candidate D2-0006 preregistration document.

    Returns a list of problems; empty means the document is structurally
    complete. A template with unfilled ``{{SLOT}}`` placeholders MUST fail.
    This checks structural completeness only — it asserts nothing about the
    scientific content, and it never fills slots itself.
    """
    problems: list[str] = []

    slots_present = set(_SLOT_PATTERN.findall(text))
    if slots_present:
        problems.append(
            "unfilled template slots remain: " + ", ".join(sorted(slots_present))
        )

    unknown = slots_present - set(MANDATORY_SLOTS)
    if unknown:
        problems.append("unrecognized slots present: " + ", ".join(sorted(unknown)))

    for marker in OPEN_FIELD_MARKERS:
        if marker in text:
            problems.append(
                f"open-field marker {marker!r} still present; decided-later "
                "fields may only be filled after D2-0005 closes"
            )

    for label in REQUIRED_SECTION_LABELS:
        if label not in text:
            problems.append(
                f"mandatory section label {label!r} missing; mandatory slots "
                "may not be deleted instead of filled"
            )

    lowered = text.lower()
    for marker in INFRA_CLAUSE_MARKERS:
        if marker.lower() not in lowered:
            problems.append(
                f"mandatory infrastructure-failure clause marker {marker!r} "
                "missing; the preregistration must adopt policy §2.5 by "
                "reference BEFORE D2-0006 executes"
            )

    return problems


# --------------------------------------------------------------------------
# Readiness gating
# --------------------------------------------------------------------------


def _check_d20005_closed_or_discontinued(
    release_dir: Path | None, discontinuation_path: Path | None
) -> dict[str, Any]:
    if release_dir is not None:
        try:
            closure = classify_release_closure(Path(release_dir))
        except GovernanceError as exc:
            return {
                "name": "d20005_closed_or_discontinued",
                "satisfied": False,
                "detail": f"D2-0005 release offered but not usable: {exc}",
            }
        if closure["generation_id"] != D20005_GENERATION_ID:
            return {
                "name": "d20005_closed_or_discontinued",
                "satisfied": False,
                "detail": (
                    f"release generation_id is {closure['generation_id']!r}, "
                    f"expected {D20005_GENERATION_ID!r}"
                ),
            }
        return {
            "name": "d20005_closed_or_discontinued",
            "satisfied": True,
            "detail": (
                f"D2-0005 closed: sealed release {closure['release_id']} "
                f"(content_hash {closure['content_hash']})"
            ),
        }
    if discontinuation_path is not None:
        path = Path(discontinuation_path)
        if not path.is_file() or not path.read_text().strip():
            return {
                "name": "d20005_closed_or_discontinued",
                "satisfied": False,
                "detail": f"discontinuation record missing or empty: {path}",
            }
        return {
            "name": "d20005_closed_or_discontinued",
            "satisfied": True,
            "detail": (
                f"D2-0005 formally discontinued per {path} "
                f"(sha256 {_sha256_file(path)})"
            ),
        }
    return {
        "name": "d20005_closed_or_discontinued",
        "satisfied": False,
        "detail": (
            "neither a sealed D2-0005 release nor a formal discontinuation "
            "record was provided"
        ),
    }


def _check_branch_memo(memo_path: Path | None, policy: dict[str, Any]) -> dict[str, Any]:
    name = "branch_selection_memo"
    if memo_path is None:
        return {
            "name": name,
            "satisfied": False,
            "detail": "no branch-selection memo provided",
        }
    memo = _load_json(Path(memo_path), "branch-selection memo")
    problems = []
    if memo.get("memo_type") != "d20006_branch_selection":
        problems.append("memo_type is not d20006_branch_selection")
    if memo.get("branch_id") not in BRANCH_NAMES:
        problems.append(f"branch_id {memo.get('branch_id')!r} is not a frozen-tree branch")
    memo_policy = (memo.get("policy_document") or {}).get("sha256")
    if memo_policy != policy["sha256"]:
        problems.append(
            "memo policy sha256 does not match the current policy document "
            f"(memo {memo_policy}, current {policy['sha256']})"
        )
    return {
        "name": name,
        "satisfied": not problems,
        "detail": "; ".join(problems) if problems else "memo validates against the frozen policy",
    }


def _check_preregistration_document(doc_path: Path | None) -> dict[str, Any]:
    name = "d20006_preregistration_complete"
    if doc_path is None:
        return {"name": name, "satisfied": False, "detail": "no preregistration document provided"}
    path = Path(doc_path)
    if not path.is_file():
        return {"name": name, "satisfied": False, "detail": f"document not found: {path}"}
    problems = validate_preregistration_document(path.read_text())
    return {
        "name": name,
        "satisfied": not problems,
        "detail": "; ".join(problems) if problems else "all mandatory slots filled; infra clause present",
    }


def _check_no_d20006_generation_file(repo_root: Path = REPO_ROOT) -> dict[str, Any]:
    """Readiness must never coexist with an armed/armable D2-0006 surface.

    Per policy §5 there is deliberately no D2-0006 generation file. Creating
    one is a separately reviewed change that follows — never precedes or
    accompanies — the preregistration freeze. If one exists, readiness is
    refused and the violation is surfaced.
    """
    name = "no_d20006_generation_or_trigger_surface"
    gen_path = Path(repo_root) / "generations" / f"{D20006_GENERATION_ID}.json"
    if gen_path.exists():
        return {
            "name": name,
            "satisfied": False,
            "detail": (
                f"{gen_path} exists: policy §5 forbids any D2-0006 generation "
                "skeleton at this stage; readiness refused"
            ),
        }
    return {
        "name": name,
        "satisfied": True,
        "detail": "no D2-0006 generation file exists (as required by policy §5)",
    }


def check_readiness(
    *,
    policy_path: Path = DEFAULT_POLICY_PATH,
    d20005_release_dir: Path | None = None,
    d20005_discontinuation_path: Path | None = None,
    branch_memo_path: Path | None = None,
    preregistration_doc_path: Path | None = None,
    repo_root: Path = REPO_ROOT,
) -> dict[str, Any]:
    """Evaluate the D2-0006 readiness checklist.

    Returns ``{"ready": bool, "prerequisites": [...]}``. ``ready`` is True
    only when EVERY explicit prerequisite is satisfied; the function never
    raises for an unmet prerequisite — it reports it. It raises
    ``GovernanceError`` only when the policy document itself is invalid
    (there is then nothing to be ready against).
    """
    policy = load_policy_document(Path(policy_path))
    prerequisites = [
        _check_d20005_closed_or_discontinued(
            Path(d20005_release_dir) if d20005_release_dir else None,
            Path(d20005_discontinuation_path) if d20005_discontinuation_path else None,
        ),
        _check_branch_memo(Path(branch_memo_path) if branch_memo_path else None, policy),
        _check_preregistration_document(
            Path(preregistration_doc_path) if preregistration_doc_path else None
        ),
        _check_no_d20006_generation_file(Path(repo_root)),
    ]
    return {
        "ready": all(p["satisfied"] for p in prerequisites),
        "policy_sha256": policy["sha256"],
        "prerequisites": prerequisites,
    }
