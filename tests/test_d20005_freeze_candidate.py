"""Freeze-candidate integrity tests for the D2-0005 amendment A5 package.

Guards (all fail-closed, pre-arming only — nothing here arms or executes anything):

1. ``docs/D2-0005_FREEZE_CANDIDATE.json`` parses and passes
   ``require_schema_version`` at its registered schema version.
2. Every sha256 recorded in the manifest recomputes byte-for-byte against the
   file it pins (drift in any frozen input breaks the freeze).
3. Every OLD text block quoted in ``docs/PREREGISTRATION_D2-0005_AMENDMENT_A5.md``
   (fenced ```old blocks) appears VERBATIM in the frozen
   ``docs/PREREGISTRATION_D2-0005.md`` — so a silent edit of either document is
   caught.
4. Every expected schema id/version in the manifest references a schema version
   registered in this repository (or is explicitly null for legacy unversioned
   model-set files, which are then asserted to carry no schema_version key).
5. The freeze is keyed to a well-formed commit and carries the NOT_ARMED status.
"""

import hashlib
import json
import re
from pathlib import Path

import pytest

from ruthless_pipeline.certification.schema_version import require_schema_version

REPO_ROOT = Path(__file__).resolve().parents[1]

MANIFEST_PATH = REPO_ROOT / "docs" / "D2-0005_FREEZE_CANDIDATE.json"
AMENDMENT_PATH = REPO_ROOT / "docs" / "PREREGISTRATION_D2-0005_AMENDMENT_A5.md"
PREREG_PATH = REPO_ROOT / "docs" / "PREREGISTRATION_D2-0005.md"

FREEZE_SCHEMA_ID = "d2-0005-freeze-candidate"
FREEZE_SCHEMA_VERSION = "1.0"
KEYED_COMMIT = "67dd53fee37279ffb032e480053e165ebf6217fb"


def _load_manifest():
    payload = json.loads(MANIFEST_PATH.read_text())
    require_schema_version(payload, FREEZE_SCHEMA_VERSION, label="D2-0005 freeze manifest")
    assert payload["schema_id"] == FREEZE_SCHEMA_ID
    return payload


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# --------------------------------------------------------------------------
# 1-2. Manifest parses, passes the schema guard, and its hashes recompute
# --------------------------------------------------------------------------

def test_manifest_parses_and_passes_schema_guard():
    manifest = _load_manifest()
    assert manifest["generation_id"] == "RAC-PER-D2-0005"
    assert manifest["status"] == "FREEZE_CANDIDATE_NOT_ARMED_PENDING_REHEARSAL_AND_AUDIT"


def test_manifest_rejects_wrong_schema_version():
    payload = json.loads(MANIFEST_PATH.read_text())
    payload["schema_version"] = "9.9"
    with pytest.raises(ValueError):
        require_schema_version(payload, FREEZE_SCHEMA_VERSION, label="freeze manifest")


def _hash_pinned_entries(manifest):
    entries = []
    for group in ("governing_documents", "analysis_implementation"):
        for name, entry in manifest[group].items():
            if isinstance(entry, dict) and entry.get("sha256") and entry.get("path"):
                entries.append((f"{group}.{name}", entry["path"], entry["sha256"]))
    for entry in manifest["frozen_inputs"]:
        entries.append((f"frozen_inputs.{entry['name']}", entry["path"], entry["sha256"]))
    return entries


def test_manifest_hashes_exist_and_recompute():
    manifest = _load_manifest()
    entries = _hash_pinned_entries(manifest)
    assert entries, "manifest must pin at least one sha256"
    for label, rel_path, recorded in entries:
        path = REPO_ROOT / rel_path
        assert path.is_file(), f"{label}: pinned file missing: {rel_path}"
        actual = _sha256(path)
        assert actual == recorded, f"{label}: sha256 drift at {rel_path}"


def test_analysis_implementation_pins_match_author_attestation():
    manifest = _load_manifest()
    impl = manifest["analysis_implementation"]
    assert impl["module"]["sha256"] == (
        "bad02b22a9061dd3baf273d92facff42c847f4da2c2e08ed891ac118f6094674"
    )
    assert impl["design_script"]["sha256"] == (
        "ddaab35f4afe382ce096808b3b083a46420c01480397c82c13f99878a91b6737"
    )


# --------------------------------------------------------------------------
# 3. Amendment OLD quotes appear verbatim in the frozen preregistration
# --------------------------------------------------------------------------

def _old_blocks():
    text = AMENDMENT_PATH.read_text()
    blocks = re.findall(r"```old\n(.*?)```", text, flags=re.DOTALL)
    assert blocks, "amendment doc must quote at least one OLD block"
    return [block.rstrip("\n") for block in blocks]


def test_amendment_old_quotes_verbatim_in_frozen_preregistration():
    prereg = PREREG_PATH.read_text()
    blocks = _old_blocks()
    assert len(blocks) >= 9, "expected OLD quotes for every amended clause"
    for i, block in enumerate(blocks):
        assert block in prereg, (
            f"OLD block {i} of the amendment no longer appears verbatim in "
            "docs/PREREGISTRATION_D2-0005.md (drift guard)"
        )


def test_amendment_header_is_not_armed():
    text = AMENDMENT_PATH.read_text()
    assert "NOT_ARMED_PENDING_REHEARSAL_AND_AUDIT" in text
    assert "FREEZE CANDIDATE" in text


# --------------------------------------------------------------------------
# 4. Expected schemas reference registered schema versions
# --------------------------------------------------------------------------

def _registered_schemas():
    """Authoritative schema id -> version map, sourced from the repo itself."""
    import scripts.design_analysis_d20005_cluster as cluster_design
    from ruthless_pipeline.certification import telemetry_contract

    runtime_lock = json.loads(
        (REPO_ROOT / "benchmarks" / "runtime_lock.json").read_text()
    )
    oc_artifact = json.loads(
        (REPO_ROOT / "artifacts" / "design_analysis_d20005_cluster" / "results.json").read_text()
    )
    registered = {
        FREEZE_SCHEMA_ID: FREEZE_SCHEMA_VERSION,
        "d2-0005-freeze-seeds": "1.0",
        "d2-0005-freeze-model-sets": "1.0",
        "d2-0005-fixture-protocol": "1.0",
        "d2-0005-fixture-manifest": "1.0",
        "d2-0005-rehearsal-icc": "1.0",
        "d2-0005-cluster-paired-arm-statistics": "1.0",
        "runtime-lock": runtime_lock["schema_version"],
        "design-analysis-d20005-cluster": cluster_design.SCHEMA_VERSION,
        "telemetry-contract": telemetry_contract.CONTRACT_VERSION,
    }
    # Cross-checks: the registered versions must agree with the actual artifacts.
    require_schema_version(runtime_lock, registered["runtime-lock"], label="runtime lock")
    require_schema_version(
        oc_artifact, registered["design-analysis-d20005-cluster"], label="OC artifact"
    )
    return registered


def test_all_manifest_schemas_registered():
    manifest = _load_manifest()
    registered = _registered_schemas()
    entries = list(manifest["frozen_inputs"]) + list(manifest["planned_outputs"])
    assert entries, "manifest must enumerate expected artifacts"
    for entry in entries:
        schema_id = entry["schema_id"]
        version = entry["schema_version"]
        if schema_id == "model-set":
            # Legacy unversioned model-set files: pinned by hash only; assert
            # they really carry no schema_version key so a future schema bump
            # cannot pass silently.
            assert version is None
            payload = json.loads((REPO_ROOT / entry["path"]).read_text())
            assert "schema_version" not in payload
            continue
        assert schema_id in registered, f"unregistered schema id {schema_id!r}"
        assert version == registered[schema_id], (
            f"{schema_id}: manifest expects {version!r}, repo registers "
            f"{registered[schema_id]!r}"
        )


def test_freeze_config_files_pass_their_declared_schemas():
    registered = _registered_schemas()
    for rel in (
        "ruthless_pipeline/certification/config/d20005_freeze/seeds.json",
        "ruthless_pipeline/certification/config/d20005_freeze/model_sets.json",
        "ruthless_pipeline/certification/config/d20005_freeze/fixture_protocol.json",
    ):
        payload = json.loads((REPO_ROOT / rel).read_text())
        require_schema_version(payload, registered[payload["schema_id"]], label=rel)
        assert payload["status"].startswith("FREEZE_CANDIDATE_NOT_ARMED")


# --------------------------------------------------------------------------
# 5. Commit keying and non-arming
# --------------------------------------------------------------------------

def test_keyed_commit_is_well_formed_and_pinned():
    manifest = _load_manifest()
    commit = manifest["keyed_to_commit"]
    assert re.fullmatch(r"[0-9a-f]{40}", commit)
    assert commit == KEYED_COMMIT
    assert manifest["arming"]["armed"] is False
