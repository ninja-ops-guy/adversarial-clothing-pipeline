#!/usr/bin/env python3
"""Fail-closed release wrapper for RAC-PRINT-ALPHA-001 production preparation.

This is the preferred operator entry point for the vendor-to-artwork phase.  It
wraps ``tools.prepare_print_alpha_production`` and adds evidence-integrity checks
that are intentionally stricter than the low-level preparation helper:

* exact Printful product id/title identity before intake is accepted;
* no unexpected non-mockup placement may appear silently;
* vendor-intake self-hash must re-derive before build;
* deterministic source archives and every recorded raw response hash must still
  match the bytes on disk;
* the existing Alpha-001 sealed-kit/pattern hashes remain mandatory;
* no spend, order placement, held-out access, arming, or efficacy claim occurs.

Use this wrapper for real production.  The underlying helper remains useful for
unit-level composition and recovery tooling.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import zipfile
from datetime import date
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools import prepare_print_alpha_production as prep  # noqa: E402


class ReleaseRefusal(RuntimeError):
    """Production release evidence failed a fail-closed integrity check."""


def _product_identity(payload: dict, product_id: int) -> tuple[int, str]:
    result = prep._result(payload)
    product = result.get("product")
    if not isinstance(product, dict):
        raise ReleaseRefusal(f"product {product_id}: result.product is missing")
    actual_id = product.get("id")
    title = product.get("title")
    if actual_id != product_id:
        raise ReleaseRefusal(
            f"product identity mismatch: requested {product_id}, response id={actual_id!r}"
        )
    expected_title = prep.PRODUCTS[product_id]["name"]
    if title != expected_title:
        raise ReleaseRefusal(
            f"product {product_id} title mismatch: {title!r} != {expected_title!r}"
        )
    return actual_id, title


def validate_raw_vendor_payloads(
    raw_payloads: dict[int, dict[str, bytes]], size: str
) -> dict[int, dict[str, Any]]:
    """Validate identity, selected variant and exact placement vocabulary."""
    summary: dict[int, dict[str, Any]] = {}
    for product_id, spec in prep.PRODUCTS.items():
        raw = raw_payloads.get(product_id)
        if not isinstance(raw, dict):
            raise ReleaseRefusal(f"missing raw payload set for product {product_id}")
        try:
            product_payload = prep.parse_json_bytes(raw["product"], f"product {product_id}")
            printfiles_payload = prep.parse_json_bytes(
                raw["printfiles"], f"printfiles {product_id}"
            )
            prep.parse_json_bytes(raw["templates"], f"templates {product_id}")
        except (KeyError, prep.ProductionRefusal) as exc:
            raise ReleaseRefusal(str(exc)) from exc

        _, title = _product_identity(product_payload, product_id)
        try:
            variant_id = prep.select_variant(product_payload, size)
            _, extras = prep.extract_geometry(
                printfiles_payload, variant_id, spec["panels"]
            )
        except prep.ProductionRefusal as exc:
            raise ReleaseRefusal(str(exc)) from exc
        if extras:
            raise ReleaseRefusal(
                f"product {product_id}: unexpected vendor placements require explicit review: {extras}"
            )
        summary[product_id] = {
            "product_id": product_id,
            "title": title,
            "size": size,
            "variant_id": variant_id,
            "placements": list(spec["panels"]),
        }
    return summary


def _rehash_intake(intake: dict) -> str:
    payload = dict(intake)
    expected = payload.pop("intake_sha256", None)
    if not isinstance(expected, str) or len(expected) != 64:
        raise ReleaseRefusal("vendor intake has no valid intake_sha256")
    actual = prep.sha256_bytes(prep.canonical_bytes(payload))
    if actual != expected:
        raise ReleaseRefusal(
            f"vendor intake self-hash mismatch: {actual} != {expected}"
        )
    return actual


def verify_vendor_intake(intake_path: Path) -> dict:
    """Verify the entire vendor-intake evidence bundle before artwork build."""
    if not intake_path.is_file():
        raise ReleaseRefusal(f"vendor intake missing: {intake_path}")
    try:
        intake = json.loads(intake_path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        raise ReleaseRefusal(f"vendor intake is not valid JSON: {exc}") from exc
    if intake.get("release_id") != prep.RELEASE_ID:
        raise ReleaseRefusal("vendor intake release_id mismatch")
    if intake.get("provider") != "Printful":
        raise ReleaseRefusal("vendor intake provider is not Printful")
    for key in ("physical_efficacy_claimed", "heldout_access", "spend_authorized", "order_placed"):
        if intake.get(key) is not False:
            raise ReleaseRefusal(f"vendor intake boundary {key} must remain false")
    _rehash_intake(intake)

    products = intake.get("products")
    if not isinstance(products, dict):
        raise ReleaseRefusal("vendor intake products map missing")
    root = intake_path.parent
    for product_id, spec in prep.PRODUCTS.items():
        record = products.get(str(product_id))
        if not isinstance(record, dict):
            raise ReleaseRefusal(f"vendor intake missing product {product_id}")
        if record.get("product_id") != product_id:
            raise ReleaseRefusal(f"vendor intake product {product_id} id drift")
        if record.get("product_name_expected") != spec["name"]:
            raise ReleaseRefusal(f"vendor intake product {product_id} expected-title drift")
        if record.get("required_panels") != list(spec["panels"]):
            raise ReleaseRefusal(f"vendor intake product {product_id} panel contract drift")
        if record.get("extra_vendor_placements") not in ([], None):
            raise ReleaseRefusal(
                f"vendor intake product {product_id} contains unreviewed extra placements"
            )

        archive = record.get("source_archive")
        if not isinstance(archive, dict):
            raise ReleaseRefusal(f"product {product_id}: source_archive missing")
        archive_name = archive.get("path")
        expected_archive_sha = archive.get("sha256")
        if not isinstance(archive_name, str) or Path(archive_name).name != archive_name:
            raise ReleaseRefusal(f"product {product_id}: unsafe source_archive path")
        archive_path = root / archive_name
        if not archive_path.is_file():
            raise ReleaseRefusal(f"product {product_id}: source archive missing: {archive_path}")
        actual_archive_sha = prep.sha256_file(archive_path)
        if actual_archive_sha != expected_archive_sha:
            raise ReleaseRefusal(
                f"product {product_id}: source archive hash mismatch"
            )

        source_files = record.get("source_files")
        if not isinstance(source_files, dict) or not source_files:
            raise ReleaseRefusal(f"product {product_id}: source_files evidence missing")
        with zipfile.ZipFile(archive_path) as zf:
            names = set(zf.namelist())
            if names != set(source_files):
                raise ReleaseRefusal(
                    f"product {product_id}: source archive member set mismatch"
                )
            for name, meta in source_files.items():
                if not isinstance(meta, dict):
                    raise ReleaseRefusal(f"product {product_id}: malformed source metadata")
                data = zf.read(name)
                if prep.sha256_bytes(data) != meta.get("sha256"):
                    raise ReleaseRefusal(
                        f"product {product_id}: archived source hash mismatch for {name}"
                    )
                if len(data) != meta.get("bytes"):
                    raise ReleaseRefusal(
                        f"product {product_id}: archived source length mismatch for {name}"
                    )
                raw_path = root / "raw" / name
                if not raw_path.is_file() or raw_path.read_bytes() != data:
                    raise ReleaseRefusal(
                        f"product {product_id}: raw source differs from archived bytes for {name}"
                    )
    return intake


def run_intake(args: argparse.Namespace) -> int:
    try:
        if args.fetch:
            token = os.environ.get(args.token_env, "")
            if not token:
                raise ReleaseRefusal(
                    f"--fetch requires non-empty {args.token_env}; the token is never stored"
                )
            raw = prep.fetch_raw_payloads(token)
        else:
            if not args.raw_dir:
                raise ReleaseRefusal("intake requires --fetch or --raw-dir")
            raw = prep.load_raw_dir(Path(args.raw_dir))
        summary = validate_raw_vendor_payloads(raw, args.size)
        output = Path(args.output_dir)
        receipt = prep.build_vendor_intake(raw, args.size, output)
        verify_vendor_intake(output / "vendor-intake.json")
    except (prep.ProductionRefusal, ReleaseRefusal) as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2

    print(json.dumps({
        "status": "VENDOR_INTAKE_VERIFIED",
        "release_id": prep.RELEASE_ID,
        "intake": str(output / "vendor-intake.json"),
        "intake_sha256": receipt["intake_sha256"],
        "products": summary,
        "spend_authorized": False,
        "order_placed": False,
        "physical_efficacy_claimed": False,
    }, indent=2, sort_keys=True))
    return 0


def run_build(args: argparse.Namespace) -> int:
    try:
        intake_path = Path(args.intake)
        intake = verify_vendor_intake(intake_path)
        pattern, source = prep.load_candidate_bytes(
            print_test_kit=Path(args.print_test_kit) if args.print_test_kit else None,
            candidate_pattern=Path(args.candidate_pattern) if args.candidate_pattern else None,
        )
        output = Path(args.output_dir)
        receipt = prep.build_panel_art_and_values(
            intake=intake,
            pattern_bytes=pattern,
            source=source,
            repo_root=Path(args.repo_root).resolve(),
            recorded_by=args.recorded_by,
            recorded_date=args.recorded_date,
            output_dir=output,
        )
        # Re-verify intake after rendering so a concurrent mutation cannot be
        # silently accepted between preflight and receipt generation.
        verify_vendor_intake(intake_path)
    except (prep.ProductionRefusal, ReleaseRefusal) as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2

    values = output / "ua-values.generated.json"
    print(json.dumps({
        "status": "BINDER_READY_VERIFIED",
        "release_id": prep.RELEASE_ID,
        "values": str(values),
        "values_sha256": receipt["values_sha256"],
        "candidate_pattern_sha256": source["pattern_sha256"],
        "next_check": f"python tools/p1_bind_ua_values.py --values {values} --check-only",
        "spend_authorized": False,
        "order_placed": False,
        "physical_efficacy_claimed": False,
        "heldout_access": False,
    }, indent=2, sort_keys=True))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)

    intake = sub.add_parser("intake", help="strictly ingest Printful production data")
    source = intake.add_mutually_exclusive_group(required=True)
    source.add_argument("--fetch", action="store_true")
    source.add_argument("--raw-dir")
    intake.add_argument("--token-env", default="PF_TOKEN")
    intake.add_argument("--size", required=True)
    intake.add_argument("--output-dir", default="production_alpha/vendor_intake")
    intake.set_defaults(func=run_intake)

    build = sub.add_parser("build", help="strictly release exact Alpha-001 panel art")
    build.add_argument(
        "--intake", default="production_alpha/vendor_intake/vendor-intake.json"
    )
    src = build.add_mutually_exclusive_group(required=True)
    src.add_argument("--print-test-kit")
    src.add_argument("--candidate-pattern")
    build.add_argument("--recorded-by", required=True)
    build.add_argument("--recorded-date", default=date.today().isoformat())
    build.add_argument("--repo-root", default=Path(__file__).resolve().parent.parent)
    build.add_argument("--output-dir", default="production_alpha/vendor_intake")
    build.set_defaults(func=run_build)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
