"""Tests for ctm.cli: digital functional path, physical fail-closed path."""
import json

import pytest

from ruthless_pipeline.ctm.cli import main
from ruthless_pipeline.ctm.genome_adapter import register_digital_genome


@pytest.fixture
def registered(checker_bytes, cfg, registry_root):
    return register_digital_genome(
        checker_bytes,
        candidate_label="fixture://checker.png",
        source_commit="0" * 40,
        runtime_lock_sha256="0" * 64,
        config=cfg,
        registry_root=registry_root,
    )


def test_digital_compare_exit_0_valid_json(registered, checker_bytes, tmp_path, capsys):
    candidate = tmp_path / "candidate.png"
    candidate.write_bytes(checker_bytes)
    rc = main(["genome", "compare", "digital", str(candidate),
               "--registry-root", registered.paths["genome.json"].split("/patterns/")[0]])
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out["identical"] is True
    assert out["claim_state"] == "EXPLORATORY"
    assert out["physical_efficacy_claimed"] is False
    assert out["pattern_id"] == registered.pattern_id
    assert set(out["families"]) == {"spectral", "topology", "color", "geometry"}


def test_digital_compare_with_pattern_id(registered, stripes_bytes, tmp_path, capsys):
    candidate = tmp_path / "stripes.png"
    candidate.write_bytes(stripes_bytes)
    rc = main(["genome", "compare", "digital", str(candidate),
               "--pattern-id", registered.pattern_id,
               "--registry-root", str(tmp_path / "nope")])  # overridden by --pattern-id path below
    # registry root here is wrong; load should fail closed
    assert rc == 1
    out = json.loads(capsys.readouterr().out)
    assert out["status"] == "ERROR"


def test_digital_compare_empty_registry_fails_closed(checker_bytes, tmp_path, capsys):
    candidate = tmp_path / "candidate.png"
    candidate.write_bytes(checker_bytes)
    rc = main(["genome", "compare", "digital", str(candidate),
               "--registry-root", str(tmp_path / "empty_registry")])
    assert rc == 1
    out = json.loads(capsys.readouterr().out)
    assert out["status"] == "ERROR"
    assert "no registered" in out["reason"]


def test_digital_compare_missing_file_fails_closed(tmp_path, capsys):
    rc = main(["genome", "compare", "digital", str(tmp_path / "missing.png"),
               "--registry-root", str(tmp_path)])
    assert rc == 1
    assert json.loads(capsys.readouterr().out)["status"] == "ERROR"


def test_physical_path_pending_user_action(capsys):
    rc = main(["genome", "compare", "physical", "fabricated"])
    assert rc == 3
    out = json.loads(capsys.readouterr().out)
    assert out["status"] == "PENDING_USER_ACTION"
    assert "UA-3/UA-1" in out["reason"]
    assert out["physical_efficacy_claimed"] is False


def test_physical_any_variant_pending(capsys):
    for target in ("fabricated", "panel_A", "swatch-7"):
        rc = main(["genome", "compare", "physical", target])
        assert rc == 3
        assert json.loads(capsys.readouterr().out)["status"] == "PENDING_USER_ACTION"


def test_unknown_args_exit_2():
    with pytest.raises(SystemExit) as excinfo:
        main(["bogus"])
    assert excinfo.value.code == 2
    with pytest.raises(SystemExit) as excinfo:
        main(["genome", "compare", "bogus", "x"])
    assert excinfo.value.code == 2
