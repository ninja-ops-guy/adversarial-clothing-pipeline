"""Bounded formal-methods adapter for RAC experimental governance.

This module is deliberately efficacy-blind. It can establish feasibility,
validate solver assignments, preserve semantic/compiled identity separation,
and emit structural routing metadata. It must never score adversarial efficacy.
"""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
import hashlib, json
from typing import Any, Callable, Mapping, Protocol, Sequence

class CICError(RuntimeError): pass
class SolveStatus(str, Enum):
    SAT="SAT"; UNSAT="UNSAT"; UNKNOWN="UNKNOWN"

def _digest(v: Any)->str:
    return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()

@dataclass(frozen=True)
class ConstraintRepresentation:
    representation:str; semantic_payload:Mapping[str,Any]; compiled_payload:Mapping[str,Any]
    semantic_variables:tuple[str,...]; auxiliary_variables:tuple[str,...]=(); independent_support:tuple[str,...]=()
    def validate(self)->None:
        if self.representation not in {"CNF","PB","SMT","EXTERNAL"}: raise CICError(f"unsupported representation: {self.representation}")
        s,a,i=set(self.semantic_variables),set(self.auxiliary_variables),set(self.independent_support)
        if not s: raise CICError("scientific projection must contain semantic variables")
        if s&a: raise CICError("semantic and auxiliary variable sets must be disjoint")
        if not i<=s: raise CICError("independent support must be a subset of semantic variables")
    @property
    def semantic_hash(self)->str: return _digest(self.semantic_payload)
    @property
    def compiled_hash(self)->str: return _digest({"representation":self.representation,"payload":self.compiled_payload})

@dataclass(frozen=True)
class StructuralMetrics:
    variable_count:int; semantic_variable_count:int; auxiliary_variable_count:int; independent_support_size:int
    constraint_count:int|None=None; graph_density:float|None=None; treewidth_estimate:float|None=None
@dataclass(frozen=True)
class SolverReply:
    status:SolveStatus; assignment:Mapping[str,Any]|None=None; unsat_core:tuple[str,...]=(); proof_artifact:str|None=None; backend:str="unknown"
@dataclass(frozen=True)
class CICResult:
    status:SolveStatus; semantic_hash:str; compiled_hash:str; scientific_projection:Mapping[str,Any]|None
    independent_support:tuple[str,...]; unsat_core:tuple[str,...]; proof_artifact:str|None; backend:str; metrics:StructuralMetrics
class SolverBackend(Protocol):
    def check(self, representation:ConstraintRepresentation, *, explain_unsat:bool)->SolverReply: ...

def check(representation:ConstraintRepresentation, *, backend:SolverBackend, assignment_verifier:Callable[[Mapping[str,Any]],bool], explain_unsat:bool=True, metrics:StructuralMetrics|None=None)->CICResult:
    representation.validate(); reply=backend.check(representation, explain_unsat=explain_unsat)
    if not isinstance(reply.status,SolveStatus): raise CICError("backend returned invalid solve status")
    projection=None
    if reply.status is SolveStatus.SAT:
        if reply.assignment is None: raise CICError("SAT backend reply requires assignment")
        if not assignment_verifier(reply.assignment): raise CICError("independent verifier rejected SAT assignment")
        missing=[n for n in representation.semantic_variables if n not in reply.assignment]
        if missing: raise CICError(f"SAT assignment missing semantic variables: {missing}")
        projection={n:reply.assignment[n] for n in representation.semantic_variables}
    elif reply.assignment is not None: raise CICError("non-SAT backend reply must not carry an assignment")
    m=metrics or StructuralMetrics(len(representation.semantic_variables)+len(representation.auxiliary_variables),len(representation.semantic_variables),len(representation.auxiliary_variables),len(representation.independent_support))
    return CICResult(reply.status,representation.semantic_hash,representation.compiled_hash,projection,tuple(representation.independent_support),tuple(reply.unsat_core) if explain_unsat else (),reply.proof_artifact,reply.backend,m)

def require_cross_encoding_agreement(results:Sequence[CICResult])->None:
    if len(results)<2: raise CICError("cross-encoding agreement requires at least two results")
    if len({r.semantic_hash for r in results})!=1: raise CICError("results do not share one semantic identity")
    if len({r.status for r in results})!=1: raise CICError("semantically equivalent encodings disagree on solve status")
