"""Fetch a read-only, hash-pinned Printful snapshot for Production Alpha.

This helper reduces Print Alpha UA-1/UA-2/UA-4 to one local command while
preserving the repository's fail-closed vendor boundary.  It only performs
GET requests, reads the bearer token from an environment variable, writes the
raw response bytes unchanged, and records SHA-256 digests in a snapshot
manifest.  It never creates an order, mutates a production manifest, or stores
the token.

Usage::

    export PF_TOKEN=<private token>
    python scripts/fetch_printful_vendor_snapshot.py

The resulting files are inputs to the existing template/SKU binding workflow;
they are not proof that Print Alpha is vendor-bound until the normal manifests
are updated and revalidated.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

BASE_URL = "https://api.printful.com"
DEFAULT_PRODUCT_ID = 388
DEFAULT_OUT_DIR = Path("production_alpha/vendor_snapshot")
USER_AGENT = "RAC-Print-Alpha-Vendor-Snapshot/1.0"


class VendorSnapshotError(RuntimeError):
    """Live vendor data could not be captured without ambiguity."""


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _endpoint_specs(product_id: int) -> tuple[tuple[str, str], ...]:
    return (
        ("oauth-scopes.json", f"{BASE_URL}/oauth/scopes"),
        (
            f"printfiles_{product_id}.json",
            f"{BASE_URL}/mockup-generator/printfiles/{product_id}",
        ),
        (
            f"templates_{product_id}.json",
            f"{BASE_URL}/mockup-generator/templates/{product_id}",
        ),
        (
            f"catalog-product_{product_id}.json",
            f"{BASE_URL}/v2/catalog-products/{product_id}",
        ),
        (
            f"catalog-variants_{product_id}.json",
            f"{BASE_URL}/v2/catalog-products/{product_id}/catalog-variants",
        ),
    )


def _read_response(
    *,
    url: str,
    token: str,
    timeout: float,
    opener: Callable[..., Any],
) -> bytes:
    request = Request(
        url,
        method="GET",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "User-Agent": USER_AGENT,
        },
    )
    try:
        with opener(request, timeout=timeout) as response:
            status = getattr(response, "status", None)
            if status is None:
                status = response.getcode()
            body = response.read()
    except HTTPError as exc:
        raise VendorSnapshotError(
            f"Printful GET failed with HTTP {exc.code}: {url}"
        ) from exc
    except URLError as exc:
        raise VendorSnapshotError(f"Printful GET failed: {url}: {exc.reason}") from exc

    if int(status) != 200:
        raise VendorSnapshotError(f"Printful GET returned HTTP {status}: {url}")
    if not body:
        raise VendorSnapshotError(f"Printful GET returned an empty body: {url}")
    try:
        json.loads(body)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise VendorSnapshotError(
            f"Printful GET did not return valid JSON: {url}"
        ) from exc
    return body


def fetch_snapshot(
    *,
    token: str,
    product_id: int = DEFAULT_PRODUCT_ID,
    out_dir: str | Path = DEFAULT_OUT_DIR,
    timeout: float = 30.0,
    opener: Callable[..., Any] = urlopen,
    retrieved_at_utc: str | None = None,
) -> dict[str, Any]:
    """Capture all read-only vendor inputs and return the snapshot manifest.

    All requests complete successfully before any file is written, preventing a
    partial snapshot from being mistaken for a complete vendor capture.
    """
    token = token.strip() if isinstance(token, str) else ""
    if not token:
        raise VendorSnapshotError("PF_TOKEN is required and must remain local")
    if not isinstance(product_id, int) or isinstance(product_id, bool) or product_id < 1:
        raise VendorSnapshotError("product_id must be a positive integer")
    if timeout <= 0:
        raise VendorSnapshotError("timeout must be positive")

    captured: list[tuple[str, str, bytes]] = []
    for filename, url in _endpoint_specs(product_id):
        body = _read_response(url=url, token=token, timeout=timeout, opener=opener)
        captured.append((filename, url, body))

    output = Path(out_dir)
    output.mkdir(parents=True, exist_ok=True)
    file_records: list[dict[str, Any]] = []
    for filename, url, body in captured:
        path = output / filename
        path.write_bytes(body)
        file_records.append(
            {
                "filename": filename,
                "endpoint": url,
                "bytes": len(body),
                "sha256": _sha256(body),
            }
        )

    manifest: dict[str, Any] = {
        "schema_version": "1.0",
        "provider": "Printful",
        "product_id": product_id,
        "retrieved_at_utc": retrieved_at_utc or _utc_now(),
        "source": "live_vendor_api_read_only",
        "evidence_class": "vendor_snapshot_unbound",
        "ordering_performed": False,
        "token_persisted": False,
        "files": file_records,
        "next_gate": (
            "bind exact template, placement geometry, artwork hashes, and matched "
            "variant into Print Alpha manifests; then rerun readiness validation"
        ),
    }
    manifest_bytes = (
        json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    ).encode("utf-8")
    (output / "snapshot-manifest.json").write_bytes(manifest_bytes)
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--product-id", type=int, default=DEFAULT_PRODUCT_ID)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument(
        "--token-env",
        default="PF_TOKEN",
        help="environment variable containing the private Printful token",
    )
    args = parser.parse_args(argv)

    token = os.environ.get(args.token_env, "")
    try:
        manifest = fetch_snapshot(
            token=token,
            product_id=args.product_id,
            out_dir=args.out_dir,
            timeout=args.timeout,
        )
    except VendorSnapshotError as exc:
        parser.error(str(exc))

    print(
        json.dumps(
            {
                "status": "VENDOR_SNAPSHOT_CAPTURED",
                "out_dir": str(args.out_dir),
                "product_id": manifest["product_id"],
                "files": len(manifest["files"]),
                "ordering_performed": False,
                "token_persisted": False,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
