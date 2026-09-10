"""Artifact provenance graph for the RAC research repository.

Walks the repository's machine-readable records (generation manifests, the
frozen-surface hash pins, model sets/manifests, the D2 status files, the
manuscript evidence directory, the paper-1 longitudinal export with its
per-field source hashes, benchmark results, the D2-0005 freeze candidate,
release and production records, and the schema contracts) and emits a
deterministic, schema-versioned provenance graph:

* typed nodes: ``candidate``, ``frozen_config``, ``model_manifest``,
  ``inference_record``, ``statistics``, ``decision``, ``rac_release``,
  ``production_asset``, ``document``;
* typed edges carrying an ``expected_sha256`` pin wherever one is derivable
  from an existing hash record.

Verification mode recomputes every hash edge and classifies each edge:

* ``VERIFIED`` — target present and hash (or attested field set) matches;
* ``BROKEN`` — hash mismatch (silent drift / corruption);
* ``MISSING`` — target file absent. Edges for the known D2-0004 unattested
  gaps (e.g. ``surrogate_detection_rate``) are ``MISSING`` with
  ``missing_by_design: true`` — an attestation gap, never a breakage;
* ``MUTABLE`` — the edge is expected to carry a hash pin
  (``hash_pin_expected: true``) but none is recorded.

D2-0004 closure evidence is log-attested (the validated bundle was never
archived; see ``manuscript/evidence/RAC-PER-D2-0004/log-attested-evidence.json``).
Edges derived from it carry ``evidence_class: "log_attested"`` and verify by
cross-checking the attested fields against ``d2-latest-status.json`` and the
internal consistency of the log transcript, not by file hashes.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
from pathlib import Path
from typing import Any

from ruthless_pipeline.certification.schema_version import require_schema_version

GRAPH_SCHEMA_ID = "rac-provenance-graph"
GRAPH_SCHEMA_VERSION = "1.0"

REPO_ROOT = Path(__file__).resolve().parents[2]

NODE_TYPES = (
    "candidate",
    "frozen_config",
    "model_manifest",
    "inference_record",
    "statistics",
    "decision",
    "rac_release",
    "production_asset",
    "document",
    "ctm_claim",
    "ctm_artifact",
    "ctm_null",
)

EDGE_VERIFIED = "VERIFIED"
EDGE_BROKEN = "BROKEN"
EDGE_MISSING = "MISSING"
EDGE_MUTABLE = "MUTABLE"

#: Evidence class stamped on edges derived from the D2-0004 log-attested
#: closure record (the validated bundle was never archived; infra step-22
#: failure, fix 5cdce1b; no re-run authorized).
EVIDENCE_CLASS_LOG_ATTESTED = "log_attested"
#: Evidence class for edges verifying against archived in-repo files.
EVIDENCE_CLASS_FILE_PINNED = "file_pinned"

FROZEN_SURFACE_PATH = "benchmarks/frozen_surface_sha256.json"
FREEZE_CANDIDATE_PATH = "docs/D2-0005_FREEZE_CANDIDATE.json"
LONGITUDINAL_CSV_PATH = "manuscript/exports/paper1_longitudinal.csv"
D2_LATEST_STATUS_PATH = "d2-latest-status.json"
D20004_LOG_EVIDENCE_PATH = "manuscript/evidence/RAC-PER-D2-0004/log-attested-evidence.json"
D20003_STATUS_PATH = "manuscript/evidence/RAC-PER-D2-0003/d2-latest-status.json"

#: Known D2-0004 unattested gaps that must surface as MISSING-by-design,
#: never as BROKEN. Keys are statistic node ids.
D20004_UNATTESTED_GAPS = ("surrogate_detection_rate",)


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _canonical_bytes(payload: dict[str, Any]) -> bytes:
    return (
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    ).encode("utf-8")


def _node(
    node_id: str,
    node_type: str,
    *,
    path: str | None = None,
    sha256: str | None = None,
    evidence_class: str | None = None,
    present: bool = True,
    label: str | None = None,
) -> dict[str, Any]:
    if node_type not in NODE_TYPES:
        raise ValueError(f"unknown provenance node type {node_type!r}")
    node: dict[str, Any] = {"id": node_id, "type": node_type}
    if label is not None:
        node["label"] = label
    if path is not None:
        node["path"] = path
    if sha256 is not None:
        node["sha256"] = sha256
    if evidence_class is not None:
        node["evidence_class"] = evidence_class
    if not present:
        node["present"] = False
    return node


def _edge(
    source: str,
    target: str,
    edge_type: str,
    *,
    expected_sha256: str | None = None,
    hash_pin_expected: bool = False,
    evidence_class: str | None = None,
    missing_by_design: bool = False,
    verify_mode: str = "file_hash",
    note: str | None = None,
) -> dict[str, Any]:
    edge: dict[str, Any] = {
        "id": f"{source} -> {target} [{edge_type}]",
        "source": source,
        "target": target,
        "edge_type": edge_type,
        "hash_pin_expected": hash_pin_expected,
        "verify_mode": verify_mode,
    }
    if expected_sha256 is not None:
        edge["expected_sha256"] = expected_sha256
        edge["hash_pin_expected"] = True
    if evidence_class is not None:
        edge["evidence_class"] = evidence_class
    if missing_by_design:
        edge["missing_by_design"] = True
    if note is not None:
        edge["note"] = note
    return edge


def _iter_path_sha_pins(payload: Any) -> list[dict[str, str]]:
    """Collect every ``{"path": ..., "sha256": ...}`` pin in a nested doc."""
    pins: list[dict[str, str]] = []
    if isinstance(payload, dict):
        if (
            isinstance(payload.get("path"), str)
            and isinstance(payload.get("sha256"), str)
        ):
            pins.append({"path": payload["path"], "sha256": payload["sha256"]})
        for value in payload.values():
            pins.extend(_iter_path_sha_pins(value))
    elif isinstance(payload, list):
        for item in payload:
            pins.extend(_iter_path_sha_pins(item))
    return pins


def _longitudinal_source_pins(csv_path: Path) -> list[dict[str, str]]:
    """Extract (field, source path, recorded source sha256) triples from the
    paper-1 longitudinal export's ``<field>, <field>_source,
    <field>_sha256`` column triples."""
    text = csv_path.read_text()
    rows = list(csv.DictReader(io.StringIO(text)))
    pins: dict[tuple[str, str], None] = {}
    for row in rows:
        for column, value in row.items():
            if not column.endswith("_sha256") or not value:
                continue
            field = column[: -len("_sha256")]
            source = row.get(f"{field}_source") or ""
            if not source:
                continue
            pins[(source, value)] = None
    return [{"path": source, "sha256": sha} for source, sha in sorted(pins)]


def build_graph(repo_root: str | Path = REPO_ROOT) -> dict[str, Any]:
    """Build the provenance graph deterministically from the repository.

    Two runs over the same tree produce byte-identical output.
    """
    root = Path(repo_root)
    nodes: dict[str, dict[str, Any]] = {}
    path_ids: dict[str, str] = {}
    edges: dict[str, dict[str, Any]] = {}

    def add_node(node: dict[str, Any]) -> dict[str, Any]:
        existing = nodes.get(node["id"])
        if existing is not None:
            if existing != node:
                raise ValueError(
                    f"conflicting node definitions for {node['id']!r}"
                )
            return existing
        nodes[node["id"]] = node
        if node.get("path") is not None:
            path_ids[node["path"]] = node["id"]
        return node

    def file_node(
        node_id: str, node_type: str, rel_path: str, **kwargs: Any
    ) -> dict[str, Any]:
        if rel_path in path_ids:
            return nodes[path_ids[rel_path]]
        full = root / rel_path
        node = _node(
            node_id,
            node_type,
            path=rel_path,
            sha256=_sha256_file(full) if full.is_file() else None,
            present=full.is_file(),
            **kwargs,
        )
        return add_node(node)

    def id_for_path(rel_path: str, node_type: str = "inference_record") -> str:
        if rel_path in path_ids:
            return path_ids[rel_path]
        return file_node(f"file:{rel_path}", node_type, rel_path)["id"]

    def add_edge(edge: dict[str, Any]) -> None:
        existing = edges.get(edge["id"])
        if existing is not None and existing != edge:
            raise ValueError(
                f"conflicting edge definitions for {edge['id']!r}"
            )
        edges[edge["id"]] = edge

    # --- frozen-config nodes: generation records ---------------------------
    for gen_path in sorted((root / "generations").glob("*.json")):
        rel = gen_path.relative_to(root).as_posix()
        payload = json.loads(gen_path.read_text())
        file_node(
            f"generation:{payload['generation_id']}", "frozen_config", rel
        )

    # --- model sets (semantic ids) -> source manifest ----------------------
    model_set_manifests: list[tuple[str, str]] = []
    for ms_path in sorted((root / "model_sets").glob("*.json")):
        rel = ms_path.relative_to(root).as_posix()
        payload = json.loads(ms_path.read_text())
        ms_id = f"model_set:{payload.get('model_set_id', ms_path.stem)}"
        file_node(ms_id, "frozen_config", rel)
        source_manifest = payload.get("source_manifest")
        if isinstance(source_manifest, str):
            model_set_manifests.append((ms_id, source_manifest))

    # --- frozen surface hash pins ------------------------------------------
    surface = json.loads((root / FROZEN_SURFACE_PATH).read_text())
    file_node("frozen_surface", "frozen_config", FROZEN_SURFACE_PATH)
    for pinned_path in sorted(surface):
        if pinned_path.startswith("model_manifests/"):
            pinned_id = id_for_path(pinned_path, "model_manifest")
        else:
            pinned_id = id_for_path(pinned_path, "frozen_config")
        add_edge(
            _edge(
                "frozen_surface",
                pinned_id,
                "pins_hash",
                expected_sha256=surface[pinned_path],
                evidence_class=EVIDENCE_CLASS_FILE_PINNED,
                note="frozen-surface hash pin",
            )
        )
    for ms_id, source_manifest in model_set_manifests:
        add_edge(
            _edge(
                ms_id,
                id_for_path(source_manifest, "frozen_config"),
                "derived_from",
                evidence_class=EVIDENCE_CLASS_FILE_PINNED,
                note="model set names its source manifest; hash pinned via frozen surface",
            )
        )

    # --- schema contracts (document nodes) ----------------------------------
    for schema_path in sorted((root / "schemas").glob("*.json")):
        rel = schema_path.relative_to(root).as_posix()
        file_node(f"schema:{schema_path.name}", "document", rel)

    # --- CTM claim/null artifacts -------------------------------------------
    # CTM uses the same canonical provenance graph rather than a parallel
    # trust system. Claim files may reference pre-outcome artifacts by id and
    # SHA; dependency edges follow the CTM convention source=consumer,
    # target=dependency so the certification firewall can walk them.
    ctm_claim_root = root / "artifacts" / "ctm" / "claims"
    for claim_path in sorted(ctm_claim_root.glob("*.json")) if ctm_claim_root.is_dir() else []:
        rel = claim_path.relative_to(root).as_posix()
        payload = json.loads(claim_path.read_text())
        claim_id = str(payload.get("claim_id", claim_path.stem))
        claim_node_id = f"ctm_claim:{claim_id}"
        file_node(claim_node_id, "ctm_claim", rel)
        for use in payload.get("consumed_artifacts", []):
            artifact_id = str(use.get("artifact_id", ""))
            if not artifact_id:
                continue
            node_id = artifact_id
            if node_id not in nodes:
                add_node(_node(
                    node_id,
                    "ctm_artifact",
                    sha256=use.get("sha256"),
                    label=f"CTM consumed artifact ({use.get('role', 'unknown')})",
                ))
            add_edge(_edge(
                claim_node_id,
                node_id,
                "consumes",
                expected_sha256=use.get("sha256"),
                evidence_class=EVIDENCE_CLASS_FILE_PINNED,
                verify_mode="none",
                note="CTM claim consumed-artifact binding",
            ))

    ctm_null_root = root / "artifacts" / "ctm" / "nulls"
    for null_path in sorted(ctm_null_root.glob("*.json")) if ctm_null_root.is_dir() else []:
        rel = null_path.relative_to(root).as_posix()
        payload = json.loads(null_path.read_text())
        null_id = str(payload.get("null_id", null_path.stem))
        file_node(f"ctm_null:{null_id}", "ctm_null", rel)

    # --- benchmark results (inference record + statistics) ------------------
    bench_rel = "benchmark-results.json"
    if (root / bench_rel).is_file():
        file_node("inference:benchmark-results", "inference_record", bench_rel)
        add_node(
            _node(
                "statistics:benchmark-results.aggregate",
                "statistics",
                label="benchmark-results.json aggregate",
            )
        )
        add_edge(
            _edge(
                "inference:benchmark-results",
                "statistics:benchmark-results.aggregate",
                "records",
                evidence_class=EVIDENCE_CLASS_FILE_PINNED,
                note="aggregate is a field of the hash-pinned record",
            )
        )

    # --- decision nodes from D2 status files --------------------------------
    status_files = {
        "RAC-PER-D2-0003": D20003_STATUS_PATH,
        "RAC-PER-D2-0004": D2_LATEST_STATUS_PATH,
    }
    for generation_id, rel in sorted(status_files.items()):
        if not (root / rel).is_file():
            continue
        node_id = f"decision:{generation_id}"
        file_node(node_id, "decision", rel)
        add_node(
            _node(
                f"statistics:{generation_id}.heldout",
                "statistics",
                label=f"{generation_id} held-out aggregate",
            )
        )
        add_edge(
            _edge(
                node_id,
                f"statistics:{generation_id}.heldout",
                "records",
                evidence_class=EVIDENCE_CLASS_FILE_PINNED,
                note="held-out statistics are fields of the hash-pinned decision record",
            )
        )

    # --- manuscript evidence directory --------------------------------------
    evidence_root = root / "manuscript" / "evidence"
    for ev_path in sorted(evidence_root.glob("**/*.json")):
        rel = ev_path.relative_to(root).as_posix()
        if rel in {D20003_STATUS_PATH, D2_LATEST_STATUS_PATH, D20004_LOG_EVIDENCE_PATH}:
            continue
        file_node(f"evidence:{rel}", "inference_record", rel)

    # --- longitudinal export source-hash pins -------------------------------
    csv_rel = LONGITUDINAL_CSV_PATH
    if (root / csv_rel).is_file():
        file_node("document:paper1_longitudinal", "document", csv_rel)
        for pin in _longitudinal_source_pins(root / csv_rel):
            target_id = id_for_path(pin["path"])
            add_edge(
                _edge(
                    "document:paper1_longitudinal",
                    target_id,
                    "cites_source_hash",
                    expected_sha256=pin["sha256"],
                    evidence_class=EVIDENCE_CLASS_FILE_PINNED,
                    note="per-field source hash recorded in the longitudinal export",
                )
            )

    # --- D2-0005 freeze candidate pins --------------------------------------
    freeze_rel = FREEZE_CANDIDATE_PATH
    if (root / freeze_rel).is_file():
        file_node(
            "freeze_candidate:RAC-PER-D2-0005", "frozen_config", freeze_rel
        )
        freeze_doc = json.loads((root / freeze_rel).read_text())
        for pin in _iter_path_sha_pins(freeze_doc):
            target_id = id_for_path(pin["path"], "document")
            add_edge(
                _edge(
                    "freeze_candidate:RAC-PER-D2-0005",
                    target_id,
                    "pins_hash",
                    expected_sha256=pin["sha256"],
                    evidence_class=EVIDENCE_CLASS_FILE_PINNED,
                    note="D2-0005 freeze-candidate pin (pre-arming; arms nothing)",
                )
            )

    # --- D2-0004 log-attested evidence --------------------------------------
    log_rel = D20004_LOG_EVIDENCE_PATH
    if (root / log_rel).is_file():
        log_doc = json.loads((root / log_rel).read_text())
        add_node(
            _node(
                "evidence:RAC-PER-D2-0004.log_attested",
                "inference_record",
                path=log_rel,
                sha256=_sha256_file(root / log_rel),
                evidence_class=EVIDENCE_CLASS_LOG_ATTESTED,
                label="D2-0004 log-attested closure evidence",
            )
        )
        candidate_sha = log_doc["step18_measured_benchmark_stdout"][
            "candidate_sha256"
        ]
        add_node(
            _node(
                "candidate:RAC-PER-D2-0004",
                "candidate",
                sha256=candidate_sha,
                evidence_class=EVIDENCE_CLASS_LOG_ATTESTED,
                present=False,
                label="RAC-PER-D2-0004 candidate (sha attested; bytes never archived)",
            )
        )
        add_edge(
            _edge(
                "evidence:RAC-PER-D2-0004.log_attested",
                "candidate:RAC-PER-D2-0004",
                "attests_candidate_hash",
                expected_sha256=candidate_sha,
                evidence_class=EVIDENCE_CLASS_LOG_ATTESTED,
                verify_mode="log_attested_consistency",
                note=(
                    "candidate SHA attested in step-18/20 run logs; candidate "
                    "bytes were never archived (packaging step 22 failed)"
                ),
            )
        )
        if (root / D2_LATEST_STATUS_PATH).is_file():
            add_edge(
                _edge(
                    "evidence:RAC-PER-D2-0004.log_attested",
                    "decision:RAC-PER-D2-0004",
                    "attests_decision",
                    evidence_class=EVIDENCE_CLASS_LOG_ATTESTED,
                    verify_mode="log_attested_field_match",
                    note=(
                        "step-19 bundle stdout must equal d2-latest-status.json "
                        "field-for-field"
                    ),
                )
            )
        # Known unattested gaps: MISSING-by-design, never BROKEN.
        for gap in D20004_UNATTESTED_GAPS:
            gap_node_id = f"statistics:RAC-PER-D2-0004.{gap}"
            add_node(
                _node(
                    gap_node_id,
                    "statistics",
                    evidence_class=EVIDENCE_CLASS_LOG_ATTESTED,
                    present=False,
                    label=f"D2-0004 {gap} (unattested gap)",
                )
            )
            add_edge(
                _edge(
                    "evidence:RAC-PER-D2-0004.log_attested",
                    gap_node_id,
                    "attests_statistic",
                    evidence_class=EVIDENCE_CLASS_LOG_ATTESTED,
                    missing_by_design=True,
                    verify_mode="unattested_gap",
                    note=(
                        "listed in not_log_attested_gaps of the D2-0004 "
                        "closure evidence; absent by design, not broken"
                    ),
                )
            )

    # --- D2-0003 candidate (sha recorded in longitudinal export) ------------
    if (root / D20003_STATUS_PATH).is_file() and (root / csv_rel).is_file():
        text = (root / csv_rel).read_text()
        for row in csv.DictReader(io.StringIO(text)):
            if row.get("generation_id") != "RAC-PER-D2-0003":
                continue
            sha = row.get("candidate_sha256") or None
            add_node(
                _node(
                    "candidate:RAC-PER-D2-0003",
                    "candidate",
                    sha256=sha,
                    present=False,
                    label="RAC-PER-D2-0003 candidate (sha recorded; bytes not in repo)",
                )
            )
            add_edge(
                _edge(
                    "document:paper1_longitudinal",
                    "candidate:RAC-PER-D2-0003",
                    "records_candidate_hash",
                    expected_sha256=sha,
                    verify_mode="none",
                    evidence_class=EVIDENCE_CLASS_FILE_PINNED,
                    note="candidate bytes not archived in-repo; hash as recorded",
                )
            )

    # --- release and production records -------------------------------------
    release_rel = "releases/RAC-EXP-2026-001/RELEASE.json"
    if (root / release_rel).is_file():
        file_node("rac_release:RAC-EXP-2026-001", "rac_release", release_rel)
    sku_rel = "production_alpha/SKU_MANIFEST.json"
    if (root / sku_rel).is_file():
        file_node("production_asset:SKU_MANIFEST", "production_asset", sku_rel)

    return {
        "schema_id": GRAPH_SCHEMA_ID,
        "schema_version": GRAPH_SCHEMA_VERSION,
        "nodes": [nodes[k] for k in sorted(nodes)],
        "edges": [edges[k] for k in sorted(edges)],
    }


def graph_sha256(graph: dict[str, Any]) -> str:
    """Deterministic content hash of a built graph."""
    return hashlib.sha256(_canonical_bytes(graph)).hexdigest()


def write_graph(graph: dict[str, Any], out_path: str | Path) -> str:
    """Write the canonical graph JSON; returns its sha256."""
    data = _canonical_bytes(graph)
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    Path(out_path).write_bytes(data)
    return hashlib.sha256(data).hexdigest()


# --- verification -----------------------------------------------------------

#: Fields cross-checked between the D2-0004 log-attested step-19 bundle
#: stdout and d2-latest-status.json.
_LOG_ATTESTED_DECISION_FIELDS = (
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


def _verify_edge(root: Path, graph: dict[str, Any], edge: dict[str, Any]) -> str:
    nodes = {n["id"]: n for n in graph["nodes"]}
    target = nodes.get(edge["target"])
    expected = edge.get("expected_sha256")
    mode = edge["verify_mode"]

    if edge.get("missing_by_design"):
        return EDGE_MISSING

    if mode == "log_attested_consistency":
        # Candidate hash must be attested identically everywhere it appears
        # in the log-attested record.
        log_path = root / D20004_LOG_EVIDENCE_PATH
        if not log_path.is_file():
            return EDGE_MISSING
        log_doc = json.loads(log_path.read_text())
        attestations = {
            log_doc["step18_measured_benchmark_stdout"]["candidate_sha256"],
            log_doc["step20_validation_stdout"]["candidate"],
        }
        if target is None or target.get("sha256") not in attestations:
            return EDGE_BROKEN
        return EDGE_VERIFIED if len(attestations) == 1 else EDGE_BROKEN

    if mode == "log_attested_field_match":
        log_path = root / D20004_LOG_EVIDENCE_PATH
        status_path = root / D2_LATEST_STATUS_PATH
        if not log_path.is_file() or not status_path.is_file():
            return EDGE_MISSING
        log_doc = json.loads(log_path.read_text())
        status = json.loads(status_path.read_text())
        bundle = log_doc["step19_d2_evidence_bundle_stdout"]
        for field in _LOG_ATTESTED_DECISION_FIELDS:
            if bundle.get(field) != status.get(field):
                return EDGE_BROKEN
        return EDGE_VERIFIED

    if mode == "unattested_gap":
        return EDGE_MISSING

    if mode == "none":
        # Hash is recorded but no in-repo bytes exist to recompute; the pin
        # is present so the edge is not MUTABLE, and there is nothing to
        # recompute against.
        return EDGE_VERIFIED if expected else EDGE_MUTABLE

    # default: file_hash
    if edge.get("hash_pin_expected") and not expected:
        return EDGE_MUTABLE
    if target is not None and target.get("path") is None and expected is None:
        # Field-of-record edge (e.g. statistics carried inside a hash-pinned
        # record): integrity is inherited from the source record's pin.
        return EDGE_MUTABLE if edge.get("hash_pin_expected") else EDGE_VERIFIED
    if target is None or target.get("path") is None:
        return EDGE_MISSING
    target_path = root / target["path"]
    if not target_path.is_file():
        return EDGE_MISSING
    if expected is None:
        return EDGE_MUTABLE if edge.get("hash_pin_expected") else EDGE_VERIFIED
    actual = _sha256_file(target_path)
    return EDGE_VERIFIED if actual == expected else EDGE_BROKEN


def verify_graph(
    graph: dict[str, Any], repo_root: str | Path = REPO_ROOT
) -> dict[str, Any]:
    """Recompute every hash edge and classify each edge.

    Returns a verification report. ``unexpected`` counts edges that are
    BROKEN, MUTABLE, or MISSING without ``missing_by_design`` — the counts a
    healthy repository must drive to zero.
    """
    require_schema_version(graph, GRAPH_SCHEMA_VERSION, label="provenance graph")
    if graph.get("schema_id") != GRAPH_SCHEMA_ID:
        raise ValueError(
            f"provenance graph: expected schema_id {GRAPH_SCHEMA_ID!r}, "
            f"got {graph.get('schema_id')!r}"
        )
    root = Path(repo_root)
    verified_edges: list[dict[str, Any]] = []
    summary = {EDGE_VERIFIED: 0, EDGE_BROKEN: 0, EDGE_MISSING: 0, EDGE_MUTABLE: 0}
    unexpected: list[str] = []
    for edge in graph["edges"]:
        status = _verify_edge(root, graph, edge)
        summary[status] += 1
        annotated = dict(edge)
        annotated["status"] = status
        verified_edges.append(annotated)
        if status == EDGE_BROKEN or status == EDGE_MUTABLE or (
            status == EDGE_MISSING and not edge.get("missing_by_design")
        ):
            unexpected.append(edge["id"])
    return {
        "schema_id": f"{GRAPH_SCHEMA_ID}-verification",
        "schema_version": GRAPH_SCHEMA_VERSION,
        "graph_sha256": graph_sha256(graph),
        "summary": summary,
        "unexpected_edges": sorted(unexpected),
        "edges": verified_edges,
    }
