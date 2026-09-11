from __future__ import annotations

import json
import re
from pathlib import Path

from ruthless_pipeline.patterns import P0_GENERATORS


ROOT = Path(__file__).resolve().parents[2]
CATALOG = ROOT / "studio-research-catalog.js"


def _browser_p0_ids() -> list[str]:
    text = CATALOG.read_text(encoding="utf-8")
    match = re.search(r"P0_CATALOG_JSON \*/(\[[^;]+\]);", text)
    assert match, "studio research catalog must expose a machine-readable P0_CATALOG_JSON list"
    return json.loads(match.group(1))


def test_browser_catalog_matches_runtime_p0_inventory_exactly() -> None:
    assert _browser_p0_ids() == [generator.name for generator in P0_GENERATORS]


def test_browser_catalog_is_loaded_by_both_studio_surfaces() -> None:
    product_loader = (ROOT / "studio-global.js").read_text(encoding="utf-8")
    production_loader = (ROOT / "vendor-template-guard.js").read_text(encoding="utf-8")
    assert "studio-research-catalog.js" in product_loader
    assert "studio-research-catalog.js" in production_loader


def test_deferred_and_refused_families_are_not_promoted_into_p0_catalog() -> None:
    ids = set(_browser_p0_ids())
    assert "bad_words" not in ids
    assert "web_attack_strings" not in ids
    assert len(ids) == 8
