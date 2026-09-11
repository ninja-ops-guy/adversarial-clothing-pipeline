from __future__ import annotations

import hashlib
import io
import json
import zipfile
from pathlib import Path

import pytest
from PIL import Image

from tools import prepare_print_alpha_production as prep
from tools.p1_bind_ua_values import validate_values


def _product(product_id: int, title: str, variant_id: int, size: str = "M") -> bytes:
    return json.dumps({
        "code": 200,
        "result": {
            "product": {"id": product_id, "title": title},
            "variants": [
                {"id": variant_id, "size": size, "color": "White"},
                {"id": variant_id + 100, "size": "L", "color": "White"},
            ],
        },
    }, separators=(",", ":")).encode()


def _printfiles(product_id: int, variant_id: int, panels: tuple[str, ...]) -> bytes:
    printfiles = []
    placements = {}
    for i, panel in enumerate(panels, start=1):
        printfiles.append({
            "printfile_id": i,
            "width": 120 + i,
            "height": 180 + i,
            "dpi": 150,
            "fill_mode": "fit",
            "can_rotate": False,
        })
        placements[panel] = i
    return json.dumps({
        "code": 200,
        "result": {
            "product_id": product_id,
            "available_placements": {p: p for p in panels},
            "printfiles": printfiles,
            "variant_printfiles": [{"variant_id": variant_id, "placements": placements}],
        },
    }, separators=(",", ":")).encode()


def _templates(product_id: int) -> bytes:
    return json.dumps({
        "code": 200,
        "result": {"version": 1, "min_dpi": 150, "variant_mapping": [], "templates": []},
    }, separators=(",", ":")).encode()


def _raw() -> dict[int, dict[str, bytes]]:
    return {
        388: {
            "product": _product(388, prep.PRODUCTS[388]["name"], 10871),
            "printfiles": _printfiles(388, 10871, prep.PRODUCTS[388]["panels"]),
            "templates": _templates(388),
        },
        257: {
            "product": _product(257, prep.PRODUCTS[257]["name"], 8852),
            "printfiles": _printfiles(257, 8852, prep.PRODUCTS[257]["panels"]),
            "templates": _templates(257),
        },
    }


def _pattern_png() -> bytes:
    im = Image.new("RGB", (7, 5), (20, 30, 40))
    im.putpixel((0, 0), (255, 0, 0))
    buf = io.BytesIO()
    im.save(buf, format="PNG", optimize=False, compress_level=9)
    return buf.getvalue()


def test_select_variant_is_exact_and_fail_closed() -> None:
    payload = json.loads(_product(388, "Hoodie", 10871))
    assert prep.select_variant(payload, "M") == 10871
    with pytest.raises(prep.ProductionRefusal):
        prep.select_variant(payload, "XS")


def test_extract_geometry_joins_variant_mapping() -> None:
    panels = ("front", "back")
    payload = json.loads(_printfiles(388, 10871, panels))
    geometry, extras = prep.extract_geometry(payload, 10871, panels)
    assert extras == []
    assert geometry["front"]["width_px"] == 121
    assert geometry["back"]["height_px"] == 182
    assert geometry["front"]["width_mm"] == round(121 / 150 * 25.4, 6)


def test_extract_geometry_refuses_missing_required_placement() -> None:
    payload = json.loads(_printfiles(388, 10871, ("front",)))
    with pytest.raises(prep.ProductionRefusal, match="missing required placements"):
        prep.extract_geometry(payload, 10871, ("front", "back"))


def test_vendor_intake_is_hash_bound_and_archives_raw_bytes(tmp_path: Path) -> None:
    out = tmp_path / "vendor"
    receipt = prep.build_vendor_intake(_raw(), "M", out)
    assert receipt["release_id"] == prep.RELEASE_ID
    assert receipt["products"]["388"]["variant_id"] == 10871
    assert receipt["products"]["257"]["variant_id"] == 8852
    assert receipt["physical_efficacy_claimed"] is False
    for pid in (388, 257):
        archive = out / f"printful-source-{pid}.zip"
        assert archive.is_file()
        assert prep.sha256_file(archive) == receipt["products"][str(pid)]["source_archive"]["sha256"]
        with zipfile.ZipFile(archive) as zf:
            assert zf.read(f"printfiles_{pid}.json") == _raw()[pid]["printfiles"]


def test_fixed_zip_is_deterministic(tmp_path: Path) -> None:
    files = [("b.txt", b"b"), ("a.txt", b"a")]
    a = tmp_path / "a.zip"
    b = tmp_path / "b.zip"
    assert prep._fixed_zip(a, files) == prep._fixed_zip(b, list(reversed(files)))
    assert a.read_bytes() == b.read_bytes()


def test_candidate_source_verifies_exact_zip_and_inner_pattern(tmp_path: Path) -> None:
    pattern = _pattern_png()
    kit = tmp_path / "kit.zip"
    with zipfile.ZipFile(kit, "w") as zf:
        zf.writestr("print-test-kit/design/pattern_tile_4096.png", pattern)
    data, source = prep.load_candidate_bytes(
        print_test_kit=kit,
        expected_pattern_sha256=hashlib.sha256(pattern).hexdigest(),
        expected_kit_sha256=prep.sha256_file(kit),
    )
    assert data == pattern
    assert source["mode"] == "sealed_print_test_kit"
    assert source["pattern_sha256"] == hashlib.sha256(pattern).hexdigest()


def test_panel_png_is_deterministic_and_control_is_distinct() -> None:
    pattern = _pattern_png()
    cand1 = prep._panel_png(pattern, 31, 29, control=False)
    cand2 = prep._panel_png(pattern, 31, 29, control=False)
    ctrl = prep._panel_png(pattern, 31, 29, control=True)
    assert cand1 == cand2
    assert hashlib.sha256(cand1).digest() != hashlib.sha256(ctrl).digest()
    assert Image.open(io.BytesIO(cand1)).size == (31, 29)


def test_build_panel_art_writes_real_binder_ready_values(tmp_path: Path) -> None:
    intake_dir = tmp_path / "intake"
    intake = prep.build_vendor_intake(_raw(), "M", intake_dir)
    repo = tmp_path / "repo"
    out = repo / "production_alpha" / "vendor_intake"
    receipt = prep.build_panel_art_and_values(
        intake,
        _pattern_png(),
        {"mode": "test", "pattern_sha256": "x" * 64},
        repo,
        "test-operator",
        "2026-09-11",
        out,
    )
    values = json.loads((out / "ua-values.generated.json").read_text())
    assert validate_values(values) == []
    assert values["garments"]["size"] == "M"
    assert values["garments"]["hoodie_variant_id"] == 10871
    assert values["garments"]["tee_variant_id"] == 8852
    assert values["mapping_files"]["front"]["candidate_file"] == "print-alpha/CANDIDATE/front.png"
    assert (repo / "print-alpha" / "CANDIDATE" / "front.png").is_file()
    assert (repo / "print-alpha" / "CONTROL" / "front.png").is_file()
    assert len(values["article_artwork_sha256"]["PA-HOODIE-CAND-001"]) == 64
    assert receipt["spend_authorized"] is False
    assert receipt["physical_efficacy_claimed"] is False
