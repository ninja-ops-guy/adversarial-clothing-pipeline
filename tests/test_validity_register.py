"""Tests for the SW-18 Canonical Validity Register.

Covers: seeded threats-to-validity extracted from the repo's papers/docs,
the RAC-RISK reference mechanism, fail-closed closure (evidence required),
open-risk visibility in the generated report, append-only registration,
determinism and schema conformance.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from ruthless_pipeline.certification.validity_register import (
    ClosureEvidence,
    ClosureEvidenceRequiredError,
    RiskCategory,
    RiskIntegrityError,
    UnknownRiskError,
    ValidityRegister,
    ValidityRegisterError,
    find_risk_references,
    make_risk,
    risk_reference_token,
    seed_register,
    validate_risk_references,
)
from ruthless_pipeline.pattern_genome.canonical import sha256_bytes
from scripts import generate_validity_register as cli

REPO_ROOT = Path(__file__).resolve().parents[1]
SCHEMA = json.loads(
    (REPO_ROOT / "schemas" / "rac_validity_risk_v1.schema.json").read_text()
)
Draft202012Validator.check_schema(SCHEMA)
VALIDATOR = Draft202012Validator(SCHEMA)


# ---------------------------------------------------------------------------
# Seed register content
# ---------------------------------------------------------------------------


def test_seed_register_contains_spec_named_risks() -> None:
    register = seed_register()
    categories = {r.category for r in register.risks}
    assert categories == {
        "simulation_gap",
        "model_selection",
        "manufacturing_variance",
        "statistical_power",
        "temporal_dependence",
    }
    for risk in register.risks:
        VALIDATOR.validate(risk.to_dict())
        assert risk.status == "open"
        assert risk.risk_id.startswith("RAC-RISK-")
        # extracted, not invented: every seed traces to repo docs/papers
        for ref in risk.source_refs:
            assert (REPO_ROOT / ref).is_file(), ref


def test_seed_is_deterministic() -> None:
    assert seed_register().to_json() == seed_register().to_json()


def test_seeded_register_file_matches_deterministic_seed() -> None:
    path = REPO_ROOT / "registry" / "validity_risks.json"
    assert path.is_file(), "run: python -m scripts.generate_validity_register --write-seed"
    on_disk = ValidityRegister.from_json(path.read_text())
    assert on_disk.to_json() == seed_register().to_json()


# ---------------------------------------------------------------------------
# Closure requires evidence (fail-closed)
# ---------------------------------------------------------------------------


def _one_risk_register():
    risk = make_risk(
        category=RiskCategory.OTHER,
        affected_experiment_class="unit test",
        severity="low",
        description="test risk",
        mitigation="test mitigation",
        residual_risk="test residual",
        source_refs=("docs/papers/README.md",),
    )
    return ValidityRegister([risk]), risk


def test_close_without_evidence_refused() -> None:
    register, risk = _one_risk_register()
    with pytest.raises(ClosureEvidenceRequiredError):
        register.close_risk(risk.risk_id, [])
    assert register.open_risks()[0].risk_id == risk.risk_id  # still open


def test_close_with_invalid_evidence_refused() -> None:
    register, risk = _one_risk_register()
    with pytest.raises(ClosureEvidenceRequiredError):
        register.close_risk(
            risk.risk_id, [ClosureEvidence(path="x", sha256="not-hex")]
        )


def test_close_with_evidence_succeeds_and_stays_traceable(tmp_path: Path) -> None:
    register, risk = _one_risk_register()
    artifact = tmp_path / "closure.json"
    artifact.write_text("{}")
    evidence = ClosureEvidence(
        path="closure.json",
        sha256=sha256_bytes(artifact.read_bytes()),
        note="unit-test closure",
    )
    closed = register.close_risk(risk.risk_id, [evidence])
    assert closed.status == "closed"
    assert closed.closure_evidence == (evidence,)
    assert not register.open_risks()
    VALIDATOR.validate(closed.to_dict())
    # the superseded (open) ID remains listed for historical references
    assert risk.risk_id in register.superseded_ids(closed.risk_id)


def test_closed_record_without_evidence_fails_validation() -> None:
    with pytest.raises(ClosureEvidenceRequiredError):
        make_risk(
            category=RiskCategory.OTHER,
            affected_experiment_class="unit test",
            severity="low",
            description="test risk",
            mitigation="test mitigation",
            residual_risk="test residual",
            status=__import__(
                "ruthless_pipeline.certification.validity_register",
                fromlist=["RiskStatus"],
            ).RiskStatus.CLOSED,
            source_refs=("docs/papers/README.md",),
        )


def test_schema_enforces_closure_evidence_when_closed() -> None:
    register, risk = _one_risk_register()
    payload = risk.to_dict()
    payload["status"] = "closed"
    payload["closure_evidence"] = []
    with pytest.raises(Exception):
        VALIDATOR.validate(payload)


# ---------------------------------------------------------------------------
# Open risks remain visible; register is append-only
# ---------------------------------------------------------------------------


def test_report_always_lists_open_risks() -> None:
    register = seed_register()
    report = register.report_markdown()
    assert "## Open risks" in report
    for risk in register.risks:
        assert risk.risk_id in report
    # close one risk: it moves sections but stays in the report
    evidence = ClosureEvidence(path="e.json", sha256="a" * 64)
    target = register.risks[0]
    register.close_risk(target.risk_id, [evidence])
    report = register.report_markdown()
    assert "## Open risks" in report and "## Closed risks" in report
    remaining = {r.risk_id for r in register.open_risks()}
    assert target.risk_id not in remaining
    assert len(register.open_risks()) == len(register.risks) - 1


def test_duplicate_risk_id_rejected() -> None:
    register, risk = _one_risk_register()
    with pytest.raises(ValidityRegisterError):
        register.add(risk)


def test_tampered_register_fails_closed() -> None:
    payload = json.loads(seed_register().to_json())
    payload["risks"][0]["residual_risk"] = "nothing left to worry about"
    with pytest.raises(RiskIntegrityError):
        ValidityRegister.from_dict(payload)


def test_roundtrip_serialization() -> None:
    register = seed_register()
    assert ValidityRegister.from_json(register.to_json()).to_json() == register.to_json()


# ---------------------------------------------------------------------------
# Reference mechanism (papers / evidence cards reference RAC-RISK IDs)
# ---------------------------------------------------------------------------


def test_reference_token_roundtrip() -> None:
    register = seed_register()
    risk_id = register.risks[0].risk_id
    token = risk_reference_token(risk_id)
    assert token == risk_id
    text = f"This limitation is tracked as {token}."
    assert find_risk_references(text) == [risk_id]
    assert validate_risk_references(text, register) == [risk_id]


def test_dangling_reference_fails_closed() -> None:
    register = seed_register()
    text = "Tracked as RAC-RISK-0000000000000000."
    with pytest.raises(UnknownRiskError):
        validate_risk_references(text, register)


def test_invalid_token_rejected() -> None:
    with pytest.raises(ValidityRegisterError):
        risk_reference_token("RAC-RISK-XYZ")


def test_unknown_risk_get_fails() -> None:
    register = seed_register()
    with pytest.raises(UnknownRiskError):
        register.get("RAC-RISK-ffffffffffffffff")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def test_cli_report_lists_open_risks(capsys) -> None:
    rc = cli.main(["--repo-root", str(REPO_ROOT)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "## Open risks" in out
    for risk in seed_register().risks:
        assert risk.risk_id in out


def test_cli_seed_write_is_idempotent(tmp_path: Path) -> None:
    args = ["--repo-root", str(tmp_path), "--write-seed"]
    assert cli.main(args) == 0
    first = (tmp_path / "registry" / "validity_risks.json").read_text()
    assert cli.main(args) == 0  # deterministic: no diff, no failure
    assert (tmp_path / "registry" / "validity_risks.json").read_text() == first


def test_cli_seed_write_refuses_divergent_overwrite(tmp_path: Path) -> None:
    assert cli.main(["--repo-root", str(tmp_path), "--write-seed"]) == 0
    path = tmp_path / "registry" / "validity_risks.json"
    path.write_text('{"schema_version": "1.0", "risks": []}\n')
    assert cli.main(["--repo-root", str(tmp_path), "--write-seed"]) == 2


def test_cli_check_docs_passes_on_repo(capsys) -> None:
    rc = cli.main(["--repo-root", str(REPO_ROOT), "--check-docs"])
    assert rc == 0
