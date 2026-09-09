"""Tests for ruthless_pipeline/certification/print_package_integrity.py.

Tamper-injection contract: modifying, deleting, or renaming any bound
artifact MUST invalidate the package (status TAMPERED). Unresolved vendor /
physical artifacts stay PENDING_USER_ACTION and are reported as such —
never bound as final, never promoted to PASS.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from ruthless_pipeline.certification.print_package_integrity import (
    INCOMPLETE,
    INTACT,
    PENDING,
    TAMPERED,
    bind_artifact,
    bind_pending,
    build_package_manifest,
    build_print_alpha_manifest,
    canonical_bytes,
    verify_package,
)

REPO_ROOT = Path(__file__).resolve().parents[2]


def _fixture_package(tmp_path: Path) -> tuple[Path, dict]:
    root = tmp_path / "pkg"
    (root / "art").mkdir(parents=True)
    (root / "docs").mkdir(parents=True)
    files = {
        "art/candidate_front.png": b"candidate-front-bytes",
        "art/control_front.png": b"control-front-bytes",
        "docs/capture-protocol.md": b"capture protocol text",
        "docs/trial-sheet.csv": b"trial,1\n",
    }
    for rel, payload in files.items():
        (root / rel).write_bytes(payload)
    entries = [
        bind_artifact(root, "art/candidate_front.png", "candidate_artwork"),
        bind_artifact(root, "art/control_front.png", "control_artwork"),
        bind_artifact(root, "docs/capture-protocol.md", "capture_protocol"),
        bind_artifact(root, "docs/trial-sheet.csv", "trial_sheet"),
    ]
    return root, build_package_manifest(root, entries)


class TestDeterminism:
    def test_manifest_byte_identical_rebuild(self, tmp_path):
        root, m1 = _fixture_package(tmp_path)
        m2 = build_print_alpha_manifest(REPO_ROOT)
        assert canonical_bytes(m2) == canonical_bytes(build_print_alpha_manifest(REPO_ROOT))
        _, m1b = _fixture_package(tmp_path / "second")
        # same bytes -> same manifest except for identical content
        root2 = tmp_path / "second" / "pkg"
        entries = [
            bind_artifact(root2, "art/candidate_front.png", "candidate_artwork"),
            bind_artifact(root2, "art/control_front.png", "control_artwork"),
            bind_artifact(root2, "docs/capture-protocol.md", "capture_protocol"),
            bind_artifact(root2, "docs/trial-sheet.csv", "trial_sheet"),
        ]
        m1b = build_package_manifest(root2, entries)
        assert m1["package_root_sha256"] == m1b["package_root_sha256"]

    def test_canonical_bytes_sorted_keys(self):
        payload = {"b": 1, "a": {"z": 2, "y": 3}}
        out = canonical_bytes(payload)
        assert out == canonical_bytes(json.loads(out))
        assert out.endswith(b"\n")


class TestIntact:
    def test_fully_bound_package_is_intact(self, tmp_path):
        root, manifest = _fixture_package(tmp_path)
        report = verify_package(manifest, root)
        assert report["status"] == INTACT
        assert report["verified_count"] == 4
        assert report["mismatches"] == []
        assert report["pending_user_action"] == []
        assert report["package_root_sha256_valid"] is True


class TestTamperInjection:
    def test_modify_bound_artifact_invalidates(self, tmp_path):
        root, manifest = _fixture_package(tmp_path)
        target = root / "art" / "candidate_front.png"
        target.write_bytes(target.read_bytes() + b"tampered")
        report = verify_package(manifest, root)
        assert report["status"] == TAMPERED
        assert report["mismatches"][0]["reason"] == "sha256_mismatch"
        assert report["mismatches"][0]["path"] == "art/candidate_front.png"

    def test_delete_bound_artifact_invalidates(self, tmp_path):
        root, manifest = _fixture_package(tmp_path)
        (root / "docs" / "trial-sheet.csv").unlink()
        report = verify_package(manifest, root)
        assert report["status"] == TAMPERED
        assert report["mismatches"][0]["reason"] == "missing_file"

    def test_single_byte_flip_in_any_bound_file(self, tmp_path):
        for rel in (
            "art/candidate_front.png",
            "art/control_front.png",
            "docs/capture-protocol.md",
            "docs/trial-sheet.csv",
        ):
            sub = tmp_path / rel.replace("/", "_")
            root, manifest = _fixture_package(sub)
            path = root / rel
            data = bytearray(path.read_bytes())
            data[0] ^= 0x01
            path.write_bytes(bytes(data))
            report = verify_package(manifest, root)
            assert report["status"] == TAMPERED, rel

    def test_manifest_entry_tamper_detected_via_root_hash(self, tmp_path):
        root, manifest = _fixture_package(tmp_path)
        tampered = json.loads(canonical_bytes(manifest))
        tampered["artifacts"][0]["sha256"] = hashlib.sha256(b"evil").hexdigest()
        report = verify_package(tampered, root)
        assert report["status"] == TAMPERED
        assert report["package_root_sha256_valid"] is False

    def test_swap_candidate_control_detected(self, tmp_path):
        root, manifest = _fixture_package(tmp_path)
        cand = root / "art" / "candidate_front.png"
        ctrl = root / "art" / "control_front.png"
        cand_bytes, ctrl_bytes = cand.read_bytes(), ctrl.read_bytes()
        cand.write_bytes(ctrl_bytes)
        ctrl.write_bytes(cand_bytes)
        report = verify_package(manifest, root)
        assert report["status"] == TAMPERED
        assert len(report["mismatches"]) == 2

    def test_efficacy_claim_true_invalidates(self, tmp_path):
        root, manifest = _fixture_package(tmp_path)
        tampered = json.loads(canonical_bytes(manifest))
        tampered["physical_efficacy_claimed"] = True
        report = verify_package(tampered, root)
        assert report["status"] == TAMPERED


class TestPendingNeverBoundAsFinal:
    def test_pending_entry_reported_not_tampered(self, tmp_path):
        root, _ = _fixture_package(tmp_path)
        entries = [
            bind_artifact(root, "art/candidate_front.png", "candidate_artwork"),
            bind_pending("art/control_front.png", "control_artwork"),
        ]
        manifest = build_package_manifest(root, entries)
        report = verify_package(manifest, root)
        assert report["status"] == INCOMPLETE
        assert report["pending_user_action"] == ["art/control_front.png"]
        assert report["mismatches"] == []

    def test_pending_never_intact(self, tmp_path):
        root = tmp_path / "pkg"
        entries = [bind_pending("missing.png", "candidate_artwork")]
        manifest = build_package_manifest(root, entries)
        report = verify_package(manifest, root)
        assert report["status"] == INCOMPLETE
        assert report["status"] != INTACT

    def test_bind_artifact_never_fabricates_hash(self, tmp_path):
        entry = bind_artifact(tmp_path, "does/not/exist.png", "candidate_artwork")
        assert entry["sha256"] == PENDING
        assert entry["status"] == PENDING

    def test_noncanonical_hash_field_fails_closed(self, tmp_path):
        root, manifest = _fixture_package(tmp_path)
        tampered = json.loads(canonical_bytes(manifest))
        tampered["artifacts"][0]["sha256"] = "pending_review"  # near-miss
        tampered["artifacts"][0]["status"] = "bound"
        # fix root hash so only the bad field is under test
        from ruthless_pipeline.certification.print_package_integrity import (
            build_package_manifest as _bpm,
        )

        rebuilt = _bpm(root, tampered["artifacts"])
        report = verify_package(rebuilt, root)
        assert report["status"] == TAMPERED
        assert any(
            m["reason"] == "non_canonical_hash_field" for m in report["mismatches"]
        )


class TestLiveRepoPackage:
    def test_real_print_alpha_package_incomplete_not_tampered(self):
        manifest = build_print_alpha_manifest(REPO_ROOT)
        report = verify_package(manifest, REPO_ROOT)
        # Pre-UA-1: artwork/template/calibration PNGs do not exist and must be
        # reported PENDING_USER_ACTION — never INTACT, never TAMPERED.
        assert report["status"] == INCOMPLETE
        assert report["mismatches"] == []
        pending = report["pending_user_action"]
        assert any(p.startswith("print-alpha/CANDIDATE/") for p in pending)
        assert any(p.startswith("print-alpha/CONTROL/") for p in pending)
        # Bound digital artifacts must verify.
        assert "print-alpha/CAPTURE/trial-sheet.csv" in report["verified"]
        assert "print-alpha/MANIFESTS/print-alpha-manifest.json" in report["verified"]
        assert report["physical_efficacy_claimed"] is False
        assert report["evidence_class"] == "experimental_print_specimen"

    def test_real_package_manifest_deterministic(self):
        m1 = build_print_alpha_manifest(REPO_ROOT)
        m2 = build_print_alpha_manifest(REPO_ROOT)
        assert canonical_bytes(m1) == canonical_bytes(m2)
        assert m1["package_root_sha256"] == m2["package_root_sha256"]

    def test_committed_package_manifest_is_schema_versioned(self):
        data = json.loads(
            (REPO_ROOT / "artifacts" / "print-alpha" / "package-manifest.json").read_text()
        )
        assert data["schema_version"] == "1.0"
        assert data["release_id"] == "RAC-PRINT-ALPHA-001"
        assert data["physical_efficacy_claimed"] is False
        assert data["evidence_class"] == "experimental_print_specimen"
        # Root hash self-consistent over its own entry list.
        stripped = {k: v for k, v in data.items() if k != "package_root_sha256"}
        assert (
            hashlib.sha256(canonical_bytes(stripped)).hexdigest()
            == data["package_root_sha256"]
        )
        # Unresolved vendor/physical artifacts remain PENDING_USER_ACTION.
        statuses = {e["status"] for e in data["artifacts"]}
        assert statuses <= {"bound", PENDING}
        assert PENDING in statuses
