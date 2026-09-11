from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools import p1_production_release as release
from tools import prepare_print_alpha_production as prep
from tests.test_prepare_print_alpha_production import _raw


def test_raw_validation_accepts_exact_identity_and_contract() -> None:
    summary = release.validate_raw_vendor_payloads(_raw(), "M")
    assert summary[388]["variant_id"] == 10871
    assert summary[257]["variant_id"] == 8852
    assert summary[388]["title"] == prep.PRODUCTS[388]["name"]


def test_raw_validation_refuses_wrong_product_identity() -> None:
    raw = _raw()
    payload = json.loads(raw[388]["product"])
    payload["result"]["product"]["id"] = 999
    raw[388]["product"] = json.dumps(payload).encode()
    with pytest.raises(release.ReleaseRefusal, match="identity mismatch"):
        release.validate_raw_vendor_payloads(raw, "M")


def test_raw_validation_refuses_unreviewed_extra_placement() -> None:
    raw = _raw()
    payload = json.loads(raw[388]["printfiles"])
    mapping = payload["result"]["variant_printfiles"][0]["placements"]
    mapping["surprise_panel"] = mapping["front"]
    raw[388]["printfiles"] = json.dumps(payload).encode()
    with pytest.raises(release.ReleaseRefusal, match="unexpected vendor placements"):
        release.validate_raw_vendor_payloads(raw, "M")


def test_vendor_intake_bundle_verifies_end_to_end(tmp_path: Path) -> None:
    output = tmp_path / "vendor"
    prep.build_vendor_intake(_raw(), "M", output)
    verified = release.verify_vendor_intake(output / "vendor-intake.json")
    assert verified["release_id"] == prep.RELEASE_ID
    assert verified["intake_sha256"]


def test_vendor_intake_self_hash_tamper_refused(tmp_path: Path) -> None:
    output = tmp_path / "vendor"
    prep.build_vendor_intake(_raw(), "M", output)
    path = output / "vendor-intake.json"
    payload = json.loads(path.read_text())
    payload["selected_size"] = "L"
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    with pytest.raises(release.ReleaseRefusal, match="self-hash mismatch"):
        release.verify_vendor_intake(path)


def test_vendor_archive_tamper_refused(tmp_path: Path) -> None:
    output = tmp_path / "vendor"
    prep.build_vendor_intake(_raw(), "M", output)
    archive = output / "printful-source-388.zip"
    archive.write_bytes(archive.read_bytes() + b"tamper")
    with pytest.raises(release.ReleaseRefusal, match="source archive hash mismatch"):
        release.verify_vendor_intake(output / "vendor-intake.json")


def test_raw_copy_tamper_refused(tmp_path: Path) -> None:
    output = tmp_path / "vendor"
    prep.build_vendor_intake(_raw(), "M", output)
    raw_file = output / "raw" / "products_257.json"
    raw_file.write_bytes(b"{}")
    with pytest.raises(release.ReleaseRefusal, match="raw source differs"):
        release.verify_vendor_intake(output / "vendor-intake.json")
