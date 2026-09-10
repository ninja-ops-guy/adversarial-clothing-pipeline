from __future__ import annotations

from pathlib import Path

from ruthless_pipeline.governance.cic_adapter import (
    ConstraintEncoding,
    EncodingKind,
    ExternalCICCoreBackend,
    SolveStatus,
    preflight,
)


SEM = "a" * 64


def _encoding() -> ConstraintEncoding:
    return ConstraintEncoding(
        encoding_kind=EncodingKind.CNF,
        semantic_hash=SEM,
        num_vars=3,
        compiled_payload=((1, 2), (-1, 3)),
        semantic_vars=frozenset({1, 2, 3}),
        scientific_projection=frozenset({1, 2, 3}),
        independent_support=frozenset({1, 2}),
        encoder_id="fixture",
        encoder_version="1",
    )


def _write_core(root: Path, *, model: str) -> None:
    shared = root / "security_tools" / "shared"
    shared.mkdir(parents=True)
    (shared / "cic_core.py").write_text(
        "def dpll_solve(clauses, num_vars, timeout=30.0):\n"
        f"    return {model}\n"
        "def build_primal_graph(num_vars, clauses):\n"
        "    graph = {v: set() for v in range(1, num_vars + 1)}\n"
        "    for clause in clauses:\n"
        "        vs = [abs(x) for x in clause]\n"
        "        for i, a in enumerate(vs):\n"
        "            for b in vs[i+1:]:\n"
        "                graph[a].add(b); graph[b].add(a)\n"
        "    return graph\n"
        "def minfill_treewidth(graph):\n"
        "    return list(graph), max((len(v) for v in graph.values()), default=0)\n"
    )


def test_external_cic_sat_model_is_verified(tmp_path):
    _write_core(tmp_path, model="{1: True, 2: True, 3: True}")
    backend = ExternalCICCoreBackend(tmp_path)
    result = preflight(_encoding(), backend)
    assert result.status is SolveStatus.SAT
    assert result.assignment_verified is True
    assert result.structural_report.treewidth_estimate is not None


def test_external_cic_none_is_unknown_not_unsat(tmp_path):
    _write_core(tmp_path, model="None")
    backend = ExternalCICCoreBackend(tmp_path)
    result = preflight(_encoding(), backend)
    assert result.status is SolveStatus.UNKNOWN
    assert result.assignment_verified is False
    assert "cannot distinguish UNSAT from timeout" in result.note
