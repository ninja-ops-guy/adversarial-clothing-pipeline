"""Deterministic derivation tests for the canonical program state compiler."""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest

from ruthless_pipeline.program_state.compile import (
    SCHEMA_VERSION,
    canonical_state_bytes,
    check_state,
    derive_state,
    render_summary_markdown,
    write_state,
)
from ruthless_pipeline.program_state.errors import SourceMissingError

from .conftest import ROOT, make_repo


def test_derivation_is_byte_identical(tmp_path: Path) -> None:
    make_repo(tmp_path)
    first = canonical_state_bytes(derive_state(tmp_path))
    second = canonical_state_bytes(derive_state(tmp_path))
    assert first == second
    assert first.endswith(b"\n")


def test_state_content_address_is_input_derived(tmp_path: Path) -> None:
    make_repo(tmp_path)
    state = derive_state(tmp_path)
    assert len(state["program_state_sha256"]) == 64
    # No wall-clock fields anywhere in the derived state.
    assert not any("time" in k.lower() or "date" in k.lower() for k in state)
    # Changing a source changes the content address.
    status = tmp_path / "d2-latest-status.json"
    payload = json.loads(status.read_text())
    payload["heldout"]["n"] = 37
    status.write_text(json.dumps(payload, indent=2, sort_keys=True))
    changed = derive_state(tmp_path)
    assert changed["program_state_sha256"] != state["program_state_sha256"]


def test_lifecycle_mapping_and_sealed_reconciliation(tmp_path: Path) -> None:
    make_repo(tmp_path)
    state = derive_state(tmp_path)
    by_id = {e["generation_id"]: e for e in state["experiments"]}
    assert by_id["RAC-PER-D2-0005"]["lifecycle_state"] == "PREREGISTERED"
    assert by_id["RAC-PER-D2-0005"]["armed"] is False
    assert state["d2_0005_arming"]["armed"] is False
    assert state["d2_0004_result"]["decision"] == "FAIL"
    assert state["boundaries"] == {
        "held_out_models_accessed": False,
        "physical_efficacy_claimed": False,
        "experiments_armed": False,
        "frozen_surfaces_modified": False,
    }


def test_derived_state_validates_against_schema() -> None:
    state = derive_state(ROOT)
    schema = json.loads(
        (ROOT / "schemas" / "program_state_v1.schema.json").read_text()
    )
    jsonschema.validate(state, schema)
    assert state["schema_version"] == SCHEMA_VERSION


def test_missing_generations_dir_fails_closed(tmp_path: Path) -> None:
    with pytest.raises(SourceMissingError):
        derive_state(tmp_path)


def test_summary_is_deterministic_and_machine_anchored(tmp_path: Path) -> None:
    make_repo(tmp_path)
    state = derive_state(tmp_path)
    a = render_summary_markdown(state)
    b = render_summary_markdown(derive_state(tmp_path))
    assert a == b
    assert state["program_state_sha256"] in a
    assert "GENERATED" in a


def test_committed_repo_state_is_fresh() -> None:
    """The committed program_state/ artifacts match a fresh derivation."""
    assert check_state(ROOT) == []


def test_write_then_check_roundtrip(tmp_path: Path) -> None:
    make_repo(tmp_path)
    write_state(tmp_path)
    assert check_state(tmp_path) == []
    committed = (tmp_path / "program_state" / "program_state.json").read_bytes()
    write_state(tmp_path)
    assert (tmp_path / "program_state" / "program_state.json").read_bytes() == committed
