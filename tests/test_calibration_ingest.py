from __future__ import annotations

import json

import pytest

from ruthless_pipeline.certification.calibration_ingest import (
    PatchMeasurement,
    PrintCameraProfile,
    RegistrationMeasurement,
    ResolutionMeasurement,
    ScaleMeasurement,
    delta_e_2000,
)


def test_ciede2000_sharma_reference_pair():
    lab1 = (50.0, 2.6772, -79.7751)
    lab2 = (50.0, 0.0, -82.7485)
    assert delta_e_2000(lab1, lab2) == pytest.approx(2.0425, abs=1e-3)


def test_ciede2000_identical_colors_zero():
    lab = (60.0, 20.0, -30.0)
    assert delta_e_2000(lab, lab) == pytest.approx(0.0, abs=1e-12)


def test_ciede2000_symmetry():
    lab1 = (50.0, 2.5, 0.0)
    lab2 = (73.0, 25.0, -18.0)
    assert delta_e_2000(lab1, lab2) == pytest.approx(delta_e_2000(lab2, lab1), abs=1e-9)


def test_scale_px_per_cm():
    s = ScaleMeasurement(ruler_id="R50", nominal_cm=50.0, measured_px=2450.0, distance_m=2.0)
    assert s.px_per_cm == pytest.approx(49.0)


def test_scale_validation_rejects_nonpositive():
    with pytest.raises(ValueError):
        ScaleMeasurement(ruler_id="R50", nominal_cm=0.0, measured_px=100.0, distance_m=2.0).validate()
    with pytest.raises(ValueError):
        ScaleMeasurement(ruler_id="R50", nominal_cm=50.0, measured_px=-1.0, distance_m=2.0).validate()


def test_resolution_cutoff():
    r = ResolutionMeasurement(
        lp_mm_steps=[(0.5, 0.8), (1.0, 0.6), (2.0, 0.25), (3.0, 0.10), (4.0, 0.05)]
    )
    assert r.cutoff() == pytest.approx(2.0)
    assert r.cutoff(contrast_threshold=0.65) == pytest.approx(0.5)
    assert r.cutoff(contrast_threshold=0.99) == 0.0


def _profile(**overrides) -> PrintCameraProfile:
    kwargs = dict(
        profile_id="RAC-PCP-1.0.0-001",
        camera_id="CAM-PHONE-MAIN-01",
        lighting_id="LIGHT-D65-01",
        created_utc="2025-01-01T00:00:00Z",
        patches=[
            PatchMeasurement("P01", (50.0, 0.0, 0.0), (51.0, 0.5, -0.5)),
            PatchMeasurement("P02", (60.0, 20.0, -30.0), (61.0, 20.5, -30.5)),
        ],
        scales=[
            ScaleMeasurement("R50", 50.0, 2450.0, 2.0),
            ScaleMeasurement("R20", 20.0, 984.0, 2.0),
        ],
        resolutions=[
            ResolutionMeasurement([(0.5, 0.8), (1.0, 0.5), (2.0, 0.1)]),
        ],
        registrations=[
            RegistrationMeasurement("TL", (0.0, 0.0), (1.0, 0.0)),
            RegistrationMeasurement("BR", (800.0, 500.0), (800.0, 501.5)),
        ],
    )
    kwargs.update(overrides)
    return PrintCameraProfile(**kwargs)


def test_profile_hash_stability():
    p1 = _profile()
    p2 = _profile()
    assert p1.to_profile_json() == p2.to_profile_json()
    assert p1.profile_sha256() == p2.profile_sha256()
    assert len(p1.profile_sha256()) == 64
    # canonical JSON: sorted keys at top level
    assert list(json.loads(p1.to_profile_json()).keys()) == sorted(
        json.loads(p1.to_profile_json()).keys()
    )


def test_acceptance_pass():
    ok, failures = _profile().acceptance()
    assert ok
    assert failures == []


def test_acceptance_fail_color():
    bad_patch = PatchMeasurement("PBAD", (50.0, 0.0, 0.0), (80.0, 40.0, 40.0))
    ok, failures = _profile(patches=[bad_patch]).acceptance()
    assert not ok
    assert any("mean_delta_e" in f for f in failures)


def test_acceptance_fail_registration():
    bad_reg = RegistrationMeasurement("TL", (0.0, 0.0), (4.0, 0.0))
    ok, failures = _profile(registrations=[bad_reg]).acceptance()
    assert not ok
    assert any("registration" in f for f in failures)


def test_validate_rejections():
    with pytest.raises(ValueError):
        _profile(patches=[]).validate()
    with pytest.raises(ValueError):
        _profile(profile_id="BAD-ID").validate()
    with pytest.raises(ValueError):
        PatchMeasurement("P01", (150.0, 0.0, 0.0), (50.0, 0.0, 0.0)).validate()
    with pytest.raises(ValueError):
        PatchMeasurement("P01", (float("nan"), 0.0, 0.0), (50.0, 0.0, 0.0)).validate()


def test_summary_contents():
    summary = _profile().summary()
    assert summary["n_patches"] == 2
    assert summary["mean_delta_e"] > 0.0
    assert summary["max_delta_e"] >= summary["mean_delta_e"]
    assert summary["resolution_cutoff_lp_mm"] == [1.0]
    assert summary["max_registration_error_mm"] == pytest.approx(1.5)
    assert set(summary["scale_error_pct"]) == {"R50@2.0m", "R20@2.0m"}
