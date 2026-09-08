"""Every mitigation cited in the threat model must be real.

Parses backticked repo-relative paths out of
docs/THREAT_MODEL_RESEARCH_PIPELINE.md and asserts each exists, so the doc
cannot cite a mitigation that isn't in the tree. Also spot-checks the two
load-bearing pins/constants the doc relies on.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs" / "THREAT_MODEL_RESEARCH_PIPELINE.md"

PATH_PREFIXES = (
    "docs/", "scripts/", "ruthless_pipeline/", "tests/", "schemas/",
    "generations/", "manuscript/", "benchmarks/", "releases/", "protocols/",
    "model_sets/", "model_manifests/", "registry/", "artifacts/",
    "production_alpha/", ".github/",
)


def _cited_paths() -> list[str]:
    text = DOC.read_text(encoding="utf-8")
    paths: list[str] = []
    for token in re.findall(r"`([^`\n]+)`", text):
        token = token.strip()
        if not token.startswith(PATH_PREFIXES):
            continue
        if any(c in token for c in "*{}$<>| "):
            continue
        candidate = token.split("#")[0].split("::")[0]
        candidate = re.sub(r":\d+$", "", candidate)
        paths.append(candidate)
    return paths


def test_threat_model_exists():
    assert DOC.is_file()


def test_all_cited_paths_exist():
    cited = _cited_paths()
    assert len(cited) >= 20, f"suspiciously few citations parsed: {cited}"
    missing = [p for p in cited if not (ROOT / p).exists()]
    assert not missing, f"threat model cites non-existent paths: {missing}"


def test_cited_freeze_candidate_pin_format():
    data = json.loads(
        (ROOT / "docs" / "D2-0005_FREEZE_CANDIDATE.json").read_text()
    )
    assert data["arming"]["armed"] is False
    pins = data["governing_documents"]
    for name, entry in pins.items():
        assert re.fullmatch(r"[0-9a-f]{64}", entry["sha256"]), name
        assert (ROOT / entry["path"]).is_file(), entry["path"]


def test_cited_evidence_labels_exist():
    from ruthless_pipeline.certification.experiment import EVIDENCE_LABELS

    assert "internally_measured" in EVIDENCE_LABELS
    assert "speculative_open" in EVIDENCE_LABELS


def test_cited_surrogate_only_boundary():
    src = (ROOT / "scripts" / "select_surrogate_candidate.py").read_text()
    assert "heldout_models=()" in src
