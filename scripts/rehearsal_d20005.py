"""CLI driver for the D2-0005 non-held-out rehearsal harness.

Exercises BOTH amendment-A5 arms (surrogate-selection, held-out-confirmation)
end to end over SYNTHETIC inputs only: fixture -> selection -> freeze ->
cluster-robust paired analysis -> evidence sealing -> publication-style
release -> manuscript export row (scratch path), plus the A5.5 rehearsal ICC
gate probes (one run above and one below ICC = 0.25).

Nothing here is evidence: every artifact carries
evidence_class "synthetic_pipeline_validation_only" and
rac_evidence_eligible: false. The final stdout line is always:
RESULT: synthetic_pipeline_validation_only — not RAC evidence

Usage:
    python scripts/rehearsal_d20005.py --output-dir /tmp/d20005-rehearsal
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ruthless_pipeline.certification import rehearsal_d20005 as rehearsal


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", required=True,
                        help="scratch output directory (NEVER under manuscript/ or fixtures/)")
    parser.add_argument("--clusters", type=int, default=rehearsal.MIN_CLUSTERS)
    parser.add_argument("--created-utc", default=rehearsal.DEFAULT_CREATED_UTC)
    parser.add_argument("--crash-after", default=None, choices=rehearsal.STAGES,
                        help="inject a deliberate crash after this stage (testing only)")
    args = parser.parse_args(argv)

    output_dir = Path(args.output_dir)
    resolved = output_dir.resolve()
    for forbidden in ("manuscript", "fixtures", "generations", "releases", "artifacts"):
        if forbidden in resolved.parts:
            parser.error(f"--output-dir must be a scratch path, not under {forbidden}/")

    summary = rehearsal.run_rehearsal(
        output_dir, k=args.clusters, created_utc=args.created_utc,
        crash_after=args.crash_after,
    )

    # ICC gate probes (A5.5): one above, one below the 0.25 gate.
    icc_report = {}
    for mode in ("high", "low"):
        probe = rehearsal.make_icc_probe_clusters(mode)
        rho, design_effect, n_eff = rehearsal.realized_icc(probe)
        decision = rehearsal.icc_gate_decision(rho)
        icc_report[mode] = {
            "realized_icc": rho,
            "design_effect": design_effect,
            "effective_sample_size": n_eff,
            "gate_passed": decision["gate_passed"],
        }
    icc_payload = rehearsal._label({
        "schema_id": "d2-0005-rehearsal-icc",
        "gate": rehearsal.ICC_GATE_MAX,
        "probes": icc_report,
        "note": "Outcome-free synthetic ICC probes proving the A5.5 ICC<=0.25 gate is exercisable.",
    })
    rehearsal._write_json(output_dir / "icc-gate-probes.json", icc_payload)

    print(json.dumps({"summary_sha256": summary["summary_sha256"],
                      "decision": summary["decision"],
                      "release_verified": summary["release_verified"],
                      "icc_probes": icc_report}, indent=2, sort_keys=True))
    print(rehearsal.RESULT_LINE)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
