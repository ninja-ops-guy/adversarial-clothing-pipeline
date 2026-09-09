"""Primitive qualitative-effect tests (all synthetic numpy arrays).

synthetic_pipeline_validation_only.
"""

import numpy as np
import pytest

from ruthless_pipeline.transformations import primitives as P


def _hf_energy(img):
    """High-frequency energy proxy: sum of |laplacian-like diffs|."""
    return float(np.abs(np.diff(img, axis=0)).sum() + np.abs(np.diff(img, axis=1)).sum())


def test_gaussian_blur_reduces_high_frequency(base_image):
    blurred = P.gaussian_blur(base_image, 2.0)
    assert blurred.shape == base_image.shape
    assert _hf_energy(blurred) < _hf_energy(base_image)


def test_exposure_shifts_mean(base_image):
    up = P.exposure(base_image, 1.0)
    down = P.exposure(base_image, -1.0)
    assert up.mean() > base_image.mean()
    assert down.mean() < base_image.mean()
    assert up.max() <= 1.0 and down.min() >= 0.0


def test_contrast_scales_deviation(base_image):
    out = P.contrast(base_image, 1.5)
    assert out.std() > base_image.std()
    out2 = P.contrast(base_image, 0.5)
    assert out2.std() < base_image.std()


def test_partial_occlusion_zeroes_region():
    img = np.full((32, 32), 0.7)
    out = P.apply_partial_occlusion(img, 0.25, seed_bits=42)
    zero_frac = float((out == 0.0).mean())
    assert 0.15 < zero_frac < 0.45
    # deterministic given seed_bits
    assert np.array_equal(out, P.apply_partial_occlusion(img, 0.25, seed_bits=42))


def test_geometry_scale_changes_content(base_image):
    ident = P.apply_geometry(base_image, {"scale": 1.0, "camera_distance": 1.0})
    zoom = P.apply_geometry(base_image, {"scale": 2.0, "camera_distance": 1.0})
    assert ident.shape == base_image.shape == zoom.shape
    assert not np.allclose(ident, zoom)
    # camera_distance == scale reciprocal gives same effective scale
    a = P.apply_geometry(base_image, {"scale": 2.0, "camera_distance": 1.0})
    b = P.apply_geometry(base_image, {"scale": 1.0, "camera_distance": 0.5})
    assert np.allclose(a, b)


def test_geometry_translation_moves_content(base_image):
    moved = P.apply_geometry(base_image, {"scale": 1.0, "camera_distance": 1.0, "translation": (5.0, 0.0)})
    assert not np.allclose(moved, base_image)


def test_resize_interpolations(base_image):
    down_near = P.resize(base_image, 0.5, "nearest")
    down_bil = P.resize(base_image, 0.5, "bilinear")
    assert down_near.shape == (32, 32) and down_bil.shape == (32, 32)
    assert _hf_energy(down_bil) <= _hf_energy(down_near) + 1e-9
    with pytest.raises(ValueError):
        P.resize(base_image, 0.5, "cubic")


def test_compression_mock_smooths(base_image):
    out = P.compression_mock(base_image, 20.0)
    assert out.shape == base_image.shape
    assert _hf_energy(out) < _hf_energy(base_image)
    hi = P.compression_mock(base_image, 95.0)
    assert _hf_energy(out) < _hf_energy(hi)


def test_garment_fields_change_image(base_image):
    for fn, kw in [
        (P.apply_stretch, {"stretch": 1.3}),
        (P.apply_wrinkle, {"amplitude": 2.0}),
        (P.apply_fold, {"amplitude": 3.0}),
        (P.apply_bend, {"curvature": 0.2}),
    ]:
        out = fn(base_image, **kw)
        assert out.shape == base_image.shape
        assert not np.allclose(out, base_image)


def test_gamut_mapping_compresses():
    img = np.linspace(0.0, 1.0, 100).reshape(10, 10)
    out = P.gamut_mapping(img, 1.0)
    assert out.min() >= 0.04 and out.max() <= 0.96
    ident = P.gamut_mapping(img, 0.0)
    assert np.allclose(ident, img)


def test_resolution_loss_smooths_and_preserves_shape(base_image):
    out = P.resolution_loss(base_image, 4.0)
    assert out.shape == base_image.shape
    assert _hf_energy(out) < _hf_energy(base_image)
    assert np.array_equal(P.resolution_loss(base_image, 1.0), base_image)


def test_calibration_refusal_fail_closed(base_image):
    # no ref requested -> identity passthrough
    assert P.calibration_transform(base_image, None) is base_image
    # ref requested but unavailable -> refuse, never fake
    with pytest.raises(P.CalibrationUnavailableError):
        P.calibration_transform(base_image, "cal-v1")
    with pytest.raises(P.CalibrationUnavailableError):
        P.apply_print_capture(base_image, {"gamut_mapping": 0.0, "resolution_loss": 1.0,
                                           "calibration_transform_ref": "cal-v1"})


def test_calibration_available_applies():
    img = np.random.default_rng(1).random((16, 16, 3))
    out = P.calibration_transform(img, "cal-v1", {"cal-v1": np.eye(3)})
    assert np.allclose(out, img)
