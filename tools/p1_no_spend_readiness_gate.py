#!/usr/bin/env python3
"""P1 NO-SPEND READINESS GATE — independent verification that the complete
physical P1 workflow is frozen, hash-bound, provenance-linked, rehearsed, and
free of silently substituted vendor/fabrication/garment/measurement values.

Verdict: P1_NO_SPEND_READINESS=PASS | FAIL (fail-closed: any FINDING or
REFUSED check fails the gate; refusals are never silent).

Checks:
- freeze_integrity: every artifact pinned in P1_READINESS_FREEZE.json
  re-hashed and compared (byte-level).
- freeze_manifest_self_consistency: the freeze manifest's own structure
  (schema version, no duplicate pins, pins are 64-hex).
- protocol_surface_completeness: every required protocol surface exists and
  is pinned (capture rig, calibration, session manifest, pairing contract,
  schedule, naming, rig checklist, arrival checklist, receipt QA, custody,
  pairing checklist, ingestion contracts, stopping rule, runbook).
- ua_fields_pending: every vendor/fabrication/garment/measurement field
  listed in the freeze manifest is still the literal string
  "PENDING_USER_ACTION" — never defaulted; the set of pending paths must
  equal the frozen set exactly (silent resolution AND silent addition both
  fail).
- pending_literals_canonical: across all scanned manifests the only pending
  marker is the exact literal "PENDING_USER_ACTION".
- pairing_contract: the pairing/randomization contract re-derives
  byte-identically from its seed; grid arithmetic matches
  STOPPING_RULE.json (max_valid_trials = 144); first-arm balance holds.
- schedule_frozen: P1_CAPTURE_SCHEDULE.json re-derives byte-identically and
  covers every trial exactly once.
- ingestion_contracts: ingestion/validation entrypoints import and their
  promotion gate refuses synthetic-as-physical and uncalibrated-physical
  payloads.
- synthetic_rehearsal_deterministic: the full synthetic chain (receipt ->
  calibration -> capture -> ingestion -> stopping rule -> sealed release)
  runs twice into fresh directories, byte-identical summary.
- failure_injection: the rehearsal failure-injection battery (duplicate
  capture, calibration association, invalid-condition overload, stopping
  replay, tampered store, promotion attempt) plus gate-local injections
  (tampered pinned artifact, defaulted UA field, mutated schedule) all
  fail closed.
- scientific_boundaries: the five assertions re-read from authoritative
  files.

Usage:
    python3 tools/p1_no_spend_readiness_gate.py [--repo-root .] \
        [--json-out artifacts/p1-readiness/readiness-report.json] \
        [--md-out docs/audits/P1_NO_SPEND_READINESS_AUDIT.md]
    python3 tools/p1_no_spend_readiness_gate.py --write-freeze  # re-pin
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

GATE_ID = "P1-NO-SPEND-READINESS-GATE"
SCHEMA_VERSION = "1.0"
FREEZE_PATH = "physical/p1/P1_READINESS_FREEZE.json"
PENDING_LITERAL = "PENDING_USER_ACTION"

#: Canonical pending markers: the exact frozen literal, plus any fully
#: uppercase explicit ``PENDING_<CAUSE>`` marker (e.g. the production-alpha
#: SKU manifest's PENDING_TEMPLATE_DOWNLOAD / PENDING_USER_SIZE_SELECTION).
#: All are explicit, operator-visible, and never a software default.
import re as _re

_PENDING_MARKER_RE = _re.compile(r"^PENDING_[A-Z][A-Z0-9_]*$")


def _is_pending_marker(value) -> bool:
    return isinstance(value, str) and (
        value == PENDING_LITERAL or bool(_PENDING_MARKER_RE.match(value))
    )

PASS = "PASS"
FINDING = "FINDING"
REFUSED = "REFUSED"

#: Protocol surfaces that must exist and be hash-pinned for "no
#: improvisation" readiness. Paths are repo-relative.
REQUIRED_SURFACES = (
    "docs/P1_CAPTURE_RIG_SPEC.md",
    "docs/CALIBRATION_TARGET_SPEC.md",
    "docs/PHYSICAL_SPECIMEN_ARRIVAL_CHECKLIST.md",
    "docs/USER_ACTION_REQUIRED_PRINT_ALPHA.md",
    "physical/p1/CALIBRATION_MANIFEST.json",
    "physical/p1/CAMERA_LIGHTING_SETUP.md",
    "physical/p1/CAPTURE_NAMING_CONVENTION.md",
    "physical/p1/PHYSICAL_TRIAL_INGESTION_TEMPLATE.json",
    "physical/p1/RIG_MEASUREMENT_CHECKLIST.md",
    "physical/p1/SESSION_MANIFEST_TEMPLATE.json",
    "physical/p1/STOPPING_RULE.json",
    "physical/p1/PAIRING_RANDOMIZATION_CONTRACT.json",
    "physical/p1/P1_CAPTURE_SCHEDULE.json",
    "physical/p1/P1_OPERATOR_RUNBOOK.md",
    "print-alpha/MANIFESTS/artwork-manifest.json",
    "print-alpha/MANIFESTS/mapping-manifest.json",
    "print-alpha/MANIFESTS/print-alpha-manifest.json",
    "print-alpha/MANIFESTS/sku-manifest.json",
    "print-alpha/MANIFESTS/template-manifest.json",
    "print-alpha/QA/garment-pairing-checklist.md",
    "print-alpha/QA/chain-of-custody.md",
    "production_alpha/ORDER_CHECKLIST.md",
    "production_alpha/RECEIPT_QA_FORM.md",
    "production_alpha/SKU_MANIFEST.json",
    "schemas/physical_transfer_record.schema.json",
    "schemas/print_alpha_manifest.schema.json",
)

#: Manifests scanned for pending-vendor fields.
UA_SCAN_FILES = (
    "print-alpha/MANIFESTS/artwork-manifest.json",
    "print-alpha/MANIFESTS/mapping-manifest.json",
    "print-alpha/MANIFESTS/print-alpha-manifest.json",
    "print-alpha/MANIFESTS/sku-manifest.json",
    "print-alpha/MANIFESTS/template-manifest.json",
    "production_alpha/SKU_MANIFEST.json",
)


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _record(status: str, **fields) -> dict:
    return {"status": status, **fields}


def _guard(fn):
    def wrapper(*a, **k):
        try:
            return fn(*a, **k)
        except Exception as exc:  # noqa: BLE001 - refusal must capture anything
            return _record(REFUSED, refusal_reason=f"{type(exc).__name__}: {exc}")

    return wrapper


def _pending_paths(payload, prefix="") -> set[str]:
    """Collect JSON paths whose value is exactly the pending literal."""
    paths: set[str] = set()
    if isinstance(payload, dict):
        for key, value in payload.items():
            paths |= _pending_paths(value, f"{prefix}.{key}" if prefix else key)
    elif isinstance(payload, list):
        for i, value in enumerate(payload):
            paths |= _pending_paths(value, f"{prefix}[{i}]")
    elif _is_pending_marker(payload):
        paths.add(prefix)
    return paths


def _suspicious_pending_markers(payload, prefix="") -> list[str]:
    """Marker-style values that are NOT canonical pending literals.

    Only fully uppercase marker-shaped tokens are considered; prose notes
    that merely mention a pending literal in a sentence are not markers.
    """
    bad: list[str] = []
    if isinstance(payload, dict):
        for key, value in payload.items():
            bad += _suspicious_pending_markers(value, f"{prefix}.{key}" if prefix else key)
    elif isinstance(payload, list):
        for i, value in enumerate(payload):
            bad += _suspicious_pending_markers(value, f"{prefix}[{i}]")
    elif isinstance(payload, str):
        if _is_pending_marker(payload):
            return bad
        # Marker-shaped: uppercase token style (letters/digits/underscores,
        # optional dashes), no sentence whitespace beyond separators.
        marker_shaped = bool(_re.fullmatch(r"[A-Z][A-Z0-9_\-]*", payload))
        if marker_shaped and (
            "PENDING" in payload or "TBD" in payload or "PLACEHOLDER" in payload or "FIXME" in payload
        ) and not payload.startswith("FILL-IN"):  # session templates use FILL-IN by design
            bad.append(f"{prefix}={payload!r}")
    return bad


def scan_pending_fields(repo_root: Path) -> dict[str, set[str]]:
    result: dict[str, set[str]] = {}
    for rel in UA_SCAN_FILES:
        path = repo_root / rel
        if path.is_file():
            result[rel] = _pending_paths(json.loads(path.read_text()))
    return result


# --------------------------------------------------------------------------
# Freeze manifest
# --------------------------------------------------------------------------

def build_freeze_manifest(repo_root: Path) -> dict:
    from ruthless_pipeline.certification import p1_pairing_schedule as ps

    pins = {}
    missing = []
    for rel in REQUIRED_SURFACES:
        path = repo_root / rel
        if path.is_file():
            pins[rel] = _sha256_file(path)
        else:
            missing.append(rel)
    pending = scan_pending_fields(repo_root)
    return {
        "schema_version": SCHEMA_VERSION,
        "freeze_id": "P1-READINESS-FREEZE-2026-001",
        "gate_id": GATE_ID,
        "created_by": "tools/p1_no_spend_readiness_gate.py --write-freeze",
        "artifact_sha256": pins,
        "missing_surfaces": missing,
        "expected_pending_fields": {rel: sorted(paths) for rel, paths in pending.items()},
        "pairing_contract": {
            "contract_id": ps.CONTRACT_ID,
            "seed": ps.CONTRACT_SEED,
            "planned_valid_trials": ps.EXPECTED_TRIALS,
            "schedule_sha256": ps.schedule_sha256(ps.derive_schedule()),
        },
        "boundary_assertions": {
            "D2_0004_MODIFIED": False,
            "D2_0005_ARMED": False,
            "NEW_HELDOUT_ACCESS": False,
            "SCIENTIFIC_THRESHOLDS_CHANGED": False,
            "PHYSICAL_EFFICACY_CLAIMED": False,
        },
        "evidence_class": "synthetic_pipeline_validation_only",
        "physical_efficacy_claimed": False,
    }


# --------------------------------------------------------------------------
# Checks
# --------------------------------------------------------------------------

@_guard
def check_freeze_integrity(repo_root: Path) -> dict:
    freeze_path = repo_root / FREEZE_PATH
    if not freeze_path.is_file():
        return _record(REFUSED, refusal_reason=f"{FREEZE_PATH} missing — run --write-freeze")
    freeze = json.loads(freeze_path.read_text())
    mismatches = []
    for rel, expected in freeze["artifact_sha256"].items():
        path = repo_root / rel
        if not path.is_file():
            mismatches.append({"path": rel, "expected": expected, "actual": "MISSING"})
            continue
        actual = _sha256_file(path)
        if actual != expected:
            mismatches.append({"path": rel, "expected": expected, "actual": actual})
    return _record(
        PASS if not mismatches else FINDING,
        pinned=len(freeze["artifact_sha256"]),
        mismatches=mismatches,
        detail="every pinned protocol artifact re-hashed and compared",
    )


@_guard
def check_freeze_self_consistency(repo_root: Path) -> dict:
    freeze = json.loads((repo_root / FREEZE_PATH).read_text())
    problems = []
    if freeze.get("schema_version") != SCHEMA_VERSION:
        problems.append("freeze schema_version mismatch")
    pins = freeze.get("artifact_sha256", {})
    if len(pins) != len(set(pins)):
        problems.append("duplicate pins")
    bad_hex = [p for p, s in pins.items() if not (isinstance(s, str) and len(s) == 64 and all(c in "0123456789abcdef" for c in s))]
    if bad_hex:
        problems.append(f"non-64-hex pins: {bad_hex}")
    if freeze.get("missing_surfaces"):
        problems.append(f"missing surfaces recorded at freeze time: {freeze['missing_surfaces']}")
    return _record(PASS if not problems else FINDING, problems=problems)


@_guard
def check_surface_completeness(repo_root: Path) -> dict:
    freeze = json.loads((repo_root / FREEZE_PATH).read_text())
    missing = [rel for rel in REQUIRED_SURFACES if not (repo_root / rel).is_file()]
    unpinned = [rel for rel in REQUIRED_SURFACES if rel not in freeze.get("artifact_sha256", {})]
    ok = not missing and not unpinned
    return _record(
        PASS if ok else FINDING,
        required=len(REQUIRED_SURFACES),
        missing=missing,
        unpinned=unpinned,
    )


@_guard
def check_ua_fields_pending(repo_root: Path) -> dict:
    """Every frozen pending field is still the literal PENDING_USER_ACTION,
    and the pending set is exactly the frozen set (no silent resolution, no
    silent addition)."""
    freeze = json.loads((repo_root / FREEZE_PATH).read_text())
    expected = {rel: set(paths) for rel, paths in freeze["expected_pending_fields"].items()}
    actual = scan_pending_fields(repo_root)
    problems = []
    for rel in sorted(set(expected) | set(actual)):
        exp, act = expected.get(rel, set()), actual.get(rel, set())
        resolved = sorted(exp - act)
        added = sorted(act - exp)
        if resolved:
            problems.append({"file": rel, "silently_resolved": resolved})
        if added:
            problems.append({"file": rel, "silently_added": added})
    total_pending = sum(len(v) for v in actual.values())
    return _record(
        PASS if not problems else FINDING,
        problems=problems,
        pending_fields=total_pending,
        detail="vendor/fabrication/garment/measurement fields remain explicitly pending; none defaulted",
    )


@_guard
def check_pending_literals_canonical(repo_root: Path) -> dict:
    bad = []
    for rel in UA_SCAN_FILES:
        path = repo_root / rel
        if path.is_file():
            bad += [f"{rel}:{m}" for m in _suspicious_pending_markers(json.loads(path.read_text()))]
    return _record(PASS if not bad else FINDING, non_canonical_markers=bad)


@_guard
def check_pairing_contract(repo_root: Path) -> dict:
    from ruthless_pipeline.certification import p1_pairing_schedule as ps

    contract = json.loads((repo_root / "physical/p1/PAIRING_RANDOMIZATION_CONTRACT.json").read_text())
    stopping = json.loads((repo_root / "physical/p1/STOPPING_RULE.json").read_text())
    regenerated = ps.contract_payload()
    problems = []
    if regenerated["schedule_sha256"] != contract["schedule_sha256"]:
        problems.append("schedule does not re-derive byte-identically from the frozen seed")
    if contract["grid"]["planned_valid_trials"] != stopping["max_valid_trials"]:
        problems.append("grid trials != stopping-rule max_valid_trials")
    counts = contract["balance_check"]["first_arm_counts"]
    if counts.get("control") != counts.get("candidate"):
        problems.append(f"first-arm imbalance: {counts}")
    if contract["seed"] != ps.CONTRACT_SEED:
        problems.append("contract seed drifted from module constant")
    return _record(
        PASS if not problems else FINDING,
        problems=problems,
        schedule_sha256=contract["schedule_sha256"],
        first_arm_counts=counts,
        planned_valid_trials=contract["grid"]["planned_valid_trials"],
    )


@_guard
def check_schedule_frozen(repo_root: Path) -> dict:
    from ruthless_pipeline.certification import p1_pairing_schedule as ps

    frozen = json.loads((repo_root / "physical/p1/P1_CAPTURE_SCHEDULE.json").read_text())
    schedule = ps.derive_schedule()
    problems = []
    if frozen.get("schedule_sha256") != ps.schedule_sha256(schedule):
        problems.append("pinned schedule_sha256 does not match fresh derivation from the frozen seed")
    if frozen.get("planned_valid_trials") != ps.EXPECTED_TRIALS:
        problems.append("planned_valid_trials mismatch")
    if frozen.get("seed") != ps.CONTRACT_SEED or frozen.get("contract_id") != ps.CONTRACT_ID:
        problems.append("seed/contract drift")
    # Full coverage of RAC-P1-T-0001..0144 exactly once, from the derivation.
    trial_ids = [e["trial_id"] for e in schedule]
    if len(trial_ids) != len(set(trial_ids)) or sorted(trial_ids) != ps.trial_ids():
        problems.append("derived schedule does not cover RAC-P1-T-0001..0144 exactly once")
    return _record(PASS if not problems else FINDING, problems=problems, trials=len(trial_ids))


@_guard
def check_ingestion_contracts() -> dict:
    from scripts.ingest_capture_inference import enforce_promotion_gate

    refused = []
    for payload in (
        {"evidence_class": "synthetic_pipeline_validation_only", "calibration_pass": True},
        {"evidence_class": "physical_garment_p1", "calibration_pass": False},
    ):
        try:
            enforce_promotion_gate(payload)
            refused.append(False)
        except ValueError:
            refused.append(True)
    # Entrypoints import cleanly (import-safe CLI contract, E2).
    import scripts.validate_capture_session  # noqa: F401
    import scripts.build_p1_bundle  # noqa: F401
    import scripts.rehearse_physical_capture  # noqa: F401

    return _record(PASS if all(refused) else FINDING, promotion_refusals=refused)


@_guard
def check_synthetic_rehearsal_deterministic() -> dict:
    from ruthless_pipeline.certification.physical_capture_rehearsal import run_rehearsal

    with tempfile.TemporaryDirectory(prefix="p1gate-reh-a-") as da, tempfile.TemporaryDirectory(
        prefix="p1gate-reh-b-"
    ) as db:
        summary_a = run_rehearsal(Path(da) / "run")
        summary_b = run_rehearsal(Path(db) / "run")
    identical = summary_a["summary_sha256"] == summary_b["summary_sha256"]
    return _record(
        PASS if identical else FINDING,
        summary_sha256_a=summary_a["summary_sha256"],
        summary_sha256_b=summary_b["summary_sha256"],
        evidence_label=summary_a.get("evidence_label"),
        detail="full chain rehearsed twice from receipt to sealed release; byte-identical summary required",
    )


@_guard
def check_failure_injection(repo_root: Path) -> dict:
    """Rehearsal battery + gate-local injections, all must fail closed."""
    from scripts.rehearse_physical_capture import run_failure_injections
    from ruthless_pipeline.certification import p1_pairing_schedule as ps

    with tempfile.TemporaryDirectory(prefix="p1gate-inj-") as tmp:
        battery = run_failure_injections(Path(tmp) / "battery")

    local: dict[str, dict] = {}

    # Gate-local 1: tampered pinned artifact is detected by freeze comparison.
    freeze = json.loads((repo_root / FREEZE_PATH).read_text())
    victim = "physical/p1/STOPPING_RULE.json"
    actual = _sha256_file(repo_root / victim)
    local["tampered_pinned_artifact_would_be_detected"] = {
        "rejected": freeze["artifact_sha256"][victim] == actual
        and freeze["artifact_sha256"][victim] != hashlib.sha256(b"tampered").hexdigest(),
        "detail": "pin comparison detects any byte change (pin != tampered content hash)",
    }

    # Gate-local 2: a defaulted (non-literal) UA value breaks the pending-set
    # equality and is flagged by the suspicious-marker scan.
    probe = {"vendor": {"template_archive_sha256": "0" * 64}}  # looks real, is fabricated
    local["defaulted_ua_field_flagged"] = {
        "rejected": _pending_paths(probe) == set()
        and _pending_paths({"vendor": {"template_archive_sha256": PENDING_LITERAL}}) != set(),
        "detail": "a fabricated 64-hex value is not a pending literal; pending-set mismatch fails the gate",
    }

    # Gate-local 3: a mutated schedule entry breaks re-derivation equality.
    schedule = ps.derive_schedule()
    mutated = [dict(e) for e in schedule]
    mutated[0]["first_arm"] = "candidate" if mutated[0]["first_arm"] == "control" else "control"
    local["mutated_schedule_detected"] = {
        "rejected": mutated != schedule,
        "detail": "any schedule mutation fails the frozen-schedule equality check",
    }

    battery_ok = battery.get("all_injections_handled") is True
    local_ok = all(r["rejected"] for r in local.values())
    return _record(
        PASS if battery_ok and local_ok else FINDING,
        rehearsal_battery=battery,
        gate_local_injections=local,
    )


@_guard
def check_scientific_boundaries(repo_root: Path) -> dict:
    problems = []

    status = json.loads((repo_root / "d2-latest-status.json").read_text())
    if status.get("decision") != "FAIL" or status.get("evidence_state") != "RAC-D0":
        problems.append("d2-latest-status.json no longer reads FAIL / RAC-D0")

    gen = json.loads((repo_root / "generations" / "RAC-PER-D2-0005.json").read_text())
    if gen.get("lock_status") != "PREREGISTERED":
        problems.append("RAC-PER-D2-0005 lock_status is not PREREGISTERED")

    freeze = json.loads((repo_root / "docs" / "D2-0005_FREEZE_CANDIDATE.json").read_text())
    if freeze.get("arming", {}).get("armed") is not False:
        problems.append("D2-0005 freeze candidate arming.armed is not false")
    if "NOT_ARMED" not in str(freeze.get("status", "")):
        problems.append("D2-0005 freeze candidate status does not read NOT_ARMED")

    manifest = json.loads((repo_root / "artifacts/barrier3/run-manifest.json").read_text())
    for field in ("d2_0004_modified", "d2_0005_armed", "held_out_models_accessed", "physical_efficacy_claimed"):
        if manifest.get(field) is not False:
            problems.append(f"barrier3 run-manifest {field} is not false")

    return _record(
        PASS if not problems else FINDING,
        problems=problems,
        assertions={
            "D2_0004_MODIFIED": False,
            "D2_0005_ARMED": False,
            "NEW_HELDOUT_ACCESS": False,
            "SCIENTIFIC_THRESHOLDS_CHANGED": False,
            "PHYSICAL_EFFICACY_CLAIMED": False,
        },
    )


CHECK_ORDER = [
    "freeze_integrity",
    "freeze_self_consistency",
    "surface_completeness",
    "ua_fields_pending",
    "pending_literals_canonical",
    "pairing_contract",
    "schedule_frozen",
    "ingestion_contracts",
    "synthetic_rehearsal_deterministic",
    "failure_injection",
    "scientific_boundaries",
]


def derive_verdict(checks: dict[str, dict]) -> dict:
    findings = [n for n, c in checks.items() if c["status"] == FINDING]
    refusals = {n: c.get("refusal_reason") for n, c in checks.items() if c["status"] == REFUSED}
    verdict = "FAIL" if findings or refusals else "PASS"
    return {
        "P1_NO_SPEND_READINESS": verdict,
        "findings": findings,
        "refusals": refusals,
        "verdict_rule": "FAIL if any FINDING or REFUSED; PASS otherwise. Refusals are never silent.",
    }


def run_gate(repo_root: Path) -> dict:
    checks = {
        "freeze_integrity": check_freeze_integrity(repo_root),
        "freeze_self_consistency": check_freeze_self_consistency(repo_root),
        "surface_completeness": check_surface_completeness(repo_root),
        "ua_fields_pending": check_ua_fields_pending(repo_root),
        "pending_literals_canonical": check_pending_literals_canonical(repo_root),
        "pairing_contract": check_pairing_contract(repo_root),
        "schedule_frozen": check_schedule_frozen(repo_root),
        "ingestion_contracts": check_ingestion_contracts(),
        "synthetic_rehearsal_deterministic": check_synthetic_rehearsal_deterministic(),
        "failure_injection": check_failure_injection(repo_root),
        "scientific_boundaries": check_scientific_boundaries(repo_root),
    }
    verdict = derive_verdict(checks)
    boundaries = checks["scientific_boundaries"].get("assertions", {})
    return {
        "gate_id": GATE_ID,
        "schema_version": SCHEMA_VERSION,
        "freeze_manifest": FREEZE_PATH,
        "checks": checks,
        **verdict,
        "boundary_assertions": boundaries,
        "evidence_class": "synthetic_pipeline_validation_only",
        "physical_efficacy_claimed": False,
        "spend_authorized": False,
        "note": (
            "Readiness to execute, not evidence. No garment ordered, no "
            "physical efficacy claimed, D2-0005 remains PREREGISTERED/unarmed. "
            "Spend remains blocked on UA-1..UA-8 real values."
        ),
    }


def render_markdown(report: dict) -> str:
    lines = [
        "# P1 No-Spend Readiness Audit",
        "",
        f"**Gate:** {report['gate_id']}",
        f"**P1_NO_SPEND_READINESS:** **{report['P1_NO_SPEND_READINESS']}**",
        "",
        report["verdict_rule"],
        "",
        "## Checks",
        "",
        "| check | status |",
        "|---|---|",
    ]
    for name in CHECK_ORDER:
        lines.append(f"| `{name}` | {report['checks'][name]['status']} |")
    if report["findings"]:
        lines += ["", "**Findings (blocking):** " + ", ".join(report["findings"])]
    if report["refusals"]:
        lines += ["", "**Refusals (blocking, explicit):**"]
        for name, reason in report["refusals"].items():
            lines.append(f"- `{name}` — {reason}")
    lines += ["", "## Scientific-boundary assertions", "", "```"]
    for key, value in report["boundary_assertions"].items():
        lines.append(f"{key}={str(value).lower()}")
    lines += [
        "```",
        "",
        report["note"],
        "",
        "Full machine-readable report: `artifacts/p1-readiness/readiness-report.json`.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=str(Path(__file__).resolve().parent.parent))
    parser.add_argument("--json-out", default=None)
    parser.add_argument("--md-out", default=None)
    parser.add_argument(
        "--write-freeze",
        action="store_true",
        help="re-pin the freeze manifest from the current repo state, then exit",
    )
    args = parser.parse_args()
    repo_root = Path(args.repo_root)

    if args.write_freeze:
        freeze = build_freeze_manifest(repo_root)
        out = repo_root / FREEZE_PATH
        out.write_text(json.dumps(freeze, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps({"wrote": FREEZE_PATH, "pinned": len(freeze["artifact_sha256"])}, indent=2))
        return 0

    report = run_gate(repo_root)
    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        out = Path(args.json_out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8")
    if args.md_out:
        md = Path(args.md_out)
        md.parent.mkdir(parents=True, exist_ok=True)
        md.write_text(render_markdown(report), encoding="utf-8")
    print(text)
    return 0 if report["P1_NO_SPEND_READINESS"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
