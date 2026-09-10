"""Tests for SPEC-18 positioning block (lane C)."""
from __future__ import annotations

import pytest

from ruthless_pipeline.ctm.corpus import CorpusError, seed_registry
from ruthless_pipeline.ctm.positioning import (
    POSITIONING_SCHEMA_VERSION,
    Positioning,
    PositioningError,
    check_narrative,
    require_narrative_conformant,
    serialize_positioning,
)


@pytest.fixture()
def seeded(tmp_path):
    snapshot = seed_registry(registry_dir=tmp_path)
    return tmp_path, snapshot.snapshot_sha256()


def _positioning(snapshot_sha: str, **overrides):
    kwargs = dict(comparison_snapshot_ref=snapshot_sha)
    kwargs.update(overrides)
    return Positioning(**kwargs)


# -- positive ----------------------------------------------------------------

def test_defaults_are_ctm_positioning(seeded):
    _, sha = seeded
    p = _positioning(sha)
    assert p.primary_axis == "measurement_infrastructure"
    assert set(p.disclaimed_axes) == {
        "attack_superiority", "policy_impact", "consumer_usability",
    }
    p.validate_against_schema()
    assert Positioning.from_dict(p.to_dict()).to_dict() == p.to_dict()
    assert p.positioning_sha256() == _positioning(sha).positioning_sha256()


def test_serialize_resolves_comparison_set_from_snapshot(seeded):
    tmp_path, sha = seeded
    out = serialize_positioning(_positioning(sha), registry_dir=tmp_path)
    assert out["comparison_snapshot_id"].startswith("RAC-CTM-CORPUS-SNAPSHOT-")
    assert len(out["comparison_set"]) == 10
    # comparison entries are resolved from the pinned snapshot, not handwritten
    assert all(len(r["entry_sha256"]) == 64 for r in out["comparison_set"])


def test_conformant_narrative_passes(seeded):
    _, sha = seeded
    p = _positioning(sha)
    require_narrative_conformant(
        "CTM contributes measurement infrastructure for the field.", p
    )


def test_amended_axis_allows_narrative(seeded):
    _, sha = seeded
    p = _positioning(
        sha,
        amendments=(
            "Amendment: we additionally compare on attack_superiority "
            "against Zhang et al. 2025 within the pinned snapshot.",
        ),
    )
    require_narrative_conformant(
        "Our garment outperforms existing attacks in the pinned comparison set.", p
    )


# -- negative / fail-closed ---------------------------------------------------

def test_absent_positioning_refused(seeded):
    tmp_path, _ = seeded
    with pytest.raises(PositioningError):
        serialize_positioning(None, registry_dir=tmp_path)


def test_unverified_snapshot_ref_refused(seeded):
    tmp_path, _ = seeded
    p = _positioning("b" * 64)  # well-formed but not in the registry
    with pytest.raises(CorpusError):
        serialize_positioning(p, registry_dir=tmp_path)


def test_malformed_snapshot_ref_fails_at_construction():
    with pytest.raises(PositioningError):
        _positioning("not-a-sha")


def test_primary_axis_cannot_be_disclaimed(seeded):
    _, sha = seeded
    with pytest.raises(PositioningError):
        _positioning(sha, disclaimed_axes=("measurement_infrastructure",))


def test_unknown_axis_fails(seeded):
    _, sha = seeded
    with pytest.raises(PositioningError):
        _positioning(sha, primary_axis="hype")


def test_narrative_implying_disclaimed_axis_refused(seeded):
    _, sha = seeded
    p = _positioning(sha)
    violations = check_narrative(
        "We present the strongest attack on surveillance pipelines to date.", p
    )
    assert violations
    with pytest.raises(PositioningError):
        require_narrative_conformant(
            "We present the strongest attack on surveillance pipelines to date.", p
        )


def test_version_string():
    assert POSITIONING_SCHEMA_VERSION == "rac-ctm-positioning/1.0"
