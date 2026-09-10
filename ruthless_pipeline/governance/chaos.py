"""Append-only chaos-candidate archive and re-screen lifecycle."""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Iterable

class ChaosGovernanceError(RuntimeError): pass
class ChaosStatus(str, Enum):
    FAILED="FAILED"; SIMULATION_ONLY="SIMULATION_ONLY"; ADMISSIBLE="ADMISSIBLE"

@dataclass(frozen=True)
class ChaosCandidate:
    candidate_id: str
    original_status: ChaosStatus
    reason_code: str

@dataclass(frozen=True)
class ChaosEvent:
    event_type: str
    candidate_id: str
    new_status: ChaosStatus | None = None
    source_candidate_id: str | None = None
    reason_code: str | None = None

@dataclass
class ChaosArchive:
    candidates: dict[str, ChaosCandidate] = field(default_factory=dict)
    events: list[ChaosEvent] = field(default_factory=list)
    def add_failure(self, candidate_id: str, reason_code: str) -> None:
        if candidate_id in self.candidates: raise ChaosGovernanceError("candidate already exists")
        self.candidates[candidate_id]=ChaosCandidate(candidate_id, ChaosStatus.FAILED, reason_code)
        self.events.append(ChaosEvent("CHAOS_REJECTED",candidate_id,ChaosStatus.FAILED,reason_code=reason_code))
    def rescreen(self, candidate_id: str, *, admissible: bool, reason_code: str) -> ChaosEvent:
        if candidate_id not in self.candidates: raise ChaosGovernanceError("unknown chaos candidate")
        status=ChaosStatus.ADMISSIBLE if admissible else ChaosStatus.SIMULATION_ONLY
        ev=ChaosEvent("CHAOS_RESCREEN",candidate_id,status,source_candidate_id=candidate_id,reason_code=reason_code)
        self.events.append(ev); return ev
    def promote_to_hypothesis(self, candidate_id: str, *, physically_admissible: bool) -> ChaosEvent:
        if not physically_admissible: raise ChaosGovernanceError("physical-admissibility gate failed")
        if candidate_id not in self.candidates: raise ChaosGovernanceError("unknown chaos candidate")
        if not any(e.candidate_id==candidate_id and e.new_status is ChaosStatus.ADMISSIBLE for e in self.events):
            raise ChaosGovernanceError("candidate must pass a new re-screen before promotion")
        ev=ChaosEvent("NEW_HYPOTHESIS",candidate_id,ChaosStatus.ADMISSIBLE,source_candidate_id=candidate_id)
        self.events.append(ev); return ev
    def yield_report(self) -> dict[str,int]:
        return {"archived":len(self.candidates),"original_failures":sum(c.original_status is ChaosStatus.FAILED for c in self.candidates.values()),"rescreens":sum(e.event_type=="CHAOS_RESCREEN" for e in self.events),"promotions":sum(e.event_type=="NEW_HYPOTHESIS" for e in self.events)}
