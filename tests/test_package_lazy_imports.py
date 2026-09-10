"""Regression tests for the package's lightweight import boundary."""

from __future__ import annotations

import subprocess
import sys
from textwrap import dedent


def _run_isolated(source: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-c", dedent(source)],
        check=False,
        capture_output=True,
        text=True,
    )


def test_plain_package_import_does_not_eager_load_ml_stack() -> None:
    result = _run_isolated(
        """
        import sys
        import ruthless_pipeline

        forbidden = {"torch", "torchvision", "numpy", "scipy", "PIL"}
        loaded = sorted(name for name in forbidden if name in sys.modules)
        assert not loaded, f"heavy modules imported eagerly: {loaded}"
        assert ruthless_pipeline.__version__ == "3.1.0"
        """
    )
    assert result.returncode == 0, result.stderr


def test_provenance_import_is_independent_of_ml_dependencies() -> None:
    result = _run_isolated(
        """
        import builtins

        real_import = builtins.__import__
        forbidden = {"torch", "torchvision", "numpy", "scipy", "PIL"}

        def guarded_import(name, globals=None, locals=None, fromlist=(), level=0):
            if name.split(".", 1)[0] in forbidden:
                raise AssertionError(f"unexpected heavy dependency import: {name}")
            return real_import(name, globals, locals, fromlist, level)

        builtins.__import__ = guarded_import
        from ruthless_pipeline.certification import provenance_graph

        assert provenance_graph.GRAPH_SCHEMA_ID == "rac-provenance-graph"
        """
    )
    assert result.returncode == 0, result.stderr


def test_lazy_public_export_resolves_and_is_cached() -> None:
    import ruthless_pipeline

    assert "BenchmarkConfig" not in ruthless_pipeline.__dict__
    resolved = ruthless_pipeline.BenchmarkConfig
    assert resolved.__module__ == "ruthless_pipeline.benchmark"
    assert ruthless_pipeline.__dict__["BenchmarkConfig"] is resolved
