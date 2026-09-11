"""Shared fixtures for the pattern-generator test suite."""
import pytest

from ruthless_pipeline.patterns import GeneratorParams

LANDMARKS = {
    "left_eye": {"position": [40, 40]},
    "right_eye": {"position": [88, 40]},
    "nose_tip": {"position": [64, 64]},
    "mouth_center": {"position": [64, 92]},
    "left_brow": {"position": [40, 28]},
    "right_brow": {"position": [88, 28]},
    "left_cheek": {"position": [36, 70]},
    "right_cheek": {"position": [92, 70]},
}

BBOXES = {
    "eyes": [30, 32, 68, 18],
    "mouth": [48, 84, 32, 16],
}


def make_mask(with_landmarks=True, with_bboxes=True):
    mask = {}
    if with_landmarks:
        mask["landmarks"] = {k: dict(v) for k, v in LANDMARKS.items()}
    if with_bboxes:
        mask["bboxes"] = {k: list(v) for k, v in BBOXES.items()}
    return mask


@pytest.fixture
def mask_geometry():
    return make_mask()


@pytest.fixture
def params(mask_geometry):
    return GeneratorParams(seed=1234, mask_geometry=mask_geometry,
                           output_size=(128, 128))
