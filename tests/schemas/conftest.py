"""Shared helpers for Barrier 1 schema contract tests.

Deterministic, no network, no torch. Only repo-module import permitted is
``ruthless_pipeline.evidence_classes_ext`` (used in its own test file).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

REPO_ROOT = Path(__file__).resolve().parents[2]
SCHEMAS_DIR = REPO_ROOT / "schemas"


def load_schema(name: str) -> dict:
    with open(SCHEMAS_DIR / name, "r", encoding="utf-8") as fh:
        return json.load(fh)


def make_validator(name: str) -> Draft202012Validator:
    schema = load_schema(name)
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


@pytest.fixture()
def validate():
    """Return a callable (schema_name, instance) -> list of validation errors."""

    def _validate(schema_name: str, instance: dict):
        return list(make_validator(schema_name).iter_errors(instance))

    return _validate
