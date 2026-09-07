"""Generate the printable P1 calibration target (PNG) and its manifest.

The target is the physical anchor for the P1 print-and-photograph session:
an 8x6 grid of color patches with known sRGB values (and derived CIELAB
D65/2 reference values), four fiducial registration markers at known mm
coordinates, and a 100 mm scale bar. Every geometric value is computed in
millimetres and rasterised at a fixed 300 dpi, so the printed sheet has
exact physical dimensions when printed at 100% scale.

Pillow is already a declared dependency of this repository (pyproject:
Pillow>=10), so no new dependency is introduced. Rendering is fully
deterministic: the same inputs always produce byte-identical PNG output.

Outputs:
- <output-dir>/<target_id>.png
- <output-dir>/calibration-target-manifest.json  (canonical JSON)

The manifest carries target_id, per-patch sRGB + Lab reference values and
grid coordinates in mm, fiducial coordinates, scale-bar length, and the
SHA-256 of the PNG, matching the repo conventions (canonical JSON, 64-hex).
"""

from __future__ import annotations

import argparse
import colorsys
import hashlib
import json
from pathlib import Path

from PIL import Image, ImageDraw

# Fixed rasterisation density. Geometry is defined in mm; pixels are derived.
DPI = 300
MM_PER_INCH = 25.4
PX_PER_MM = DPI / MM_PER_INCH

TARGET_ID = "RAC-CALT-P1-0001"
GRID_ROWS = 6
GRID_COLS = 8
PATCH_MM = 15.0
PATCH_GAP_MM = 3.0
MARGIN_MM = 15.0
SCALE_BAR_MM = 100.0
SCALE_BAR_HEIGHT_MM = 4.0
FIDUCIAL_RADIUS_MM = 3.0


def _mm(value_mm: float) -> int:
    return int(round(value_mm * PX_PER_MM))


def _patch_srgb_values() -> list[tuple[int, int, int]]:
    """Deterministic 48-patch set spanning the garment print gamut.

    12 hues x 2 chroma/values (saturated + mid), 6 high-chroma secondaries,
    6 skin-tone approximations, 12 neutral grays (dark substrate through
    unprinted fabric white).
    """
    patches: list[tuple[int, int, int]] = []
    hues = [i * 30.0 / 360.0 for i in range(12)]
    for h in hues:
        patches.append(_hsv_to_rgb(h, 1.0, 0.90))
    for h in hues:
        patches.append(_hsv_to_rgb(h, 0.55, 0.60))
    for h in (15.0, 75.0, 135.0, 195.0, 255.0, 315.0):
        patches.append(_hsv_to_rgb(h / 360.0, 0.95, 0.75))
    # Skin-tone-ish band (low saturation warm hues).
    for h, s, v in (
        (0.07, 0.35, 0.95),
        (0.07, 0.45, 0.85),
        (0.06, 0.50, 0.75),
        (0.05, 0.55, 0.65),
        (0.05, 0.60, 0.55),
        (0.04, 0.65, 0.45),
    ):
        patches.append(_hsv_to_rgb(h, s, v))
    for i in range(12):
        level = int(round(20 + i * (235.0 / 11)))
        patches.append((level, level, level))
    return patches


def _hsv_to_rgb(h: float, s: float, v: float) -> tuple[int, int, int]:
    r, g, b = colorsys.hsv_to_rgb(h, s, v)
    return (int(round(r * 255)), int(round(g * 255)), int(round(b * 255)))


def _srgb_to_linear(channel: float) -> float:
    c = channel / 255.0
    if c <= 0.04045:
        return c / 12.92
    return ((c + 0.055) / 1.055) ** 2.4


def srgb_to_lab(rgb: tuple[int, int, int]) -> tuple[float, float, float]:
    """sRGB -> CIELAB (D65/2 degree), matching calibration_ingest Lab ranges."""
    r, g, b = (_srgb_to_linear(c) for c in rgb)
    x = r * 0.4124564 + g * 0.3575761 + b * 0.1804375
    y = r * 0.2126729 + g * 0.7151522 + b * 0.0721750
    z = r * 0.0193339 + g * 0.1191920 + b * 0.9503041
    # D65 white point.
    xn, yn, zn = 0.95047, 1.0, 1.08883

    def f(t: float) -> float:
        delta = 6.0 / 29.0
        if t > delta**3:
            return t ** (1.0 / 3.0)
        return t / (3.0 * delta * delta) + 4.0 / 29.0

    fx, fy, fz = f(x / xn), f(y / yn), f(z / zn)
    return (116.0 * fy - 16.0, 500.0 * (fx - fy), 200.0 * (fy - fz))


def _draw_fiducial(draw: ImageDraw.ImageDraw, cx: int, cy: int, radius_px: int) -> None:
    draw.ellipse(
        [cx - radius_px, cy - radius_px, cx + radius_px, cy + radius_px],
        outline=(0, 0, 0),
        width=max(2, radius_px // 4),
    )
    arm = radius_px * 2
    width = max(2, radius_px // 4)
    draw.line([cx - arm, cy, cx + arm, cy], fill=(0, 0, 0), width=width)
    draw.line([cx, cy - arm, cx, cy + arm], fill=(0, 0, 0), width=width)
    draw.ellipse([cx - 2, cy - 2, cx + 2, cy + 2], fill=(0, 0, 0))


def generate(output_dir: Path) -> dict:
    patches = _patch_srgb_values()
    if len(patches) != GRID_ROWS * GRID_COLS:
        raise ValueError("patch set does not match the grid")

    grid_w_mm = GRID_COLS * PATCH_MM + (GRID_COLS - 1) * PATCH_GAP_MM
    grid_h_mm = GRID_ROWS * PATCH_MM + (GRID_ROWS - 1) * PATCH_GAP_MM
    # Sheet: margin, grid, label/scale-bar band, margin.
    band_mm = 20.0
    sheet_w_mm = 2 * MARGIN_MM + grid_w_mm
    sheet_h_mm = 2 * MARGIN_MM + grid_h_mm + band_mm
    sheet_w_px = _mm(sheet_w_mm)
    sheet_h_px = _mm(sheet_h_mm)

    image = Image.new("RGB", (sheet_w_px, sheet_h_px), (255, 255, 255))
    draw = ImageDraw.Draw(image)

    # Color patches.
    patch_entries: list[dict] = []
    for idx, rgb in enumerate(patches):
        row, col = divmod(idx, GRID_COLS)
        x_mm = MARGIN_MM + col * (PATCH_MM + PATCH_GAP_MM)
        y_mm = MARGIN_MM + row * (PATCH_MM + PATCH_GAP_MM)
        draw.rectangle(
            [_mm(x_mm), _mm(y_mm), _mm(x_mm + PATCH_MM), _mm(y_mm + PATCH_MM)],
            fill=rgb,
            outline=(0, 0, 0),
        )
        lab = srgb_to_lab(rgb)
        patch_entries.append(
            {
                "patch_id": f"P{row + 1}{chr(ord('A') + col)}",
                "row": row,
                "col": col,
                "srgb": list(rgb),
                "reference_lab_d65": [round(v, 4) for v in lab],
                "center_mm": [
                    round(x_mm + PATCH_MM / 2.0, 4),
                    round(y_mm + PATCH_MM / 2.0, 4),
                ],
                "size_mm": PATCH_MM,
            }
        )

    # Fiducials at the four sheet corners, inset half the margin.
    inset = MARGIN_MM / 2.0
    fiducial_specs = [
        ("FID-TL", inset, inset),
        ("FID-TR", sheet_w_mm - inset, inset),
        ("FID-BL", inset, sheet_h_mm - inset),
        ("FID-BR", sheet_w_mm - inset, sheet_h_mm - inset),
    ]
    fiducial_entries: list[dict] = []
    for mark_id, x_mm, y_mm in fiducial_specs:
        _draw_fiducial(draw, _mm(x_mm), _mm(y_mm), _mm(FIDUCIAL_RADIUS_MM))
        fiducial_entries.append({"mark_id": mark_id, "center_mm": [round(x_mm, 4), round(y_mm, 4)]})

    # Scale bar, exactly SCALE_BAR_MM long, below the grid.
    bar_x_mm = MARGIN_MM
    bar_y_mm = MARGIN_MM + grid_h_mm + 5.0
    draw.rectangle(
        [_mm(bar_x_mm), _mm(bar_y_mm), _mm(bar_x_mm + SCALE_BAR_MM), _mm(bar_y_mm + SCALE_BAR_HEIGHT_MM)],
        fill=(0, 0, 0),
    )
    # Tick marks at each 10 mm.
    tick = 0
    while tick <= SCALE_BAR_MM:
        x = _mm(bar_x_mm + tick)
        draw.line([x, _mm(bar_y_mm - 1.5), x, _mm(bar_y_mm)], fill=(0, 0, 0), width=3)
        tick += 10

    # Human + machine readable target id printed on the sheet.
    label_x_mm = bar_x_mm + SCALE_BAR_MM + 10.0
    label = f"{TARGET_ID}  scale-bar={SCALE_BAR_MM:.0f}mm  dpi={DPI}"
    draw.text((_mm(label_x_mm), _mm(bar_y_mm)), label, fill=(0, 0, 0))

    output_dir.mkdir(parents=True, exist_ok=True)
    png_name = f"{TARGET_ID}.png"
    png_path = output_dir / png_name
    image.save(png_path, format="PNG", dpi=(DPI, DPI))
    png_sha256 = hashlib.sha256(png_path.read_bytes()).hexdigest()

    manifest = {
        "schema_version": "1.0",
        "target_id": TARGET_ID,
        "dpi": DPI,
        "sheet_size_mm": [round(sheet_w_mm, 4), round(sheet_h_mm, 4)],
        "grid": {
            "rows": GRID_ROWS,
            "cols": GRID_COLS,
            "patch_mm": PATCH_MM,
            "gap_mm": PATCH_GAP_MM,
            "origin_mm": [MARGIN_MM, MARGIN_MM],
        },
        "patches": patch_entries,
        "fiducials": fiducial_entries,
        "scale_bar": {
            "length_mm": SCALE_BAR_MM,
            "start_mm": [round(bar_x_mm, 4), round(bar_y_mm, 4)],
            "end_mm": [round(bar_x_mm + SCALE_BAR_MM, 4), round(bar_y_mm, 4)],
        },
        "png_file": png_name,
        "png_sha256": png_sha256,
        "evidence_label": "internally_measured",
    }
    manifest_path = output_dir / "calibration-target-manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, sort_keys=True, separators=(",", ":")) + "\n"
    )
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--output-dir", default="physical/p1/calibration-target")
    args = parser.parse_args()
    manifest = generate(Path(args.output_dir))
    print(json.dumps({"target_id": manifest["target_id"], "png_sha256": manifest["png_sha256"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
