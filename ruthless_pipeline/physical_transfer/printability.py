"""Printability loss for physical-transfer candidates.

``printability_loss(candidate, production_profile)`` evaluates how well a
digital candidate (HxWx3 float RGB in [0, 1]) is expected to survive a
specific print production process. Every vendor-specific quantity (gamut
bounds, min feature size, MTF cutoff, DPI, bleed / safe-area geometry) is
read from the *versioned* ``production_profile`` dict — nothing is assumed
about vendor behavior.

Components (each returned separately in ``PrintabilityLoss.components``):

- ``gamut_distance``: mean Euclidean RGB distance of out-of-gamut pixels
  outside the printable gamut box ``profile['gamut']['rgb_min']`` /
  ``['rgb_max']`` (an ICC-less axis-aligned RGB-cube gamut model). This is a
  documented DeltaE-like proxy, NOT a calibrated DeltaE00; a measured
  calibration target (docs/CALIBRATION_TARGET_SPEC.md) is required before
  claiming perceptual accuracy.
- ``min_feature_size``: penalty for the smallest detected structure
  (estimated via a morphological-erosion proxy on the high-gradient mask)
  falling below ``profile['min_feature_mm']`` converted to pixels via
  ``profile['dpi']``.
- ``high_frequency_survivability``: fraction of FFT radial energy above the
  cutoff spatial frequency (``profile['mtf_cutoff_cycles_per_mm']`` if
  present, else a dpi-derived fraction of Nyquist). Energy above cutoff is
  predicted not to survive the print MTF.
- ``resolution_dpi_check``: effective dpi implied by the image size and the
  panel's physical dimensions vs ``profile['dpi']`` requirement.
- ``bleed_safe_area_check``: border-margin check against
  ``bleed_mm`` / ``safe_area_mm`` and panel geometry: content detected inside
  the bleed margin (or missing bleed fill) is penalized.
- ``digital_to_camera_discrepancy``: only when the profile carries a measured
  calibration reference (``profile['calibration_ref']`` with
  ``status == 'measured'``). Otherwise the component is ``None`` with
  ``status='MEASUREMENT_UNAVAILABLE'`` — never fabricated.

Missing vendor measurements do not silently default: the affected component
is ``None`` + a status string, the total is computed over available
components with weights renormalized, and the result is flagged
``partial=True``.

Fail-closed: NaN / non-finite input raises ``PrintabilityInputError``.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

MEASUREMENT_UNAVAILABLE = "MEASUREMENT_UNAVAILABLE"

MM_PER_INCH = 25.4

# Default component weights (equal); renormalized over available components.
DEFAULT_WEIGHTS = {
    "gamut_distance": 1.0,
    "min_feature_size": 1.0,
    "high_frequency_survivability": 1.0,
    "resolution_dpi_check": 1.0,
    "bleed_safe_area_check": 1.0,
    "digital_to_camera_discrepancy": 1.0,
}


class PrintabilityInputError(ValueError):
    """Raised on invalid candidate input (fail-closed on NaN/inf/shape)."""


@dataclass
class ComponentResult:
    """One printability component.

    ``value`` is a non-negative penalty in [0, inf) normalized to roughly
    [0, 1]; ``None`` means the component could not be evaluated, in which
    case ``status`` explains why.
    """

    name: str
    value: float | None
    status: str = "OK"
    detail: dict = field(default_factory=dict)


@dataclass
class PrintabilityLoss:
    """Aggregate printability loss.

    ``value`` is the weighted mean of available component penalties.
    ``partial`` is True when at least one component was unavailable and the
    weights were renormalized. ``components`` maps name -> ComponentResult.
    """

    value: float
    components: dict[str, ComponentResult]
    partial: bool = False
    available_components: list[str] = field(default_factory=list)
    unavailable_components: list[str] = field(default_factory=list)


def _validate_candidate(candidate: np.ndarray) -> np.ndarray:
    arr = np.asarray(candidate, dtype=np.float64)
    if arr.ndim != 3 or arr.shape[2] != 3:
        raise PrintabilityInputError(
            f"candidate must be HxWx3 RGB, got shape {arr.shape}"
        )
    if not np.all(np.isfinite(arr)):
        raise PrintabilityInputError("candidate contains NaN or inf (fail-closed)")
    if arr.min() < 0.0 or arr.max() > 1.0:
        raise PrintabilityInputError("candidate RGB values must lie in [0, 1]")
    return arr


def _mm_to_px(mm: float, dpi: float) -> float:
    return mm / MM_PER_INCH * dpi


def _luminance(arr: np.ndarray) -> np.ndarray:
    return (
        0.2126 * arr[..., 0] + 0.7152 * arr[..., 1] + 0.0722 * arr[..., 2]
    )


def _gamut_distance(arr: np.ndarray, profile: dict) -> ComponentResult:
    gamut = profile.get("gamut")
    if not gamut or "rgb_min" not in gamut or "rgb_max" not in gamut:
        return ComponentResult(
            "gamut_distance", None, MEASUREMENT_UNAVAILABLE,
            {"reason": "profile missing gamut.rgb_min/rgb_max"},
        )
    lo = np.asarray(gamut["rgb_min"], dtype=np.float64)
    hi = np.asarray(gamut["rgb_max"], dtype=np.float64)
    under = np.clip(lo - arr, 0.0, None)
    over = np.clip(arr - hi, 0.0, None)
    dist = np.linalg.norm(under + over, axis=-1)
    oog = dist > 0.0
    mean_dist = float(dist[oog].mean()) if oog.any() else 0.0
    return ComponentResult(
        "gamut_distance", mean_dist, "OK",
        {
            "model": "axis-aligned RGB-cube gamut; DeltaE-like Euclidean proxy "
                     "(NOT calibrated DeltaE00)",
            "out_of_gamut_fraction": float(oog.mean()),
            "mean_distance_oog": mean_dist,
        },
    )


def _erode(mask: np.ndarray) -> np.ndarray:
    padded = np.pad(mask, 1, mode="constant", constant_values=False)
    eroded = np.ones_like(mask)
    for dy in range(3):
        for dx in range(3):
            eroded &= padded[dy:dy + mask.shape[0], dx:dx + mask.shape[1]]
    return eroded


def _label_components(mask: np.ndarray) -> list[np.ndarray]:
    """4-connected component labeling via BFS (stdlib, no scipy)."""
    h, w = mask.shape
    seen = np.zeros_like(mask)
    components = []
    for sy, sx in zip(*np.nonzero(mask & ~seen)):
        if seen[sy, sx]:
            continue
        comp = np.zeros_like(mask)
        stack = [(int(sy), int(sx))]
        seen[sy, sx] = True
        comp[sy, sx] = True
        while stack:
            y, x = stack.pop()
            for ny, nx in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
                if (
                    0 <= ny < h
                    and 0 <= nx < w
                    and mask[ny, nx]
                    and not seen[ny, nx]
                ):
                    seen[ny, nx] = True
                    comp[ny, nx] = True
                    stack.append((ny, nx))
        components.append(comp)
    return components


def _smallest_structure_px(gray: np.ndarray) -> float:
    """Morphological-erosion proxy for the smallest detected structure.

    Content pixels are those deviating from the background (image median)
    by more than 2%. Each 4-connected component is eroded (3x3, pure numpy)
    until it vanishes; a component surviving ``k`` full erosions has an
    approximate minimum width of ``2k + 1`` pixels. The smallest such width
    across components is returned. Returns ``inf`` for an image with no
    detectable structure.
    """
    bg = np.median(gray)
    mask = np.abs(gray - bg) > 0.02
    if not mask.any():
        return float("inf")
    smallest = float("inf")
    for comp in _label_components(mask):
        k = 0
        current = comp
        while current.any():
            eroded = _erode(current)
            if not eroded.any():
                break
            current = eroded
            k += 1
            if 2 * k + 1 >= smallest:
                break
        smallest = min(smallest, float(2 * k + 1))
        if smallest <= 1.0:
            break
    return smallest


def _min_feature_size(arr: np.ndarray, profile: dict) -> ComponentResult:
    min_mm = profile.get("min_feature_mm")
    dpi = profile.get("dpi")
    if min_mm is None or dpi is None:
        return ComponentResult(
            "min_feature_size", None, MEASUREMENT_UNAVAILABLE,
            {"reason": "profile missing min_feature_mm or dpi"},
        )
    required_px = _mm_to_px(float(min_mm), float(dpi))
    smallest_px = _smallest_structure_px(_luminance(arr))
    if smallest_px == float("inf"):
        value = 0.0  # no structure: nothing can be too small
    elif smallest_px <= 0:
        value = 1.0
    else:
        value = float(min(1.0, max(0.0, 1.0 - smallest_px / required_px)))
    return ComponentResult(
        "min_feature_size", value, "OK",
        {
            "smallest_structure_px": (
                None if smallest_px == float("inf") else smallest_px
            ),
            "required_min_px": required_px,
        },
    )


def _high_frequency_survivability(arr: np.ndarray, profile: dict) -> ComponentResult:
    dpi = profile.get("dpi")
    if dpi is None:
        return ComponentResult(
            "high_frequency_survivability", None, MEASUREMENT_UNAVAILABLE,
            {"reason": "profile missing dpi"},
        )
    gray = _luminance(arr)
    h, w = gray.shape
    fy = np.fft.fftfreq(h)[:, None]  # cycles/pixel
    fx = np.fft.fftfreq(w)[None, :]
    radial = np.hypot(fy * h, fx * w)  # cycles/image -> normalize below
    # Convert to cycles/mm: cycles/pixel * pixels/mm.
    px_per_mm = dpi / MM_PER_INCH
    freq_cmm = np.hypot(fy, fx) * px_per_mm
    power = np.abs(np.fft.fft2(gray - gray.mean())) ** 2
    total = float(power.sum())
    if total <= 0:
        return ComponentResult(
            "high_frequency_survivability", 0.0, "OK",
            {"reason": "constant image, no high-frequency energy"},
        )
    cutoff = profile.get("mtf_cutoff_cycles_per_mm")
    if cutoff is None:
        # dpi-derived: 40% of the sampling Nyquist (cycles/mm).
        cutoff = 0.4 * (0.5 * px_per_mm)
        cutoff_source = "dpi_derived_0.4_nyquist"
    else:
        cutoff = float(cutoff)
        cutoff_source = "profile_mtf_cutoff"
    above = float(power[freq_cmm > cutoff].sum()) / total
    return ComponentResult(
        "high_frequency_survivability", above, "OK",
        {
            "energy_above_cutoff_fraction": above,
            "cutoff_cycles_per_mm": cutoff,
            "cutoff_source": cutoff_source,
        },
    )


def _resolution_dpi_check(arr: np.ndarray, profile: dict) -> ComponentResult:
    dpi_req = profile.get("dpi")
    panel = profile.get("panel") or {}
    width_mm = panel.get("width_mm")
    if dpi_req is None or width_mm is None:
        return ComponentResult(
            "resolution_dpi_check", None, MEASUREMENT_UNAVAILABLE,
            {"reason": "profile missing dpi or panel.width_mm"},
        )
    h, w = arr.shape[:2]
    effective_dpi = w / (float(width_mm) / MM_PER_INCH)
    shortfall = max(0.0, 1.0 - effective_dpi / float(dpi_req))
    return ComponentResult(
        "resolution_dpi_check", float(min(1.0, shortfall)), "OK",
        {
            "effective_dpi": float(effective_dpi),
            "required_dpi": float(dpi_req),
            "image_px": [int(h), int(w)],
        },
    )


def _bleed_safe_area_check(arr: np.ndarray, profile: dict) -> ComponentResult:
    panel = profile.get("panel") or {}
    bleed_mm = panel.get("bleed_mm", profile.get("bleed_mm"))
    safe_mm = panel.get("safe_area_mm", profile.get("safe_area_mm"))
    dpi = profile.get("dpi")
    if bleed_mm is None or safe_mm is None or dpi is None:
        return ComponentResult(
            "bleed_safe_area_check", None, MEASUREMENT_UNAVAILABLE,
            {"reason": "profile missing bleed_mm/safe_area_mm/dpi"},
        )
    gray = _luminance(arr)
    h, w = gray.shape
    bg = np.median(gray)
    content = np.abs(gray - bg) > 0.02
    bleed_px = max(1, int(round(_mm_to_px(float(bleed_mm), float(dpi)))))
    safe_px = max(1, int(round(_mm_to_px(float(safe_mm), float(dpi)))))
    if bleed_px * 2 >= h or bleed_px * 2 >= w or safe_px * 2 >= h or safe_px * 2 >= w:
        return ComponentResult(
            "bleed_safe_area_check", 1.0, "OK",
            {"reason": "margins exceed image size"},
        )
    # Content inside the safe margin (inside the inner safe area is fine;
    # content in the bleed/trim band between edge and safe area is at risk).
    inner = content[safe_px:-safe_px, safe_px:-safe_px]
    outer_band = content.copy()
    outer_band[safe_px:-safe_px, safe_px:-safe_px] = False
    at_risk = float(outer_band.sum())
    total = float(content.sum())
    value = 0.0 if total == 0 else float(min(1.0, at_risk / max(total, 1.0)))
    return ComponentResult(
        "bleed_safe_area_check", value, "OK",
        {
            "bleed_px": bleed_px,
            "safe_area_px": safe_px,
            "content_px_at_risk": at_risk,
            "content_px_total": total,
        },
    )


def _digital_to_camera_discrepancy(arr: np.ndarray, profile: dict) -> ComponentResult:
    calib = profile.get("calibration_ref")
    if not calib or calib.get("status") != "measured":
        return ComponentResult(
            "digital_to_camera_discrepancy", None, MEASUREMENT_UNAVAILABLE,
            {
                "reason": "profile carries no measured calibration reference; "
                          "discrepancy is never fabricated (UA-4 gate)"
            },
        )
    # Measured path: compare candidate mean color against the measured
    # reference target patch response recorded in the calibration ref.
    ref_rgb = calib.get("reference_patch_rgb")
    measured_rgb = calib.get("measured_patch_rgb")
    if ref_rgb is None or measured_rgb is None:
        return ComponentResult(
            "digital_to_camera_discrepancy", None, MEASUREMENT_UNAVAILABLE,
            {"reason": "calibration_ref lacks reference/measured patch RGB"},
        )
    shift = np.asarray(measured_rgb, dtype=np.float64) - np.asarray(
        ref_rgb, dtype=np.float64
    )
    corrected = np.clip(arr + shift, 0.0, 1.0)
    value = float(np.abs(corrected - arr).mean())
    return ComponentResult(
        "digital_to_camera_discrepancy", value, "OK",
        {
            "calibration_ref_id": calib.get("id"),
            "mean_shift_rgb": [float(s) for s in shift],
        },
    )


_COMPONENT_FUNCS = {
    "gamut_distance": _gamut_distance,
    "min_feature_size": _min_feature_size,
    "high_frequency_survivability": _high_frequency_survivability,
    "resolution_dpi_check": _resolution_dpi_check,
    "bleed_safe_area_check": _bleed_safe_area_check,
    "digital_to_camera_discrepancy": _digital_to_camera_discrepancy,
}


def printability_loss(candidate: np.ndarray, production_profile: dict) -> PrintabilityLoss:
    """Compute the aggregate printability loss for a candidate.

    See module docstring for component semantics. Fail-closed on NaN input.
    Missing vendor measurements yield ``None`` components with a status; the
    total is then a renormalized weighted mean over available components and
    ``partial`` is True.
    """
    if not isinstance(production_profile, dict):
        raise PrintabilityInputError("production_profile must be a dict")
    arr = _validate_candidate(candidate)

    weights = dict(DEFAULT_WEIGHTS)
    weights.update(production_profile.get("component_weights") or {})

    components: dict[str, ComponentResult] = {}
    for name, fn in _COMPONENT_FUNCS.items():
        components[name] = fn(arr, production_profile)

    available = [n for n, c in components.items() if c.value is not None]
    unavailable = [n for n, c in components.items() if c.value is None]
    if not available:
        raise PrintabilityInputError(
            "no printability components could be evaluated from this profile "
            f"(unavailable: {unavailable})"
        )
    wsum = sum(weights[n] for n in available)
    value = float(
        sum(weights[n] * components[n].value for n in available) / wsum
    )
    return PrintabilityLoss(
        value=value,
        components=components,
        partial=bool(unavailable),
        available_components=available,
        unavailable_components=unavailable,
    )
