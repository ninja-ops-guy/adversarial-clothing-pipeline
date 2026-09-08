"""Smoke tests for scripts/profile_pipeline.py and its documentation."""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "profile_pipeline.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("profile_pipeline", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_profiler_script_exists_and_doc_exists():
    assert SCRIPT.is_file()
    assert (ROOT / "docs" / "PERFORMANCE_AND_COST.md").is_file()


def test_time_helper_reports_all_fields():
    module = _load_module()
    result = module._time(lambda: None, 3)
    assert result["repeats"] == 3
    assert result["min_s"] <= result["median_s"] <= result["max_s"]


def test_profiler_covers_required_segments():
    module = _load_module()
    src = SCRIPT.read_text(encoding="utf-8")
    for key in (
        "status_ingest",
        "release_verification",
        "manuscript_export_inputs",
        "rehearsal_harness_end_to_end",
        "pytest_fast_segment",
    ):
        assert key in src
    assert callable(module.profile)
