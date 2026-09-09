"""Documentation staleness linter for the research pipeline.

Scans docs/**, README.md, and manuscript/backlog/** for:

* stale experiment statuses (D2-0004 described as open/in-progress while the
  published status JSON records it closed; D2-0005 described as armed while
  the generation skeleton and freeze candidate say PREREGISTERED / not armed),
* broken relative repository paths (markdown links and backticked paths),
* conflicting Product Studio manifest schema versions (must match
  schemas/product_studio_manifest.contract.json accepted_schema_version),
* stale CI run numbers presented as current/in-progress,
* quantitative held-out claims that do not trace to the RAC status JSON.

Intentional history is supported via an allowlist: either an inline HTML
comment marker ``<!-- doclint:allow check="<check_id>" reason="..." -->``
anywhere in a file (``check`` may be ``*`` or omitted to allow all checks in
that file), or a repo-root ``.doclint-allow.json`` of the form::

    {"allow": [{"path": "docs/X.md", "check": "stale-d2-0004-status",
                "match": "optional substring", "reason": "..."}]}

Entries with ``"check": "*"`` allow every check for that path; ``match``
(when present) restricts the entry to findings whose line contains it.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Iterable

CHECK_STALE_D2_0004 = "stale-d2-0004-status"
CHECK_STALE_D2_0005_ARMED = "stale-d2-0005-armed"
CHECK_BROKEN_PATH = "broken-path"
CHECK_SCHEMA_DRIFT = "schema-version-drift"
CHECK_STALE_CI_RUN = "stale-ci-run"
CHECK_QUANT_CLAIM = "untraceable-quantitative-claim"

ALL_CHECKS = (
    CHECK_STALE_D2_0004,
    CHECK_STALE_D2_0005_ARMED,
    CHECK_BROKEN_PATH,
    CHECK_SCHEMA_DRIFT,
    CHECK_STALE_CI_RUN,
    CHECK_QUANT_CLAIM,
)

ALLOWLIST_FILENAME = ".doclint-allow.json"
INLINE_ALLOW_RE = re.compile(
    r"<!--\s*doclint:allow(?:\s+check=\"(?P<check>[^\"]+)\")?"
    r"(?:\s+reason=\"(?P<reason>[^\"]*)\")?\s*-->"
)

# Repo-relative path prefixes treated as verifiable repository paths when
they appear in backticks.
PATH_PREFIXES = (
    "docs/", "scripts/", "ruthless_pipeline/", "tests/", "schemas/",
    "generations/", "manuscript/", "benchmarks/", "releases/", "protocols/",
    "model_sets/", "model_manifests/", "registry/", "artifacts/",
    "production_alpha/", "design_profiles/", "templates/", "physical/",
    "examples/", "patterns/",
)

MARKDOWN_LINK_RE = re.compile(r"\[[^\]]*\]\((?P<target>[^)\s#]+)(?:#[^)]*)?\)")
BACKTICK_RE = re.compile(r"`(?P<target>[^`\n]+)`")

# Present-tense "open / in progress" phrasings that would be stale for the
# closed D2-0004 generation. Kept deliberately precise; borderline hits are
# expected to be resolved via the allowlist, not by broadening these.
D2_0004_STALE_PATTERNS = (
    re.compile(
        r"D2-?0004\b[^.\n]{0,30}?\b(?:is|remains?|currently)\s+"
        r"(?:still\s+)?(?:open|in[- ]progress)\b",
        re.IGNORECASE,
    ),
    re.compile(r"D2-?0004\s+still\s+open\b", re.IGNORECASE),
    re.compile(
        r"D2-?0004\s*[·:→\-]+\s*(?:status\s*)?(?:OPEN|IN[- ]PROGRESS)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"D2-?0004\b[^.\n]{0,60}?READY_FOR_FRESH_HELDOUT_RUN\b"
        r"|READY_FOR_FRESH_HELDOUT_RUN\b[^.\n]{0,60}?D2-?0004",
        re.IGNORECASE,
    ),
)
# Past-tense / closure context that is NOT a stale-status claim.
D2_0004_OK_RE = re.compile(
    r"\b(?:was|were)\s+(?:still\s+)?open\b|\bclosed\b|\bclosure\b",
    re.IGNORECASE,
)

D2_0005_ARMED_RE = re.compile(r"\barmed\b", re.IGNORECASE)
D2_0005_NEGATION_RE = re.compile(
    r"\b(not|NOT|never|unarmed|pre[- ]?arm|pending|awaits?|before|cannot|"
    r"without|not yet|must not|MUST NOT)\b"
    r"|\barmed\b\s*[:=]?\s*`?false",
    re.IGNORECASE,
)

CI_RUN_RE = re.compile(r"\b(?:CI |workflow )?run\s*#?(?P<num>\d{6,})\b", re.IGNORECASE)
CI_CURRENT_RE = re.compile(r"\b(in[- ]progress|currently running)\b", re.IGNORECASE)

PRODUCT_STUDIO_VERSION_RE = re.compile(r"\b\d+\.\d+\b")
NUMBER_RE = re.compile(r"(?<![\w.])(?P<num>-?\d+\.\d+)(?![\w.])")


@dataclass
class Finding:
    check: str
    path: str
    line: int
    message: str
    excerpt: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class AllowEntry:
    path: str
    check: str = "*"
    match: str | None = None
    reason: str = ""

    def covers(self, finding: Finding) -> bool:
        if self.path != finding.path:
            return False
        if self.check not in ("*", finding.check):
            return False
        if self.match is not None and self.match not in finding.excerpt:
            return False
        return True


@dataclass
class LintResult:
    findings: list[Finding] = field(default_factory=list)
    allowed: list[Finding] = field(default_factory=list)
    scanned_files: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.findings

    def to_dict(self) -> dict:
        return {
            "ok": self.ok,
            "scanned_files": len(self.scanned_files),
            "finding_count": len(self.findings),
            "allowed_count": len(self.allowed),
            "findings": [f.to_dict() for f in self.findings],
            "allowed": [f.to_dict() for f in self.allowed],
        }


def _doc_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for pattern in ("docs/**/*.md", "manuscript/backlog/**/*.md"):
        files.extend(sorted(root.glob(pattern)))
    readme = root / "README.md"
    if readme.exists():
        files.append(readme)
    return [f for f in files if f.is_file()]


def _load_allowlist(root: Path) -> list[AllowEntry]:
    entries: list[AllowEntry] = []
    allow_file = root / ALLOWLIST_FILENAME
    if allow_file.exists():
        data = json.loads(allow_file.read_text(encoding="utf-8"))
        for item in data.get("allow", []):
            entries.append(
                AllowEntry(
                    path=item["path"],
                    check=item.get("check", "*"),
                    match=item.get("match"),
                    reason=item.get("reason", ""),
                )
            )
    return entries


def _inline_allows(text: str) -> set[str]:
    checks: set[str] = set()
    for m in INLINE_ALLOW_RE.finditer(text):
        checks.add(m.group("check") or "*")
    return checks


def _truth(root: Path) -> dict:
    """Load machine-readable sources of truth."""
    truth: dict = {}
    status_path = root / "d2-latest-status.json"
    if status_path.exists():
        truth["d2_status"] = json.loads(status_path.read_text(encoding="utf-8"))
    gen4 = root / "generations" / "RAC-PER-D2-0004.json"
    if gen4.exists():
        truth["d2_0004"] = json.loads(gen4.read_text(encoding="utf-8"))
    gen5 = root / "generations" / "RAC-PER-D2-0005.json"
    if gen5.exists():
        truth["d2_0005"] = json.loads(gen5.read_text(encoding="utf-8"))
    freeze = root / "docs" / "D2-0005_FREEZE_CANDIDATE.json"
    if freeze.exists():
        truth["d2_0005_freeze"] = json.loads(freeze.read_text(encoding="utf-8"))
    contract = root / "schemas" / "product_studio_manifest.contract.json"
    if contract.exists():
        truth["manifest_contract"] = json.loads(contract.read_text(encoding="utf-8"))
    return truth


def _d2_0004_closed(truth: dict) -> bool:
    status = truth.get("d2_status", {})
    return status.get("candidate_id") == "RAC-PER-D2-0004" and bool(
        status.get("decision")
    )


def _d2_0005_armed(truth: dict) -> bool:
    gen5 = truth.get("d2_0005", {})
    freeze = truth.get("d2_0005_freeze", {})
    if gen5.get("lock_status") == "PREREGISTERED":
        return False
    if freeze.get("arming", {}).get("armed") is False:
        return False
    return bool(freeze.get("arming", {}).get("armed"))


def _known_quantities(truth: dict) -> list[tuple[str, float]]:
    heldout = truth.get("d2_status", {}).get("heldout", {})
    known: list[tuple[str, float]] = []
    for key in (
        "baseline_detection_rate",
        "candidate_detection_rate",
        "baseline_mean",
        "candidate_mean",
        "mean_delta",
        "invalid_condition_fraction",
    ):
        value = heldout.get(key)
        if isinstance(value, (int, float)):
            known.append((key, float(value)))
    return known


def _matches_known(value: float, decimals: int, known: Iterable[tuple[str, float]]) -> str | None:
    tolerance = max(0.5 * 10 ** (-decimals), 1e-9)
    for name, ref in known:
        if abs(value - ref) <= tolerance:
            return name
    return None


def _check_stale_d2_0004(root: Path, rel: str, lineno: int, line: str, truth: dict) -> Finding | None:
    if not _d2_0004_closed(truth):
        return None
    if "D2-0004" not in line and "D2 0004" not in line:
        return None
    if not any(p.search(line) for p in D2_0004_STALE_PATTERNS):
        return None
    # Past-tense / closure context is not a stale-status claim.
    if D2_0004_OK_RE.search(line):
        return None
    status = truth["d2_status"]
    return Finding(
        check=CHECK_STALE_D2_0004,
        path=rel,
        line=lineno,
        message=(
            "D2-0004 described as open/in-progress, but d2-latest-status.json "
            f"records candidate_id={status.get('candidate_id')} "
            f"decision={status.get('decision')} (closed)"
        ),
        excerpt=line.strip(),
    )


def _check_stale_d2_0005_armed(rel: str, lineno: int, line: str, truth: dict) -> Finding | None:
    if _d2_0005_armed(truth):
        return None
    if "D2-0005" not in line:
        return None
    if not D2_0005_ARMED_RE.search(line):
        return None
    if D2_0005_NEGATION_RE.search(line):
        return None
    return Finding(
        check=CHECK_STALE_D2_0005_ARMED,
        path=rel,
        line=lineno,
        message=(
            "D2-0005 described as armed, but generations/RAC-PER-D2-0005.json "
            "lock_status=PREREGISTERED and docs/D2-0005_FREEZE_CANDIDATE.json "
            "arming.armed=false"
        ),
        excerpt=line.strip(),
    )


def _iter_repo_paths(text: str) -> Iterable[str]:
    for m in MARKDOWN_LINK_RE.finditer(text):
        target = m.group("target")
        if re.match(r"^[a-zA-Z]+://|^mailto:", target):
            continue
        yield target
    for m in BACKTICK_RE.finditer(text):
        token = m.group("target").strip()
        if not token.startswith(PATH_PREFIXES):
            continue
        if any(c in token for c in "*{}$<>| "):
            continue
        yield token


def _check_broken_paths(root: Path, doc: Path, rel: str, text: str) -> list[Finding]:
    findings: list[Finding] = []
    line_starts = [0]
    for m in re.finditer(r"\n", text):
        line_starts.append(m.end())

    def lineno_of(pos: int) -> int:
        lo, hi = 0, len(line_starts) - 1
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if line_starts[mid] <= pos:
                lo = mid
            else:
                hi = mid - 1
        return lo + 1

    for m in MARKDOWN_LINK_RE.finditer(text):
        target = m.group("target")
        if re.match(r"^[a-zA-Z]+://|^mailto:", target):
            continue
        resolved = (doc.parent / target).resolve()
        try:
            resolved.relative_to(root.resolve())
        except ValueError:
            findings.append(Finding(
                check=CHECK_BROKEN_PATH, path=rel, line=lineno_of(m.start()),
                message=f"markdown link escapes repository: {target}",
                excerpt=target,
            ))
            continue
        if not resolved.exists():
            findings.append(Finding(
                check=CHECK_BROKEN_PATH, path=rel, line=lineno_of(m.start()),
                message=f"broken relative link: {target}",
                excerpt=target,
            ))
    for m in BACKTICK_RE.finditer(text):
        token = m.group("target").strip()
        if not token.startswith(PATH_PREFIXES):
            continue
        if any(c in token for c in "*{}$<>| "):
            continue
        # Strip anchor, symbol (::name), and line-number (:NN) suffixes.
        candidate = token.split("#")[0].split("::")[0]
        candidate = re.sub(r":\d+$", "", candidate)
        if not (root / candidate).exists():
            findings.append(Finding(
                check=CHECK_BROKEN_PATH, path=rel, line=lineno_of(m.start()),
                message=f"backticked repo path does not exist: {token}",
                excerpt=token,
            ))
    return findings


def _check_schema_drift(rel: str, lineno: int, line: str, truth: dict) -> Finding | None:
    contract = truth.get("manifest_contract")
    if not contract:
        return None
    accepted = str(contract.get("accepted_schema_version"))
    lowered = line.lower()
    if "product studio" not in lowered and "product-studio" not in lowered and "production manifest" not in lowered:
        return None
    if "schema" not in lowered and "version" not in lowered and "manifest" not in lowered:
        return None
    versions = PRODUCT_STUDIO_VERSION_RE.findall(line)
    if not versions:
        return None
    if accepted in versions:
        return None
    return Finding(
        check=CHECK_SCHEMA_DRIFT,
        path=rel,
        line=lineno,
        message=(
            f"Product Studio manifest schema version(s) {versions} conflict with "
            f"accepted_schema_version={accepted} in "
            "schemas/product_studio_manifest.contract.json"
        ),
        excerpt=line.strip(),
    )


def _check_stale_ci_run(rel: str, lineno: int, line: str) -> Finding | None:
    m = CI_RUN_RE.search(line)
    if not m:
        return None
    # Strip backticked spans (e.g. `d2-latest-status.json`) so filenames do
    # not trip the "latest"/"current" detector.
    stripped = re.sub(r"`[^`]*`", "", line)
    if not CI_CURRENT_RE.search(stripped):
        return None
    return Finding(
        check=CHECK_STALE_CI_RUN,
        path=rel,
        line=lineno,
        message=(
            f"CI run {m.group('num')} presented as current/in-progress; "
            "verify against live CI or mark as history"
        ),
        excerpt=line.strip(),
    )


def _check_quant_claim(rel: str, lineno: int, line: str, truth: dict) -> Finding | None:
    lowered = line.lower()
    if "held-out" not in lowered and "heldout" not in lowered:
        return None
    if "detection" not in lowered and "mean" not in lowered:
        return None
    known = _known_quantities(truth)
    if not known:
        return None
    # Only numbers appearing after the first "held-out" mention are candidate
    # claims, and only rate-like values in [0, 1] are checked (version numbers,
    # thresholds > 1, z-scores, etc. are out of scope).
    first = re.search(r"held-?out", lowered)
    assert first is not None
    bad: list[str] = []
    for m in NUMBER_RE.finditer(line, pos=first.end()):
        token = m.group("num")
        value = float(token)
        if not (0.0 <= value <= 1.0):
            continue
        decimals = len(token.split(".")[1])
        if _matches_known(value, decimals, known) is None:
            bad.append(token)
    if not bad:
        return None
    return Finding(
        check=CHECK_QUANT_CLAIM,
        path=rel,
        line=lineno,
        message=(
            f"held-out quantitative value(s) {bad} do not match any quantity in "
            "d2-latest-status.json heldout block"
        ),
        excerpt=line.strip(),
    )


def lint_repo(root: Path | str) -> LintResult:
    root = Path(root)
    truth = _truth(root)
    allow_entries = _load_allowlist(root)
    result = LintResult()

    for doc in _doc_files(root):
        rel = doc.relative_to(root).as_posix()
        result.scanned_files.append(rel)
        text = doc.read_text(encoding="utf-8")
        inline_checks = _inline_allows(text)

        file_findings: list[Finding] = []
        for lineno, line in enumerate(text.splitlines(), start=1):
            for finding in (
                _check_stale_d2_0004(root, rel, lineno, line, truth),
                _check_stale_d2_0005_armed(rel, lineno, line, truth),
                _check_schema_drift(rel, lineno, line, truth),
                _check_stale_ci_run(rel, lineno, line),
                _check_quant_claim(rel, lineno, line, truth),
            ):
                if finding is not None:
                    file_findings.append(finding)
        file_findings.extend(_check_broken_paths(root, doc, rel, text))

        for finding in file_findings:
            if "*" in inline_checks or finding.check in inline_checks:
                result.allowed.append(finding)
            elif any(entry.covers(finding) for entry in allow_entries):
                result.allowed.append(finding)
            else:
                result.findings.append(finding)
    return result


def format_summary(result: LintResult) -> str:
    lines = [
        f"doclint: scanned {len(result.scanned_files)} files; "
        f"{len(result.findings)} finding(s), {len(result.allowed)} allowlisted.",
    ]
    for f in result.findings:
        lines.append(f"  [{f.check}] {f.path}:{f.line}: {f.message}")
    if result.ok:
        lines.append("doclint: OK")
    else:
        lines.append("doclint: FAIL")
    return "\n".join(lines)
