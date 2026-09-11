"""Tests for the SW-08 Negative Result / Failure Index.

Covers: generation from canonical evidence (never manual copies), traceable
query results (category / generator family / experiment), append-only
fail-closed immutability, determinism, schema conformance and typed errors.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from ruthless_pipeline.certification.negative_result_index import (
    IndexImmutableError,
    NegativeOutcomeRecord,
    NegativeResultIndex,
    NegativeResultIndexError,
    OutcomeKind,
    RecordIntegrityError,
    UnknownOutcomeKindError,
    EvidenceRef,
    build_index,
    make_record,
)
from scripts import build_negative_result_index as cli

REPO_ROOT = Path(__file__).resolve().parents[1]
SCHEMA = json.loads(
    (REPO_ROOT / "schemas" / "rac_negative_outcome_v1.schema.json").read_text()
)
Draft202012Validator.check_schema(SCHEMA)
VALIDATOR = Draft202012Validator(SCHEMA)


# ---------------------------------------------------------------------------
# Fixture: minimal synthetic canonical evidence tree
# ---------------------------------------------------------------------------


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def make_canonical_tree(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    _write_json(
        root / "generations" / "RAC-PER-T-0001.json",
        {
            "generation_id": "RAC-PER-T-0001",
            "status": "CLOSED_FAIL",
            "protocol": "protocols/T-1.0.json",
            "surrogate_model_set": "SUR-T",
            "heldout_model_set": "HO-T",
            "generator_family": "TestGeneratorFamily",
            "candidate_pool": {"design_profile": "test-profile-v1"},
        },
    )
    _write_json(
        root / "releases" / "RAC-EXP-T-001" / "FAILURE.json",
        {
            "failure_reason": "transfer did not survive held-out evaluation",
            "failure_stage": "generation",
            "classification": {
                "record_id": "FR-RAC-EXP-T-001",
                "experiment_id": "RAC-EXP-T-001",
                "generation_id": "RAC-PER-T-0001",
                "category": "cross_architecture_transfer_failure",
                "confidence": "high",
                "explanation": "surrogate suppression did not transfer",
                "created_utc": "2026-01-01T00:00:00Z",
                "signals": [
                    {"name": "heldout_detection_rate", "value": 1.0, "detail": "high"}
                ],
            },
        },
    )
    _write_json(
        root / "releases" / "RAC-EXP-T-001" / "experiment.json",
        {"experiment_id": "RAC-EXP-T-001"},
    )
    _write_json(
        root
        / "manuscript"
        / "evidence"
        / "RAC-PER-T-0002"
        / "d2-latest-status.json",
        {
            "decision": "FAIL",
            "candidate_id": "RAC-PER-T-0002",
            "evidence_state": "RAC-D0",
            "protocol_id": "RAC-PERSON-DETECT",
            "protocol_version": "1.1",
            "surrogate_model_set": "SUR-T",
            "heldout_model_set": "HO-T2",
            "heldout": {
                "baseline_detection_rate": 1.0,
                "candidate_detection_rate": 1.0,
                "n": 36,
            },
        },
    )
    return root


# ---------------------------------------------------------------------------
# Generation from canonical evidence
# ---------------------------------------------------------------------------


def test_build_index_generates_records_from_canonical_evidence(tmp_path: Path) -> None:
    root = make_canonical_tree(tmp_path)
    index = build_index(root)
    assert len(index.records) == 2

    by_exp = index.by_experiment("RAC-EXP-T-001")
    assert len(by_exp) == 1
    record = by_exp[0]
    assert record.outcome_kind == OutcomeKind.NEGATIVE.value
    assert record.failure_category == "cross_architecture_transfer_failure"
    assert record.generator_family == "TestGeneratorFamily"
    assert record.root_cause == "surrogate suppression did not transfer"
    assert record.root_cause_established is True
    assert record.uncertainty == "high"
    assert record.lessons  # reusable lessons attached
    assert record.record_id.startswith("RAC-NR-")
    VALIDATOR.validate(record.to_dict())


def test_records_are_traceable_to_canonical_files(tmp_path: Path) -> None:
    root = make_canonical_tree(tmp_path)
    index = build_index(root)
    for record in index.records:
        assert record.evidence_refs, "traceability is mandatory"
        for ref in record.evidence_refs:
            path = root / ref.path
            assert path.is_file(), ref.path
            from ruthless_pipeline.pattern_genome.canonical import sha256_bytes

            assert sha256_bytes(path.read_bytes()) == ref.sha256


def test_build_is_deterministic(tmp_path: Path) -> None:
    root = make_canonical_tree(tmp_path)
    first = build_index(root).to_json()
    second = build_index(root).to_json()
    assert first == second
    assert "record_id" in first


def test_statistical_inconclusive_maps_to_inconclusive_kind(tmp_path: Path) -> None:
    root = make_canonical_tree(tmp_path)
    failure = root / "releases" / "RAC-EXP-T-001" / "FAILURE.json"
    payload = json.loads(failure.read_text())
    payload["classification"]["category"] = "statistical_inconclusive"
    payload["classification"]["confidence"] = "medium"
    failure.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    index = build_index(root)
    inc = index.by_outcome_kind("inconclusive")
    assert len(inc) == 1
    assert inc[0].root_cause_established is False  # only high confidence establishes


# ---------------------------------------------------------------------------
# Query API
# ---------------------------------------------------------------------------


def test_query_by_category_family_and_experiment(tmp_path: Path) -> None:
    root = make_canonical_tree(tmp_path)
    index = build_index(root)
    assert index.by_category("cross_architecture_transfer_failure")
    assert not index.by_category("manufacturing_loss")
    assert index.by_generator_family("TestGeneratorFamily")
    assert index.by_generation("RAC-PER-T-0002")
    with pytest.raises(NegativeResultIndexError):
        index.by_category("not_a_category")
    with pytest.raises(UnknownOutcomeKindError):
        index.by_outcome_kind("not_a_kind")


# ---------------------------------------------------------------------------
# Append-only / fail-closed immutability
# ---------------------------------------------------------------------------


def test_index_refuses_all_deletion_paths(tmp_path: Path) -> None:
    root = make_canonical_tree(tmp_path)
    index = build_index(root)
    before = len(index.records)
    for mutator in (index.remove, index.delete, index.discard):
        with pytest.raises(IndexImmutableError):
            mutator(index.records[0].record_id)
    assert len(index.records) == before
    # no removal API exists beyond the fail-closed aliases
    assert not hasattr(index, "pop")
    assert not hasattr(index, "clear")


def test_duplicate_record_id_rejected(tmp_path: Path) -> None:
    root = make_canonical_tree(tmp_path)
    index = build_index(root)
    with pytest.raises(NegativeResultIndexError):
        index.add(index.records[0])


def test_tampered_serialization_fails_closed(tmp_path: Path) -> None:
    root = make_canonical_tree(tmp_path)
    index = build_index(root)
    payload = json.loads(index.to_json())
    payload["records"][0]["root_cause"] = "rewritten history"
    with pytest.raises(RecordIntegrityError):
        NegativeResultIndex.from_dict(payload)


def test_roundtrip_serialization(tmp_path: Path) -> None:
    root = make_canonical_tree(tmp_path)
    index = build_index(root)
    loaded = NegativeResultIndex.from_json(index.to_json())
    assert loaded.to_json() == index.to_json()


def test_record_without_evidence_refs_is_rejected() -> None:
    with pytest.raises(NegativeResultIndexError):
        make_record(
            outcome_kind=OutcomeKind.NEGATIVE,
            failure_category=None,
            experiment_id="EXP",
            generation_id="GEN",
            candidate_id=None,
            generator_family=None,
            conditions={},
            evidence_class="test",
            evidence_refs=[],
            root_cause=None,
            root_cause_established=False,
            uncertainty="low",
            lessons=(),
            created_utc="",
        )


def test_bad_evidence_ref_sha_rejected() -> None:
    with pytest.raises(NegativeResultIndexError):
        EvidenceRef(path="x.json", sha256="Z" * 64).validate()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def test_cli_query_by_category(tmp_path: Path, capsys) -> None:
    root = make_canonical_tree(tmp_path)
    rc = cli.main(
        ["--repo-root", str(root), "--category", "cross_architecture_transfer_failure"]
    )
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out["result_count"] == 1
    assert out["results"][0]["experiment_id"] == "RAC-EXP-T-001"


def test_cli_unknown_category_fails_closed(tmp_path: Path, capsys) -> None:
    root = make_canonical_tree(tmp_path)
    rc = cli.main(["--repo-root", str(root), "--category", "bogus"])
    assert rc == 2
    assert "error" in capsys.readouterr().err


def test_cli_writes_index_file(tmp_path: Path) -> None:
    root = make_canonical_tree(tmp_path)
    out = tmp_path / "index.json"
    assert cli.main(["--repo-root", str(root), "--out", str(out)]) == 0
    loaded = NegativeResultIndex.from_json(out.read_text())
    assert len(loaded.records) == 2


# ---------------------------------------------------------------------------
# Real repository: the retained negative results must be indexed
# ---------------------------------------------------------------------------


def test_real_repo_indexes_retained_negative_results() -> None:
    index = build_index(REPO_ROOT)
    experiments = {r.experiment_id for r in index.records}
    # D2-0003 (retained measured negative generation) and D2-0004
    # (FAIL / RAC-D0 with failure taxonomy) must always be listed.
    assert "RAC-PER-D2-0003" in experiments
    assert "RAC-EXP-2026-001" in experiments
    d2004 = index.by_experiment("RAC-EXP-2026-001")
    assert any(
        r.failure_category == "cross_architecture_transfer_failure" for r in d2004
    )
    for record in index.records:
        VALIDATOR.validate(record.to_dict())


def test_real_repo_index_is_deterministic() -> None:
    assert build_index(REPO_ROOT).to_json() == build_index(REPO_ROOT).to_json()


def test_frozen_evidence_untouched_by_build() -> None:
    """Building the index is read-only over canonical evidence."""
    before = {
        p: p.read_bytes()
        for p in [
            REPO_ROOT / "generations" / "RAC-PER-D2-0004.json",
            REPO_ROOT / "releases" / "RAC-EXP-2026-001" / "FAILURE.json",
            REPO_ROOT / "registry" / "experiments.json",
        ]
    }
    build_index(REPO_ROOT)
    for path, content in before.items():
        assert path.read_bytes() == content
