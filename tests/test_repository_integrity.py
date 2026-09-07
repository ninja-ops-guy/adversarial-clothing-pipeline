import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_json(path: str):
    return json.loads((ROOT / path).read_text())


def test_current_manifest_protocol_and_sets_are_identical_contracts():
    manifest = load_json("benchmarks/model_manifest.json")
    protocol = load_json("protocols/RAC-PERSON-DETECT-1.2.json")
    surrogate = load_json("model_sets/PERSON-SUR-v3.json")
    heldout = load_json("model_sets/PERSON-HO-v3.json")

    manifest_surrogate = [m["id"] for m in manifest["models"] if m["role"] == "surrogate"]
    manifest_heldout = [m["id"] for m in manifest["models"] if m["role"] == "heldout"]

    assert manifest["lock_status"] == "PREREGISTERED"
    assert manifest["lock_inference_performed"] is False
    assert manifest_surrogate == surrogate["models"]
    assert manifest_heldout == heldout["models"]
    assert protocol["surrogate_model_set"] == surrogate["model_set_id"]
    assert protocol["heldout_model_set"] == heldout["model_set_id"]
    assert set(manifest_surrogate).isdisjoint(manifest_heldout)


def test_d2_0004_workflow_targets_fresh_generation_and_eight_models():
    workflow = (ROOT / ".github/workflows/measured-benchmark.yml").read_text()
    required = {
        "RAC-PERSON-DETECT-1.2.json",
        "RAC-PER-D2-0004",
        "PERSON-SUR-v3",
        "PERSON-HO-v3",
        "fasterrcnn_resnet50_fpn_v2",
        "maskrcnn_resnet50_fpn_v2",
        "Run environment-adaptive surrogate search",
        "Freeze adaptive winner before held-out inference",
        "lock_inference_performed",
        "Product Studio",
        "Build D2 evidence bundle",
        "Build high-resolution print-test assets",
        "Validate print-test kit boundary",
    }
    missing = sorted(item for item in required if item not in workflow)
    assert not missing, f"v3 Product Studio workflow contract missing: {missing}"


def test_frontend_workflow_references_existing_specs():
    workflow = (ROOT / ".github/workflows/frontend-e2e.yml").read_text()
    for spec in (
        "tests/e2e/pattern-lab.spec.js",
        "tests/e2e/product-studio.spec.js",
        "tests/e2e/production-studio.spec.js",
    ):
        if spec in workflow:
            assert (ROOT / spec).exists(), f"frontend workflow references missing spec: {spec}"


def test_current_published_result_matches_current_generation_when_v2_models_are_used():
    result_path = ROOT / "benchmark-results.json"
    status_path = ROOT / "d2-latest-status.json"
    if not result_path.exists() or not status_path.exists():
        return

    result = json.loads(result_path.read_text())
    status = json.loads(status_path.read_text())
    heldout = result.get("benchmark", {}).get("heldout_models", [])

    is_current_model_generation = heldout == ["fasterrcnn_resnet50_fpn_v2", "maskrcnn_resnet50_fpn_v2"]
    if is_current_model_generation:
        assert status.get("protocol_version") == "1.2"
        assert status.get("candidate_id") == "RAC-PER-D2-0004"
        assert status.get("surrogate_model_set") == "PERSON-SUR-v3"
        assert status.get("heldout_model_set") == "PERSON-HO-v3"
    else:
        # Historical D2-0003 evidence may remain published while D2-0004 is being
        # searched or before a manual held-out run. It must retain its old identity.
        assert status.get("candidate_id") == "RAC-PER-D2-0003"


def test_all_current_model_manifests_match_benchmark_hash_contract():
    manifest = load_json("benchmarks/model_manifest.json")
    for model in manifest["models"]:
        frozen = load_json(f"model_manifests/{model['id']}.json")
        assert frozen["weights_sha256"] == model["state_dict_sha256"]
        assert float(frozen["decision_threshold"]) == float(model["decision_threshold"])
        assert frozen["framework"] == model["framework"]
        assert frozen["framework_version"]
        assert frozen["preprocessing"]
