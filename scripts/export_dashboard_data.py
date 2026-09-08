"""Export Research OS dashboard data (data-only; no UI).

Emits ``artifacts/dashboard/experiments.json`` (schema
``research-os-dashboard`` version ``1.0``): one record per
experiment/generation (RAC-PER-D2-0003, RAC-PER-D2-0004, RAC-PER-D2-0005,
RAC-PER-D2-0006, Production Alpha/P1) with state, evidence class, decision,
source commit, key hashes, runtime-lock reference, publication/physical
state, blockers, and user actions required (harvested from
``docs/PRODUCTION_COMPLETION_CHECKLIST.md``, ``docs/PRODUCTION_ALPHA_SKU.md``
open items, and ``docs/D2-0005_ARMING_PACKET.md``).

Promotion guard: measured fields (decisions, detection rates, held-out
statistics) are populated ONLY from attested evidence classes
(``archived_in_repo``, ``log_attested``). Synthetic, draft, preregistered,
or planned records can never carry measured values — attempting to do so
raises :class:`PromotionGuardError`.

The export is deterministic: no timestamps, no ambient git state; two runs
over the same tree produce byte-identical output.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
import sys
from pathlib import Path
from typing import Any, Callable

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from ruthless_pipeline.certification.schema_version import (  # noqa: E402
    require_schema_version,
)

DASHBOARD_SCHEMA_ID = "research-os-dashboard"
DASHBOARD_SCHEMA_VERSION = "1.0"

DEFAULT_OUT = REPO_ROOT / "artifacts" / "dashboard" / "experiments.json"

RUNTIME_LOCK_PATH = "benchmarks/runtime_lock.json"

#: Evidence classes from which measured fields may be populated. Anything
#: else (synthetic, draft, preregistered, planned) is a promotion violation.
MEASURED_EVIDENCE_CLASSES = frozenset({"archived_in_repo", "log_attested"})

#: Fields copied verbatim from d2-latest-status.json into the D2-0004
#: measured block (no transcription: parsed, never retyped).
D2_STATUS_MEASURED_FIELDS = (
    "bundle_verified",
    "candidate_id",
    "certificate_id",
    "decision",
    "evidence_state",
    "heldout",
    "heldout_model_set",
    "invalid_condition_fraction",
    "protocol_id",
    "protocol_version",
    "source_commit",
    "surrogate_model_set",
    "verification_failures",
)

#: User-action items that require a human, harvested from
#: docs/D2-0005_ARMING_PACKET.md §8 (READY_TO_ARM: NO).
ARMING_PACKET_PATH = "docs/D2-0005_ARMING_PACKET.md"
CHECKLIST_PATH = "docs/PRODUCTION_COMPLETION_CHECKLIST.md"
SKU_DOC_PATH = "docs/PRODUCTION_ALPHA_SKU.md"


class PromotionGuardError(ValueError):
    """Raised when code attempts to populate measured fields from a
    non-measured evidence class (synthetic/draft/preregistered/planned)."""


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def measured_fields_for(
    evidence_class: str, loader: Callable[[], dict[str, Any]]
) -> dict[str, Any]:
    """Return measured fields for a record, or raise.

    ``loader`` is invoked ONLY when ``evidence_class`` is an attested
    measured class; otherwise PromotionGuardError is raised and the loader
    is never called. This is the single choke point that keeps synthetic or
    planned data out of measured fields.
    """
    if evidence_class not in MEASURED_EVIDENCE_CLASSES:
        raise PromotionGuardError(
            f"evidence_class {evidence_class!r} cannot populate measured "
            f"fields; allowed: {sorted(MEASURED_EVIDENCE_CLASSES)}"
        )
    return loader()


def _measured_or_none(
    evidence_class: str, loader: Callable[[], dict[str, Any]]
) -> dict[str, Any] | None:
    """Populate measured fields when permitted; None otherwise."""
    if evidence_class not in MEASURED_EVIDENCE_CLASSES:
        return None
    return measured_fields_for(evidence_class, loader)


def _harvest_arming_packet_actions(text: str) -> list[str]:
    """Harvest the ordered action items from the arming packet §8."""
    section = re.search(
        r"## 8\..*?(?=\n## 9\.)", text, flags=re.DOTALL
    )
    if section is None:
        return []
    actions = []
    for match in re.finditer(
        r"^\d+\.\s+\*\*(.+?)\*\*", section.group(0), flags=re.MULTILINE
    ):
        actions.append(re.sub(r"\s+", " ", match.group(1)).strip())
    tail = re.search(r"Remaining-action list \(ordered\): (.+)", section.group(0))
    if tail is not None:
        actions.append(
            "Ordered remaining actions: "
            + re.sub(r"\s+", " ", tail.group(1)).strip()
        )
    return actions


def _harvest_sku_open_items(text: str) -> list[str]:
    """Harvest §7 Open Items (external) from PRODUCTION_ALPHA_SKU.md."""
    section = re.search(r"## 7\..*?(?=\n## 8\.)", text, flags=re.DOTALL)
    if section is None:
        return []
    items = []
    for match in re.finditer(
        r"^\d+\.\s+(.+)$", section.group(0), flags=re.MULTILINE
    ):
        items.append(re.sub(r"\s+", " ", match.group(1)).strip())
    return items


def _harvest_checklist_next_action(text: str) -> str | None:
    match = re.search(
        r"## Next single action\s+(.+?)(?:\n\n|\Z)", text, flags=re.DOTALL
    )
    if match is None:
        return None
    return re.sub(r"\s+", " ", match.group(1)).strip().rstrip("* ").strip()


def _runtime_lock_ref(root: Path) -> dict[str, str]:
    lock = root / RUNTIME_LOCK_PATH
    ref = {"path": RUNTIME_LOCK_PATH}
    if lock.is_file():
        ref["sha256"] = _sha256_file(lock)
    return ref


def build_dashboard(repo_root: str | Path = REPO_ROOT) -> dict[str, Any]:
    """Build the dashboard export deterministically from the repository."""
    root = Path(repo_root)
    runtime_lock = _runtime_lock_ref(root)
    records: list[dict[str, Any]] = []

    # --- RAC-PER-D2-0003 (closed; archived in-repo evidence) ---------------
    d3_status_rel = "manuscript/evidence/RAC-PER-D2-0003/d2-latest-status.json"
    d3_status = json.loads((root / d3_status_rel).read_text())
    bench_rel = "benchmark-results.json"
    # Candidate SHA as recorded in the longitudinal export (bytes are not
    # archived in-repo; harvested, never retyped).
    d3_candidate_sha = None
    for row in csv.DictReader(
        io.StringIO(
            (root / "manuscript/exports/paper1_longitudinal.csv").read_text()
        )
    ):
        if row.get("generation_id") == "RAC-PER-D2-0003":
            d3_candidate_sha = row.get("candidate_sha256") or None

    def _load_d3_measured() -> dict[str, Any]:
        return {k: d3_status[k] for k in D2_STATUS_MEASURED_FIELDS if k in d3_status}

    records.append(
        {
            "experiment_id": "RAC-PER-D2-0003",
            "kind": "generation",
            "state": "closed",
            "armed": False,
            "evidence_class": "archived_in_repo",
            "decision": d3_status.get("decision"),
            "source_commit": d3_status.get("source_commit"),
            "key_hashes": {
                "status_file_sha256": _sha256_file(root / d3_status_rel),
                "benchmark_results_sha256": _sha256_file(root / bench_rel),
                "candidate_sha256": d3_candidate_sha,
            },
            "runtime_lock": runtime_lock,
            "publication_state": "exported_in_manuscript/paper1_longitudinal.csv",
            "physical_state": "not_applicable_digital_only",
            "blockers": [],
            "user_actions_required": [],
            "measured": _measured_or_none("archived_in_repo", _load_d3_measured),
        }
    )

    # --- RAC-PER-D2-0004 (closed; log-attested) -----------------------------
    d4_status_rel = "d2-latest-status.json"
    d4_status = json.loads((root / d4_status_rel).read_text())
    d4_log_rel = "manuscript/evidence/RAC-PER-D2-0004/log-attested-evidence.json"
    d4_log = json.loads((root / d4_log_rel).read_text())

    def _load_d4_measured() -> dict[str, Any]:
        return {k: d4_status[k] for k in D2_STATUS_MEASURED_FIELDS if k in d4_status}

    records.append(
        {
            "experiment_id": "RAC-PER-D2-0004",
            "kind": "generation",
            "state": "closed",
            "armed": False,
            "evidence_class": "log_attested",
            "decision": d4_status.get("decision"),
            "source_commit": d4_status.get("source_commit"),
            "key_hashes": {
                "status_file_sha256": _sha256_file(root / d4_status_rel),
                "log_attested_evidence_sha256": _sha256_file(root / d4_log_rel),
                "candidate_sha256": d4_log["step18_measured_benchmark_stdout"][
                    "candidate_sha256"
                ],
            },
            "runtime_lock": runtime_lock,
            "publication_state": "exported_in_manuscript/paper1_longitudinal.csv",
            "physical_state": "not_applicable_digital_only",
            "blockers": [],
            "user_actions_required": [],
            "measured": _measured_or_none("log_attested", _load_d4_measured),
        }
    )

    # --- RAC-PER-D2-0005 (PREREGISTERED; not armed) --------------------------
    d5_gen_rel = "generations/RAC-PER-D2-0005.json"
    d5_gen = json.loads((root / d5_gen_rel).read_text())
    d5_freeze_rel = "docs/D2-0005_FREEZE_CANDIDATE.json"
    d5_freeze = json.loads((root / d5_freeze_rel).read_text())
    packet_text = (root / ARMING_PACKET_PATH).read_text()
    packet_status = re.search(r"PACKET STATUS: ([A-Z_]+)", packet_text)
    records.append(
        {
            "experiment_id": "RAC-PER-D2-0005",
            "kind": "generation",
            "state": d5_gen["status"],
            "armed": bool(d5_freeze["arming"]["armed"]),
            "evidence_class": "preregistered_not_executed",
            "decision": None,
            "source_commit": d5_gen.get("lock_source_commit"),
            "key_hashes": {
                "generation_file_sha256": _sha256_file(root / d5_gen_rel),
                "freeze_candidate_sha256": _sha256_file(root / d5_freeze_rel),
            },
            "runtime_lock": runtime_lock,
            "publication_state": "unpublished",
            "physical_state": "not_applicable_digital_only",
            "blockers": [
                "arming packet awaiting user decision "
                f"({ARMING_PACKET_PATH}: "
                f"{packet_status.group(1) if packet_status else 'UNKNOWN'})"
            ],
            "user_actions_required": _harvest_arming_packet_actions(packet_text),
            "measured": _measured_or_none(
                "preregistered_not_executed", lambda: {}
            ),
        }
    )

    # --- RAC-PER-D2-0006 (draft interpretation policy only) ------------------
    d6_doc_rel = "docs/PREREGISTRATION_D2-0006_DRAFT.md"
    records.append(
        {
            "experiment_id": "RAC-PER-D2-0006",
            "kind": "generation",
            "state": "draft_policy_only",
            "armed": False,
            "evidence_class": "draft",
            "decision": None,
            "source_commit": None,
            "key_hashes": {
                "draft_policy_sha256": _sha256_file(root / d6_doc_rel),
            },
            "runtime_lock": runtime_lock,
            "publication_state": "unpublished",
            "physical_state": "not_applicable_digital_only",
            "blockers": [
                "directional hypothesis BLOCKED until D2-0005 closes "
                "(docs/PREREGISTRATION_D2-0006_DRAFT.md)"
            ],
            "user_actions_required": [],
            "measured": _measured_or_none("draft", lambda: {}),
        }
    )

    # --- Production Alpha / P1 ----------------------------------------------
    checklist_text = (root / CHECKLIST_PATH).read_text()
    sku_text = (root / SKU_DOC_PATH).read_text()
    sku_manifest_rel = "production_alpha/SKU_MANIFEST.json"
    next_action = _harvest_checklist_next_action(checklist_text)
    user_actions = _harvest_sku_open_items(sku_text)
    if next_action:
        user_actions.insert(0, f"Next single action: {next_action}")
    records.append(
        {
            "experiment_id": "PRODUCTION-ALPHA-P1",
            "kind": "production",
            "state": "open_external_blockers",
            "armed": False,
            "evidence_class": "planned",
            "decision": None,
            "source_commit": None,
            "key_hashes": {
                "sku_manifest_sha256": _sha256_file(root / sku_manifest_rel),
            },
            "runtime_lock": runtime_lock,
            "publication_state": "internal_only",
            "physical_state": "no_physical_sample_received",
            "blockers": [
                "real POD production template not yet acquired "
                "(checklist item 3; single biggest external blocker)",
                "physical control/candidate pair not yet ordered "
                "(checklist item 7)",
            ],
            "user_actions_required": user_actions,
            "measured": _measured_or_none("planned", lambda: {}),
        }
    )

    return {
        "schema_id": DASHBOARD_SCHEMA_ID,
        "schema_version": DASHBOARD_SCHEMA_VERSION,
        "runtime_lock": runtime_lock,
        "records": records,
    }


def _canonical_bytes(payload: dict[str, Any]) -> bytes:
    return (
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    ).encode("utf-8")


def dashboard_sha256(payload: dict[str, Any]) -> str:
    return hashlib.sha256(_canonical_bytes(payload)).hexdigest()


def write_dashboard(payload: dict[str, Any], out_path: str | Path) -> str:
    data = _canonical_bytes(payload)
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    Path(out_path).write_bytes(data)
    return hashlib.sha256(data).hexdigest()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    args = parser.parse_args(argv)
    payload = build_dashboard(args.repo_root)
    require_schema_version(
        payload, DASHBOARD_SCHEMA_VERSION, label="dashboard export"
    )
    digest = write_dashboard(payload, args.out)
    print(
        json.dumps(
            {
                "written": str(args.out),
                "sha256": digest,
                "records": [r["experiment_id"] for r in payload["records"]],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
