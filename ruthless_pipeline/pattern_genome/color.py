"""Color features: deterministic palette, CIELAB, delta-E, entropy."""
from __future__ import annotations
import math
import numpy as np
from .config import PatternGenomeConfig
from .errors import PatternGenomeNonFiniteError
from .schema import ColorGenome

def _rgb_to_lab(rgb_flat):
    srgb = rgb_flat / 255.0
    linear = np.where(srgb <= 0.04045, srgb / 12.92, ((srgb + 0.055) / 1.055) ** 2.4)
    xyz = linear @ np.array([
        [0.4124564, 0.2126729, 0.0193339],
        [0.3575761, 0.7151522, 0.1191920],
        [0.1804375, 0.0721750, 0.9503041],
    ]).T / np.array([0.95047, 1.0, 1.08883])
    eps, kappa = 216.0 / 24389.0, 24389.0 / 27.0
    f = np.where(xyz > eps, np.cbrt(xyz), (kappa * xyz + 16.0) / 116.0)
    return np.stack([116.0 * f[:, 1] - 16.0, 500.0 * (f[:, 0] - f[:, 1]),
                     200.0 * (f[:, 1] - f[:, 2])], axis=1)

def _kmeans_palette(flat, config):
    unique_values = np.unique(flat, axis=0)
    k = min(config.palette_max_colors, len(unique_values))
    if k < 1:
        raise ValueError("cannot extract palette from empty input")
    rng = np.random.RandomState(config.palette_seed)
    centroids = [unique_values[rng.randint(len(unique_values))]]
    for _ in range(1, k):
        d2 = np.min([((unique_values - c) ** 2).sum(axis=1) for c in centroids], axis=0)
        centroids.append(unique_values[int(np.argmax(d2))])
    centroids = np.array(centroids, dtype=np.float64)
    for _ in range(config.palette_iterations):
        dists = ((flat[:, None, :] - centroids[None, :, :]) ** 2).sum(axis=2)
        labels = dists.argmin(axis=1)
        new_c = np.array([flat[labels == i].mean(axis=0) if (labels == i).any() else centroids[i]
                          for i in range(k)])
        if np.allclose(new_c, centroids):
            break
        centroids = new_c
    unique, umap = [], {}
    for i, c in enumerate(centroids):
        found = False
        for j, uc in enumerate(unique):
            if np.allclose(c, uc, atol=1.0):
                umap[i] = j; found = True; break
        if not found:
            umap[i] = len(unique); unique.append(c)
    return np.array(unique), np.array([umap[l] for l in labels])

def extract_color(rgb, config):
    flat = rgb.reshape(-1, 3).astype(np.float64)
    rgb_mean = tuple(float(v) for v in flat.mean(axis=0))
    rgb_std = tuple(float(v) for v in flat.std(axis=0))
    lab = _rgb_to_lab(flat)
    lab_mean = tuple(float(v) for v in lab.mean(axis=0))
    lab_cov = np.cov(lab.T)
    lab_covariance = tuple(tuple(float(lab_cov[i, j]) for j in range(3)) for i in range(3))
    lab_range_l = float(lab[:, 0].max() - lab[:, 0].min())
    lab_range_a = float(lab[:, 1].max() - lab[:, 1].min())
    lab_range_b = float(lab[:, 2].max() - lab[:, 2].min())
    unique_centroids, labels = _kmeans_palette(flat, config)
    palette_k = len(unique_centroids)
    counts = np.bincount(labels, minlength=palette_k).astype(np.float64)
    fractions = counts / counts.sum()
    lab_centroids = _rgb_to_lab(unique_centroids)
    lum_order = np.argsort(-lab_centroids[:, 0])
    dominant_palette = tuple(
        {"lab": [float(v) for v in lab_centroids[idx]], "fraction": float(fractions[idx])}
        for idx in lum_order)
    if palette_k > 1:
        deltas = [float(np.sqrt(((lab_centroids[i] - lab_centroids[j]) ** 2).sum()))
                  for i in range(palette_k) for j in range(i + 1, palette_k)]
        mean_de, max_de = float(np.mean(deltas)), float(np.max(deltas))
    else:
        mean_de = max_de = 0.0
    luminance_contrast = min(1.0, max(0.0, float((lab[:, 0].max() - lab[:, 0].min()) / 100.0)))
    chroma = np.sqrt(lab[:, 1] ** 2 + lab[:, 2] ** 2)
    chromatic_contrast = float((chroma.max() - chroma.min()) / (chroma.max() + 1e-12))
    p = fractions[fractions > 0]
    color_entropy = float(-(p * np.log2(p)).sum())
    result = ColorGenome(
        palette_size=int(palette_k), rgb_mean=rgb_mean, rgb_std=rgb_std,
        lab_mean=lab_mean, lab_covariance=lab_covariance,
        lab_range_l=lab_range_l, lab_range_a=lab_range_a, lab_range_b=lab_range_b,
        mean_pairwise_delta_e=mean_de, max_pairwise_delta_e=max_de,
        luminance_contrast=luminance_contrast, chromatic_contrast=chromatic_contrast,
        color_entropy=color_entropy, dominant_palette=dominant_palette,
    )
    vals = list(result.rgb_mean) + list(result.rgb_std) + list(result.lab_mean) + [
        result.lab_range_l, result.lab_range_a, result.lab_range_b,
        result.mean_pairwise_delta_e, result.max_pairwise_delta_e,
        result.luminance_contrast, result.chromatic_contrast, result.color_entropy,
    ] + [v for row in result.lab_covariance for v in row]
    if not all(np.isfinite(v) and math.isfinite(v) for v in vals):
        raise PatternGenomeNonFiniteError("non-finite color feature")
    return result
