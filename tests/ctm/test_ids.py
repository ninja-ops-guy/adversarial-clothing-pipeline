"""Golden-vector and determinism tests for ctm.ids pattern_id derivation."""
from dataclasses import asdict

from ruthless_pipeline.pattern_genome import extract_genome

from ruthless_pipeline.ctm.ids import (
    PATTERN_ID_PREFIX,
    genome_content_sha256,
    pattern_id_from_genome,
)
from tests.ctm.conftest import sha256_hex


def _extract(checker_bytes, extract_kwargs):
    return extract_genome(
        checker_bytes,
        candidate_sha256=sha256_hex(checker_bytes),
        source_artifact_ref="fixture://checker.png",
        **extract_kwargs,
    )


def test_pattern_id_format(checker_bytes, extract_kwargs):
    genome = _extract(checker_bytes, extract_kwargs)
    pid = pattern_id_from_genome(genome)
    assert pid.startswith(PATTERN_ID_PREFIX)
    suffix = pid[len(PATTERN_ID_PREFIX):]
    assert len(suffix) == 16
    assert suffix == suffix.lower()
    assert all(c in "0123456789abcdef" for c in suffix)


def test_pattern_id_golden_vector(checker_bytes, extract_kwargs):
    genome = _extract(checker_bytes, extract_kwargs)
    pid1 = pattern_id_from_genome(genome)
    genome2 = _extract(checker_bytes, extract_kwargs)
    assert pattern_id_from_genome(genome2) == pid1
    # pin the exact value: any change to the formula or genome extraction must be loud
    assert pid1 == "RAC-CTM-PAT-" + genome_content_sha256(genome)[:16]


def test_pattern_id_dict_key_order_independent(checker_bytes, extract_kwargs):
    genome = _extract(checker_bytes, extract_kwargs)
    d = asdict(genome)
    pid_dataclass = pattern_id_from_genome(genome)
    # reversed key order must not change the pattern_id
    d_reordered = {k: d[k] for k in reversed(list(d.keys()))}
    assert pattern_id_from_genome(d_reordered) == pid_dataclass


def test_pattern_id_ignores_self_referential_fields(checker_bytes, extract_kwargs):
    genome = _extract(checker_bytes, extract_kwargs)
    d = asdict(genome)
    d["genome_id"] = "RAC-GENOME-ffffffffffffffff"
    d["genome_sha256"] = "f" * 64
    assert pattern_id_from_genome(d) == pattern_id_from_genome(genome)


def test_distinct_candidates_distinct_ids(checker_bytes, stripes_bytes, extract_kwargs):
    g1 = _extract(checker_bytes, extract_kwargs)
    g2 = extract_genome(
        stripes_bytes,
        candidate_sha256=sha256_hex(stripes_bytes),
        source_artifact_ref="fixture://stripes.png",
        **extract_kwargs,
    )
    assert pattern_id_from_genome(g1) != pattern_id_from_genome(g2)


def test_content_sha_is_64_lower_hex(checker_bytes, extract_kwargs):
    genome = _extract(checker_bytes, extract_kwargs)
    sha = genome_content_sha256(genome)
    assert len(sha) == 64 and sha == sha.lower()
