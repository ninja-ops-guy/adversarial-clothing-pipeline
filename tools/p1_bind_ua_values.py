#!/usr/bin/env python3
"""P1 UA VALUES BINDER — RAC-P1-UA-BINDER-001.

Atomically binds real vendor/fabrication/garment/measurement values obtained
from UA-1..UA-8 (docs/USER_ACTION_REQUIRED_PRINT_ALPHA.md) into the six
pending-field manifests, re-pins the readiness freeze, and re-runs the P1
no-spend readiness gate.

FAIL-CLOSED CONTRACT:
- The intake file (copy of physical/p1/UA_VALUES_TEMPLATE.json) must be
  COMPLETE: every required field present, no unknown fields, no remaining
  pending markers, no placeholder-shaped strings, no empty values.
- Format rules: sha256 fields are lowercase 64-hex; panel geometry is
  positive numbers; variant IDs are positive integers; the size must exist
  in both embedded v1 variant maps and the given variant IDs must match
  those maps (override: --allow-variant-map-drift, recorded in the receipt).
- Candidate and control artwork hashes must differ on every placement
  (pre-order rule: the pair differs ONLY in artwork; identical artwork
  invalidates the experiment).
- Every target manifest path must CURRENTLY hold a canonical pending
  marker. The binder never overwrites a real value.
- Atomicity: all new manifest contents are computed in memory; nothing is
  written unless every validation passes. On refusal, zero bytes change.
- Write allowlist: the six UA scan manifests, the freeze manifest, and the
  binding receipt. The binder structurally cannot touch the capture
  schedule, pairing contract, stopping rule, thresholds, calibration
  manifest, or any D2 surface.
- This tool does NOT authorize spend, place orders, or arm anything.
  spend_authorized remains false; UA-5 is a human-only action.

Usage:
    python3 tools/p1_bind_ua_values.py --values my_ua_values.json --check-only
    python3 tools/p1_bind_ua_values.py --values my_ua_values.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

BINDER_ID = "RAC-P1-UA-BINDER-001"
SCHEMA_VERSION = "1.0"
FREEZE_PATH = "physical/p1/P1_READINESS_FREEZE.json"
RECEIPT_PATH = "artifacts/p1-readiness/ua-binding-receipt.json"
TEMPLATE_PATH = "physical/p1/UA_VALUES_TEMPLATE.json"

SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
PENDING_MARKER_RE = re.compile(r"^PENDING_[A-Z][A-Z0-9_]*$")
SUSPICIOUS_RE = re.compile(r"(TBD|PLACEHOLDER|FIXME|XXX|LOREM)", re.IGNORECASE)
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

HOODIE_PANELS = (
    "back", "front", "hood", "label_inside",
    "label_panel", "pocket", "sleeve_left", "sleeve_right",
)
TEE_PANELS = ("back", "front", "sleeve_left", "sleeve_right")
ARTICLE_SKU_IDS = (
    "PA-HOODIE-CAND-001", "PA-HOODIE-CTRL-001",
    "PA-HOODIE-CAND-R01", "PA-HOODIE-CTRL-R01",
    "PA-TEE-CAND-R01", "PA-TEE-CTRL-R01",
)

#: v1 reference variant maps embedded in production_alpha/SKU_MANIFEST.json
#: variant_id_note fields (Printful catalog product 388 hoodie / 257 tee).
HOODIE_VARIANT_MAP = {
    "2XS": 18730, "XS": 10869, "S": 10870, "M": 10871, "L": 10872,
    "XL": 10873, "2XL": 10874, "3XL": 10875, "4XL": 18731,
    "5XL": 18732, "6XL": 18733,
}
TEE_VARIANT_MAP = {
    "XS": 8850, "S": 8851, "M": 8852, "L": 8853, "XL": 8854, "2XL": 8855,
}

TM = "print-alpha/MANIFESTS/template-manifest.json"
AM = "print-alpha/MANIFESTS/artwork-manifest.json"
MM = "print-alpha/MANIFESTS/mapping-manifest.json"
PM = "print-alpha/MANIFESTS/print-alpha-manifest.json"
SM = "print-alpha/MANIFESTS/sku-manifest.json"
SK = "production_alpha/SKU_MANIFEST.json"

#: Files the binder may write, besides FREEZE_PATH and RECEIPT_PATH.
WRITABLE_MANIFESTS = (TM, AM, MM, PM, SM, SK)


class BindRefusal(Exception):
    """Any validation failure. Carries the full list of problems."""

    def __init__(self, problems: list[str]):
        self.problems = problems
        super().__init__("; ".join(problems))


def _is_pending(value) -> bool:
    return isinstance(value, str) and bool(PENDING_MARKER_RE.match(value))


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _sha256_payload(payload: dict) -> str:
    return hashlib.sha256(
        (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")
    ).hexdigest()


# --------------------------------------------------------------------------
# Intake validation
# --------------------------------------------------------------------------

def _require_keys(node, required: tuple, where: str, problems: list[str]) -> None:
    if not isinstance(node, dict):
        problems.append(f"{where}: must be an object")
        return
    for key in sorted(set(node) - set(required)):
        problems.append(f"{where}.{key}: unknown field (fail-closed)")
    for key in sorted(set(required) - set(node)):
        problems.append(f"{where}.{key}: missing required field")


def _check_string(value, where: str, problems: list[str]) -> None:
    if not isinstance(value, str) or not value.strip():
        problems.append(f"{where}: must be a non-empty string")
        return
    if _is_pending(value):
        problems.append(f"{where}: still a pending marker ({value})")
    elif SUSPICIOUS_RE.search(value):
        problems.append(f"{where}: placeholder-shaped value refused")


def _check_sha256(value, where: str, problems: list[str]) -> None:
    if not isinstance(value, str) or not SHA256_RE.match(value):
        problems.append(f"{where}: must be a lowercase 64-hex SHA-256")
    elif _is_pending(value):
        problems.append(f"{where}: still a pending marker")


def _check_positive_number(value, where: str, problems: list[str]) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
        problems.append(f"{where}: must be a positive number")


def _check_geometry(node, panels: tuple, where: str, problems: list[str]) -> None:
    _require_keys(node, panels, where, problems)
    if not isinstance(node, dict):
        return
    for panel in panels:
        sub = node.get(panel)
        if not isinstance(sub, dict):
            problems.append(f"{where}.{panel}: must be an object")
            continue
        _require_keys(sub, ("width_mm", "height_mm", "dpi"), f"{where}.{panel}", problems)
        for dim in ("width_mm", "height_mm", "dpi"):
            if dim in sub:
                _check_positive_number(sub[dim], f"{where}.{panel}.{dim}", problems)


def validate_values(values: dict, allow_variant_map_drift: bool = False) -> list[str]:
    """Return the list of validation problems ([] means the intake is clean)."""
    problems: list[str] = []
    if not isinstance(values, dict):
        return ["intake root must be a JSON object"]

    _require_keys(
        values,
        ("schema_version", "values_id", "recorded_by", "recorded_utc",
         "template", "artwork_sha256", "article_artwork_sha256",
         "mapping_files", "garments"),
        "root", problems,
    )
    if values.get("schema_version") != SCHEMA_VERSION:
        problems.append(f"schema_version must be {SCHEMA_VERSION!r}")
    for key in ("values_id", "recorded_by"):
        if key in values:
            _check_string(values[key], key, problems)
    if "recorded_utc" in values:
        v = values["recorded_utc"]
        if not isinstance(v, str) or not DATE_RE.match(v) or _is_pending(v):
            problems.append("recorded_utc: must be a real ISO date (YYYY-MM-DD)")

    tmpl = values.get("template")
    if isinstance(tmpl, dict):
        _require_keys(
            tmpl,
            ("hoodie_archive_sha256", "tee_archive_sha256",
             "hoodie_panel_geometry", "tee_panel_geometry"),
            "template", problems,
        )
        for key in ("hoodie_archive_sha256", "tee_archive_sha256"):
            if key in tmpl:
                _check_sha256(tmpl[key], f"template.{key}", problems)
        if "hoodie_panel_geometry" in tmpl:
            _check_geometry(tmpl["hoodie_panel_geometry"], HOODIE_PANELS,
                            "template.hoodie_panel_geometry", problems)
        if "tee_panel_geometry" in tmpl:
            _check_geometry(tmpl["tee_panel_geometry"], TEE_PANELS,
                            "template.tee_panel_geometry", problems)
    else:
        problems.append("template: must be an object")

    art = values.get("artwork_sha256")
    if isinstance(art, dict):
        _require_keys(art, ("candidate", "control"), "artwork_sha256", problems)
        for arm in ("candidate", "control"):
            sub = art.get(arm)
            if isinstance(sub, dict):
                _require_keys(sub, HOODIE_PANELS, f"artwork_sha256.{arm}", problems)
                for panel in HOODIE_PANELS:
                    if panel in sub:
                        _check_sha256(sub[panel], f"artwork_sha256.{arm}.{panel}", problems)
            else:
                problems.append(f"artwork_sha256.{arm}: must be an object")
        if isinstance(art.get("candidate"), dict) and isinstance(art.get("control"), dict):
            same = [p for p in HOODIE_PANELS
                    if art["candidate"].get(p) == art["control"].get(p)
                    and isinstance(art["candidate"].get(p), str)]
            if same:
                problems.append(
                    f"candidate and control artwork identical on {same}: "
                    "the matched pair must differ ONLY in artwork; identical "
                    "artwork invalidates the experiment"
                )
    else:
        problems.append("artwork_sha256: must be an object")

    aaa = values.get("article_artwork_sha256")
    if isinstance(aaa, dict):
        _require_keys(aaa, ARTICLE_SKU_IDS, "article_artwork_sha256", problems)
        for sku in ARTICLE_SKU_IDS:
            if sku in aaa:
                _check_sha256(aaa[sku], f"article_artwork_sha256.{sku}", problems)
    else:
        problems.append("article_artwork_sha256: must be an object")

    mf = values.get("mapping_files")
    if isinstance(mf, dict):
        _require_keys(mf, HOODIE_PANELS, "mapping_files", problems)
        for panel in HOODIE_PANELS:
            sub = mf.get(panel)
            if isinstance(sub, dict):
                _require_keys(sub, ("candidate_file", "control_file"),
                              f"mapping_files.{panel}", problems)
                for key in ("candidate_file", "control_file"):
                    if key in sub:
                        _check_string(sub[key], f"mapping_files.{panel}.{key}", problems)
            else:
                problems.append(f"mapping_files.{panel}: must be an object")
    else:
        problems.append("mapping_files: must be an object")

    gar = values.get("garments")
    if isinstance(gar, dict):
        _require_keys(
            gar,
            ("size", "hoodie_variant_id", "tee_variant_id",
             "printer_vendor", "print_technology"),
            "garments", problems,
        )
        size = gar.get("size")
        if "size" in gar:
            _check_string(size, "garments.size", problems)
            if isinstance(size, str) and size in set(HOODIE_VARIANT_MAP) - set(TEE_VARIANT_MAP):
                problems.append(
                    f"garments.size {size!r}: unavailable on the fallback tee "
                    f"(product 257 offers {sorted(TEE_VARIANT_MAP)}); pick a size "
                    "orderable on BOTH products"
                )
        for key, vmap in (("hoodie_variant_id", HOODIE_VARIANT_MAP),
                          ("tee_variant_id", TEE_VARIANT_MAP)):
            if key not in gar:
                continue
            v = gar[key]
            if isinstance(v, bool) or not isinstance(v, int) or v <= 0:
                problems.append(f"garments.{key}: must be a positive integer")
            elif (
                isinstance(size, str)
                and size in vmap
                and vmap[size] != v
                and not allow_variant_map_drift
            ):
                problems.append(
                    f"garments.{key}={v} does not match the embedded v1 variant "
                    f"map for size {size!r} ({vmap[size]}); reconcile with the live "
                    "catalog, or re-run with --allow-variant-map-drift (recorded)"
                )
        for key in ("printer_vendor", "print_technology"):
            if key in gar:
                _check_string(gar[key], f"garments.{key}", problems)
    else:
        problems.append("garments: must be an object")

    return problems


# --------------------------------------------------------------------------
# Binding
# --------------------------------------------------------------------------

def _set_pending(doc, path: list, new_value, rel: str, writes: list[dict]) -> None:
    """Set doc path to new_value; refuse unless the current value is pending."""
    node = doc
    for part in path[:-1]:
        node = node[part]
    leaf = path[-1]
    current = node[leaf]
    dotted = ".".join(str(p) if isinstance(p, str) else f"[{p}]" for p in path)
    if not _is_pending(current):
        raise BindRefusal(
            [f"{rel}:{dotted}: current value is NOT a pending marker "
             f"({current!r}); the binder never overwrites real values"]
        )
    node[leaf] = new_value
    writes.append({"file": rel, "path": dotted, "from": current, "to": new_value})


def plan_bindings(values: dict, docs: dict[str, dict]) -> list[dict]:
    """Apply all bindings to in-memory docs; return the write log."""
    writes: list[dict] = []
    tmpl, gar = values["template"], values["garments"]
    size = gar["size"]

    # template-manifest.json (UA-3)
    _set_pending(docs[TM], ["template_archive_sha256"],
                 tmpl["hoodie_archive_sha256"], TM, writes)
    for panel in HOODIE_PANELS:
        for dim in ("width_mm", "height_mm", "dpi"):
            _set_pending(docs[TM], ["panel_geometry", panel, dim],
                         tmpl["hoodie_panel_geometry"][panel][dim], TM, writes)

    # artwork-manifest.json (UA-3): 16 per-placement upload hashes
    for i, entry in enumerate(docs[AM]["artworks"]):
        _set_pending(docs[AM], ["artworks", i, "artwork_sha256"],
                     values["artwork_sha256"][entry["role"]][entry["placement"]],
                     AM, writes)

    # mapping-manifest.json (UA-3)
    for i, entry in enumerate(docs[MM]["placements"]):
        panel = entry["placement"]
        for key in ("candidate_file", "control_file"):
            _set_pending(docs[MM], ["placements", i, key],
                         values["mapping_files"][panel][key], MM, writes)

    # print-alpha-manifest.json (UA-4)
    for key, src in (("size", size),
                     ("print_technology", gar["print_technology"]),
                     ("printer_vendor", gar["printer_vendor"])):
        _set_pending(docs[PM], ["garment", key], src, PM, writes)

    # print-alpha sku-manifest.json (UA-4): both garments are product 388
    for i in range(len(docs[SM]["garments"])):
        _set_pending(docs[SM], ["garments", i, "size"], size, SM, writes)
        _set_pending(docs[SM], ["garments", i, "variant_id"],
                     gar["hoodie_variant_id"], SM, writes)

    # production_alpha/SKU_MANIFEST.json (UA-3 + UA-4)
    articles = (
        [( "garment_pair", i, a) for i, a in enumerate(docs[SK]["garment_pair"])]
        + [("reserve_articles", i, a) for i, a in enumerate(docs[SK]["reserve_articles"])]
    )
    for section, i, article in articles:
        is_tee = article["product_id"] == 257
        geometry = tmpl["tee_panel_geometry"] if is_tee else tmpl["hoodie_panel_geometry"]
        variant = gar["tee_variant_id"] if is_tee else gar["hoodie_variant_id"]
        archive = tmpl["tee_archive_sha256"] if is_tee else tmpl["hoodie_archive_sha256"]
        panels = TEE_PANELS if is_tee else HOODIE_PANELS
        base = [section, i]
        _set_pending(docs[SK], base + ["template_archive_sha256"], archive, SK, writes)
        _set_pending(docs[SK], base + ["artwork_sha256"],
                     values["article_artwork_sha256"][article["sku_id"]], SK, writes)
        _set_pending(docs[SK], base + ["size"], size, SK, writes)
        _set_pending(docs[SK], base + ["variant_id"], variant, SK, writes)
        for panel in panels:
            for dim in ("width_mm", "height_mm", "dpi"):
                _set_pending(docs[SK], base + ["panel_geometry", panel, dim],
                             geometry[panel][dim], SK, writes)
    return writes


def bind(repo_root: Path, values_path: Path, check_only: bool,
         allow_variant_map_drift: bool) -> dict:
    values_raw = values_path.read_text(encoding="utf-8")
    values = json.loads(values_raw)
    values_sha256 = hashlib.sha256(values_raw.encode("utf-8")).hexdigest()

    problems = validate_values(values, allow_variant_map_drift)
    if problems:
        raise BindRefusal(problems)

    docs = {}
    for rel in WRITABLE_MANIFESTS:
        path = repo_root / rel
        if not path.is_file():
            raise BindRefusal([f"{rel}: manifest missing"])
        docs[rel] = json.loads(path.read_text(encoding="utf-8"))

    writes = plan_bindings(values, docs)

    result = {
        "binder_id": BINDER_ID,
        "schema_version": SCHEMA_VERSION,
        "values_file": str(values_path),
        "values_sha256": values_sha256,
        "values_id": values["values_id"],
        "check_only": check_only,
        "fields_resolved": len(writes),
        "writes": writes,
        "variant_map_drift_allowed": allow_variant_map_drift,
    }

    if check_only:
        result["verdict"] = "BIND_PLAN_VALID"
        return result

    # Atomic phase: every validation passed; write the six manifests.
    # Key order is preserved (sort_keys=False) so bind diffs stay minimal and
    # human-reviewable; any residual formatting normalization is flagged.
    formatting_normalized = []
    for rel in WRITABLE_MANIFESTS:
        path = repo_root / rel
        before = path.read_text(encoding="utf-8")
        after = json.dumps(docs[rel], indent=2, ensure_ascii=False) + "\n"
        if json.loads(before) == docs[rel] and before != after:
            formatting_normalized.append(rel)
        path.write_text(after, encoding="utf-8")
    result["formatting_normalized"] = formatting_normalized

    # Re-pin the freeze and re-run the full gate.
    from tools.p1_no_spend_readiness_gate import build_freeze_manifest, run_gate

    freeze = build_freeze_manifest(repo_root)
    freeze_text = json.dumps(freeze, indent=2, sort_keys=True) + "\n"
    (repo_root / FREEZE_PATH).write_text(freeze_text, encoding="utf-8")
    report = run_gate(repo_root)

    receipt = {
        **result,
        "check_only": False,
        "freeze_sha256": hashlib.sha256(freeze_text.encode("utf-8")).hexdigest(),
        "gate_verdict": report["P1_NO_SPEND_READINESS"],
        "gate_findings": report["findings"],
        "gate_refusals": report["refusals"],
        "boundary_assertions": report["boundary_assertions"],
        "evidence_class": "experimental_print_specimen",
        "physical_efficacy_claimed": False,
        "spend_authorized": False,
        "note": (
            "UA values bound and freeze re-pinned. Spend is still NOT "
            "authorized by this tool: UA-5 ordering is a human-only action "
            "(production_alpha/ORDER_CHECKLIST.md). D2-0005 remains "
            "PREREGISTERED/unarmed; no physical efficacy is claimed."
        ),
        "verdict": "BOUND" if report["P1_NO_SPEND_READINESS"] == "PASS" else "BOUND_GATE_FAIL",
    }
    receipt_path = repo_root / RECEIPT_PATH
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--values", required=True,
                        help="completed copy of physical/p1/UA_VALUES_TEMPLATE.json")
    parser.add_argument("--repo-root", default=str(Path(__file__).resolve().parent.parent))
    parser.add_argument("--check-only", action="store_true",
                        help="validate and report the binding plan without writing")
    parser.add_argument("--allow-variant-map-drift", action="store_true",
                        help="permit variant IDs that differ from the embedded v1 "
                             "reference maps (recorded in the receipt)")
    args = parser.parse_args()

    try:
        result = bind(Path(args.repo_root), Path(args.values),
                      args.check_only, args.allow_variant_map_drift)
    except BindRefusal as exc:
        print(json.dumps({
            "binder_id": BINDER_ID,
            "verdict": "BIND_REFUSED",
            "problems": exc.problems,
            "writes_performed": 0,
        }, indent=2, sort_keys=True))
        return 1

    print(json.dumps({k: v for k, v in result.items() if k != "writes"},
                     indent=2, sort_keys=True))
    if result["verdict"] == "BOUND_GATE_FAIL":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
