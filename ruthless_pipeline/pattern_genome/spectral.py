"""Spectral features: radial FFT energy, orientation, entropy."""
from __future__ import annotations
import numpy as np
from .config import PatternGenomeConfig
from .errors import PatternGenomeNonFiniteError
from .schema import SpectralGenome

def _luminance(rgb, method):
    if method == "rec709":
        return 0.2126 * rgb[..., 0] + 0.7152 * rgb[..., 1] + 0.0722 * rgb[..., 2]
    raise ValueError(f"unknown luminance_method: {method}")

def _window_2d(shape, window):
    if window == "hann":
        return np.outer(np.hanning(shape[0]), np.hanning(shape[1]))
    if window == "none":
        return np.ones(shape)
    raise ValueError(f"unknown fft_window: {window}")

def extract_spectral(rgb, config):
    h, w = rgb.shape[:2]
    lum = _luminance(rgb, config.luminance_method)
    lum = lum - lum.mean()
    lum_win = lum * _window_2d((h, w), config.fft_window)
    power = np.abs(np.fft.fftshift(np.fft.fft2(lum_win))) ** 2
    cy, cx = h // 2, w // 2
    y, x = np.indices((h, w))
    r_norm = np.clip(np.sqrt((y - cy) ** 2 + (x - cx) ** 2) / (min(h, w) / 2.0), 0.0, 1.0)
    n_bins = config.radial_bins
    edges = np.linspace(0.0, 1.0, n_bins + 1)
    bin_energy = np.zeros(n_bins)
    for i in range(n_bins):
        mask = (r_norm >= edges[i]) & (r_norm < edges[i + 1] if i < n_bins - 1 else r_norm <= edges[i + 1])
        bin_energy[i] = power[mask].sum()
    total = bin_energy.sum()
    if total <= 0.0 or not np.isfinite(total):
        raise PatternGenomeNonFiniteError("spectral power sum is zero or non-finite")
    radial = tuple(float(e / total) for e in bin_energy)
    low_r = float(power[r_norm < 1.0/3.0].sum() / total)
    mid_r = float(power[(r_norm >= 1.0/3.0) & (r_norm < 2.0/3.0)].sum() / total)
    high_r = float(power[r_norm >= 2.0/3.0].sum() / total)
    centroid = float((r_norm * power).sum() / total)
    p = bin_energy / total
    p_nz = p[p > 0]
    entropy = float(-(p_nz * np.log2(p_nz)).sum() / np.log2(n_bins))
    gy, gx = np.gradient(lum)
    gxx, gyy, gxy = (gx*gx).sum(), (gy*gy).sum(), (gx*gy).sum()
    theta = 0.5 * np.arctan2(2.0 * gxy, gxx - gyy)
    orientation_deg = float(np.degrees(theta) % 180.0)
    orientation_strength = float(np.sqrt((gxx - gyy) ** 2 + 4.0 * gxy**2) / (gxx + gyy + 1e-12))
    result = SpectralGenome(
        radial_energy=radial, low_frequency_ratio=low_r, mid_frequency_ratio=mid_r,
        high_frequency_ratio=high_r, spectral_centroid=centroid, spectral_entropy=entropy,
        dominant_orientation_deg=orientation_deg,
        orientation_strength=min(1.0, max(0.0, orientation_strength)),
    )
    vals = list(result.radial_energy) + [result.low_frequency_ratio, result.mid_frequency_ratio,
        result.high_frequency_ratio, result.spectral_centroid, result.spectral_entropy,
        result.dominant_orientation_deg, result.orientation_strength]
    if not all(np.isfinite(v) for v in vals):
        raise PatternGenomeNonFiniteError("non-finite spectral feature")
    return result
