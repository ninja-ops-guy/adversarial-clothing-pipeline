"""Tests for ctm.compare."""
import pytest

from ruthless_pipeline.pattern_genome import extract_genome

from ruthless_pipeline.ctm.compare import CLAIM_STATE, compare_genomes
from ruthless_pipeline.ctm.errors import ComparisonError
from tests.ctm.conftest import sha256_hex


def _genome(data, label, extract_kwargs):
    return extract_genome(
        data,
        candidate_sha256=sha256_hex(data),
        source_artifact_ref=label,
        **extract_kwargs,
    )


def test_identical_when_same(checker_bytes, extract_kwargs):
    g = _genome(checker_bytes, "fixture://checker.png", extract_kwargs)
    report = compare_genomes(g, g)
    assert report.identical is True
    assert report.overall_distance == 0.0
    for fam in ("spectral", "topology", "color", "geometry"):
        assert report.families[fam]["l2"] == 0.0
        assert report.families[fam]["feature_count"] > 0


def test_distance_positive_when_different(checker_bytes, stripes_bytes, extract_kwargs):
    g1 = _genome(checker_bytes, "fixture://checker.png", extract_kwargs)
    g2 = _genome(stripes_bytes, "fixture://stripes.png", extract_kwargs)
    report = compare_genomes(g1, g2)
    assert report.identical is False
    assert report.overall_distance > 0.0


def test_determinism(checker_bytes, stripes_bytes, extract_kwargs):
    g1 = _genome(checker_bytes, "fixture://checker.png", extract_kwargs)
    g2 = _genome(stripes_bytes, "fixture://stripes.png", extract_kwargs)
    r1 = compare_genomes(g1, g2)
    r2 = compare_genomes(g2, g1)
    r3 = compare_genomes(g1, g2)
    assert r1.to_dict() == r3.to_dict()
    # metrics are symmetric
    assert r1.overall_distance == pytest.approx(r2.overall_distance)


def test_claim_state_hard_exploratory(checker_bytes, extract_kwargs):
    g = _genome(checker_bytes, "fixture://checker.png", extract_kwargs)
    report = compare_genomes(g, g, evidence_tier="SYNTHETIC")
    assert report.claim_state == "EXPLORATORY"
    assert report.claim_state == CLAIM_STATE
    assert report.physical_efficacy_claimed is False
    assert report.evidence_tier == "SYNTHETIC"


def test_evidence_tier_default_and_validation(checker_bytes, extract_kwargs):
    g = _genome(checker_bytes, "fixture://checker.png", extract_kwargs)
    assert compare_genomes(g, g).evidence_tier == "DIGITAL"
    with pytest.raises(ComparisonError):
        compare_genomes(g, g, evidence_tier="PHYSICAL")


def test_dict_input_accepted(checker_bytes, extract_kwargs):
    from dataclasses import asdict
    g = _genome(checker_bytes, "fixture://checker.png", extract_kwargs)
    report = compare_genomes(asdict(g), g)
    assert report.identical is True


def test_missing_family_fails_closed(checker_bytes, extract_kwargs):
    g = _genome(checker_bytes, "fixture://checker.png", extract_kwargs)
    bad = {"spectral": {}}
    with pytest.raises(ComparisonError):
        compare_genomes(g, bad)
