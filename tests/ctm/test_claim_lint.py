"""Tests for SPEC-3 corpus-bounded universal-negative lint (lane C)."""
from __future__ import annotations

import pytest

from ruthless_pipeline.ctm.claim_lint import (
    CLAIM_LINT_RULESET_VERSION,
    ClaimLintError,
    lint_text,
    require_bounded,
)

SNAP = "RAC-CTM-CORPUS-SNAPSHOT-1fa6285372d1c434"


# -- positive ----------------------------------------------------------------

def test_bounded_negative_passes():
    text = (
        f"No prior work measures physical transfer, in a coded corpus of 20 "
        f"papers at corpus snapshot {SNAP}."
    )
    assert lint_text(text).ok
    require_bounded(text)


def test_bounded_first_claim_passes_with_qualifier_and_snapshot():
    text = (
        "This is the first factorial decomposition within the corpus covered "
        f"by registry snapshot {SNAP}."
    )
    assert lint_text(text).ok


def test_ordinary_positive_prose_passes():
    assert lint_text("The pattern reduced detection rate by 12%.").ok


def test_allowlist_with_reason_passes():
    sentence = "No paper has replicated this."
    result = lint_text(sentence, allowlist={sentence: "quote from cited source, kept verbatim"})
    assert result.ok
    assert len(result.allowlisted) == 1


# -- negative / fail-closed ---------------------------------------------------

@pytest.mark.parametrize("phrase", [
    "No prior work has measured physical transfer.",
    "No paper has done this.",
    "Nobody has measured it.",
    "Nothing exists for garments.",
    "This is the first factorial decomposition.",
    "Physical transfer has not been measured.",
    "No known attack survives fabrication.",
])
def test_bare_universal_negative_fails(phrase):
    result = lint_text(phrase)
    assert not result.ok
    assert result.violations[0].missing == (
        "corpus_scope_qualifier",
        "snapshot_ref",
    )
    with pytest.raises(ClaimLintError):
        require_bounded(phrase)


def test_qualifier_without_snapshot_ref_fails():
    text = "No paper has done this in a coded corpus of 20 papers."
    result = lint_text(text)
    assert not result.ok
    assert result.violations[0].missing == ("snapshot_ref",)


def test_snapshot_ref_without_qualifier_fails():
    text = f"Nobody has measured this; see snapshot {SNAP}."
    result = lint_text(text)
    assert not result.ok
    assert result.violations[0].missing == ("corpus_scope_qualifier",)


def test_allowlist_without_reason_does_not_allowlist():
    sentence = "No paper has replicated this."
    assert not lint_text(sentence, allowlist={sentence: ""}).ok
    assert not lint_text(sentence, allowlist={sentence: "   "}).ok


def test_scope_must_be_same_sentence():
    text = (
        "We coded a corpus of 20 papers. No paper has measured physical transfer."
    )
    assert not lint_text(text).ok


def test_ruleset_version_string():
    assert CLAIM_LINT_RULESET_VERSION == "rac-ctm-claim-lint/1.0"
