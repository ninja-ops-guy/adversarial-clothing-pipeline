"""Pure-numpy transformation primitives for the 4 dimension groups.

synthetic_pipeline_validation_only.

All operations take/return float numpy arrays with values nominally in
[0, 1]. 2-D (grayscale) and 3-D (H, W, C) arrays are supported; geometric
warps are applied per channel. Everything is deterministic given explicit
parameters (random fields are derived from the passed parameters, never from
ambient entropy).

Dimension groups:
- geometry: scale, camera_distance, perspective, yaw/pitch/roll, translation
  (affine/projective warp on 2D arrays; camera_distance maps to an effective
  scale factor via REFERENCE_CAMERA_DISTANCE / camera_distance).
- imaging: gaussian blur, resize (interpolation choice), JPEG-like
  compression mock via 8x8 block DCT quantization, exposure, contrast.
- garment: stretch, wrinkle/fold/bend (sinusoidal / piecewise displacement
  fields), partial_occlusion (rectangular mask).
- print_capture: gamut_mapping (documented RGB clip/compress curve),
  resolution_loss (downsample-upsample), calibration_transform_ref
  passthrough that REFUSES (fail-closed CalibrationUnavailableError) when a
  real calibration transform is requested but unavailable — never faked.
"""

from __future__ import annotations

import math
from typing import Any, Dict, Optional, Tuple

import numpy as np

REFERENCE_CAMERA_DISTANCE = 1.0


class CalibrationUnavailableError(RuntimeError):
    """Raised when a real calibration transform is requested but unavailable."""


# ---------------------------------------------------------------------------
# shared resampling helpers
# ---------------------------------------------------------------------------

def _coords(shape: Tuple[int, int]) -> Tuple[np.ndarray, np.ndarray]:
    yy, xx = np.mgrid[0 : shape[0], 0 : shape[1]].astype(np.float64)
    return yy, xx


def bilinear_sample(img2d: np.ndarray, ys: np.ndarray, xs: np.ndarray, fill: float = 0.0) -> np.ndarray:
    """Sample img2d at floating (ys, xs) with bilinear interpolation."""
    h, w = img2d.shape
    x0 = np.floor(xs).astype(np.int64)
    y0 = np.floor(ys).astype(np.int64)
    x1 = x0 + 1
    y1 = y0 + 1
    wx = xs - x0
    wy = ys - y0
    valid = (x0 >= 0) & (y0 >= 0) & (x1 < w) & (y1 < h)
    x0c = np.clip(x0, 0, w - 1)
    x1c = np.clip(x1, 0, w - 1)
    y0c = np.clip(y0, 0, h - 1)
    y1c = np.clip(y1, 0, h - 1)
    Ia = img2d[y0c, x0c]
    Ib = img2d[y0c, x1c]
    Ic = img2d[y1c, x0c]
    Id = img2d[y1c, x1c]
    out = (1 - wx) * (1 - wy) * Ia + wx * (1 - wy) * Ib + (1 - wx) * wy * Ic + wx * wy * Id
    return np.where(valid, out, fill)


def warp(img: np.ndarray, map_y: np.ndarray, map_x: np.ndarray, fill: float = 0.0) -> np.ndarray:
    """Warp img with an inverse coordinate map (per channel for 3-D input)."""
    if img.ndim == 2:
        return bilinear_sample(img, map_y, map_x, fill)
    if img.ndim == 3:
        chans = [bilinear_sample(img[..., c], map_y, map_x, fill) for c in range(img.shape[2])]
        return np.stack(chans, axis=-1)
    raise ValueError("expected 2-D or 3-D array")


# ---------------------------------------------------------------------------
# geometry
# ---------------------------------------------------------------------------

def geometry_matrix(params: Dict[str, Any], shape: Tuple[int, int]) -> np.ndarray:
    """Build the 3x3 forward affine matrix for a geometry parameter set.

    camera_distance maps to effective scale: eff_scale =
    scale * REFERENCE_CAMERA_DISTANCE / camera_distance. yaw/pitch are
    approximated (small-angle) as anisotropic scale + shear; perspective adds
    an additional shear proportional to its value; roll is an in-plane
    rotation; translation is (dx, dy) in pixels (a scalar is broadcast).
    """
    h, w = shape
    cx, cy = (w - 1) / 2.0, (h - 1) / 2.0

    scale = float(params.get("scale", 1.0))
    cam = float(params.get("camera_distance", REFERENCE_CAMERA_DISTANCE))
    eff = scale * (REFERENCE_CAMERA_DISTANCE / max(cam, 1e-9))

    yaw = math.radians(float(params.get("yaw", 0.0)))
    pitch = math.radians(float(params.get("pitch", 0.0)))
    roll = math.radians(float(params.get("roll", 0.0)))
    persp = float(params.get("perspective", 0.0))

    # anisotropic foreshortening + shear from yaw/pitch/perspective
    a = math.cos(yaw) * eff
    b = math.sin(yaw) * 0.5 * eff + persp * 0.05
    d = math.sin(pitch) * 0.5 * eff + persp * 0.05
    e = math.cos(pitch) * eff
    m_asp = np.array([[a, b, 0.0], [d, e, 0.0], [0.0, 0.0, 1.0]])

    cr, sr = math.cos(roll), math.sin(roll)
    m_rot = np.array([[cr, -sr, 0.0], [sr, cr, 0.0], [0.0, 0.0, 1.0]])

    t = params.get("translation", (0.0, 0.0))
    if np.isscalar(t):
        tx = ty = float(t)
    else:
        tx, ty = float(t[0]), float(t[1])

    to_c = np.array([[1.0, 0.0, -cx], [0.0, 1.0, -cy], [0.0, 0.0, 1.0]])
    back = np.array([[1.0, 0.0, cx + tx], [0.0, 1.0, cy + ty], [0.0, 0.0, 1.0]])
    return back @ m_rot @ m_asp @ to_c


def apply_geometry(img: np.ndarray, params: Dict[str, Any], fill: float = 0.0) -> np.ndarray:
    """Apply the geometry group as an affine warp (inverse-mapped bilinear)."""
    fwd = geometry_matrix(params, img.shape[:2])
    inv = np.linalg.inv(fwd)
    yy, xx = _coords(img.shape[:2])
    ones = np.ones_like(xx)
    pts = inv @ np.stack([xx.ravel(), yy.ravel(), ones.ravel()])
    map_x = pts[0].reshape(xx.shape)
    map_y = pts[1].reshape(yy.shape)
    return warp(img, map_y, map_x, fill)


# ---------------------------------------------------------------------------
# imaging
# ---------------------------------------------------------------------------

def gaussian_blur(img: np.ndarray, sigma: float) -> np.ndarray:
    """Separable gaussian blur; sigma <= 0 is an identity."""
    sigma = float(sigma)
    if sigma <= 0:
        return img.copy()
    radius = max(1, int(math.ceil(3.0 * sigma)))
    x = np.arange(-radius, radius + 1, dtype=np.float64)
    k = np.exp(-(x**2) / (2.0 * sigma * sigma))
    k /= k.sum()

    def conv2(a: np.ndarray) -> np.ndarray:
        pad = ((radius, radius), (radius, radius))
        ap = np.pad(a, pad, mode="reflect")
        tmp = np.apply_along_axis(
            lambda r: np.convolve(r, k, mode="valid"), 1, ap
        )
        return np.apply_along_axis(lambda r: np.convolve(r, k, mode="valid"), 0, tmp)

    if img.ndim == 2:
        return conv2(img)
    return np.stack([conv2(img[..., c]) for c in range(img.shape[2])], axis=-1)


def resize(img: np.ndarray, factor: float, interpolation: str = "bilinear") -> np.ndarray:
    """Resize by factor with 'nearest' or 'bilinear' interpolation."""
    factor = float(factor)
    h, w = img.shape[:2]
    nh = max(1, int(round(h * factor)))
    nw = max(1, int(round(w * factor)))
    if interpolation == "nearest":
        ys = np.clip((np.arange(nh) / factor).astype(np.int64), 0, h - 1)
        xs = np.clip((np.arange(nw) / factor).astype(np.int64), 0, w - 1)
        return img[ys][:, xs] if img.ndim == 2 else img[ys][:, xs, :]
    if interpolation == "bilinear":
        ys = (np.arange(nh) + 0.5) / factor - 0.5
        xs = (np.arange(nw) + 0.5) / factor - 0.5
        yy, xx = np.meshgrid(ys, xs, indexing="ij")
        return warp(img, yy, xx)
    raise ValueError(f"unknown interpolation: {interpolation!r}")


def _dct_matrix(n: int = 8) -> np.ndarray:
    k = np.arange(n)
    x = np.arange(n)
    m = np.cos((2 * x[None, :] + 1) * k[:, None] * math.pi / (2 * n))
    m[0] *= 1.0 / math.sqrt(2.0)
    return m * math.sqrt(2.0 / n)


_DCT = _dct_matrix(8)
# Standard JPEG-like luminance quantization table (documented mock).
_QTABLE = np.array(
    [
        [16, 11, 10, 16, 24, 40, 51, 61],
        [12, 12, 14, 19, 26, 58, 60, 55],
        [14, 13, 16, 24, 40, 57, 69, 56],
        [14, 17, 22, 29, 51, 87, 80, 62],
        [18, 22, 37, 56, 68, 109, 103, 77],
        [24, 35, 55, 64, 81, 104, 113, 92],
        [49, 64, 78, 87, 103, 121, 120, 101],
        [72, 92, 95, 98, 112, 100, 103, 99],
    ],
    dtype=np.float64,
)


def compression_mock(img: np.ndarray, quality: float) -> np.ndarray:
    """JPEG-like compression mock via 8x8 block DCT quantization.

    quality in (0, 100]; higher keeps more coefficients. This is a documented
    quantization mock, not an actual JPEG codec.
    """
    q = float(np.clip(quality, 1.0, 100.0))
    scale = 5000.0 / q if q < 50 else 200.0 - 2.0 * q
    table = np.clip((_QTABLE * scale + 50.0) / 100.0, 1.0, 255.0)

    def proc(a: np.ndarray) -> np.ndarray:
        h, w = a.shape
        out = a.copy()
        for by in range(0, h - 7, 8):
            for bx in range(0, w - 7, 8):
                block = out[by : by + 8, bx : bx + 8] - 0.5
                coeff = _DCT @ block @ _DCT.T
                quant = np.round(coeff / table) * table
                out[by : by + 8, bx : bx + 8] = _DCT.T @ quant @ _DCT + 0.5
        return np.clip(out, 0.0, 1.0)

    if img.ndim == 2:
        return proc(img)
    return np.stack([proc(img[..., c]) for c in range(img.shape[2])], axis=-1)


def exposure(img: np.ndarray, ev: float) -> np.ndarray:
    """Exposure shift in EV stops: multiply by 2**ev, clip to [0,1]."""
    return np.clip(img * (2.0 ** float(ev)), 0.0, 1.0)


def contrast(img: np.ndarray, factor: float) -> np.ndarray:
    """Contrast scaling around the global mean, clipped to [0,1]."""
    f = float(factor)
    return np.clip((img - img.mean()) * f + img.mean(), 0.0, 1.0)


def apply_imaging(img: np.ndarray, params: Dict[str, Any]) -> np.ndarray:
    out = gaussian_blur(img, float(params.get("blur", 0.0)))
    interp = params.get("resize_interpolation", "bilinear")
    factor = float(params.get("resize_factor", 1.0))
    if factor != 1.0:
        out = resize(out, factor, str(interp))
    q = params.get("compression", None)
    if q is not None:
        out = compression_mock(out, float(q))
    out = exposure(out, float(params.get("exposure", 0.0)))
    out = contrast(out, float(params.get("contrast", 1.0)))
    return out


# ---------------------------------------------------------------------------
# garment
# ---------------------------------------------------------------------------

def apply_stretch(img: np.ndarray, stretch: float) -> np.ndarray:
    """Anisotropic horizontal stretch (factor on x, 1/sqrt on y to conserve area)."""
    s = max(float(stretch), 1e-6)
    h, w = img.shape[:2]
    yy, xx = _coords((h, w))
    cx, cy = (w - 1) / 2.0, (h - 1) / 2.0
    map_x = cx + (xx - cx) / s
    map_y = cy + (yy - cy) * math.sqrt(s)
    return warp(img, map_y, map_x)


def apply_wrinkle(img: np.ndarray, amplitude: float, frequency: float = 0.15, phase: float = 0.0) -> np.ndarray:
    """High-frequency sinusoidal displacement field (wrinkle)."""
    h, w = img.shape[:2]
    yy, xx = _coords((h, w))
    disp = amplitude * np.sin(2 * math.pi * frequency * xx + phase)
    return warp(img, yy + disp, xx)


def apply_fold(img: np.ndarray, amplitude: float, crease_position: float = 0.5) -> np.ndarray:
    """Piecewise-linear crease displacement (fold) across the vertical axis."""
    h, w = img.shape[:2]
    yy, xx = _coords((h, w))
    c = float(np.clip(crease_position, 0.0, 1.0)) * (w - 1)
    # tent-shaped displacement peaking at the crease
    tent = amplitude * (1.0 - np.abs(xx - c) / max(c, (w - 1) - c, 1.0))
    tent = np.clip(tent, 0.0, None)
    return warp(img, yy + tent, xx)


def apply_bend(img: np.ndarray, curvature: float) -> np.ndarray:
    """Low-frequency smooth bend: quadratic displacement in x across y."""
    h, w = img.shape[:2]
    yy, xx = _coords((h, w))
    yn = (yy - (h - 1) / 2.0) / max((h - 1) / 2.0, 1.0)
    disp = curvature * (yn**2) * (w - 1)
    return warp(img, yy, xx + disp)


def apply_partial_occlusion(img: np.ndarray, fraction: float, seed_bits: int = 0) -> np.ndarray:
    """Zero out a deterministic rectangular region covering `fraction` of area.

    Rectangle position/shape is derived deterministically from seed_bits so
    replay reproduces it exactly.
    """
    out = img.copy()
    frac = float(np.clip(fraction, 0.0, 1.0))
    if frac <= 0.0:
        return out
    h, w = img.shape[:2]
    rng = np.random.default_rng(np.random.SeedSequence([int(seed_bits)]))
    area = frac * h * w
    aspect = float(rng.uniform(0.5, 2.0))
    rh = max(1, int(round(math.sqrt(area * aspect))))
    rw = max(1, int(round(area / rh)))
    rh = min(rh, h)
    rw = min(rw, w)
    y0 = int(rng.integers(0, h - rh + 1))
    x0 = int(rng.integers(0, w - rw + 1))
    out[y0 : y0 + rh, x0 : x0 + rw] = 0.0
    return out


def apply_garment(img: np.ndarray, params: Dict[str, Any]) -> np.ndarray:
    out = apply_stretch(img, float(params.get("stretch", 1.0)))
    out = apply_wrinkle(out, float(params.get("wrinkle", 0.0)))
    out = apply_fold(out, float(params.get("fold", 0.0)))
    out = apply_bend(out, float(params.get("bend", 0.0)))
    out = apply_partial_occlusion(out, float(params.get("partial_occlusion", 0.0)))
    return out


# ---------------------------------------------------------------------------
# print_capture
# ---------------------------------------------------------------------------

def gamut_mapping(img: np.ndarray, intensity: float) -> np.ndarray:
    """Documented RGB gamut clip/compress curve.

    intensity in [0,1]: 0 = identity, 1 = maximal compression. Values outside
    the printable gamut proxy [lo, hi] = [0.05, 0.95] are compressed toward it
    via a soft-clip (tanh) curve; the image is then renormalized so the curve
    endpoints map exactly to [lo, hi]. Pure clip/compress, no color science.
    """
    t = float(np.clip(intensity, 0.0, 1.0))
    if t == 0.0:
        return np.clip(img, 0.0, 1.0)
    lo, hi = 0.05, 0.95
    # soft-clip toward [lo, hi] as intensity grows
    x = np.clip(img, 0.0, 1.0)
    k = 1.0 + 3.0 * t
    compressed = 0.5 + 0.5 * np.tanh(k * (x - 0.5)) / math.tanh(k / 2.0)
    blended = (1.0 - t) * x + t * (lo + (hi - lo) * compressed)
    return np.clip(blended, 0.0, 1.0)


def resolution_loss(img: np.ndarray, factor: float) -> np.ndarray:
    """Resolution loss = downsample then upsample back to the original shape."""
    f = float(factor)
    if f <= 1.0:
        return img.copy()
    down = resize(img, 1.0 / f, "bilinear")
    h, w = img.shape[:2]
    up = resize(down, f, "bilinear")
    # trim/pad back to exact original shape
    out = np.zeros_like(img)
    oh = min(h, up.shape[0])
    ow = min(w, up.shape[1])
    out[:oh, :ow] = up[:oh, :ow]
    return out


def calibration_transform(
    img: np.ndarray,
    calibration_transform_ref: Optional[str],
    available: Optional[Dict[str, Any]] = None,
) -> np.ndarray:
    """Calibration transform passthrough.

    - ref None -> identity (no calibration requested).
    - ref set but not present in `available` -> fail-closed
      CalibrationUnavailableError. A real calibration transform is NEVER
      faked.
    - ref present in `available` as a 3x3 matrix -> applied to RGB channels.
    """
    if calibration_transform_ref is None:
        return img
    available = available or {}
    if calibration_transform_ref not in available:
        raise CalibrationUnavailableError(
            f"calibration transform {calibration_transform_ref!r} requested but unavailable; "
            "refusing to fabricate a calibration"
        )
    matrix = np.asarray(available[calibration_transform_ref], dtype=np.float64)
    if img.ndim == 3 and img.shape[2] == 3 and matrix.shape == (3, 3):
        flat = img.reshape(-1, 3) @ matrix.T
        return np.clip(flat.reshape(img.shape), 0.0, 1.0)
    raise CalibrationUnavailableError(
        f"calibration transform {calibration_transform_ref!r} is incompatible with the input"
    )


def apply_print_capture(
    img: np.ndarray,
    params: Dict[str, Any],
    available_calibrations: Optional[Dict[str, Any]] = None,
) -> np.ndarray:
    out = gamut_mapping(img, float(params.get("gamut_mapping", 0.0)))
    out = resolution_loss(out, float(params.get("resolution_loss", 1.0)))
    out = calibration_transform(out, params.get("calibration_transform_ref"), available_calibrations)
    return out
