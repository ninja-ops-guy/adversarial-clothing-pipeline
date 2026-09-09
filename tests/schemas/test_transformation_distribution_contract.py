"""Contract tests for schemas/transformation_distribution.schema.json."""

from __future__ import annotations

SCHEMA = "transformation_distribution.schema.json"


def _dist(t="uniform", **params):
    return {"type": t, "params": params or {"min": 0.0, "max": 1.0}}


def _minimal():
    return {
        "schema_version": "1.0",
        "distribution_id": "RAC-TD-0001",
        "parameter_manifest": {
            "geometry": {
                "scale": _dist(),
                "camera_distance": _dist("uniform", min=2.0, max=8.0),
                "perspective": _dist("fixed", value=0.0),
                "yaw": _dist("uniform", min=-30.0, max=30.0),
                "pitch": _dist("uniform", min=-10.0, max=10.0),
                "roll": _dist("uniform", min=-5.0, max=5.0),
                "translation": _dist("normal", mean=0.0, std=0.05),
            },
            "imaging": {
                "blur": _dist("lognormal", mean=0.0, std=0.3),
                "resize_interpolation": _dist("choice", values=["bilinear", "bicubic"]),
                "compression": _dist("uniform", min=70, max=100),
                "exposure": _dist("normal", mean=0.0, std=0.1),
                "contrast": _dist("normal", mean=1.0, std=0.05),
            },
            "garment": {
                "stretch": _dist("uniform", min=0.95, max=1.05),
                "wrinkle": _dist("uniform", min=0.0, max=1.0),
                "fold": _dist("uniform", min=0.0, max=1.0),
                "bend": _dist("uniform", min=0.0, max=15.0),
                "partial_occlusion": _dist("uniform", min=0.0, max=0.3),
            },
            "print_capture": {
                "gamut_mapping": _dist("choice", values=["perceptual", "relative"]),
                "resolution_loss": _dist("uniform", min=0.0, max=0.2),
            },
        },
        "seed": 42,
        "sampling_reproducibility_note": (
            "Sample i is reproducible from (distribution_id, parameter_manifest, "
            "seed, i); no hidden entropy."
        ),
        "robustness_surface": {
            "grid_axes": ["geometry.scale", "imaging.blur"],
            "response_metric": "person_detection_rate",
            "cell_value_type": "scalar",
            "scalar_only_permitted": False,
        },
    }


def _full():
    m = _minimal()
    m["parameter_manifest"]["print_capture"]["calibration_transform_ref"] = (
        "calibration/RAC-CAL-0001.json"
    )
    m["robustness_surface"]["grid_axes"] = [
        "geometry.scale",
        "geometry.yaw",
        "imaging.blur",
        "garment.wrinkle",
        "print_capture.resolution_loss",
    ]
    m["robustness_surface"]["cell_value_type"] = "distribution_summary"
    return m


def test_minimal_valid(validate):
    assert validate(SCHEMA, _minimal()) == []


def test_full_valid(validate):
    assert validate(SCHEMA, _full()) == []


def test_missing_required_field_fails(validate):
    m = _minimal()
    del m["seed"]
    assert validate(SCHEMA, m)
    m = _minimal()
    del m["parameter_manifest"]["garment"]
    assert validate(SCHEMA, m)


def test_bad_distribution_type_fails(validate):
    m = _minimal()
    m["parameter_manifest"]["geometry"]["scale"]["type"] = "poisson"
    assert validate(SCHEMA, m)


def test_additional_properties_fails(validate):
    m = _minimal()
    m["extra"] = 1
    assert validate(SCHEMA, m)
    m = _minimal()
    m["parameter_manifest"]["geometry"]["extra_dim"] = _dist()
    assert validate(SCHEMA, m)


def test_scalar_only_surface_fails(validate):
    m = _minimal()
    m["robustness_surface"]["scalar_only_permitted"] = True
    assert validate(SCHEMA, m)


def test_seed_must_be_integer(validate):
    m = _minimal()
    m["seed"] = 1.5
    assert validate(SCHEMA, m)


def test_distribution_missing_params_fails(validate):
    m = _minimal()
    m["parameter_manifest"]["imaging"]["blur"] = {"type": "normal"}
    assert validate(SCHEMA, m)
