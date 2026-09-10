"""Tests for SPEC-6 citation verification status (lane C)."""
from __future__ import annotations

import pytest

from ruthless_pipeline.ctm.citations import (
    CITATION_SCHEMA_VERSION,
    Citation,
    CitationError,
    CitationVerificationError,
    check_claim_export,
    export_claim_artifact,
)


def _citation(**overrides):
    kwargs = dict(
        citation_id="cit-1",
        claim_id="claim-1",
        target_ref="RAC-CTM-LIT-016a7dad0898de17",
        verification_status="full_text_verified",
        load_bearing=True,
        load_bearing_reason="Claim would need rewording if Voronoi were removed.",
    )
    kwargs.update(overrides)
    return Citation(**kwargs)


# -- positive ----------------------------------------------------------------

def test_citation_roundtrip_schema_and_determinism():
    cit = _citation()
    cit.validate_against_schema()
    assert Citation.from_dict(cit.to_dict()) == cit
    assert cit.citation_sha256() == _citation().citation_sha256()


def test_export_with_full_text_verified_load_bearing():
    artifact = export_claim_artifact("claim-1", "Bounded claim.", [_citation()])
    assert artifact["citations"][0]["verification_status"] == "full_text_verified"
    assert len(artifact["citation_matrix_sha256"]) == 64


def test_export_with_reproduced_internally_load_bearing():
    artifact = export_claim_artifact(
        "claim-1", "Bounded claim.", [_citation(verification_status="reproduced_internally")]
    )
    assert artifact["citations"]


def test_non_load_bearing_abstract_only_exports_with_label():
    cit = _citation(load_bearing=False, load_bearing_reason="",
                    verification_status="abstract_only")
    artifact = export_claim_artifact("claim-1", "Contextual mention.", [cit])
    # the label travels with the citation
    assert artifact["citations"][0]["verification_status"] == "abstract_only"


# -- negative / fail-closed ---------------------------------------------------

def test_load_bearing_abstract_only_export_refused():
    cit = _citation(verification_status="abstract_only")
    with pytest.raises(CitationVerificationError):
        export_claim_artifact("claim-1", "Overclaimed.", [cit])
    with pytest.raises(CitationVerificationError):
        check_claim_export([cit], claim_id="claim-1")


def test_load_bearing_requires_reason():
    with pytest.raises(CitationError):
        _citation(load_bearing_reason="")


def test_reason_without_load_bearing_refused():
    with pytest.raises(CitationError):
        _citation(load_bearing=False, load_bearing_reason="implied")


def test_unknown_status_fails_closed():
    with pytest.raises(CitationError):
        _citation(verification_status="peer_reviewed")


def test_claim_id_mismatch_fails_closed():
    cit = _citation(claim_id="claim-2")
    with pytest.raises(CitationError):
        check_claim_export([cit], claim_id="claim-1")


def test_version_string():
    assert CITATION_SCHEMA_VERSION == "rac-ctm-citation/1.0"
