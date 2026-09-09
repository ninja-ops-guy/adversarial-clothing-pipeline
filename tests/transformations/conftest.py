import numpy as np
import pytest

from ruthless_pipeline.transformations.distribution import TransformationDistributionSpec


def _uniform(lo, hi):
    return {"type": "uniform", "params": {"min": lo, "hi": hi, "max": hi} if False else {"min": lo, "max": hi}}


def valid_spec_dict():
    return {
        "schema_version": "1.0",
        "distribution_id": "rac-eot-test-dist-v1",
        "parameter_manifest": {
            "geometry": {
                "scale": {"type": "uniform", "params": {"min": 0.8, "max": 1.2}},
                "camera_distance": {"type": "uniform", "params": {"min": 0.9, "max": 1.1}},
                "perspective": {"type": "normal", "params": {"mean": 0.0, "std": 0.5}},
                "yaw": {"type": "uniform", "params": {"min": -15.0, "max": 15.0}},
                "pitch": {"type": "uniform", "params": {"min": -15.0, "max": 15.0}},
                "roll": {"type": "uniform", "params": {"min": -30.0, "max": 30.0}},
                "translation": {"type": "fixed", "params": {"value": 0.0}},
            },
            "imaging": {
                "blur": {"type": "uniform", "params": {"min": 0.0, "max": 2.0}},
                "resize_interpolation": {"type": "choice", "params": {"values": ["nearest", "bilinear"]}},
                "compression": {"type": "uniform", "params": {"min": 30.0, "max": 95.0}},
                "exposure": {"type": "uniform", "params": {"min": -0.5, "max": 0.5}},
                "contrast": {"type": "lognormal", "params": {"mean": 0.0, "std": 0.1}},
            },
            "garment": {
                "stretch": {"type": "uniform", "params": {"min": 0.9, "max": 1.1}},
                "wrinkle": {"type": "uniform", "params": {"min": 0.0, "max": 2.0}},
                "fold": {"type": "uniform", "params": {"min": 0.0, "max": 2.0}},
                "bend": {"type": "uniform", "params": {"min": -0.2, "max": 0.2}},
                "partial_occlusion": {"type": "uniform", "params": {"min": 0.0, "max": 0.2}},
            },
            "print_capture": {
                "gamut_mapping": {"type": "uniform", "params": {"min": 0.0, "max": 1.0}},
                "resolution_loss": {"type": "uniform", "params": {"min": 1.0, "max": 4.0}},
            },
        },
        "seed": 1234,
        "sampling_reproducibility_note": (
            "Any sample index is fully reproducible from (distribution_id, "
            "parameter_manifest, seed, sample_index) with no hidden entropy source."
        ),
        "robustness_surface": {
            "grid_axes": ["geometry.scale", "imaging.blur"],
            "response_metric": "eval_fn_response",
            "cell_value_type": "scalar",
            "scalar_only_permitted": False,
        },
    }


@pytest.fixture
def spec_dict():
    return valid_spec_dict()


@pytest.fixture
def spec(spec_dict):
    return TransformationDistributionSpec.from_dict(spec_dict)


@pytest.fixture
def base_image():
    rng = np.random.default_rng(0)
    yy, xx = np.mgrid[0:64, 0:64]
    img = 0.5 + 0.4 * np.sin(xx / 3.0) * np.cos(yy / 5.0) + rng.normal(0, 0.02, (64, 64))
    return np.clip(img, 0.0, 1.0)
