from __future__ import annotations

import hashlib
import json
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request

import pytest

import scripts.fetch_printful_vendor_snapshot as snapshot


class FakeResponse:
    def __init__(self, body: bytes, status: int = 200) -> None:
        self.body = body
        self.status = status

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def read(self) -> bytes:
        return self.body

    def getcode(self) -> int:
        return self.status


def _responses(product_id: int = 388) -> dict[str, bytes]:
    base = snapshot.BASE_URL
    return {
        f"{base}/oauth/scopes": b'{"result":["catalog"]}',
        f"{base}/mockup-generator/printfiles/{product_id}": b'{"result":{"printfiles":[]}}',
        f"{base}/mockup-generator/templates/{product_id}": b'{"result":{"templates":[]}}',
        f"{base}/v2/catalog-products/{product_id}": b'{"data":{"id":388}}',
        f"{base}/v2/catalog-products/{product_id}/catalog-variants": b'{"data":[]}',
    }


def test_snapshot_writes_exact_vendor_bytes_and_hash_manifest(tmp_path: Path) -> None:
    responses = _responses()
    requests: list[Request] = []

    def opener(request: Request, timeout: float):
        assert timeout == 7.0
        requests.append(request)
        return FakeResponse(responses[request.full_url])

    manifest = snapshot.fetch_snapshot(
        token="private-fixture-token",
        out_dir=tmp_path,
        timeout=7.0,
        opener=opener,
        retrieved_at_utc="2026-09-10T18:00:00Z",
    )

    assert manifest["provider"] == "Printful"
    assert manifest["product_id"] == 388
    assert manifest["ordering_performed"] is False
    assert manifest["token_persisted"] is False
    assert len(manifest["files"]) == 5

    for record in manifest["files"]:
        raw = responses[record["endpoint"]]
        assert (tmp_path / record["filename"]).read_bytes() == raw
        assert record["sha256"] == hashlib.sha256(raw).hexdigest()
        assert record["bytes"] == len(raw)

    persisted = json.loads((tmp_path / "snapshot-manifest.json").read_text())
    assert persisted == manifest
    assert "private-fixture-token" not in (tmp_path / "snapshot-manifest.json").read_text()
    assert all(
        request.get_header("Authorization") == "Bearer private-fixture-token"
        for request in requests
    )
    assert all(request.get_method() == "GET" for request in requests)


def test_missing_token_fails_before_network_or_filesystem(tmp_path: Path) -> None:
    called = False

    def opener(request: Request, timeout: float):
        nonlocal called
        called = True
        raise AssertionError("network must not be called")

    out_dir = tmp_path / "snapshot"
    with pytest.raises(snapshot.VendorSnapshotError, match="PF_TOKEN"):
        snapshot.fetch_snapshot(token="", out_dir=out_dir, opener=opener)
    assert called is False
    assert not out_dir.exists()


def test_non_200_fails_without_writing_partial_snapshot(tmp_path: Path) -> None:
    responses = _responses()
    calls = 0

    def opener(request: Request, timeout: float):
        nonlocal calls
        calls += 1
        body = responses[request.full_url]
        if calls == 3:
            return FakeResponse(body, status=503)
        return FakeResponse(body)

    out_dir = tmp_path / "snapshot"
    with pytest.raises(snapshot.VendorSnapshotError, match="HTTP 503"):
        snapshot.fetch_snapshot(
            token="private-fixture-token",
            out_dir=out_dir,
            opener=opener,
        )
    assert not out_dir.exists()


def test_invalid_json_fails_closed_without_writing(tmp_path: Path) -> None:
    responses = _responses()

    def opener(request: Request, timeout: float):
        if "templates" in request.full_url:
            return FakeResponse(b"not-json")
        return FakeResponse(responses[request.full_url])

    out_dir = tmp_path / "snapshot"
    with pytest.raises(snapshot.VendorSnapshotError, match="valid JSON"):
        snapshot.fetch_snapshot(
            token="private-fixture-token",
            out_dir=out_dir,
            opener=opener,
        )
    assert not out_dir.exists()


def test_network_error_is_fail_closed_and_does_not_echo_token(tmp_path: Path) -> None:
    def opener(request: Request, timeout: float):
        raise URLError("offline")

    with pytest.raises(snapshot.VendorSnapshotError) as exc_info:
        snapshot.fetch_snapshot(
            token="secret-token-never-echo",
            out_dir=tmp_path / "snapshot",
            opener=opener,
        )
    assert "secret-token-never-echo" not in str(exc_info.value)


def test_invalid_product_id_is_rejected_before_network(tmp_path: Path) -> None:
    def opener(request: Request, timeout: float):
        raise AssertionError("network must not be called")

    with pytest.raises(snapshot.VendorSnapshotError, match="positive integer"):
        snapshot.fetch_snapshot(
            token="fixture",
            product_id=0,
            out_dir=tmp_path / "snapshot",
            opener=opener,
        )
