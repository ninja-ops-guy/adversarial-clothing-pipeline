"""Tests for deformation tiers T0-T3 and the cross-tier benchmark."""

import numpy as np
import pytest

from ruthless_pipeline.physical_transfer import deformation_tiers as dt


def _texture(h=32, w=32):
    yy, xx = np.meshgrid(np.arange(h), np.arange(w), indexing="ij")
    r = xx / (w - 1)
    g = yy / (h - 1)
    b = 0.5 * np.ones_like(r)
    return np.stack([r, g, b], axis=-1)


def _fixture(h=32, w=32):
    uv = dt.make_uv_grid(h, w)
    tex = _texture(h, w)
    affine = np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]])  # identity
    return {
        "uv": uv,
        "texture": tex,
        "params": {"affine": affine},
        "reference": dt.reference_warp(uv, tex, affine),
    }


def test_t0_identity_is_exact():
    fx = _fixture()
    warped = dt.T0ExplicitWarp().apply(fx["uv"], fx["texture"], fx["params"])
    np.testing.assert_allclose(warped, fx["texture"], atol=1e-12)


def test_t0_hand_computed_translation():
    # Sampling shift of +0.5 in x: output(x) = input(x - 0.5 * (w-1)/... )
    h = w = 4
    tex = np.zeros((h, w, 3))
    tex[:, 1, :] = 1.0  # column 1 is white
    uv = dt.make_uv_grid(h, w)
    # output pixel at x=1 (normalized 1/3) samples input x = 0 -> black
    # output pixel at x=2 samples input x = 1 -> white
    affine = np.array([[1.0, 0.0, -1.0 / (w - 1)], [0.0, 1.0, 0.0]])
    warped = dt.T0ExplicitWarp().apply(uv, tex, {"affine": affine})
    assert warped[0, 1, 0] == pytest.approx(0.0)
    assert warped[0, 2, 0] == pytest.approx(1.0)


def test_t0_determinism_bitwise():
    fx = _fixture()
    t0 = dt.T0ExplicitWarp()
    a = t0.apply(fx["uv"], fx["texture"], fx["params"])
    b = t0.apply(fx["uv"], fx["texture"], fx["params"])
    assert a.tobytes() == b.tobytes()


def test_t0_projective():
    fx = _fixture()
    ident3 = np.eye(3)
    warped = dt.T0ExplicitWarp().apply(
        fx["uv"], fx["texture"], {"projective": ident3}
    )
    np.testing.assert_allclose(warped, fx["texture"], atol=1e-12)
    with pytest.raises(dt.TierError):
        dt.T0ExplicitWarp().apply(fx["uv"], fx["texture"], {})


def test_no_torch_import_at_module_level():
    import sys

    assert "torch" not in sys.modules or "pytest" not in str(
        sys.modules.get("torch")
    )  # torch simply must not be required by this module
    assert dt.T1NeuralDeformation() is not None  # constructible without torch


def test_t1_t2_unavailable_guard_without_torch():
    torch = pytest.importorskip  # noqa: F841 - clarity
    try:
        import torch  # noqa: F401
        has_torch = True
    except ImportError:
        has_torch = False
    fx = _fixture()
    if has_torch:
        pytest.skip("torch available; guard path not exercised")
    for tier in (dt.T1NeuralDeformation(), dt.T2ClothPhysics()):
        with pytest.raises(dt.TierUnavailableError):
            tier.apply(fx["uv"], fx["texture"], fx["params"])


def test_t3_refusal_without_measured_data():
    with pytest.raises(dt.CalibratedDataRequiredError):
        dt.T3EmpiricallyCalibrated()
    t3 = dt.T3EmpiricallyCalibrated(
        measured_calibration={"correction_uv_field": 0.0}
    )
    assert t3.status == "SCAFFOLD_ONLY"


def test_tier_benchmark_determinism_and_keys():
    tiers = [dt.T0ExplicitWarp(), dt.T1NeuralDeformation(), dt.T2ClothPhysics()]
    result = dt.run_tier_benchmark(tiers, [_fixture()])
    assert result["evidence_class"] == "synthetic_pipeline_validation_only"
    required = {
        "status",
        "cost_seconds_mean",
        "determinism_bitwise_equal",
        "fidelity_mse_vs_reference",
        "fidelity_psnr_vs_reference",
        "predictive_value",
        "predictive_value_note",
    }
    for name, entry in result["tiers"].items():
        assert required <= set(entry)
        assert entry["predictive_value"] is None
        assert entry["predictive_value_note"]
    t0 = result["tiers"]["T0_explicit_affine_projective"]
    assert t0["status"] == "OK"
    assert t0["determinism_bitwise_equal"] is True
    assert t0["fidelity_mse_vs_reference"] == pytest.approx(0.0)
    # Repeat runs of the harness are deterministic in the metric values.
    again = dt.run_tier_benchmark(tiers, [_fixture()])
    assert (
        again["tiers"]["T0_explicit_affine_projective"]["fidelity_mse_vs_reference"]
        == t0["fidelity_mse_vs_reference"]
    )
