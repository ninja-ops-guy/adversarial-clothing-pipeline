"""Barrier 3 integration tests: composition, determinism, replay, and the
failure-injection gate on the integrated path.

All runs are synthetic (synthetic_pipeline_validation_only). No held-out
models, no measured evidence, physical_efficacy_claimed=False throughout.
"""

from __future__ import annotations

import json

import jsonschema
import numpy as np
import pytest

from ruthless_pipeline.integration import barrier3
from ruthless_pipeline.integration.barrier3 import (
    Barrier3Config,
    Barrier3Error,
    run_barrier3,
    verify_artifact_hashes,
    verify_provenance,
    verify_replay,
    write_replay_report,
)
from ruthless_pipeline.optimization.objective_registry import NaNRefusalError
from ruthless_pipeline.optimization.schemas import ObjectiveSpec
from ruthless_pipeline.physical_transfer.transfer_record import (
    emit as emit_transfer_record,
)
from ruthless_pipeline.transformations.distribution import validate_spec_dict


@pytest.fixture(scope="module")
def run_dirs(tmp_path_factory):
    config = Barrier3Config()
    a = tmp_path_factory.mktemp("b3a")
    b = tmp_path_factory.mktemp("b3b")
    manifest = run_barrier3(config, a)
    run_barrier3(config, b)
    report = verify_replay(a, b)
    write_replay_report(report, a)
    return a, b, manifest, report


class TestComposition:
    def test_all_six_stages_present(self, run_dirs):
        a, _, manifest, _ = run_dirs
        stages = [s["stage"] for s in manifest["stages"]]
        assert stages == [
            "optimization_v3",
            "eot",
            "detector_science",
            "pareto_style",
            "printability",
            "physical_transfer",
        ]

    def test_artifact_package_complete(self, run_dirs):
        a, _, _, _ = run_dirs
        expected = {
            "run-manifest.json",
            "input-hashes.json",
            "runtime-environment.json",
            "objective-telemetry.json",
            "provenance.json",
            "hashes.sha256",
        }
        present = {p.name for p in a.iterdir() if p.is_file()}
        assert expected <= present
        stage_files = {p.name for p in (a / "stage-artifacts").iterdir()}
        assert stage_files == {
            "stage1-optimization.json",
            "stage2-eot.json",
            "stage3-detector-science.json",
            "stage4-pareto-style.json",
            "stage5-printability.json",
            "stage6-physical-transfer.json",
        }

    def test_every_stage_proves_lineage(self, run_dirs):
        a, _, manifest, _ = run_dirs
        for stage in manifest["stages"]:
            for key in (
                "input_source",
                "input_sha256",
                "configuration",
                "seed",
                "version",
                "output_sha256",
                "upstream",
            ):
                assert stage[key] is not None, f"{stage['stage']} missing {key}"
            assert len(stage["input_sha256"]) == 64

    def test_artifact_integrity_clean(self, run_dirs):
        a, _, _, _ = run_dirs
        assert verify_artifact_hashes(a) == []

    def test_provenance_clean(self, run_dirs):
        a, _, _, _ = run_dirs
        assert verify_provenance(a) == []

    def test_scientific_boundaries(self, run_dirs):
        _, _, manifest, _ = run_dirs
        assert manifest["evidence_class"] == "synthetic_pipeline_validation_only"
        assert manifest["physical_efficacy_claimed"] is False
        assert manifest["held_out_models_accessed"] is False
        assert manifest["d2_0004_modified"] is False
        assert manifest["d2_0005_armed"] is False

    def test_optimization_result_is_pool_member(self, run_dirs):
        a, _, manifest, _ = run_dirs
        stage1 = json.loads((a / "stage-artifacts" / "stage1-optimization.json").read_text())
        assert manifest["best_candidate_id"] in stage1["per_candidate_total"]
        assert stage1["per_candidate_total"][manifest["best_candidate_id"]] == pytest.approx(
            manifest["best_value"]
        )


class TestDeterministicReplay:
    def test_two_runs_equivalent(self, run_dirs):
        _, _, _, report = run_dirs
        assert report["verdict"] == "PASS"
        assert report["replay_equivalent"] is True
        assert report["mismatched_artifacts"] == []
        assert report["stage_seeds_equal"] is True

    def test_different_seed_diverges(self, tmp_path):
        a = tmp_path / "a"
        b = tmp_path / "b"
        run_barrier3(Barrier3Config(master_seed=1), a)
        run_barrier3(Barrier3Config(master_seed=2), b)
        report = verify_replay(a, b)
        assert report["verdict"] == "FAIL"
        assert report["mismatched_artifacts"]  # unexpected drift detection works


class TestFailureInjectionGate:
    """The integrated path fails closed on injected faults; no silent recovery."""

    def test_corrupt_stage_artifact_detected(self, run_dirs, tmp_path):
        a, _, _, _ = run_dirs
        target = a / "stage-artifacts" / "stage3-detector-science.json"
        payload = json.loads(target.read_text())
        payload["detector_loss"]["b3-cand-000"] = 0.123456789
        target.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
        violations = verify_artifact_hashes(a)
        assert any("stage3-detector-science.json" in v for v in violations)
        assert any("tampered" in v or "mismatch" in v for v in violations)

    def test_missing_stage_artifact_detected(self, tmp_path):
        out = tmp_path / "run"
        run_barrier3(Barrier3Config(), out)
        (out / "stage-artifacts" / "stage5-printability.json").unlink()
        violations = verify_provenance(out)
        assert any("silent stage skip" in v for v in violations)

    def test_broken_provenance_edge_detected(self, tmp_path):
        out = tmp_path / "run"
        run_barrier3(Barrier3Config(), out)
        prov_path = out / "provenance.json"
        prov = json.loads(prov_path.read_text())
        prov["stages"][0]["upstream"] = ["stage-artifacts/does-not-exist.json"]
        prov_path.write_text(json.dumps(prov, indent=2, sort_keys=True) + "\n")
        violations = verify_provenance(out)
        assert any("broken provenance edge" in v for v in violations)

    def test_invalid_objective_refused(self):
        with pytest.raises(jsonschema.ValidationError):
            ObjectiveSpec.from_dict(
                {
                    "schema_version": "1.0",
                    "objective_id": "bad",
                    "seed": 1,
                    "terms": {"detector_loss": {"aggregation": "CVAR", "log_separately": True}},
                    "future_generations_only": True,
                }
            )

    def test_nonfinite_objective_refused(self):
        from ruthless_pipeline.optimization.objective_registry import Objective

        spec = ObjectiveSpec.from_dict(
            {
                "schema_version": "1.0",
                "objective_id": "nan-fixture",
                "seed": 1,
                "terms": {"regularization": {"lambda_reg": 1.0, "log_separately": True}},
                "future_generations_only": True,
            }
        )
        obj = Objective(spec)
        obj.register_term("regularization", lambda p: (float("nan"), {}))
        with pytest.raises(NaNRefusalError):
            obj.evaluate(np.zeros(4))

    def test_invalid_eot_distribution_refused(self):
        with pytest.raises(jsonschema.ValidationError):
            validate_spec_dict(
                {
                    "schema_version": "1.0",
                    "distribution_id": "bad",
                    "parameter_manifest": {"geometry": {"scale": {"type": "cauchy", "params": {"x0": 0}}}},
                    "seed": 1,
                    "sampling_reproducibility_note": "x",
                    "robustness_surface": {
                        "grid_axes": ["geometry.scale"],
                        "response_metric": "r",
                        "cell_value_type": "scalar",
                        "scalar_only_permitted": False,
                    },
                }
            )

    def test_unknown_detector_family_refused(self):
        from ruthless_pipeline.detector_science.family_registry import (
            UnknownFamilyError,
            family_for_model,
        )

        with pytest.raises((UnknownFamilyError, KeyError)):
            family_for_model("nonexistent-detector-xyz")

    def test_synthetic_presented_as_measured_refused(self):
        """Synthetic evidence can never promote to measured: the promotion
        gate refuses it, and emit() forces synthetic_generator frames to the
        synthetic class even when a measured class is requested."""
        from scripts.ingest_capture_inference import enforce_promotion_gate

        with pytest.raises(ValueError, match="promotion gate"):
            enforce_promotion_gate(
                {
                    "evidence_class": "synthetic_pipeline_validation_only",
                    "calibration_pass": True,
                }
            )
        record = emit_transfer_record(
            artwork=b"a",
            template=b"t",
            mapping=b"m",
            captured_frame=b"f",
            garment_sku="x",
            fabric="x",
            print_process="x",
            capture_id="x",
            camera="x",
            lighting="x",
            pose="x",
            view="x",
            synthetic_generator=True,
            evidence_class="measured_physical_capture",
        )
        assert record["evidence_class"] == "synthetic_pipeline_validation_only"
        assert record["physical_efficacy_claimed"] is False

    def test_wrong_input_hash_detected(self, tmp_path):
        out = tmp_path / "run"
        run_barrier3(Barrier3Config(), out)
        ih_path = out / "input-hashes.json"
        ih = json.loads(ih_path.read_text())
        ih["config_sha256"] = "0" * 64
        ih_path.write_text(json.dumps(ih, indent=2, sort_keys=True) + "\n")
        assert verify_artifact_hashes(out)  # tampered input pin detected

    def test_candidate_control_collision_refused(self):
        from scripts_print_alpha.validate_manifests import validate_mapping_pairing

        with pytest.raises(jsonschema.ValidationError):
            validate_mapping_pairing(
                {"placements": [{"control_file": "x.jpg", "candidate_file": "x.jpg"}]}
            )

    def test_stale_production_mapping_refused(self, tmp_path):
        import hashlib

        from scripts_print_alpha.validate_manifests import validate_mapping_source_pin

        source = tmp_path / "sku-manifest.json"
        source.write_text('{"garments": ["v1"]}')
        with pytest.raises(jsonschema.ValidationError):
            validate_mapping_source_pin(
                {"source_manifest_sha256": hashlib.sha256(b"old").hexdigest()}, source
            )

    def test_config_rejects_invalid_params(self):
        with pytest.raises(Barrier3Error):
            Barrier3Config(n_candidates=1)
        with pytest.raises(Barrier3Error):
            Barrier3Config(aggregation="CVAR", alpha=0.0)
        with pytest.raises(Barrier3Error):
            Barrier3Config(n_detectors=99)
