"""Mechanical CTM provenance firewall.

Certification walks the dependency chain from a CTM claim and refuses any
claim whose DOE/generator/acceptance lineage reaches a held-out observation.
This is an executable certification condition, not merely a test policy.
"""
from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass

from .contracts import CTMClaim, CTMArtifactRole, PRE_OUTCOME_ROLES


DEPENDENCY_EDGE_TYPES = frozenset({
    "consumes",
    "derived_from",
    "generated_from",
    "selected_by",
    "accepted_by",
    "uses_genome",
    "uses_null_design",
    "uses_surrogate_observation",
})


@dataclass(frozen=True)
class FirewallResult:
    ok: bool
    visited_nodes: tuple[str, ...]
    prohibited_paths: tuple[tuple[str, ...], ...]


def _node_role(node: dict) -> str | None:
    return node.get("ctm_role") or node.get("role") or node.get("type")


def check_provenance_firewall(claim: CTMClaim, graph: dict) -> FirewallResult:
    """Walk claim dependency paths and reject held-out leakage into pre-outcome paths.

    CTM graph convention: edge source consumes/depends on edge target.
    """
    claim.validate()
    nodes = {n["id"]: n for n in graph.get("nodes", [])}
    outgoing = defaultdict(list)
    for edge in graph.get("edges", []):
        if edge.get("edge_type") in DEPENDENCY_EDGE_TYPES:
            outgoing[edge["source"]].append(edge["target"])

    roots = [
        a.artifact_id
        for a in claim.consumed_artifacts
        if a.role in PRE_OUTCOME_ROLES
    ]
    prohibited: list[tuple[str, ...]] = []
    visited: set[str] = set()

    for root in roots:
        queue = deque([(root, (root,))])
        local_seen: set[str] = set()
        while queue:
            node_id, path = queue.popleft()
            if node_id in local_seen:
                continue
            local_seen.add(node_id)
            visited.add(node_id)
            node = nodes.get(node_id, {})
            role = _node_role(node)
            if (
                role == CTMArtifactRole.HELDOUT_OBSERVATION.value
                or node.get("heldout_observation") is True
                or node.get("data_split") == "heldout"
            ):
                prohibited.append(path)
                continue
            for target in sorted(outgoing.get(node_id, ())):
                queue.append((target, path + (target,)))

    return FirewallResult(
        ok=not prohibited,
        visited_nodes=tuple(sorted(visited)),
        prohibited_paths=tuple(sorted(prohibited)),
    )


def require_provenance_firewall(claim: CTMClaim, graph: dict) -> FirewallResult:
    result = check_provenance_firewall(claim, graph)
    if not result.ok:
        rendered = " | ".join(" -> ".join(p) for p in result.prohibited_paths)
        raise ValueError(
            "CTM certification firewall failure: pre-outcome provenance reaches "
            f"held-out observation: {rendered}"
        )
    return result
