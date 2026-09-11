#!/usr/bin/env python3
"""Prepare RAC-PRINT-ALPHA-001 for physical production without fabricating evidence.

This tool closes the mechanical gap between the frozen P1/Print Alpha protocol and
real vendor inputs. It has two explicit phases:

1. ``intake`` — consume untouched Printful product/printfile/template JSON responses,
   select one size, verify the exact required placement set, and write a hash-bound
   vendor intake plus deterministic source archives.
2. ``build`` — verify the sealed Alpha-001 candidate bytes, render exact-size
   candidate/control panel PNGs, build deterministic article artwork archives, and
   write a complete ``UA_VALUES`` file accepted by ``tools/p1_bind_ua_values.py``.

The tool NEVER stores API tokens, places orders, changes scientific thresholds,
accesses held-out models, arms an experiment, or claims physical efficacy.

Typical use (online intake):

    export PF_TOKEN=...  # never committed
    python tools/prepare_print_alpha_production.py intake \
        --fetch --size M --output-dir production_alpha/vendor_intake

Offline intake from files previously downloaded unchanged:

    python tools/prepare_print_alpha_production.py intake \
        --raw-dir template_archive --size M \
        --output-dir production_alpha/vendor_intake

Build panel art from the sealed kit:

    python tools/prepare_print_alpha_production.py build \
        --intake production_alpha/vendor_intake/vendor-intake.json \
        --print-test-kit /secure/path/print-test-kit.zip \
        --recorded-by "<operator>"

Then bind only after review:

    python tools/p1_bind_ua_values.py \
        --values production_alpha/vendor_intake/ua-values.generated.json --check-only
    python tools/p1_bind_ua_values.py \
        --values production_alpha/vendor_intake/ua-values.generated.json
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import sys
import urllib.error
import urllib.request
import zipfile
from datetime import date
from pathlib import Path
from typing import Any

RELEASE_ID = "RAC-PRINT-ALPHA-001"
CANDIDATE_ID = "RAC-PER-D2-0003"
EXPECTED_PATTERN_SHA256 = "b07b617fe6dbe178330fff2d9f65c2b720948b641e2bd4865e43ebd62c261546"
EXPECTED_KIT_SHA256 = "b22b022fd98bc8587251099464010dbc3288f8da70756e183f8e366be06f0548"
PRINTFUL_BASE = "https://api.printful.com"
SCHEMA_VERSION = "1.0"

PRODUCTS: dict[int, dict[str, Any]] = {
    388: {
        "kind": "hoodie",
        "name": "All-Over Print Recycled Unisex Hoodie",
        "panels": (
            "back", "front", "hood", "label_inside", "label_panel", "pocket",
            "sleeve_left", "sleeve_right",
        ),
    },
    257: {
        "kind": "tee",
        "name": "All-Over Print Men's Crew Neck T-Shirt",
        "panels": ("back", "front", "sleeve_left", "sleeve_right"),
    },
}

ARTICLE_SKUS = {
    "PA-HOODIE-CAND-001": (388, "candidate"),
    "PA-HOODIE-CTRL-001": (388, "control"),
    "PA-HOODIE-CAND-R01": (388, "candidate"),
    "PA-HOODIE-CTRL-R01": (388, "control"),
    "PA-TEE-CAND-R01": (257, "candidate"),
    "PA-TEE-CTRL-R01": (257, "control"),
}


class ProductionRefusal(RuntimeError):
    """Fail-closed production-preparation refusal."""


def canonical_bytes(payload: Any) -> bytes:
    return (json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def pretty_bytes(payload: Any) -> bytes:
    return (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _result(payload: Any) -> dict:
    if not isinstance(payload, dict):
        raise ProductionRefusal("Printful payload root must be an object")
    if payload.get("code") not in (None, 200):
        raise ProductionRefusal(f"Printful payload code is not 200: {payload.get('code')!r}")
    if payload.get("error"):
        raise ProductionRefusal(f"Printful payload contains error: {payload['error']!r}")
    result = payload.get("result", payload)
    if not isinstance(result, dict):
        raise ProductionRefusal("Printful payload result must be an object")
    return result


def parse_json_bytes(raw: bytes, label: str) -> dict:
    try:
        payload = json.loads(raw.decode("utf-8"))
    except Exception as exc:  # noqa: BLE001
        raise ProductionRefusal(f"{label}: not valid UTF-8 JSON: {exc}") from exc
    _result(payload)
    return payload


def select_variant(product_payload: dict, size: str, color: str = "White") -> int:
    result = _result(product_payload)
    variants = result.get("variants")
    if not isinstance(variants, list):
        raise ProductionRefusal("product response does not contain result.variants[]")
    matches: list[int] = []
    for variant in variants:
        if not isinstance(variant, dict):
            continue
        vsize = str(variant.get("size", "")).strip()
        vcolor = str(variant.get("color", "")).strip()
        vid = variant.get("id", variant.get("variant_id"))
        if vsize == size and vcolor.lower() == color.lower() and isinstance(vid, int):
            matches.append(vid)
    if len(matches) != 1:
        raise ProductionRefusal(
            f"expected exactly one {color} size {size!r} variant; found {matches or 'none'}"
        )
    return matches[0]


def _placement_printfile_id(value: Any) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, dict):
        for key in ("printfile_id", "id"):
            if isinstance(value.get(key), int):
                return value[key]
    raise ProductionRefusal(f"unsupported variant placement mapping: {value!r}")


def extract_geometry(
    printfiles_payload: dict,
    variant_id: int,
    required_panels: tuple[str, ...],
) -> tuple[dict[str, dict[str, Any]], list[str]]:
    result = _result(printfiles_payload)
    printfiles = result.get("printfiles")
    mappings = result.get("variant_printfiles")
    if not isinstance(printfiles, list) or not isinstance(mappings, list):
        raise ProductionRefusal("printfiles response lacks printfiles[]/variant_printfiles[]")

    by_id: dict[int, dict] = {}
    for pf in printfiles:
        if isinstance(pf, dict) and isinstance(pf.get("printfile_id"), int):
            by_id[pf["printfile_id"]] = pf
    if not by_id:
        raise ProductionRefusal("no printfile records found")

    selected = [m for m in mappings if isinstance(m, dict) and m.get("variant_id") == variant_id]
    if len(selected) != 1:
        raise ProductionRefusal(
            f"expected one variant_printfiles record for variant {variant_id}; found {len(selected)}"
        )
    placements = selected[0].get("placements")
    if not isinstance(placements, dict):
        raise ProductionRefusal(f"variant {variant_id} placements is not an object")

    missing = [p for p in required_panels if p not in placements]
    if missing:
        raise ProductionRefusal(
            f"variant {variant_id} missing required placements: {', '.join(missing)}"
        )
    extras = sorted(set(placements) - set(required_panels) - {"mockup"})

    geometry: dict[str, dict[str, Any]] = {}
    for panel in required_panels:
        pfid = _placement_printfile_id(placements[panel])
        pf = by_id.get(pfid)
        if pf is None:
            raise ProductionRefusal(f"placement {panel} references missing printfile_id {pfid}")
        width, height, dpi = pf.get("width"), pf.get("height"), pf.get("dpi")
        if not all(
            isinstance(x, (int, float)) and not isinstance(x, bool) and x > 0
            for x in (width, height, dpi)
        ):
            raise ProductionRefusal(f"placement {panel}: width/height/dpi must be positive numbers")
        geometry[panel] = {
            "printfile_id": pfid,
            "width_px": int(width),
            "height_px": int(height),
            "dpi": float(dpi),
            "width_mm": round(float(width) / float(dpi) * 25.4, 6),
            "height_mm": round(float(height) / float(dpi) * 25.4, 6),
            "fill_mode": pf.get("fill_mode"),
            "can_rotate": pf.get("can_rotate"),
        }
    return geometry, extras


def _fixed_zip(path: Path, files: list[tuple[str, bytes]]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for arcname, data in sorted(files, key=lambda item: item[0]):
            info = zipfile.ZipInfo(arcname, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            zf.writestr(info, data)
    return sha256_file(path)


def build_vendor_intake(
    raw_payloads: dict[int, dict[str, bytes]],
    size: str,
    output_dir: Path,
) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    products_out: dict[str, dict[str, Any]] = {}
    for product_id, spec in PRODUCTS.items():
        raw = raw_payloads[product_id]
        product = parse_json_bytes(raw["product"], f"product {product_id}")
        printfiles = parse_json_bytes(raw["printfiles"], f"printfiles {product_id}")
        parse_json_bytes(raw["templates"], f"templates {product_id}")
        variant_id = select_variant(product, size)
        geometry, extras = extract_geometry(printfiles, variant_id, spec["panels"])

        raw_dir = output_dir / "raw"
        raw_dir.mkdir(parents=True, exist_ok=True)
        names = {
            "product": f"products_{product_id}.json",
            "printfiles": f"printfiles_{product_id}.json",
            "templates": f"templates_{product_id}.json",
        }
        for key, filename in names.items():
            (raw_dir / filename).write_bytes(raw[key])

        source_zip = output_dir / f"printful-source-{product_id}.zip"
        source_sha = _fixed_zip(source_zip, [(names[k], raw[k]) for k in sorted(names)])
        products_out[str(product_id)] = {
            "product_id": product_id,
            "product_name_expected": spec["name"],
            "size": size,
            "variant_id": variant_id,
            "required_panels": list(spec["panels"]),
            "extra_vendor_placements": extras,
            "panel_geometry": geometry,
            "source_files": {
                names[k]: {"sha256": sha256_bytes(raw[k]), "bytes": len(raw[k])}
                for k in sorted(names)
            },
            "source_archive": {
                "path": source_zip.name,
                "sha256": source_sha,
                "contents_are_untouched_vendor_responses": True,
            },
            "template_response_sha256": sha256_bytes(raw["templates"]),
            "printfiles_response_sha256": sha256_bytes(raw["printfiles"]),
        }

    receipt = {
        "schema_version": SCHEMA_VERSION,
        "release_id": RELEASE_ID,
        "provider": "Printful",
        "selected_size": size,
        "products": products_out,
        "physical_efficacy_claimed": False,
        "heldout_access": False,
        "spend_authorized": False,
        "order_placed": False,
        "note": (
            "Vendor intake only. Source archives contain untouched API response bytes; "
            "no scientific state or physical-efficacy claim is changed."
        ),
    }
    receipt["intake_sha256"] = sha256_bytes(canonical_bytes(receipt))
    (output_dir / "vendor-intake.json").write_bytes(pretty_bytes(receipt))
    return receipt


def _fetch(url: str, token: str | None) -> bytes:
    headers = {"User-Agent": "RAC-P1-Production-Prep/1.0"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:  # noqa: S310 - fixed trusted host
            status = getattr(resp, "status", 200)
            raw = resp.read()
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", "replace")[:400]
        raise ProductionRefusal(f"GET {url} failed HTTP {exc.code}: {body}") from exc
    if status != 200:
        raise ProductionRefusal(f"GET {url} failed HTTP {status}")
    parse_json_bytes(raw, url)
    return raw


def fetch_raw_payloads(token: str) -> dict[int, dict[str, bytes]]:
    if not token.strip():
        raise ProductionRefusal("PF_TOKEN is empty")
    payloads: dict[int, dict[str, bytes]] = {}
    for product_id in PRODUCTS:
        payloads[product_id] = {
            "product": _fetch(f"{PRINTFUL_BASE}/products/{product_id}", token),
            "printfiles": _fetch(
                f"{PRINTFUL_BASE}/mockup-generator/printfiles/{product_id}?technique=CUT-SEW",
                token,
            ),
            "templates": _fetch(
                f"{PRINTFUL_BASE}/mockup-generator/templates/{product_id}?technique=CUT-SEW",
                token,
            ),
        }
    return payloads


def load_raw_dir(raw_dir: Path) -> dict[int, dict[str, bytes]]:
    payloads: dict[int, dict[str, bytes]] = {}
    for product_id in PRODUCTS:
        paths = {
            "product": raw_dir / f"products_{product_id}.json",
            "printfiles": raw_dir / f"printfiles_{product_id}.json",
            "templates": raw_dir / f"templates_{product_id}.json",
        }
        missing = [p.as_posix() for p in paths.values() if not p.is_file()]
        if missing:
            raise ProductionRefusal(f"raw vendor files missing: {', '.join(missing)}")
        payloads[product_id] = {k: p.read_bytes() for k, p in paths.items()}
    return payloads


def load_candidate_bytes(
    *,
    print_test_kit: Path | None = None,
    candidate_pattern: Path | None = None,
    expected_pattern_sha256: str = EXPECTED_PATTERN_SHA256,
    expected_kit_sha256: str = EXPECTED_KIT_SHA256,
) -> tuple[bytes, dict[str, Any]]:
    if bool(print_test_kit) == bool(candidate_pattern):
        raise ProductionRefusal("provide exactly one of --print-test-kit or --candidate-pattern")
    if print_test_kit:
        if not print_test_kit.is_file():
            raise ProductionRefusal(f"print-test kit missing: {print_test_kit}")
        kit_sha = sha256_file(print_test_kit)
        if kit_sha != expected_kit_sha256:
            raise ProductionRefusal(
                f"print-test kit sha256 mismatch: {kit_sha} != {expected_kit_sha256}"
            )
        with zipfile.ZipFile(print_test_kit) as zf:
            candidates = [
                "print-test-kit/design/pattern_tile_4096.png",
                "design/pattern_tile_4096.png",
            ]
            member = next((m for m in candidates if m in zf.namelist()), None)
            if member is None:
                raise ProductionRefusal("sealed kit lacks design/pattern_tile_4096.png")
            data = zf.read(member)
        source = {
            "mode": "sealed_print_test_kit",
            "kit_path": print_test_kit.name,
            "kit_sha256": kit_sha,
            "member": member,
        }
    else:
        assert candidate_pattern is not None
        if not candidate_pattern.is_file():
            raise ProductionRefusal(f"candidate pattern missing: {candidate_pattern}")
        data = candidate_pattern.read_bytes()
        source = {
            "mode": "pattern_only_hash_verified",
            "pattern_path": candidate_pattern.name,
            "kit_sha256_verified": False,
        }
    pattern_sha = sha256_bytes(data)
    if pattern_sha != expected_pattern_sha256:
        raise ProductionRefusal(
            f"candidate pattern sha256 mismatch: {pattern_sha} != {expected_pattern_sha256}"
        )
    source["pattern_sha256"] = pattern_sha
    return data, source


def _panel_png(pattern_bytes: bytes, width: int, height: int, *, control: bool) -> bytes:
    try:
        from PIL import Image
    except ImportError as exc:  # pragma: no cover
        raise ProductionRefusal("Pillow is required to build panel artwork") from exc

    if control:
        out = Image.new("RGB", (width, height), (128, 128, 128))
    else:
        try:
            tile = Image.open(io.BytesIO(pattern_bytes)).convert("RGB")
        except Exception as exc:  # noqa: BLE001
            raise ProductionRefusal(f"candidate pattern is not a readable image: {exc}") from exc
        if tile.width < 1 or tile.height < 1:
            raise ProductionRefusal("candidate pattern has invalid dimensions")
        out = Image.new("RGB", (width, height))
        for y in range(0, height, tile.height):
            for x in range(0, width, tile.width):
                out.paste(tile, (x, y))
    buf = io.BytesIO()
    out.save(buf, format="PNG", optimize=False, compress_level=9)
    return buf.getvalue()


def _article_pack(path: Path, panel_bytes: dict[str, bytes]) -> str:
    return _fixed_zip(path, [(f"{panel}.png", data) for panel, data in panel_bytes.items()])


def build_panel_art_and_values(
    intake: dict,
    pattern_bytes: bytes,
    source: dict[str, Any],
    repo_root: Path,
    recorded_by: str,
    recorded_date: str,
    output_dir: Path,
) -> dict:
    if intake.get("release_id") != RELEASE_ID or intake.get("provider") != "Printful":
        raise ProductionRefusal("vendor intake is not for RAC-PRINT-ALPHA-001 / Printful")
    if intake.get("physical_efficacy_claimed") is not False:
        raise ProductionRefusal("vendor intake breaches physical-efficacy boundary")
    products = intake.get("products")
    if not isinstance(products, dict):
        raise ProductionRefusal("vendor intake products missing")
    size = intake.get("selected_size")
    if not isinstance(size, str) or not size:
        raise ProductionRefusal("vendor intake selected_size missing")
    if not recorded_by.strip():
        raise ProductionRefusal("--recorded-by must be non-empty")

    output_dir.mkdir(parents=True, exist_ok=True)
    artifact_hashes: dict[int, dict[str, dict[str, str]]] = {}
    panel_bytes_by_product: dict[int, dict[str, dict[str, bytes]]] = {}

    for product_id, spec in PRODUCTS.items():
        p = products.get(str(product_id))
        if not isinstance(p, dict):
            raise ProductionRefusal(f"vendor intake missing product {product_id}")
        geometry = p.get("panel_geometry")
        if not isinstance(geometry, dict):
            raise ProductionRefusal(f"product {product_id} panel_geometry missing")
        panel_bytes_by_product[product_id] = {"candidate": {}, "control": {}}
        artifact_hashes[product_id] = {"candidate": {}, "control": {}}

        for panel in spec["panels"]:
            g = geometry.get(panel)
            if not isinstance(g, dict):
                raise ProductionRefusal(f"product {product_id} geometry missing {panel}")
            width, height = g.get("width_px"), g.get("height_px")
            if not isinstance(width, int) or not isinstance(height, int) or width < 1 or height < 1:
                raise ProductionRefusal(f"product {product_id}.{panel}: invalid pixel geometry")
            for role in ("candidate", "control"):
                data = _panel_png(pattern_bytes, width, height, control=(role == "control"))
                panel_bytes_by_product[product_id][role][panel] = data
                artifact_hashes[product_id][role][panel] = sha256_bytes(data)

                if product_id == 388:
                    target = repo_root / "print-alpha" / role.upper() / f"{panel}.png"
                else:
                    target = output_dir / "tee-panels" / role / f"{panel}.png"
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)

    for product_id, spec in PRODUCTS.items():
        same = [
            panel for panel in spec["panels"]
            if artifact_hashes[product_id]["candidate"][panel]
            == artifact_hashes[product_id]["control"][panel]
        ]
        if same:
            raise ProductionRefusal(f"candidate/control artwork collision for product {product_id}: {same}")

    pack_hashes: dict[tuple[int, str], str] = {}
    pack_dir = output_dir / "artwork-packs"
    for product_id in PRODUCTS:
        for role in ("candidate", "control"):
            pack_path = pack_dir / f"product-{product_id}-{role}.zip"
            pack_hashes[(product_id, role)] = _article_pack(
                pack_path, panel_bytes_by_product[product_id][role]
            )

    hoodie = products["388"]
    tee = products["257"]

    def geometry_values(product: dict, panels: tuple[str, ...]) -> dict:
        out: dict[str, dict[str, Any]] = {}
        for panel in panels:
            g = product["panel_geometry"][panel]
            out[panel] = {
                "width_mm": g["width_mm"],
                "height_mm": g["height_mm"],
                "dpi": g["dpi"],
            }
        return out

    values = {
        "schema_version": SCHEMA_VERSION,
        "values_id": f"RAC-P1-UA-VALUES-{intake['intake_sha256'][:12]}",
        "recorded_by": recorded_by,
        "recorded_utc": recorded_date,
        "template": {
            "hoodie_archive_sha256": hoodie["source_archive"]["sha256"],
            "tee_archive_sha256": tee["source_archive"]["sha256"],
            "hoodie_panel_geometry": geometry_values(hoodie, PRODUCTS[388]["panels"]),
            "tee_panel_geometry": geometry_values(tee, PRODUCTS[257]["panels"]),
        },
        "artwork_sha256": artifact_hashes[388],
        "article_artwork_sha256": {
            sku: pack_hashes[(product_id, role)]
            for sku, (product_id, role) in ARTICLE_SKUS.items()
        },
        "mapping_files": {
            panel: {
                "candidate_file": f"print-alpha/CANDIDATE/{panel}.png",
                "control_file": f"print-alpha/CONTROL/{panel}.png",
            }
            for panel in PRODUCTS[388]["panels"]
        },
        "garments": {
            "size": size,
            "hoodie_variant_id": hoodie["variant_id"],
            "tee_variant_id": tee["variant_id"],
            "printer_vendor": "Printful",
            "print_technology": "CUT-SEW all-over synthetic (sublimation)",
        },
    }

    code_root = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(code_root))
    try:
        from tools.p1_bind_ua_values import validate_values
        problems = validate_values(values)
    finally:
        try:
            sys.path.remove(str(code_root))
        except ValueError:
            pass
    if problems:
        raise ProductionRefusal("generated UA values fail binder validation: " + "; ".join(problems))

    values_path = output_dir / "ua-values.generated.json"
    values_path.write_bytes(pretty_bytes(values))
    receipt = {
        "schema_version": SCHEMA_VERSION,
        "release_id": RELEASE_ID,
        "candidate_id": CANDIDATE_ID,
        "candidate_source": source,
        "vendor_intake_sha256": intake["intake_sha256"],
        "selected_size": size,
        "hoodie_variant_id": hoodie["variant_id"],
        "tee_variant_id": tee["variant_id"],
        "values_path": values_path.name,
        "values_sha256": sha256_file(values_path),
        "candidate_panel_hashes": artifact_hashes[388]["candidate"],
        "control_panel_hashes": artifact_hashes[388]["control"],
        "article_artwork_archives": {
            sku: {
                "sha256": values["article_artwork_sha256"][sku],
                "role": ARTICLE_SKUS[sku][1],
                "product_id": ARTICLE_SKUS[sku][0],
            }
            for sku in sorted(ARTICLE_SKUS)
        },
        "control_rule": "flat mid-gray sRGB(128,128,128) full-coverage scenario_assumption",
        "binder_check_required": True,
        "spend_authorized": False,
        "order_placed": False,
        "physical_efficacy_claimed": False,
        "heldout_access": False,
    }
    receipt["receipt_sha256"] = sha256_bytes(canonical_bytes(receipt))
    (output_dir / "production-prep-receipt.json").write_bytes(pretty_bytes(receipt))
    return receipt


def _intake_cli(args: argparse.Namespace) -> int:
    output = Path(args.output_dir)
    if args.fetch:
        token = os.environ.get(args.token_env, "")
        if not token:
            raise ProductionRefusal(
                f"--fetch requires a non-empty {args.token_env} environment variable; token is never stored"
            )
        payloads = fetch_raw_payloads(token)
    else:
        if not args.raw_dir:
            raise ProductionRefusal("intake requires either --fetch or --raw-dir")
        payloads = load_raw_dir(Path(args.raw_dir))
    receipt = build_vendor_intake(payloads, args.size, output)
    print(json.dumps({
        "status": "VENDOR_INTAKE_READY",
        "intake": (output / "vendor-intake.json").as_posix(),
        "intake_sha256": receipt["intake_sha256"],
        "size": receipt["selected_size"],
        "hoodie_variant_id": receipt["products"]["388"]["variant_id"],
        "tee_variant_id": receipt["products"]["257"]["variant_id"],
        "spend_authorized": False,
    }, indent=2, sort_keys=True))
    return 0


def _build_cli(args: argparse.Namespace) -> int:
    repo_root = Path(args.repo_root).resolve()
    intake_path = Path(args.intake)
    intake = json.loads(intake_path.read_text(encoding="utf-8"))
    pattern_bytes, source = load_candidate_bytes(
        print_test_kit=Path(args.print_test_kit) if args.print_test_kit else None,
        candidate_pattern=Path(args.candidate_pattern) if args.candidate_pattern else None,
    )
    output = Path(args.output_dir)
    receipt = build_panel_art_and_values(
        intake,
        pattern_bytes,
        source,
        repo_root,
        args.recorded_by,
        args.recorded_date,
        output,
    )
    values = output / "ua-values.generated.json"
    print(json.dumps({
        "status": "BINDER_READY",
        "values": values.as_posix(),
        "values_sha256": receipt["values_sha256"],
        "candidate_pattern_sha256": source["pattern_sha256"],
        "next_check": f"python tools/p1_bind_ua_values.py --values {values.as_posix()} --check-only",
        "next_bind": f"python tools/p1_bind_ua_values.py --values {values.as_posix()}",
        "spend_authorized": False,
        "order_placed": False,
    }, indent=2, sort_keys=True))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)

    intake = sub.add_parser("intake", help="fetch or ingest untouched Printful template data")
    source = intake.add_mutually_exclusive_group(required=True)
    source.add_argument("--fetch", action="store_true", help="fetch Printful responses using PF_TOKEN")
    source.add_argument("--raw-dir", help="directory containing products/printfiles/templates JSON for 388 and 257")
    intake.add_argument("--token-env", default="PF_TOKEN")
    intake.add_argument("--size", required=True, help="one size available for both hoodie and fallback tee, e.g. M")
    intake.add_argument("--output-dir", default="production_alpha/vendor_intake")
    intake.set_defaults(func=_intake_cli)

    build = sub.add_parser("build", help="render exact panel art and create binder-ready UA values")
    build.add_argument("--intake", default="production_alpha/vendor_intake/vendor-intake.json")
    src = build.add_mutually_exclusive_group(required=True)
    src.add_argument("--print-test-kit", help="sealed print-test-kit.zip; exact kit hash is enforced")
    src.add_argument("--candidate-pattern", help="exact frozen pattern image; pattern hash is enforced")
    build.add_argument("--recorded-by", required=True)
    build.add_argument("--recorded-date", default=date.today().isoformat())
    build.add_argument("--repo-root", default=Path(__file__).resolve().parent.parent)
    build.add_argument("--output-dir", default="production_alpha/vendor_intake")
    build.set_defaults(func=_build_cli)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except ProductionRefusal as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
