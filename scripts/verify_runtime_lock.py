"""Pre-inference runtime gate for the frozen model software contract.

Loads ``benchmarks/runtime_lock.json`` and fails closed unless the installed
``torch``/``torchvision``/``ultralytics``/``transformers`` versions match the
locked strings EXACTLY, using the same semantics as
``scripts/build_d2_bundle.py::verify_frozen_model_contract``: a plain string
equality check with no normalization. The frozen model manifests record local
version specifiers verbatim (e.g. ``torchvision == "0.29.0+cpu"``), so the
``+cpu`` suffix is part of the locked value and must match character for
character. Also asserts the Python major.minor version.
"""

from __future__ import annotations

import argparse
import importlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ruthless_pipeline.certification.schema_version import require_schema_version

DEFAULT_LOCK_PATH = Path(__file__).resolve().parents[1] / "benchmarks" / "runtime_lock.json"

REQUIRED_FIELDS = ("python", "torch", "torchvision", "ultralytics", "transformers")

FRAMEWORK_MODULES = ("torch", "torchvision", "ultralytics", "transformers")


def load_lock(path: Path) -> dict:
    lock = json.loads(Path(path).read_text())
    require_schema_version(lock, "1.0", label="runtime lock")
    for field in REQUIRED_FIELDS:
        value = lock.get(field)
        if not isinstance(value, str) or not value:
            raise ValueError(f"runtime lock missing required field: {field}")
    return lock


def version_matches(installed: str, locked: str) -> bool:
    """Mirror the frozen-contract comparison in build_d2_bundle.py exactly.

    ``verify_frozen_model_contract`` raises unless
    ``str(manifest['framework_version']) == str(measured['framework_version'])``;
    there is deliberately no normalization. ``+cpu`` local specifiers are
    therefore significant and must match verbatim.
    """
    return str(installed) == str(locked)


def python_matches(lock: dict) -> bool:
    locked_major, locked_minor = (int(part) for part in lock["python"].split(".")[:2])
    return sys.version_info[:2] == (locked_major, locked_minor)


def installed_versions() -> dict:
    versions = {}
    for name in FRAMEWORK_MODULES:
        try:
            module = importlib.import_module(name)
        except ImportError:
            versions[name] = None
        else:
            versions[name] = str(module.__version__)
    return versions


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify the installed runtime against the frozen model software contract.")
    parser.add_argument("--lock", default=str(DEFAULT_LOCK_PATH), help="path to benchmarks/runtime_lock.json")
    args = parser.parse_args()

    lock = load_lock(Path(args.lock))
    installed = installed_versions()

    failures = []
    for name in FRAMEWORK_MODULES:
        locked = lock[name]
        found = installed[name]
        print(f"{name}: installed={found if found is not None else 'NOT INSTALLED'} locked={locked}")
        if found is None:
            failures.append(f"{name}: not installed (locked {locked})")
        elif not version_matches(found, locked):
            failures.append(f"{name}: installed {found} != locked {locked}")

    locked_python = lock["python"]
    installed_python = f"{sys.version_info.major}.{sys.version_info.minor}"
    print(f"python: installed={installed_python} locked={locked_python}")
    if not python_matches(lock):
        failures.append(f"python: installed {installed_python} != locked {locked_python}")

    if failures:
        print("RUNTIME LOCK VIOLATION: installed frameworks do not satisfy the frozen model software contract:", file=sys.stderr)
        for failure in failures:
            print(f"  {failure}", file=sys.stderr)
        return 1

    print("runtime lock satisfied: installed runtime matches the frozen model software contract")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
