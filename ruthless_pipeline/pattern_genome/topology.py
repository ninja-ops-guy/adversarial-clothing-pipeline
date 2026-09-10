"""Topological features: palette-segmented components, symmetry, motifs."""
from __future__ import annotations
import numpy as np
from scipy import ndimage
from .color import _kmeans_palette
from .errors import PatternGenomeNonFiniteError
from .schema import TopologyGenome

SEGMENTATION_METHOD = "deterministic_palette_v1"

def _ncc(a, b):
    a, b = a.astype(np.float64), b.astype(np.float64)
    a, b = a - a.mean(), b - b.mean()
    denom = np.sqrt((a**2).sum() * (b**2).sum())
    if denom < 1e-12:
        return 1.0 if np.allclose(a, b) else 0.0
    return float((a * b).sum() / denom)

def extract_topology(rgb, config):
    h, w = rgb.shape[:2]
    flat = rgb.reshape(-1, 3).astype(np.float64)
    unique_centroids, labels = _kmeans_palette(flat, config)
    palette_k = len(unique_centroids)
    label_img = labels.reshape(h, w)
    structure = ndimage.generate_binary_structure(2, 2) if config.connectivity == 8 else ndimage.generate_binary_structure(2, 1)
    total_components, all_areas, total_holes = 0, [], 0
    for li in range(palette_k):
        mask = label_img == li
        if not mask.any():
            continue
        lab_arr, n = ndimage.label(mask, structure=structure)
        total_components += n
        all_areas.extend(ndimage.sum(mask, lab_arr, range(1, n + 1)).tolist())
        inv = ~mask
        inv_lab, inv_n = ndimage.label(inv, structure=structure)
        border = set(inv_lab[0, :]) | set(inv_lab[-1, :]) | set(inv_lab[:, 0]) | set(inv_lab[:, -1])
        border.discard(0)
        total_holes += max(0, inv_n - len(border))
    areas = np.array(all_areas, dtype=np.float64)
    total_px = h * w
    lum = 0.2126 * rgb[..., 0] + 0.7152 * rgb[..., 1] + 0.0722 * rgb[..., 2]
    gy, gx = np.gradient(lum)
    grad_mag = np.sqrt(gx**2 + gy**2)
    edge_density = float((grad_mag > grad_mag.mean() + grad_mag.std()).sum() / total_px)
    clamp01 = lambda v: min(1.0, max(0.0, v))
    h_sym = clamp01(_ncc(lum, lum[::-1, :]))
    v_sym = clamp01(_ncc(lum, lum[:, ::-1]))
    d_main = clamp01(_ncc(lum, lum.T) if h == w else _ncc(lum, np.rot90(lum, 2).T[::-1, ::-1]))
    d_anti = clamp01(_ncc(lum, np.rot90(lum.T, 2)) if h == w else _ncc(lum, np.rot90(lum, 2).T))
    r180 = clamp01(_ncc(lum, np.rot90(lum, 2)))
    F = np.fft.fft2(lum - lum.mean())
    autocorr = np.fft.fftshift(np.fft.ifft2(np.abs(F) ** 2).real)
    autocorr = autocorr / (autocorr.max() + 1e-12)
    cy, cx = h // 2, w // 2
    autocorr[cy, cx] = 0
    peak_idx = np.unravel_index(np.argmax(autocorr), autocorr.shape)
    motif_peak = float(autocorr[peak_idx])
    motif_py, motif_px = float(abs(peak_idx[0] - cy)), float(abs(peak_idx[1] - cx))
    result = TopologyGenome(
        connected_component_count=int(total_components) if total_components > 0 else 0,
        largest_component_fraction=float(areas.max() / total_px) if len(areas) else 0.0,
        mean_component_fraction=float(areas.mean() / total_px) if len(areas) else 0.0,
        median_component_fraction=float(np.median(areas) / total_px) if len(areas) else 0.0,
        component_area_std=float(areas.std() / total_px) if len(areas) else 0.0,
        hole_count=int(total_holes), euler_characteristic=int(total_components - total_holes),
        edge_density=edge_density, horizontal_symmetry=h_sym, vertical_symmetry=v_sym,
        diagonal_symmetry_main=d_main, diagonal_symmetry_anti=d_anti,
        rotational_symmetry_180=r180, motif_autocorrelation_peak=motif_peak,
        motif_period_x=motif_px, motif_period_y=motif_py,
        fragmentation_index=float(total_components / max(1, palette_k)),
        segmentation_method=SEGMENTATION_METHOD, palette_k=palette_k,
    )
    vals = [result.largest_component_fraction, result.mean_component_fraction,
        result.median_component_fraction, result.component_area_std, result.edge_density,
        result.horizontal_symmetry, result.vertical_symmetry, result.diagonal_symmetry_main,
        result.diagonal_symmetry_anti, result.rotational_symmetry_180,
        result.motif_autocorrelation_peak, result.motif_period_x, result.motif_period_y,
        result.fragmentation_index]
    if not all(np.isfinite(v) for v in vals):
        raise PatternGenomeNonFiniteError("non-finite topology feature")
    return result
