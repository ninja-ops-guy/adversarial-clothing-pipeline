"""Compile the canonical program state (SW-01).

Usage::

    PYTHONPATH=. python scripts/compile_program_state.py [--check] [--format json|summary]

Default mode regenerates ``program_state/program_state.json`` and
``program_state/SUMMARY.md`` deterministically from the canonical sources
(experiment records, sealed status JSON, freeze candidate, releases,
Barrier-3 report/audit, P1 readiness, CTM registry, frozen-surface pins).
``--check`` is the CI gate: exit 1 when the committed artifacts are stale
or the sources contradict; it writes nothing.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from ruthless_pipeline.program_state.compile import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
