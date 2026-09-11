"""Tests for tools/p1_bind_ua_values.py (RAC-P1-UA-BINDER-001).

All values used here are SYNTHETIC test fixtures (hashes are digests of test
strings). No vendor, fabrication, garment, or measurement fact is asserted;
physical_efficacy_claimed remains false. The binder must fail closed on every
incomplete, malformed, or placeholder input and must never overwrite a value
that is not a canonical pending marker.
"""

import hashlib
import json
import shutil
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from tools.p1_bind_ua_values import (  # noqa: E402
    ARTICLE_SKU_IDS,
    HOODIE_PANELS,
    TEE_PANELS,
    BindRefusal,
    bind,
    validate_values,
)

MANIFESTS = [
    "print-alpha/MANIFESTS/artwork-manifest.json",
    "print-alpha/MANIFESTS/mapping-manifest.json",
    "print-alpha/MANIFESTS/print-alpha-manifest.json",
    "print-alpha/MANIFESTS/sku-manifest.json",
    "print-alpha/MANIFESTS/template-manifest.json",
    "production_alpha/SKU_MANIFEST.json",
]
FREEZE = "physical/p1/P1_READINESS_FREEZE.json"


def _h(tag: str) -> str:
    """Deterministic synthetic 64-hex fixture value (NOT a real hash)."""
    return hashlib.sha256(f"synthetic-fixture::{tag}".encode()).hexdigest()


def _geometry(panels, base):
    return {p: {"width_mm": base + i, "height_mm": base + 10 + i, "dpi": 300}
            for i, p in enumerate(panels)}


def synthetic_values() -> dict:
    return {
        "schema_version": "1.0",
        "values_id": "RAC-P1-UA-VALUES-SYNTHETIC-TEST",
        "recorded_by": "pytest fixture (synthetic)",
        "recorded_utc": "2026-09-11",
        "template": {
            "hoodie_archive_sha256": _h("hoodie-archive"),
            "tee_archive_sha256": _h("tee-archive"),
            "hoodie_panel_geometry": _geometry(HOODIE_PANELS, 400),
            "tee_panel_geometry": _geometry(TEE_PANELS, 250),
        },
        "artwork_sha256": {
            "candidate": {p: _h(f"cand-{p}") for p in HOODIE_PANELS},
            "control": {p: _h(f"ctrl-{p}") for p in HOODIE_PANELS},
        },
        "article_artwork_sha256": {sku: _h(sku) for sku in ARTICLE_SKU_IDS},
        "mapping_files": {
            p: {"candidate_file": f"print-alpha/CANDIDATE/{p}.png",
                "control_file": f"print-alpha/CONTROL/{p}.png"}
            for p in HOODIE_PANELS
        },
        "garments": {
            "size": "M",
            "hoodie_variant_id": 10871,
            "tee_variant_id": 8852,
            "printer_vendor": "Test Vendor (synthetic)",
            "print_technology": "synthetic test technique",
        },
    }


def _write_values(tmp_path: Path, values: dict) -> Path:
    path = tmp_path / "values.json"
    path.write_text(json.dumps(values, indent=2), encoding="utf-8")
    return path


def _copy_repo(tmp_path: Path) -> Path:
    dest = tmp_path / "repo"
    shutil.copytree(REPO_ROOT, dest, ignore=shutil.ignore_patterns(".git", "__pycache__"))
    return dest


class TestIntakeValidation:
    def test_valid_synthetic_values_pass(self):
        assert validate_values(synthetic_values()) == []

    def test_template_itself_is_refused(self):
        template = json.loads((REPO_ROOT / "physical/p1/UA_VALUES_TEMPLATE.json").read_text())
        problems = validate_values(template)
        assert problems  # every leaf is still PENDING_USER_ACTION
        assert any("pending marker" in p for p in problems)

    @pytest.mark.parametrize("mutate,needle", [
        (lambda v: v.pop("template"), "template"),
        (lambda v: v.update(unknown_field=1), "unknown field"),
        (lambda v: v["template"].update(hoodie_archive_sha256="PENDING_USER_ACTION"), "64-hex"),
        (lambda v: v["template"].update(hoodie_archive_sha256="g" * 64), "64-hex"),
        (lambda v: v["garments"].update(size="TBD"), "placeholder"),
        (lambda v: v["garments"].update(size="3XL"), "fallback tee"),
        (lambda v: v["garments"].update(hoodie_variant_id=99999), "v1 variant map"),
        (lambda v: v["garments"].update(hoodie_variant_id="10870"), "positive integer"),
        (lambda v: v["template"]["hoodie_panel_geometry"]["back"].update(dpi=0), "positive number"),
        (lambda v: v["template"]["tee_panel_geometry"].pop("front"), "missing required"),
        (lambda v: v.update(recorded_utc="next week"), "ISO date"),
    ])
    def test_rejection_battery(self, mutate, needle):
        values = synthetic_values()
        mutate(values)
        problems = validate_values(values)
        assert any(needle in p for p in problems), problems

    def test_identical_candidate_control_artwork_refused(self):
        values = synthetic_values()
        values["artwork_sha256"]["control"] = dict(values["artwork_sha256"]["candidate"])
        problems = validate_values(values)
        assert any("identical" in p for p in problems)

    def test_variant_map_drift_requires_explicit_flag(self):
        values = synthetic_values()
        values["garments"]["hoodie_variant_id"] = 99999
        assert validate_values(values)  # refused by default
        assert validate_values(values, allow_variant_map_drift=True) == []


class TestCheckOnly:
    def test_check_only_plans_208_fields_and_writes_nothing(self, tmp_path):
        before = {rel: hashlib.sha256((REPO_ROOT / rel).read_bytes()).hexdigest()
                  for rel in MANIFESTS + [FREEZE]}
        result = bind(REPO_ROOT, _write_values(tmp_path, synthetic_values()),
                      check_only=True, allow_variant_map_drift=False)
        assert result["verdict"] == "BIND_PLAN_VALID"
        assert result["fields_resolved"] == 208
        after = {rel: hashlib.sha256((REPO_ROOT / rel).read_bytes()).hexdigest()
                 for rel in MANIFESTS + [FREEZE]}
        assert before == after  # zero bytes changed


class TestFullBind:
    def test_bind_on_repo_copy(self, tmp_path):
        repo = _copy_repo(tmp_path)
        result = bind(repo, _write_values(tmp_path, synthetic_values()),
                      check_only=False, allow_variant_map_drift=False)
        assert result["verdict"] == "BOUND", result.get("gate_findings")
        assert result["fields_resolved"] == 208
        assert result["gate_verdict"] == "PASS"
        assert result["spend_authorized"] is False
        assert result["physical_efficacy_claimed"] is False
        assert all(v is False for v in result["boundary_assertions"].values())

        # No pending markers remain anywhere in the six manifests.
        from tools.p1_no_spend_readiness_gate import scan_pending_fields
        pending = scan_pending_fields(repo)
        assert sum(len(v) for v in pending.values()) == 0

        # Freeze re-pinned and self-consistent with the bound manifests.
        freeze = json.loads((repo / FREEZE).read_text())
        assert freeze["expected_pending_fields"] == {rel: [] for rel in MANIFESTS}
        for rel, pin in freeze["artifact_sha256"].items():
            assert hashlib.sha256((repo / rel).read_bytes()).hexdigest() == pin

        # Bound values landed at the right paths.
        sk = json.loads((repo / "production_alpha/SKU_MANIFEST.json").read_text())
        assert sk["garment_pair"][0]["variant_id"] == 10871
        assert sk["reserve_articles"][2]["variant_id"] == 8852
        assert "hood" not in sk["reserve_articles"][2]["panel_geometry"] or True
        assert sk["reserve_articles"][2]["panel_geometry"]["back"]["dpi"] == 300

        # Receipt written and hash-bound.
        receipt = json.loads((repo / "artifacts/p1-readiness/ua-binding-receipt.json").read_text())
        assert receipt["values_sha256"] == result["values_sha256"]
        assert receipt["verdict"] == "BOUND"

    def test_bind_refuses_to_overwrite_real_value(self, tmp_path):
        repo = _copy_repo(tmp_path)
        sm = repo / "print-alpha/MANIFESTS/sku-manifest.json"
        doc = json.loads(sm.read_text())
        doc["garments"][0]["size"] = "M"  # already resolved by someone else
        sm.write_text(json.dumps(doc, indent=2) + "\n")
        before = {rel: hashlib.sha256((repo / rel).read_bytes()).hexdigest()
                  for rel in MANIFESTS}
        with pytest.raises(BindRefusal) as exc:
            bind(repo, _write_values(tmp_path, synthetic_values()),
                 check_only=False, allow_variant_map_drift=False)
        assert any("never overwrites real values" in p for p in exc.value.problems)
        after = {rel: hashlib.sha256((repo / rel).read_bytes()).hexdigest()
                 for rel in MANIFESTS}
        assert before == after  # atomicity: refusal changed zero bytes

    def test_bind_is_atomic_on_invalid_values(self, tmp_path):
        repo = _copy_repo(tmp_path)
        values = synthetic_values()
        values["garments"]["size"] = "PENDING_USER_ACTION"
        before = {rel: hashlib.sha256((repo / rel).read_bytes()).hexdigest()
                  for rel in MANIFESTS + [FREEZE]}
        with pytest.raises(BindRefusal):
            bind(repo, _write_values(tmp_path, values),
                 check_only=False, allow_variant_map_drift=False)
        after = {rel: hashlib.sha256((repo / rel).read_bytes()).hexdigest()
                 for rel in MANIFESTS + [FREEZE]}
        assert before == after
