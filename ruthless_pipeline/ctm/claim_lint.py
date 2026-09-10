"""SPEC-3 — Corpus-bounded-claim linter for manuscripts.

Lesson L1: every negative claim carries its corpus scope in the sentence
("in a coded corpus of N papers ..."), never bare universal quantification.
A near-miss (arXiv 2606.17711) surfaced in minutes of targeted searching —
the claim survived but the epistemic wrapper was wrong. This linter turns
that remembered rule into a gate: universal-negative patterns must co-occur,
in the SAME sentence, with (a) a corpus-scope qualifier and (b) a citation
to a content-addressed corpus snapshot (SPEC-4). Violations fail lint unless
allowlisted with a stated reason.

Fail closed with :class:`ClaimLintError` (or collect violations via
:func:`lint_text`). This module is additive and complements the existing
documentation linter (``certification/doc_lint.py``); it does not modify it.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable, Mapping

from .errors import CTMBridgeError

CLAIM_LINT_RULESET_VERSION = "rac-ctm-claim-lint/1.0"

#: Universal-negative / priority patterns (case-insensitive). "the first" is
#: included as a priority claim, which is a universal negative in disguise.
UNIVERSAL_NEGATIVE_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(p, re.IGNORECASE)
    for p in (
        r"\bno prior work\b",
        r"\bno paper has\b",
        r"\bno papers have\b",
        r"\bnobody has\b",
        r"\bno one has\b",
        r"\bnothing exists\b",
        r"\bno existing\b",
        r"\bnever been\b",
        r"\bhas not been (?:measured|done|shown|demonstrated|reported)\b",
        r"\bhave not been (?:measured|done|shown|demonstrated|reported)\b",
        r"\bthe first\b",
        r"\bfirst to\b",
        r"\bno known\b",
    )
)

#: Corpus-scope qualifiers bounding the negative to a coded corpus.
_CORPUS_SCOPE_QUALIFIERS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(p, re.IGNORECASE)
    for p in (
        r"\bcoded corpus\b",
        r"\bliving corpus\b",
        r"\bcorpus of \d+\b",
        r"\bwithin (?:the|our|this) corpus\b",
        r"\bin the corpus\b",
        r"\bcorpus snapshot\b",
        r"\bregistry snapshot\b",
    )
)

#: A citation to a content-addressed SPEC-4 corpus snapshot: either the
#: snapshot id or a raw 64-hex content hash named as a snapshot ref.
_SNAPSHOT_REF = re.compile(
    r"RAC-CTM-CORPUS-SNAPSHOT-[0-9a-f]{16}"
    r"|\bsnapshot\s*(?:ref|sha256)?[:#]?\s*[0-9a-f]{64}\b",
    re.IGNORECASE,
)

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+|\n+")


class ClaimLintError(CTMBridgeError):
    """Corpus-bounded-claim lint failure (SPEC-3). Fail closed."""


@dataclass(frozen=True)
class ClaimLintViolation:
    """One unbounded universal-negative finding."""

    sentence_index: int
    pattern: str
    sentence: str
    missing: tuple[str, ...]  # any of: "corpus_scope_qualifier", "snapshot_ref"

    def to_dict(self) -> dict:
        return {
            "sentence_index": self.sentence_index,
            "pattern": self.pattern,
            "sentence": self.sentence,
            "missing": list(self.missing),
        }


@dataclass(frozen=True)
class ClaimLintResult:
    """Lint outcome. ``ok`` iff no non-allowlisted violations."""

    violations: tuple[ClaimLintViolation, ...]
    allowlisted: tuple[ClaimLintViolation, ...]

    @property
    def ok(self) -> bool:
        return not self.violations

    def to_dict(self) -> dict:
        return {
            "ruleset_version": CLAIM_LINT_RULESET_VERSION,
            "ok": self.ok,
            "violations": [v.to_dict() for v in self.violations],
            "allowlisted": [v.to_dict() for v in self.allowlisted],
        }


def _violation(sentence_index: int, pattern: str, sentence: str) -> ClaimLintViolation | None:
    missing: list[str] = []
    if not any(q.search(sentence) for q in _CORPUS_SCOPE_QUALIFIERS):
        missing.append("corpus_scope_qualifier")
    if not _SNAPSHOT_REF.search(sentence):
        missing.append("snapshot_ref")
    if not missing:
        return None
    return ClaimLintViolation(
        sentence_index=sentence_index,
        pattern=pattern,
        sentence=sentence.strip(),
        missing=tuple(missing),
    )


def lint_text(
    text: str,
    *,
    allowlist: Mapping[str, str] | None = None,
) -> ClaimLintResult:
    """Lint manuscript text for unbounded universal negatives.

    ``allowlist`` maps the exact sentence text to a stated reason (mirroring
    the reasoned-allowlist mechanism of the existing doc linter). An
    allowlist entry without a non-empty reason does not allowlist.
    """
    if not isinstance(text, str):
        raise ClaimLintError("lint_text expects a string")
    allowlist = dict(allowlist or {})
    violations: list[ClaimLintViolation] = []
    allowlisted: list[ClaimLintViolation] = []
    sentences = [s for s in _SENTENCE_SPLIT.split(text) if s.strip()]
    for idx, sentence in enumerate(sentences):
        for pattern in UNIVERSAL_NEGATIVE_PATTERNS:
            m = pattern.search(sentence)
            if not m:
                continue
            v = _violation(idx, m.group(0).lower(), sentence)
            if v is None:
                continue
            reason = allowlist.get(sentence.strip())
            if reason and reason.strip():
                allowlisted.append(v)
            else:
                violations.append(v)
    return ClaimLintResult(violations=tuple(violations), allowlisted=tuple(allowlisted))


def require_bounded(
    text: str, *, allowlist: Mapping[str, str] | None = None
) -> None:
    """Fail-closed variant: raise :class:`ClaimLintError` on any violation."""
    result = lint_text(text, allowlist=allowlist)
    if not result.ok:
        detail = "; ".join(
            f"sentence {v.sentence_index} ({v.pattern!r}, missing "
            f"{','.join(v.missing)}): {v.sentence[:120]!r}"
            for v in result.violations
        )
        raise ClaimLintError(
            "unbounded universal-negative claim(s) fail lint (L1: every "
            "negative claim carries its corpus scope and a corpus-snapshot "
            f"citation in the same sentence): {detail}"
        )


def lint_files(
    paths: Iterable[str], *, allowlist: Mapping[str, str] | None = None
) -> ClaimLintResult:
    """Lint multiple manuscript files, merging violations."""
    from pathlib import Path

    all_v: list[ClaimLintViolation] = []
    all_a: list[ClaimLintViolation] = []
    for p in paths:
        result = lint_text(Path(p).read_text(encoding="utf-8"), allowlist=allowlist)
        all_v.extend(result.violations)
        all_a.extend(result.allowlisted)
    return ClaimLintResult(violations=tuple(all_v), allowlisted=tuple(all_a))
