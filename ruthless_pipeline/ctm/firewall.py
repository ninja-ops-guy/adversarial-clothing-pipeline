"""Mechanical CTM provenance firewall.

Certification walks the dependency chain from a CTM claim and refuses any
claim whose DOE/generator/acceptance lineage reaches a held-out observation.
It also refuses missing provenance roots and claim↔graph hash mismatches.
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
    missing_roots: tuple[str, ...] = ()
    hash_mismatches: tuple[str, ...] = ()


def _node_role(node: dict) -> str | None:
    return node.get("ctm_role") or node.get("role") or node.get("type")


def check_provenance_firewall(claim: CTMClaim, graph: dict) -> FirewallResult:
    """Walk claim dependency paths and reject held-out leakage.

    CTM graph convention: edge source consumes/depends on edge target.
    Every pre-outcome artifact named by the claim must exist in the graph and
    its graph SHA, when supplied, must match the claim's pinned SHA.
    """
    claim.validate()
    nodes = {n["id"]: n for n in graph.get("nodes", [])}
    outgoing = defaultdict(list)
    for edge in graph.get("edges", []):
        if edge.get("edge_type") in DEPENDENCY_EDGE_TYPES:
            outgoing[edge["source"]].append(edge["target"])

    pre_outcome = [
        a for a in claim.consumed_artifacts if a.role in PRE_OUTCOME_ROLES
    ]
    missing_roots: list[str] = []
    hash_mismatches: list[str] = []

    for artifact in pre_outcome:
        node = nodes.get(artifact.artifact_id)
        if node is None:
            missing_roots.append(artifact.artifact_id)
            continue
        graph_sha = node.get("sha256")
        if not graph_sha:
            hash_mismatches.append(
                f"{artifact.artifact_id}: graph node missing sha256"
            )
        elif graph_sha != artifact.sha256:
            hash_mismatches.append(
                f"{artifact.artifact_id}: claim={artifact.sha256} graph={graph_sha}"
            )

    prohibited: list[tuple[str, ...]] = []
    visited: set[str] = set()

    for artifact in pre_outcome:
        root = artifact.artifact_id
        if root not in nodes:
            continue
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

    ok = not prohibited and not missing_roots and not hash_mismatches
    return FirewallResult(
        ok=ok,
        visited_nodes=tuple(sorted(visited)),
        prohibited_paths=tuple(sorted(prohibited)),
        missing_roots=tuple(sorted(missing_roots)),
        hash_mismatches=tuple(sorted(hash_mismatches)),
    )


def require_provenance_firewall(claim: CTMClaim, graph: dict) -> FirewallResult:
    result = check_provenance_firewall(claim, graph)
    if result.ok:
        return result

    reasons: list[str] = []
    if result.missing_roots:
        reasons.append("missing roots: " + ", ".join(result.missing_roots))
    if result.hash_mismatches:
        reasons.append("hash mismatch: " + " | ".join(result.hash_mismatches))
    if result.prohibited_paths:
        reasons.append(
            "held-out path: "
            + " | ".join(" -> ".join(p) for p in result.prohibited_paths)
        )
    raise ValueError(
        "CTM certification firewall failure: " + "; ".join(reasons)
    )
