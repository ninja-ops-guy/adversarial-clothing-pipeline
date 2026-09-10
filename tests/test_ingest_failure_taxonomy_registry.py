from __future__ import annotations

import json
from pathlib import Path

from ruthless_pipeline.certification.experiment import ExperimentRegistry
from scripts import ingest_closed_generation as icg
from tests.test_ingest_closed_generation import make_args, make_run


def test_closed_failure_taxonomy_persists_to_registry_and_report(tmp_path: Path) -> None:
    heldout = {
        "fasterrcnn_resnet50_fpn_v2": 0.95,
        "maskrcnn_resnet50_fpn_v2": 0.90,
    }
    fixtures = make_run(tmp_path, heldout_rates=heldout)
    assert icg.main(make_args(tmp_path, fixtures)) == 0

    release = tmp_path / "releases" / "RAC-EXP-2025-001"
    failure = json.loads((release / "FAILURE.json").read_text())
    expected = failure["classification"]["category"]

    registry = ExperimentRegistry.from_json((tmp_path / "registry.json").read_text())
    artifact = registry.get("RAC-EXP-2025-001")
    assert artifact.validity_flags["failure_taxonomy"]["category"] == expected

    report = (release / "REPORT.md").read_text()
    assert "## Failure taxonomy" in report
    assert expected in report
    assert failure["failure_reason"] in report
