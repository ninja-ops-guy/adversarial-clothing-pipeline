"""Deterministic stale-artifact detector (drift watch) for the research pipeline.

This module is DETECT-ONLY: it recomputes derived artifacts (or recomputes
the hashes pinned inside them) and reports which surfaces must be
regenerated. It never writes, regenerates, or repairs anything itself.

Surfaces checked:

* ``artifacts/provenance/graph.json`` — the graph is re-derived with
  :func:`provenance_graph.build_graph` and compared byte-for-byte
  (the build is deterministic); additionally every hash edge is re-verified.
* ``schemas/*`` — every schema file parses as JSON, carries a stable
  identifier, and identifiers are unique across the registry.
* ``artifacts/rac_deliverable_inventory.json`` — envelope well-formedness,
  known class vocabulary, safety flags (no physical-efficacy claim, D2-0005
  unarmed), and existence of every referenced evidence path.
* ``manuscript/figures/*.json`` and ``manuscript/exports/*`` — every
  embedded ``source_artifacts`` / ``sha256`` source pin is recomputed
  against the current tree.
* ``artifacts/dashboard/experiments.json`` — re-exported deterministically
  and compared byte-for-byte.
* ``artifacts/design_analysis_d20005_cluster/results.json`` — pinned by
  SHA-256 (frozen pre-arming simulation output; never regenerated here).
* documentation indexes — the existing :mod:`doc_lint` repository lint is
  reused; any finding is reported as staleness of the documentation surface.

The report is machine-readable and deterministic (no timestamps, no
ambient git state).
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable

from .doc_lint import lint_repo
from .provenance_graph import build_graph, verify_graph

STATUS_FRESH = "FRESH"
STATUS_STALE = "STALE"
STATUS_MISSING = "MISSING"

PROVENANCE_GRAPH_PATH = "artifacts/provenance/graph.json"
DASHBOARD_PATH = "artifacts/dashboard/experiments.json"
INVENTORY_PATH = "artifacts/rac_deliverable_inventory.json"
CLUSTER_RESULTS_PATH = "artifacts/design_analysis_d20005_cluster/results.json"
SCHEMAS_DIR = "schemas"
MANUSCRIPT_FIGURES_DIR = "manuscript/figures"
MANUSCRIPT_EXPORTS_DIR = "manuscript/exports"

#: SHA-256 pin of the frozen D2-0005 cluster-aware pre-arming simulation
#: output. The grid is expensive and is frozen scientific evidence; drift is
#: detected by hash comparison only and regeneration is NEVER performed by
#: this tool (and only ever re-authorized by a pre-arming review).
CLUSTER_RESULTS_SHA256 = (
    "5e8c78b1af395a67258960ac4d4f35e3e7cf20bfef381fd39f8d70c43a67d7d1"
)

INVENTORY_KNOWN_CLASSES = {
    "COMPLETE",
    "PARTIAL",
    "MISSING",
    "BLOCKED",
    "USER_ACTION_REQUIRED",
    "OWNED_BY_OTHER_SWARM",
}

_SCHEMA_ID_KEYS = ("$id", "schema_id", "id", "title", "contract_id")


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _canonical_bytes(payload: Any) -> bytes:
    # Matches provenance_graph._canonical_bytes / export_dashboard_data
    # ._canonical_bytes exactly (indent=2, sort_keys, no ASCII escaping,
    # trailing newline) so byte comparison reflects the committed format.
    return (
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    ).encode("utf-8")


@dataclass
class SurfaceReport:
    """Result of checking one derived-artifact surface."""

    surface: str
    status: str
    findings: list[str] = field(default_factory=list)
    regenerate: list[str] = field(default_factory=list)

    @property
    def stale(self) -> bool:
        return self.status != STATUS_FRESH


@dataclass
class DriftReport:
    """Machine-readable aggregate report."""

    schema_version: str
    generator: str
    stale: bool
    surfaces: list[SurfaceReport]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "generator": self.generator,
            "stale": self.stale,
            "surfaces": [asdict(s) for s in self.surfaces],
        }


# --- provenance graph --------------------------------------------------------


def check_provenance_graph(root: Path) -> SurfaceReport:
    report = SurfaceReport(surface=PROVENANCE_GRAPH_PATH, status=STATUS_FRESH)
    graph_path = root / PROVENANCE_GRAPH_PATH
    if not graph_path.is_file():
        report.status = STATUS_MISSING
        report.findings.append("provenance graph artifact is absent")
        report.regenerate.append(
            "PYTHONPATH=. python scripts/build_provenance_graph.py"
        )
        return report
    try:
        rebuilt = build_graph(root)
    except Exception as exc:  # a surface that cannot be re-derived is stale
        report.status = STATUS_STALE
        report.findings.append(f"provenance graph rebuild failed: {exc!r}")
        report.regenerate.append(
            "PYTHONPATH=. python scripts/build_provenance_graph.py"
        )
        return report
    if _canonical_bytes(rebuilt) != graph_path.read_bytes():
        report.status = STATUS_STALE
        report.findings.append(
            "re-derived provenance graph differs from committed artifact"
        )
        report.regenerate.append(
            "PYTHONPATH=. python scripts/build_provenance_graph.py"
        )
        return report
    verification = verify_graph(rebuilt, root)
    failures = [
        f"edge {edge_id}: unexpected verification failure"
        for edge_id in verification.get("unexpected", [])
    ]
    if failures:
        report.status = STATUS_STALE
        report.findings.extend(failures)
        report.regenerate.append(
            "repair the broken hash edges, then "
            "PYTHONPATH=. python scripts/build_provenance_graph.py"
        )
    return report


# --- schemas registry ---------------------------------------------------------


def check_schemas_registry(root: Path) -> SurfaceReport:
    report = SurfaceReport(surface=SCHEMAS_DIR, status=STATUS_FRESH)
    schemas_dir = root / SCHEMAS_DIR
    if not schemas_dir.is_dir():
        report.status = STATUS_MISSING
        report.findings.append("schemas/ directory is absent")
        return report
    seen: dict[str, str] = {}
    for path in sorted(schemas_dir.glob("*.json")):
        rel = path.relative_to(root).as_posix()
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            report.status = STATUS_STALE
            report.findings.append(f"{rel}: invalid JSON ({exc})")
            continue
        if not isinstance(payload, dict):
            report.status = STATUS_STALE
            report.findings.append(f"{rel}: schema document is not an object")
            continue
        identifier = next(
            (str(payload[k]) for k in _SCHEMA_ID_KEYS if payload.get(k)), None
        )
        if identifier is None:
            report.status = STATUS_STALE
            report.findings.append(
                f"{rel}: no stable identifier ({'/'.join(_SCHEMA_ID_KEYS)})"
            )
            continue
        if identifier in seen:
            report.status = STATUS_STALE
            report.findings.append(
                f"{rel}: duplicate schema identifier {identifier!r} "
                f"(also in {seen[identifier]})"
            )
        else:
            seen[identifier] = rel
    if report.stale:
        report.regenerate.append(
            "repair schemas/* so every schema parses and identifiers are unique"
        )
    return report


# --- RAC deliverable inventory ------------------------------------------------


def check_inventory(root: Path) -> SurfaceReport:
    report = SurfaceReport(surface=INVENTORY_PATH, status=STATUS_FRESH)
    inv_path = root / INVENTORY_PATH
    if not inv_path.is_file():
        report.status = STATUS_MISSING
        report.findings.append("RAC deliverable inventory is absent")
        return report
    try:
        inv = json.loads(inv_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        report.status = STATUS_STALE
        report.findings.append(f"invalid JSON ({exc})")
        return report
    if not inv.get("inventory_id") or not isinstance(inv.get("requirements"), list):
        report.status = STATUS_STALE
        report.findings.append("envelope missing inventory_id or requirements")
        return report
    if set(inv.get("classes", [])) != INVENTORY_KNOWN_CLASSES:
        report.status = STATUS_STALE
        report.findings.append("class vocabulary drifted from the known set")
    if inv.get("physical_efficacy_claimed") is not False:
        report.status = STATUS_STALE
        report.findings.append("physical_efficacy_claimed flag drifted")
    d20005 = inv.get("scientific_state", {}).get("D2-0005", {})
    if d20005.get("armed") is not False or d20005.get("ready_to_arm") is not False:
        report.status = STATUS_STALE
        report.findings.append("D2-0005 arming flags drifted (must stay false)")
    for req in inv.get("requirements", []):
        if req.get("class") not in INVENTORY_KNOWN_CLASSES:
            report.status = STATUS_STALE
            report.findings.append(
                f"{req.get('id')}: unknown class {req.get('class')!r}"
            )
        for evidence in req.get("evidence", []) or []:
            # Evidence entries may carry "path: field" suffixes or
            # parenthetical notes; only bare repo paths are checked.
            match = _EVIDENCE_PATH_RE.match(evidence)
            candidate = match.group(0) if match else ""
            if "/" in candidate and candidate.split("/")[0] in _REPO_TOP_LEVEL:
                if not (root / candidate).exists():
                    report.status = STATUS_STALE
                    report.findings.append(
                        f"{req.get('id')}: evidence path missing: {candidate}"
                    )
    if report.stale:
        report.regenerate.append(
            "regenerate artifacts/rac_deliverable_inventory.json from the "
            "current tree (derived data artifact)"
        )
    return report


# Leading repo-relative path token in an inventory evidence string; stops at
# the first whitespace or ":" so notes like "path.py Symbol" or
# "path: field" do not pollute the existence check.
_EVIDENCE_PATH_RE = re.compile(r"^[\w\-./]+")

_REPO_TOP_LEVEL = {
    "docs",
    "scripts",
    "ruthless_pipeline",
    "tests",
    "schemas",
    "generations",
    "manuscript",
    "benchmarks",
    "releases",
    "protocols",
    "model_sets",
    "model_manifests",
    "registry",
    "artifacts",
    "production_alpha",
    "design_profiles",
    "templates",
    "physical",
    "examples",
    "patterns",
}


# --- manuscript figures + exports --------------------------------------------


def _iter_source_pins(payload: Any) -> Iterable[tuple[str, str]]:
    """Yield (path, sha256) pairs embedded in a manuscript artifact."""
    if isinstance(payload, dict):
        source_artifacts = payload.get("source_artifacts")
        if isinstance(source_artifacts, dict):
            for path, digest in source_artifacts.items():
                if isinstance(digest, str):
                    yield path, digest
        if isinstance(payload.get("path"), str) and isinstance(
            payload.get("sha256"), str
        ):
            yield payload["path"], payload["sha256"]
        for value in payload.values():
            yield from _iter_source_pins(value)
    elif isinstance(payload, list):
        for item in payload:
            yield from _iter_source_pins(item)


def _check_manuscript_dir(root: Path, rel_dir: str) -> SurfaceReport:
    report = SurfaceReport(surface=rel_dir, status=STATUS_FRESH)
    directory = root / rel_dir
    if not directory.is_dir():
        report.status = STATUS_MISSING
        report.findings.append(f"{rel_dir}/ is absent")
        return report
    for path in sorted(directory.glob("*.json")) + sorted(directory.glob("*.csv")):
        rel = path.relative_to(root).as_posix()
        if path.suffix != ".json":
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            report.status = STATUS_STALE
            report.findings.append(f"{rel}: invalid JSON ({exc})")
            continue
        for source_path, expected in sorted(set(_iter_source_pins(payload))):
            target = root / source_path
            if not target.is_file():
                report.status = STATUS_STALE
                report.findings.append(
                    f"{rel}: pinned source {source_path} is missing"
                )
                continue
            actual = _sha256_file(target)
            if actual != expected:
                report.status = STATUS_STALE
                report.findings.append(
                    f"{rel}: source hash drift for {source_path} "
                    f"(pinned {expected[:12]}..., actual {actual[:12]}...)"
                )
    if report.stale:
        report.regenerate.append(
            "re-derive the affected manuscript figure/export scaffolds from "
            "their source artifacts (never invent values)"
        )
    return report


# --- dashboard ----------------------------------------------------------------


def check_dashboard(root: Path) -> SurfaceReport:
    from scripts.export_dashboard_data import build_dashboard

    report = SurfaceReport(surface=DASHBOARD_PATH, status=STATUS_FRESH)
    dash_path = root / DASHBOARD_PATH
    if not dash_path.is_file():
        report.status = STATUS_MISSING
        report.findings.append("dashboard export is absent")
        report.regenerate.append(
            "PYTHONPATH=. python scripts/export_dashboard_data.py"
        )
        return report
    try:
        rebuilt = build_dashboard(root)
    except Exception as exc:  # a surface that cannot be re-derived is stale
        report.status = STATUS_STALE
        report.findings.append(f"dashboard rebuild failed: {exc!r}")
        report.regenerate.append(
            "PYTHONPATH=. python scripts/export_dashboard_data.py"
        )
        return report
    if _canonical_bytes(rebuilt) != dash_path.read_bytes():
        report.status = STATUS_STALE
        report.findings.append(
            "re-exported dashboard payload differs from committed artifact"
        )
        report.regenerate.append(
            "PYTHONPATH=. python scripts/export_dashboard_data.py"
        )
    return report


# --- cluster results hash pin --------------------------------------------------


def check_cluster_results_pin(
    root: Path, expected_sha256: str = CLUSTER_RESULTS_SHA256
) -> SurfaceReport:
    report = SurfaceReport(surface=CLUSTER_RESULTS_PATH, status=STATUS_FRESH)
    path = root / CLUSTER_RESULTS_PATH
    if not path.is_file():
        report.status = STATUS_MISSING
        report.findings.append("cluster design-analysis results are absent")
        return report
    actual = _sha256_file(path)
    if actual != expected_sha256:
        report.status = STATUS_STALE
        report.findings.append(
            f"hash pin mismatch (pinned {expected_sha256[:12]}..., "
            f"actual {actual[:12]}...); the frozen simulation output "
            "changed — regeneration requires a pre-arming review, never "
            "an automatic rerun"
        )
    return report


# --- documentation indexes (doc_lint reuse) -------------------------------------


def check_documentation(root: Path) -> SurfaceReport:
    report = SurfaceReport(surface="docs/** + manuscript/backlog/**", status=STATUS_FRESH)
    result = lint_repo(root)
    findings = getattr(result, "findings", None) or []
    for finding in findings:
        report.findings.append(
            f"{getattr(finding, 'path', '?')}: "
            f"{getattr(finding, 'check', '?')}: "
            f"{getattr(finding, 'line', '')}".rstrip(": ")
        )
    if report.findings:
        report.status = STATUS_STALE
        report.regenerate.append(
            "fix documentation drift reported by doc_lint "
            "(PYTHONPATH=. python scripts/lint_docs.py)"
        )
    return report


# --- aggregate ------------------------------------------------------------------


ALL_CHECKS = (
    check_provenance_graph,
    check_schemas_registry,
    check_inventory,
    lambda root: _check_manuscript_dir(root, MANUSCRIPT_FIGURES_DIR),
    lambda root: _check_manuscript_dir(root, MANUSCRIPT_EXPORTS_DIR),
    check_dashboard,
    check_cluster_results_pin,
    check_documentation,
)


def check_repo(root: str | Path) -> DriftReport:
    """Run every surface check and aggregate the machine-readable report."""
    root = Path(root)
    surfaces = [check(root) for check in ALL_CHECKS]
    return DriftReport(
        schema_version="1.0",
        generator="scripts/check_stale_artifacts.py",
        stale=any(surface.stale for surface in surfaces),
        surfaces=surfaces,
    )
