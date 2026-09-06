from __future__ import annotations

import argparse
import json
from pathlib import Path

from ruthless_pipeline.certification import (
    ArtifactBundle,
    ArtifactRef,
    EvidenceState,
    PatternManifest,
    issue_certificate,
    load_protocol,
    verify_certificate_bundle,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Issue or verify an internal RAC evidence certificate.")
    sub = parser.add_subparsers(dest="command", required=True)
    issue = sub.add_parser("issue")
    issue.add_argument("--bundle", required=True)
    issue.add_argument("--manifest", required=True)
    issue.add_argument("--protocol", required=True)
    issue.add_argument("--benchmark", required=True)
    issue.add_argument(
        "--master",
        help="Optional path to the immutable master artifact. If supplied it is copied into the bundle at manifest.master.path.",
    )
    issue.add_argument("--state", default="RAC-D2", choices=[state.value for state in EvidenceState])
    issue.add_argument("--physical-evidence", action="store_true")
    verify = sub.add_parser("verify")
    verify.add_argument("--bundle", required=True)
    args = parser.parse_args()

    if args.command == "verify":
        ok, failures = verify_certificate_bundle(args.bundle)
        print(json.dumps({"verified": ok, "failures": failures}, indent=2))
        return 0 if ok else 1

    payload = json.loads(Path(args.manifest).read_text())
    payload["master"] = ArtifactRef(**payload["master"])
    payload["evidence_state"] = EvidenceState(payload.get("evidence_state", "RAC-D0"))
    manifest = PatternManifest(**payload)
    benchmark = json.loads(Path(args.benchmark).read_text())
    summary = benchmark.get("summary", benchmark)
    bundle = ArtifactBundle.create(args.bundle)
    bundled_master = bundle.resolve_path(manifest.master.path)
    if args.master:
        source_master = Path(args.master)
        if not source_master.exists() or not source_master.is_file():
            raise SystemExit(f"master artifact not found: {source_master}")
        bundled_master.parent.mkdir(parents=True, exist_ok=True)
        bundled_master.write_bytes(source_master.read_bytes())
    cert = issue_certificate(
        bundle=bundle,
        manifest=manifest,
        protocol=load_protocol(args.protocol),
        digital_summary=summary,
        requested_state=EvidenceState(args.state),
        physical_evidence_present=args.physical_evidence,
    )
    print(json.dumps({"certificate_id": cert.certificate_id, "decision": cert.decision.value}, indent=2))
    return 0 if cert.decision.value == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
