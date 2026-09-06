import json
import subprocess
import sys
from pathlib import Path


def test_d2_bundle_rejects_stale_or_unlocked_result(tmp_path: Path):
    result = {
        "status": "measured_unlocked",
        "certification_eligible": False,
        "candidate": {"config": {"candidate_id": "RAC-PER-D2-0002"}},
    }
    result_path = tmp_path / "result.json"
    candidate = tmp_path / "candidate.png"
    result_path.write_text(json.dumps(result))
    candidate.write_bytes(b"not-used")

    proc = subprocess.run(
        [
            sys.executable,
            "scripts/build_d2_bundle.py",
            "--result",
            str(result_path),
            "--candidate",
            str(candidate),
            "--protocol",
            "protocols/RAC-PERSON-DETECT-1.1.json",
            "--output",
            str(tmp_path / "bundle"),
        ],
        text=True,
        capture_output=True,
    )
    assert proc.returncode != 0
    assert "detector ensemble is not preregistered" in (proc.stdout + proc.stderr)


def test_v2_protocol_and_model_sets_are_preregistered_and_distinct():
    protocol = json.loads(Path("protocols/RAC-PERSON-DETECT-1.1.json").read_text())
    surrogate = json.loads(Path("model_sets/PERSON-SUR-v2.json").read_text())
    heldout = json.loads(Path("model_sets/PERSON-HO-v2.json").read_text())

    assert protocol["version"] == "1.1"
    assert protocol["surrogate_model_set"] == surrogate["model_set_id"]
    assert protocol["heldout_model_set"] == heldout["model_set_id"]
    assert surrogate["status"] == "PREREGISTERED"
    assert heldout["status"] == "PREREGISTERED"
    assert set(surrogate["models"]).isdisjoint(heldout["models"])
    assert heldout["models"] == ["retinanet_resnet50_fpn_v2", "fcos_resnet50_fpn"]


def test_all_v2_model_manifests_pin_runtime_and_weight_hash():
    ids = [
        "yolov8n",
        "fasterrcnn_mobilenet_v3_320",
        "detr_resnet50",
        "ssdlite320_mobilenet_v3",
        "retinanet_resnet50_fpn_v2",
        "fcos_resnet50_fpn",
    ]
    for model_id in ids:
        payload = json.loads(Path(f"model_manifests/{model_id}.json").read_text())
        digest = payload["weights_sha256"]
        assert len(digest) == 64
        int(digest, 16)
        assert payload["framework"]
        assert payload["framework_version"]
        assert 0 <= float(payload["decision_threshold"]) <= 1
