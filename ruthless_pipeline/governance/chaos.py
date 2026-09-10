"""Append-only chaos-candidate archive and re-screen lifecycle.

Chaos exploration is retained as a first-class research lane.  Rejections are
never rewritten away; changed capabilities create new re-screen events, and
promotion requires the latest re-screen to be physically admissible.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Mapping


class ChaosGovernanceError(RuntimeError):
    pass


class ChaosStatus(str, Enum):
    FAILED = "FAILED"
    SIMULATION_ONLY = "SIMULATION_ONLY"
    ADMISSIBLE = "ADMISSIBLE"


@dataclass(frozen=True)
class ChaosCandidate:
    candidate_id: str
    original_status: ChaosStatus
    reason_code: str
    generator_class: str = "UNKNOWN"
    topology_class: str = "UNKNOWN"
    spectral_class: str = "UNKNOWN"


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

    def add_failure(
        self,
        candidate_id: str,
        reason_code: str,
        *,
        generator_class: str = "UNKNOWN",
        topology_class: str = "UNKNOWN",
        spectral_class: str = "UNKNOWN",
    ) -> None:
        if not candidate_id or not reason_code:
            raise ChaosGovernanceError("candidate_id and reason_code are required")
        if candidate_id in self.candidates:
            raise ChaosGovernanceError("candidate already exists")
        candidate = ChaosCandidate(
            candidate_id=candidate_id,
            original_status=ChaosStatus.FAILED,
            reason_code=reason_code,
            generator_class=generator_class or "UNKNOWN",
            topology_class=topology_class or "UNKNOWN",
            spectral_class=spectral_class or "UNKNOWN",
        )
        self.candidates[candidate_id] = candidate
        self.events.append(
            ChaosEvent(
                "CHAOS_REJECTED",
                candidate_id,
                ChaosStatus.FAILED,
                reason_code=reason_code,
            )
        )

    def rescreen(
        self,
        candidate_id: str,
        *,
        admissible: bool,
        reason_code: str,
    ) -> ChaosEvent:
        if candidate_id not in self.candidates:
            raise ChaosGovernanceError("unknown chaos candidate")
        if not reason_code:
            raise ChaosGovernanceError("re-screen reason_code is required")
        status = ChaosStatus.ADMISSIBLE if admissible else ChaosStatus.SIMULATION_ONLY
        event = ChaosEvent(
            "CHAOS_RESCREEN",
            candidate_id,
            status,
            source_candidate_id=candidate_id,
            reason_code=reason_code,
        )
        self.events.append(event)
        return event

    def _latest_rescreen(self, candidate_id: str) -> ChaosEvent | None:
        for event in reversed(self.events):
            if event.candidate_id == candidate_id and event.event_type == "CHAOS_RESCREEN":
                return event
        return None

    def current_status(self, candidate_id: str) -> ChaosStatus:
        if candidate_id not in self.candidates:
            raise ChaosGovernanceError("unknown chaos candidate")
        latest = self._latest_rescreen(candidate_id)
        if latest is not None and latest.new_status is not None:
            return latest.new_status
        return self.candidates[candidate_id].original_status

    def promote_to_hypothesis(
        self,
        candidate_id: str,
        *,
        physically_admissible: bool,
    ) -> ChaosEvent:
        if not physically_admissible:
            raise ChaosGovernanceError("physical-admissibility gate failed")
        if candidate_id not in self.candidates:
            raise ChaosGovernanceError("unknown chaos candidate")
        latest = self._latest_rescreen(candidate_id)
        if latest is None or latest.new_status is not ChaosStatus.ADMISSIBLE:
            raise ChaosGovernanceError(
                "candidate must pass its latest re-screen before promotion"
            )
        if any(
            event.candidate_id == candidate_id
            and event.event_type == "NEW_HYPOTHESIS"
            for event in self.events
        ):
            raise ChaosGovernanceError("candidate already promoted")
        event = ChaosEvent(
            "NEW_HYPOTHESIS",
            candidate_id,
            ChaosStatus.ADMISSIBLE,
            source_candidate_id=candidate_id,
        )
        self.events.append(event)
        return event

    def yield_report(self) -> dict[str, int]:
        """Backwards-compatible event-count report."""
        return {
            "archived": len(self.candidates),
            "original_failures": sum(
                candidate.original_status is ChaosStatus.FAILED
                for candidate in self.candidates.values()
            ),
            "rescreens": sum(
                event.event_type == "CHAOS_RESCREEN" for event in self.events
            ),
            "promotions": sum(
                event.event_type == "NEW_HYPOTHESIS" for event in self.events
            ),
        }

    def admissibility_report(self) -> dict[str, object]:
        """Describe what the physical gate retains without hiding failures."""
        total = len(self.candidates)
        statuses = Counter(self.current_status(cid).value for cid in self.candidates)
        admissible = statuses[ChaosStatus.ADMISSIBLE.value]
        return {
            "archived": total,
            "admissible": admissible,
            "simulation_only": statuses[ChaosStatus.SIMULATION_ONLY.value],
            "never_rescreened_failed": statuses[ChaosStatus.FAILED.value],
            "admissibility_rate": (admissible / total) if total else 0.0,
            "original_failure_reasons": dict(
                sorted(Counter(c.reason_code for c in self.candidates.values()).items())
            ),
            "latest_rescreen_reasons": dict(
                sorted(
                    Counter(
                        event.reason_code
                        for event in self.events
                        if event.event_type == "CHAOS_RESCREEN" and event.reason_code
                    ).items()
                )
            ),
        }

    def gate_bias_report(self, group_by: str) -> dict[str, Mapping[str, object]]:
        """Descriptive gate-retention rates by pre-outcome candidate class.

        This is a survivorship-bias diagnostic, not evidence of adversarial
        efficacy.  Only metadata recorded when the failed candidate entered the
        archive may be used as a grouping variable.
        """
        allowed = {"generator_class", "topology_class", "spectral_class"}
        if group_by not in allowed:
            raise ChaosGovernanceError(
                f"group_by must be one of {sorted(allowed)}"
            )
        grouped: dict[str, list[ChaosStatus]] = defaultdict(list)
        for candidate_id, candidate in self.candidates.items():
            grouped[str(getattr(candidate, group_by))].append(
                self.current_status(candidate_id)
            )

        report: dict[str, Mapping[str, object]] = {}
        for group in sorted(grouped):
            statuses = grouped[group]
            total = len(statuses)
            admissible = sum(status is ChaosStatus.ADMISSIBLE for status in statuses)
            simulation_only = sum(
                status is ChaosStatus.SIMULATION_ONLY for status in statuses
            )
            report[group] = {
                "archived": total,
                "admissible": admissible,
                "simulation_only": simulation_only,
                "failed": total - admissible - simulation_only,
                "admissibility_rate": admissible / total,
            }
        return report
