import importlib.util
import json
import re
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
_LOCK_PATH = _REPO / "benchmarks" / "runtime_lock.json"
_MANIFEST_DIR = _REPO / "model_manifests"

_VERIFY_PATH = _REPO / "scripts" / "verify_runtime_lock.py"
_VERIFY_SPEC = importlib.util.spec_from_file_location("rac_verify_runtime_lock", _VERIFY_PATH)
assert _VERIFY_SPEC is not None and _VERIFY_SPEC.loader is not None
_VERIFY = importlib.util.module_from_spec(_VERIFY_SPEC)
_VERIFY_SPEC.loader.exec_module(_VERIFY)


@pytest.fixture(scope="module")
def lock() -> dict:
    return json.loads(_LOCK_PATH.read_text())


def test_runtime_lock_schema_fields_present(lock: dict):
    assert lock["schema_version"] == "1.0"
    for field in ("python", "torch", "torchvision", "ultralytics", "transformers"):
        assert isinstance(lock[field], str) and lock[field], field
    assert re.fullmatch(r"\d+\.\d+", lock["python"])
    # torch/torchvision CPU wheels carry the +cpu local specifier, which the
    # frozen manifests treat as significant.
    assert lock["torch"].endswith("+cpu")
    assert lock["torchvision"].endswith("+cpu")


def test_runtime_lock_matches_every_frozen_manifest(lock: dict):
    manifests = sorted(_MANIFEST_DIR.glob("*.json"))
    assert manifests, "no frozen model manifests found"
    seen_frameworks = set()
    for manifest_path in manifests:
        manifest = json.loads(manifest_path.read_text())
        framework = manifest["framework"]
        frozen_version = manifest["framework_version"]
        seen_frameworks.add(framework)
        assert framework in lock, f"{manifest_path.name}: framework {framework} not covered by runtime lock"
        assert lock[framework] == frozen_version, (
            f"{manifest_path.name}: runtime lock {lock[framework]} != frozen manifest {frozen_version}"
        )
    assert seen_frameworks == {"torchvision", "ultralytics", "transformers"}


def test_load_lock_roundtrip_and_validation(lock: dict, tmp_path: Path):
    loaded = _VERIFY.load_lock(_LOCK_PATH)
    assert loaded == lock
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"schema_version": "1.0", "python": "3.11"}))
    with pytest.raises(ValueError):
        _VERIFY.load_lock(bad)
    bad.write_text(json.dumps({**lock, "schema_version": "9.9"}))
    with pytest.raises(ValueError):
        _VERIFY.load_lock(bad)


def test_version_matches_exact_semantics():
    # Mirrors build_d2_bundle.verify_frozen_model_contract: plain equality, no normalization.
    assert _VERIFY.version_matches("0.29.0+cpu", "0.29.0+cpu")
    assert _VERIFY.version_matches("8.4.142", "8.4.142")
    assert not _VERIFY.version_matches("0.29.1+cpu", "0.29.0+cpu")
    # +cpu local specifier is significant: a non-CPU wheel must NOT match.
    assert not _VERIFY.version_matches("0.29.0", "0.29.0+cpu")
    assert not _VERIFY.version_matches("0.29.0+cpu", "0.29.0")
    assert not _VERIFY.version_matches("2.14.0+cu126", "2.14.0+cpu")


def test_python_matches(lock: dict):
    locked_major, locked_minor = (int(p) for p in lock["python"].split(".")[:2])
    assert _VERIFY.python_matches(lock) == ((__import__("sys").version_info[:2]) == (locked_major, locked_minor))
    wrong = dict(lock)
    wrong["python"] = "0.0"
    assert not _VERIFY.python_matches(wrong)


_WORKFLOWS = (
    _REPO / ".github" / "workflows" / "model-lock-bootstrap.yml",
    _REPO / ".github" / "workflows" / "measured-benchmark.yml",
)


@pytest.mark.parametrize("workflow", _WORKFLOWS, ids=lambda p: p.name)
def test_workflow_installs_from_runtime_lock_and_gates_before_inference(workflow: Path):
    text = workflow.read_text()
    # Installs all four pinned packages from the lock (single source of truth).
    for package in ("torch", "torchvision", "ultralytics", "transformers"):
        assert f"runtime_lock.json'))['{package}']" in text, f"{workflow.name}: {package} not installed from runtime_lock.json"
        assert f"{package}==${{" in text or f'"{package}==${{' in text, f"{workflow.name}: {package} not pinned with =="
    # No unpinned/broad installs of these packages remain.
    assert not re.search(r"pip install --index-url \S+ torch torchvision\b", text)
    # The gate runs before any model download / inference step.
    gate = text.index("scripts/verify_runtime_lock.py")
    if workflow.name == "measured-benchmark.yml":
        inference = text.index("run_measured_benchmark.py", text.index("steps:"))
    else:
        inference = text.index("bootstrap_model_lock.py", text.index("steps:"))
    assert gate < inference, f"{workflow.name}: runtime lock gate must run before inference"


def test_amendment_records_true_root_cause():
    text = (_REPO / "docs" / "AMENDMENT_D2-0004_INFRA-001.md").read_text()
    # The record must name the loader TypeError root cause and its fix commit,
    # and must not drift back to the refuted framework-drift narrative.
    assert "load_protocol" in text
    assert "generation_id" in text
    assert "7148202d" in text
    assert "TypeError" in text
    assert "REFUTED" in text
    assert "never observed" in text


def test_measured_benchmark_trigger_paths_unchanged():
    text = (_REPO / ".github" / "workflows" / "measured-benchmark.yml").read_text()
    trigger = text.split("jobs:", 1)[0]
    paths_block = re.search(r"paths:\n((?:\s+- .*\n)+)", trigger)
    assert paths_block is not None, "measured-benchmark.yml push trigger lost its paths: block"
    entries = re.findall(r"-\s+'([^']+)'", paths_block.group(1))
    assert entries == ["generations/RAC-PER-D2-0004.json"], entries
