"""Tests for printability loss components."""

import numpy as np
import pytest

from ruthless_pipeline.physical_transfer.printability import (
    MEASUREMENT_UNAVAILABLE,
    PrintabilityInputError,
    printability_loss,
)


def full_profile():
    """Complete profile so every measurable component evaluates."""
    return {
        "profile_id": "test-vendor",
        "version": 1,
        "vendor": "test",
        "source": "vendor_spec",
        "created": "2026-01-01",
        "gamut": {"rgb_min": [0.05, 0.05, 0.05], "rgb_max": [0.95, 0.95, 0.95]},
        "min_feature_mm": 0.5,
        "dpi": 150,
        "mtf_cutoff_cycles_per_mm": 1.0,
        "panel": {
            "width_mm": 300.0,
            "height_mm": 300.0,
            "bleed_mm": 3.0,
            "safe_area_mm": 10.0,
        },
    }


def mid_gray_image(h=64, w=64):
    return np.full((h, w, 3), 0.5)


def test_gamut_distance_positive_for_out_of_gamut_pixel():
    img = mid_gray_image()
    img[0, 0] = [1.0, 1.0, 1.0]  # above rgb_max 0.95 -> out of gamut
    loss = printability_loss(img, full_profile())
    g = loss.components["gamut_distance"]
    assert g.status == "OK"
    assert g.value > 0
    assert g.detail["out_of_gamut_fraction"] > 0


def test_gamut_distance_zero_inside_gamut():
    loss = printability_loss(mid_gray_image(), full_profile())
    assert loss.components["gamut_distance"].value == 0.0


def test_tiny_feature_penalized():
    # Large smooth block passes; single-pixel dot violates min feature size.
    img = mid_gray_image(128, 128)
    img[64, 64] = 0.9  # 1-px feature
    loss = printability_loss(img, full_profile())
    m = loss.components["min_feature_size"]
    assert m.status == "OK"
    assert m.value > 0.5

    img2 = mid_gray_image(128, 128)
    img2[48:80, 48:80] = 0.9  # 32-px feature >> required px
    loss2 = printability_loss(img2, full_profile())
    assert loss2.components["min_feature_size"].value < m.value


def _blur(img, iters=8):
    out = img
    for _ in range(iters):
        out = (
            out
            + np.roll(out, 1, 0)
            + np.roll(out, -1, 0)
            + np.roll(out, 1, 1)
            + np.roll(out, -1, 1)
        ) / 5.0
    return out


def test_high_freq_survivability_increases_with_high_freq_and_decreases_with_blur():
    h = w = 128
    yy, xx = np.meshgrid(np.arange(h), np.arange(w), indexing="ij")
    hf = 0.5 + 0.4 * np.sin(2 * np.pi * xx / 2.0)  # near-Nyquist stripes
    hf_img = np.clip(np.stack([hf] * 3, axis=-1), 0, 1)
    smooth_img = _blur(hf_img)

    p = full_profile()
    val_hf = printability_loss(hf_img, p).components[
        "high_frequency_survivability"
    ].value
    val_blur = printability_loss(smooth_img, p).components[
        "high_frequency_survivability"
    ].value
    assert val_hf > 0.3
    assert val_blur < val_hf


def test_resolution_dpi_check_shortfall_penalized():
    p = full_profile()  # requires 150 dpi across 300mm -> 1772 px wide
    small = mid_gray_image(64, 64)  # ~5.4 dpi effective
    loss = printability_loss(small, p)
    r = loss.components["resolution_dpi_check"]
    assert r.status == "OK"
    assert r.value > 0.9


def test_bleed_safe_area_content_at_risk():
    p = full_profile()
    img = mid_gray_image(300, 300)
    img[2:6, 100:200] = 0.0  # content hugging the edge (inside bleed band)
    loss = printability_loss(img, p)
    b = loss.components["bleed_safe_area_check"]
    assert b.status == "OK"
    assert b.value > 0

    img2 = mid_gray_image(300, 300)
    img2[100:200, 100:200] = 0.0  # content well inside safe area
    assert printability_loss(img2, p).components["bleed_safe_area_check"].value == 0.0


def test_missing_measurements_partial_renormalization():
    p = full_profile()
    del p["gamut"]
    del p["mtf_cutoff_cycles_per_mm"]  # falls back to dpi-derived, still OK
    loss = printability_loss(mid_gray_image(), p)
    assert loss.partial is True
    assert loss.components["gamut_distance"].value is None
    assert loss.components["gamut_distance"].status == MEASUREMENT_UNAVAILABLE
    assert "gamut_distance" in loss.unavailable_components
    # total is a renormalized mean over available components only
    assert loss.value == pytest.approx(
        np.mean([loss.components[n].value for n in loss.available_components])
    )


def test_digital_to_camera_discrepancy_unavailable_without_measured_ref():
    loss = printability_loss(mid_gray_image(), full_profile())
    d = loss.components["digital_to_camera_discrepancy"]
    assert d.value is None
    assert d.status == MEASUREMENT_UNAVAILABLE


def test_digital_to_camera_discrepancy_with_measured_ref():
    p = full_profile()
    p["calibration_ref"] = {
        "status": "measured",
        "id": "cal-001",
        "reference_patch_rgb": [0.5, 0.5, 0.5],
        "measured_patch_rgb": [0.55, 0.5, 0.45],
    }
    loss = printability_loss(mid_gray_image(), p)
    d = loss.components["digital_to_camera_discrepancy"]
    assert d.status == "OK"
    assert d.value is not None and d.value > 0


def test_nan_input_fails_closed():
    img = mid_gray_image()
    img[3, 3, 0] = np.nan
    with pytest.raises(PrintabilityInputError):
        printability_loss(img, full_profile())


def test_out_of_range_and_bad_shape_fail():
    with pytest.raises(PrintabilityInputError):
        printability_loss(np.full((8, 8, 3), 2.0), full_profile())
    with pytest.raises(PrintabilityInputError):
        printability_loss(np.zeros((8, 8)), full_profile())


def test_empty_profile_fails_closed():
    with pytest.raises(PrintabilityInputError):
        printability_loss(mid_gray_image(), {})
