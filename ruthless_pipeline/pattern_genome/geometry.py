"""Geometric features: spatial composition, coverage, feature sizes."""
from __future__ import annotations
import numpy as np
from scipy import ndimage
from .color import _kmeans_palette
from .errors import PatternGenomeNonFiniteError
from .schema import GeometryGenome

def extract_geometry(rgb, config):
    h, w = rgb.shape[:2]
    total_px = h * w
    flat = rgb.reshape(-1, 3).astype(np.float64)
    unique_centroids, labels = _kmeans_palette(flat, config)
    palette_k = len(unique_centroids)
    label_img = labels.reshape(h, w)
    counts = np.bincount(labels, minlength=palette_k)
    bg_label = int(counts.argmax())
    foreground = label_img != bg_label
    foreground_coverage_fraction = float(foreground.sum() / total_px)
    if foreground.any():
        dist = ndimage.distance_transform_edt(foreground)
        maxima = dist == ndimage.maximum_filter(dist, size=3)
        widths = 2.0 * dist[maxima]
        if len(widths) == 0:
            widths = np.array([0.0])
        mean_fw = float(widths.mean())
        median_fw = float(np.median(widths))
        min_fw = float(widths.min())
        mean_fw_norm = float(widths.mean() / min(h, w))
        min_fw_norm = float(widths.min() / min(h, w))
    else:
        mean_fw = median_fw = min_fw = mean_fw_norm = min_fw_norm = 0.0
    lum = 0.2126 * rgb[..., 0] + 0.7152 * rgb[..., 1] + 0.0722 * rgb[..., 2]
    gy, gx = np.gradient(lum)
    grad_mag = np.sqrt(gx**2 + gy**2)
    edge_map = grad_mag > grad_mag.mean() + grad_mag.std()
    edge_to_area_ratio = float(edge_map.sum() / max(1, foreground.sum()))
    if foreground.any():
        rows = np.any(foreground, axis=1)
        cols = np.any(foreground, axis=0)
        rmin, rmax = np.where(rows)[0][[0, -1]]
        cmin, cmax = np.where(cols)[0][[0, -1]]
        bbox_area = (rmax - rmin + 1) * (cmax - cmin + 1)
        bbox_occupancy = float(foreground.sum() / bbox_area)
    else:
        bbox_occupancy = 0.0
    if foreground.any():
        cy_fg, cx_fg = ndimage.center_of_mass(foreground)
    else:
        cy_fg, cx_fg = h / 2.0, w / 2.0
    com_x = float(cx_fg / w)
    com_y = float(cy_fg / h)
    mid_y, mid_x = h // 2, w // 2
    quadrant_energy = (
        float(lum[:mid_y, :mid_x].mean()), float(lum[:mid_y, mid_x:].mean()),
        float(lum[mid_y:, :mid_x].mean()), float(lum[mid_y:, mid_x:].mean()),
    )
    if foreground.any():
        hist, _, _ = np.histogram2d(*np.where(foreground), bins=16, range=[[0, h], [0, w]])
        p = hist.flatten()
        p = p[p > 0] / p.sum()
        spatial_entropy = float(-(p * np.log2(p)).sum())
    else:
        spatial_entropy = 0.0
    result = GeometryGenome(
        foreground_coverage_fraction=foreground_coverage_fraction,
        edge_to_area_ratio=edge_to_area_ratio, mean_feature_width_px=mean_fw,
        median_feature_width_px=median_fw, min_feature_width_px=min_fw,
        mean_feature_width_normalized=mean_fw_norm, min_feature_width_normalized=min_fw_norm,
        bbox_occupancy_fraction=bbox_occupancy, center_of_mass_x=com_x, center_of_mass_y=com_y,
        quadrant_energy=quadrant_energy, spatial_entropy=spatial_entropy,
    )
    vals = [
        result.foreground_coverage_fraction, result.edge_to_area_ratio,
        result.mean_feature_width_px, result.median_feature_width_px,
        result.min_feature_width_px, result.mean_feature_width_normalized,
        result.min_feature_width_normalized, result.bbox_occupancy_fraction,
        result.center_of_mass_x, result.center_of_mass_y, result.spatial_entropy,
    ] + list(result.quadrant_energy)
    if not all(np.isfinite(v) for v in vals):
        raise PatternGenomeNonFiniteError("non-finite geometry feature")
    return result
