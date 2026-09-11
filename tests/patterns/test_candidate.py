"""Candidate-artifact contract tests for to_candidate()."""
import re

import pytest

from ruthless_pipeline.patterns import GeneratorParams, HyperfaceLikeGenerator
from ruthless_pipeline.patterns.base import GeneratedPattern

from .conftest import make_mask

REQUIRED_FIELDS = {
    "candidate_id",
    "pattern_sha256",
    "generator",
    "generator_version",
    "provenance_hash",
    "params",
    "evidence_class",
    "physical_efficacy_claimed",
    "claim_state",
}


def _pattern(seed=42):
    gen = HyperfaceLikeGenerator()
    return gen.generate(GeneratorParams(seed=seed, mask_geometry=make_mask(),
                                        output_size=(96, 96)))


def test_candidate_schema_fields():
    cand = _pattern().to_candidate()
    assert REQUIRED_FIELDS <= set(cand)
    assert cand["evidence_class"] == "digital_candidate"
    assert cand["claim_state"] == "EXPLORATORY"
    assert re.fullmatch(r"[0-9a-f]{64}", cand["pattern_sha256"])
    assert re.fullmatch(r"[0-9a-f]{64}", cand["provenance_hash"])


def test_candidate_never_claims_physical_efficacy():
    assert _pattern().to_candidate()["physical_efficacy_claimed"] is False


def test_candidate_id_deterministic():
    a = _pattern(seed=42).to_candidate()
    b = _pattern(seed=42).to_candidate()
    c = _pattern(seed=43).to_candidate()
    assert a["candidate_id"] == b["candidate_id"]
    assert a["candidate_id"].startswith("RAC-PAT-CAND-")
    assert a["candidate_id"] != c["candidate_id"]
