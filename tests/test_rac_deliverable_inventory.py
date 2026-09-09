"""Light structural contract for the Barrier-0 RAC deliverable inventory.

The inventory (artifacts/rac_deliverable_inventory.json) is owned by the
parallel swarm; these tests only pin its envelope (well-formedness, known
class vocabulary, safety flags) without asserting its content semantics.
"""

from __future__ import annotations

import json
from pathlib import Path

INVENTORY_PATH = (
    Path(__file__).resolve().parents[1]
    / "artifacts"
    / "rac_deliverable_inventory.json"
)

KNOWN_CLASSES = {
    "COMPLETE",
    "PARTIAL",
    "MISSING",
    "BLOCKED",
    "USER_ACTION_REQUIRED",
    "OWNED_BY_OTHER_SWARM",
}


def _load_inventory() -> dict:
    return json.loads(INVENTORY_PATH.read_text())


def test_inventory_is_well_formed():
    inv = _load_inventory()
    assert inv["inventory_id"]
    assert inv["repo"] == "ninja-ops-guy/adversarial-clothing-pipeline"
    assert isinstance(inv["requirements"], list) and inv["requirements"]
    assert set(inv["classes"]) == KNOWN_CLASSES


def test_inventory_safety_flags():
    inv = _load_inventory()
    # No physical-efficacy claims and D2-0005 must stay unarmed.
    assert inv["physical_efficacy_claimed"] is False
    d20005 = inv["scientific_state"]["D2-0005"]
    assert d20005["armed"] is False
    assert d20005["ready_to_arm"] is False


def test_inventory_requirement_classes_are_known():
    inv = _load_inventory()
    for req in inv["requirements"]:
        assert req["class"] in KNOWN_CLASSES, req["id"]
        assert isinstance(req.get("evidence", []), list)
