"""Tests for the artifact provenance graph (Wave I item 6).

Guards:

1. The graph builds deterministically — two runs produce identical sha256.
2. Seeded corruption of a scratch copy of a hash-pinned file is flagged
   BROKEN on exactly the affected edge.
3. A deliberately unpinned edge (hash pin expected but absent) is flagged
   MUTABLE.
4. The real repository graph verifies with zero unexpected BROKEN / MUTABLE
   / MISSING edges; the known D2-0004 unattested gap
   (``surrogate_detection_rate``) is MISSING-by-design, never BROKEN.
5. The committed ``artifacts/provenance/graph.json`` re-derives exactly.
"""

import json
import shutil
from pathlib import Path

import pytest

from ruthless_pipeline.certification import provenance_graph as pg
from ruthless_pipeline.certification.schema_version import (
    SchemaVersionError,
    require_schema_version,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
COMMITTED_GRAPH = REPO_ROOT / "artifacts" / "provenance" / "graph.json"


def test_graph_build_is_deterministic():
    g1 = pg.build_graph(REPO_ROOT)
    g2 = pg.build_graph(REPO_ROOT)
    assert pg.graph_sha256(g1) == pg.graph_sha256(g2)
    assert json.dumps(g1, sort_keys=True) == json.dumps(g2, sort_keys=True)


def test_graph_schema_versioned():
    graph = pg.build_graph(REPO_ROOT)
    require_schema_version(
        graph, pg.GRAPH_SCHEMA_VERSION, label="provenance graph"
    )
    assert graph["schema_id"] == pg.GRAPH_SCHEMA_ID
    with pytest.raises(SchemaVersionError):
        require_schema_version(
            {**graph, "schema_version": "0.9"},
            pg.GRAPH_SCHEMA_VERSION,
            label="provenance graph",
        )


def test_node_types_are_within_registered_set():
    graph = pg.build_graph(REPO_ROOT)
    for node in graph["nodes"]:
        assert node["type"] in pg.NODE_TYPES
    seen = {n["type"] for n in graph["nodes"]}
    # The repo currently exercises the core types.
    assert {"frozen_config", "decision", "inference_record"} <= seen


def test_real_repo_graph_verifies_with_zero_unexpected_edges():
    graph = pg.build_graph(REPO_ROOT)
    report = pg.verify_graph(graph, REPO_ROOT)
    assert report["unexpected_edges"] == []
    assert report["summary"][pg.EDGE_BROKEN] == 0
    assert report["summary"][pg.EDGE_MUTABLE] == 0


def test_d20004_unattested_gap_is_missing_by_design_not_broken():
    graph = pg.build_graph(REPO_ROOT)
    report = pg.verify_graph(graph, REPO_ROOT)
    gap_edges = [
        e for e in report["edges"] if e["target"].endswith("surrogate_detection_rate")
    ]
    assert len(gap_edges) == 1
    edge = gap_edges[0]
    assert edge["status"] == pg.EDGE_MISSING
    assert edge["missing_by_design"] is True
    assert edge["evidence_class"] == pg.EVIDENCE_CLASS_LOG_ATTESTED


def test_d20004_log_attested_edges_carry_evidence_class():
    graph = pg.build_graph(REPO_ROOT)
    log_edges = [
        e
        for e in graph["edges"]
        if e["source"] == "evidence:RAC-PER-D2-0004.log_attested"
    ]
    assert log_edges, "expected log-attested D2-0004 edges"
    for edge in log_edges:
        assert edge["evidence_class"] == pg.EVIDENCE_CLASS_LOG_ATTESTED


def test_seeded_corruption_is_flagged_broken(tmp_path):
    graph = pg.build_graph(REPO_ROOT)
    # Scratch copy containing a corrupted hash-pinned file.
    target_rel = "benchmarks/runtime_lock.json"
    scratch_file = tmp_path / target_rel
    scratch_file.parent.mkdir(parents=True)
    shutil.copy2(REPO_ROOT / target_rel, scratch_file)
    scratch_file.write_bytes(scratch_file.read_bytes() + b"corruption")

    report = pg.verify_graph(graph, tmp_path)
    edge_id = f"frozen_surface -> file:{target_rel} [pins_hash]"
    statuses = {e["id"]: e["status"] for e in report["edges"]}
    assert statuses[edge_id] == pg.EDGE_BROKEN
    assert edge_id in report["unexpected_edges"]


def test_unpinned_edge_is_flagged_mutable(tmp_path):
    graph = pg.build_graph(REPO_ROOT)
    # Copy the graph and strip the expected sha from one pins_hash edge
    # while keeping hash_pin_expected true.
    mutated = json.loads(json.dumps(graph))
    victim = next(
        e
        for e in mutated["edges"]
        if e["edge_type"] == "pins_hash" and e["source"] == "frozen_surface"
    )
    del victim["expected_sha256"]
    victim["hash_pin_expected"] = True
    # The file exists so only the missing pin can drive the verdict.
    report = pg.verify_graph(mutated, REPO_ROOT)
    statuses = {e["id"]: e["status"] for e in report["edges"]}
    assert statuses[victim["id"]] == pg.EDGE_MUTABLE
    assert victim["id"] in report["unexpected_edges"]


def test_missing_target_is_flagged_missing(tmp_path):
    graph = pg.build_graph(REPO_ROOT)
    # Scratch copy with everything except one pinned file.
    target_rel = "benchmarks/runtime_lock.json"
    (tmp_path / "benchmarks").mkdir(parents=True)
    report = pg.verify_graph(graph, tmp_path)
    edge_id = f"frozen_surface -> file:{target_rel} [pins_hash]"
    statuses = {e["id"]: e["status"] for e in report["edges"]}
    assert statuses[edge_id] == pg.EDGE_MISSING


def test_committed_graph_rederives_exactly():
    if not COMMITTED_GRAPH.is_file():
        pytest.skip("committed graph artifact not present")
    committed = json.loads(COMMITTED_GRAPH.read_text())
    rebuilt = pg.build_graph(REPO_ROOT)
    assert pg.graph_sha256(rebuilt) == pg.graph_sha256(committed)
