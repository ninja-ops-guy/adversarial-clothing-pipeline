from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .canonical import FORMAT_ID, sha256_hex


def refusal_receipt(reason: str, attempted_record: dict[str, Any], *, detail: str | None = None) -> dict[str, Any]:
    attempted_sha256 = sha256_hex(attempted_record)
    identity_payload = {"reason": reason, "attempted_record_sha256": attempted_sha256, "detail": detail}
    return {
        "schema": "rac.prc-refusal-receipt.v1",
        "receipt_id": f"RAC-PRC-REF-{sha256_hex(identity_payload)[:16].upper()}",
        "reason": reason,
        "detail": detail,
        "attempted_record_sha256": attempted_sha256,
        "canonical_format": FORMAT_ID,
        "created_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
    }
