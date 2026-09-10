"""Tests for SPEC-10 camera/ISP channel semantics (lane B)."""
from __future__ import annotations

import pytest

from ruthless_pipeline.ctm.channel import (
    CHANNEL_CLASSES,
    CHANNEL_SCHEMA_VERSION,
    ChannelRecord,
    ChannelSemanticsError,
    claim_ceiling,
    derive_replicated_channel_class,
    require_digital_claim_eligible,
    require_physical_replicated_eligible,
    require_strong_physical_eligible,
)


def _physical_unknown(**overrides):
    kwargs = dict(channel_id="phys-unknown-1", tier="physical")
    kwargs.update(overrides)
    return ChannelRecord(**kwargs)


def _physical_identified(**overrides):
    kwargs = dict(
        channel_id="phys-camA-1",
        tier="physical",
        camera_model="sony-imx500",
        isp_pipeline_id="sony-imx500-default-v3",
        raw_available="yes",
        codec_format="h264",
        codec_bitrate_class="high",
        demosaic="vendor-a",
        denoise="temporal-strong",
        tone_map="s-curve-v2",
    )
    kwargs.update(overrides)
    return ChannelRecord(**kwargs)


def _digital_two_proxies(**overrides):
    kwargs = dict(
        channel_id="dig-1",
        tier="digital",
        isp_proxy_refs=("isp-proxy-phan2021", "isp-proxy-cap2024"),
    )
    kwargs.update(overrides)
    return ChannelRecord(**kwargs)


# -- positive / derivation ----------------------------------------------------

def test_physical_identified_is_channel_b():
    rec = _physical_identified()
    assert rec.camera_identified is True
    assert rec.channel_class == "CHANNEL-B"
    assert claim_ceiling(rec) == "PHYSICAL_SINGLE_CHANNEL"


def test_digital_two_proxies_is_channel_b():
    rec = _digital_two_proxies()
    assert rec.channel_class == "CHANNEL-B"
    assert claim_ceiling(rec) == "DIGITAL_REPLICATED"
    require_digital_claim_eligible(rec)


def test_schema_validation_roundtrip():
    for rec in (_physical_unknown(), _physical_identified(), _digital_two_proxies()):
        rec.validate_against_schema()
        assert ChannelRecord.from_dict(rec.to_dict()).canonical_bytes() == rec.canonical_bytes()


def test_serialization_is_deterministic():
    a = _digital_two_proxies()
    b = _digital_two_proxies(isp_proxy_refs=tuple(reversed(a.isp_proxy_refs)))
    assert a.canonical_bytes() == b.canonical_bytes()
    assert a.channel_sha256() == b.channel_sha256()


def test_unknowns_serialize_explicitly():
    d = _physical_unknown().to_dict()
    assert d["camera_model"] == "unknown"
    assert d["isp_pipeline_id"] == "unknown"
    assert d["codec"] == {"format": "unknown", "bitrate_class": "unknown"}
    assert d["isp_descriptors"]["denoise"] == "unknown"


# -- rule (a): missing camera identity => CHANNEL-C / observational -----------

def test_unknown_camera_identity_is_channel_c_observational():
    rec = _physical_unknown()
    assert rec.camera_identified is False
    assert rec.channel_class == "CHANNEL-C"
    assert claim_ceiling(rec) == "OBSERVATIONAL"


def test_inferred_camera_identity_is_not_identified():
    rec = _physical_unknown(camera_model="inferred", isp_pipeline_id="inferred")
    assert rec.camera_identified is False
    assert rec.channel_class == "CHANNEL-C"
    assert claim_ceiling(rec) == "OBSERVATIONAL"


def test_partial_camera_identity_is_not_identified():
    rec = _physical_unknown(camera_model="sony-imx500")
    assert rec.camera_identified is False
    assert claim_ceiling(rec) == "OBSERVATIONAL"


def test_strong_physical_refused_without_camera_identity():
    with pytest.raises(ChannelSemanticsError):
        require_strong_physical_eligible(_physical_unknown())


def test_strong_physical_allowed_with_camera_identity():
    require_strong_physical_eligible(_physical_identified())


# -- rule (b): digital claims need >= 2 distinct ISP-proxy variants ------------

def test_digital_single_proxy_fails_closed():
    rec = _digital_two_proxies(isp_proxy_refs=("isp-proxy-phan2021",))
    assert rec.channel_class == "CHANNEL-C"
    assert claim_ceiling(rec) == "OBSERVATIONAL"
    with pytest.raises(ChannelSemanticsError):
        require_digital_claim_eligible(rec)


def test_digital_duplicate_proxies_do_not_count():
    with pytest.raises(ChannelSemanticsError):
        _digital_two_proxies(
            isp_proxy_refs=("isp-proxy-phan2021", "isp-proxy-phan2021")
        )


def test_digital_without_any_proxy_refused_at_construction():
    with pytest.raises(ChannelSemanticsError):
        ChannelRecord(channel_id="dig-bad", tier="digital")


def test_digital_claim_refused_for_physical_tier():
    with pytest.raises(ChannelSemanticsError):
        require_digital_claim_eligible(_physical_identified())


# -- rule (c): cross-camera replication precondition ---------------------------

def test_physical_replicated_requires_two_distinct_cameras():
    cam_a = _physical_identified()
    cam_b = _physical_identified(
        channel_id="phys-camB-1",
        camera_model="ov5640",
        isp_pipeline_id="ov5640-tuning-v1",
    )
    require_physical_replicated_eligible([cam_a, cam_b])
    assert derive_replicated_channel_class([cam_a, cam_b]) == "CHANNEL-A"


def test_physical_replicated_refused_for_same_camera_twice():
    cam_a = _physical_identified()
    cam_a2 = _physical_identified(channel_id="phys-camA-2")
    with pytest.raises(ChannelSemanticsError):
        require_physical_replicated_eligible([cam_a, cam_a2])


def test_physical_replicated_refused_when_any_record_unidentified():
    cam_a = _physical_identified()
    unknown = _physical_unknown()
    with pytest.raises(ChannelSemanticsError):
        require_physical_replicated_eligible([cam_a, unknown])
    # Replication set downgrades to the weakest member (CHANNEL-C), never A.
    assert derive_replicated_channel_class([cam_a, unknown]) == "CHANNEL-C"


def test_physical_replicated_refused_for_empty_set():
    with pytest.raises(ChannelSemanticsError):
        require_physical_replicated_eligible([])
    with pytest.raises(ChannelSemanticsError):
        derive_replicated_channel_class([])


# -- fail-closed validation -----------------------------------------------------

def test_bad_tier_fails_closed():
    with pytest.raises(ChannelSemanticsError):
        ChannelRecord(channel_id="x", tier="analog")


def test_bad_schema_version_fails_closed():
    with pytest.raises(ChannelSemanticsError):
        _physical_unknown(schema_version="rac-ctm-channel/0.9")


def test_bad_raw_available_fails_closed():
    with pytest.raises(ChannelSemanticsError):
        _physical_unknown(raw_available="maybe")


def test_user_asserted_channel_class_disagreeing_fails_closed():
    d = _physical_unknown().to_dict()
    d["channel_class"] = "CHANNEL-A"  # cannot self-promote
    with pytest.raises(ChannelSemanticsError):
        ChannelRecord.from_dict(d)


def test_user_asserted_camera_identified_disagreeing_fails_closed():
    d = _physical_unknown().to_dict()
    d["camera_identified"] = True
    with pytest.raises(ChannelSemanticsError):
        ChannelRecord.from_dict(d)


def test_channel_class_enum():
    assert CHANNEL_CLASSES == frozenset({"CHANNEL-A", "CHANNEL-B", "CHANNEL-C"})
    assert CHANNEL_SCHEMA_VERSION == "rac-ctm-channel/1.0"
