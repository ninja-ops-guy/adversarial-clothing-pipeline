"""Genome record validation. Fail-closed on any violation."""
from __future__ import annotations
import math
import numpy as np
from .errors import PatternGenomeValidationError
from .provenance import validate_provenance
from .schema import SCHEMA_VERSION, PatternGenome

TOLERANCE = 1e-9

def _require(condition, message):
    if not condition:
        raise PatternGenomeValidationError(message)

def _finite(value, name):
    _require(isinstance(value, (int, float)) and math.isfinite(value),
             f"{name} must be a finite number, got {value!r}")

def _in_range(value, lo, hi, name):
    _finite(value, name)
    _require(lo - TOLERANCE <= value <= hi + TOLERANCE,
             f"{name} must be in [{lo}, {hi}], got {value}")

def validate_genome(genome: PatternGenome) -> None:
    _require(genome.schema_version == SCHEMA_VERSION,
             f"schema_version must be {SCHEMA_VERSION!r}, got {genome.schema_version!r}")
    _require(bool(genome.genome_id), "genome_id is required")
    _require(len(genome.candidate_sha256) == 64,
             f"candidate_sha256 must be 64 hex chars, got {len(genome.candidate_sha256)}")
    _require(genome.source.width_px > 0, "source.width_px must be positive")
    _require(genome.source.height_px > 0, "source.height_px must be positive")
    _require(genome.source.channels == 3, "source.channels must be 3")
    s = genome.spectral
    _require(len(s.radial_energy) == 8, f"radial_energy must have 8 bins, got {len(s.radial_energy)}")
    for i, v in enumerate(s.radial_energy):
        _in_range(v, 0.0, 1.0, f"spectral.radial_energy[{i}]")
    _require(abs(sum(s.radial_energy) - 1.0) < 1e-6,
             f"radial_energy must sum to 1.0, got {sum(s.radial_energy)}")
    _in_range(s.low_frequency_ratio, 0.0, 1.0, "spectral.low_frequency_ratio")
    _in_range(s.mid_frequency_ratio, 0.0, 1.0, "spectral.mid_frequency_ratio")
    _in_range(s.high_frequency_ratio, 0.0, 1.0, "spectral.high_frequency_ratio")
    _finite(s.spectral_centroid, "spectral.spectral_centroid")
    _in_range(s.spectral_entropy, 0.0, 1.0, "spectral.spectral_entropy")
    _in_range(s.dominant_orientation_deg, 0.0, 180.0, "spectral.dominant_orientation_deg")
    _in_range(s.orientation_strength, 0.0, 1.0, "spectral.orientation_strength")
    t = genome.topology
    _require(t.connected_component_count >= 0, "topology.connected_component_count must be >= 0")
    _in_range(t.largest_component_fraction, 0.0, 1.0, "topology.largest_component_fraction")
    _in_range(t.mean_component_fraction, 0.0, 1.0, "topology.mean_component_fraction")
    _in_range(t.median_component_fraction, 0.0, 1.0, "topology.median_component_fraction")
    _in_range(t.component_area_std, 0.0, 1.0, "topology.component_area_std")
    _require(t.hole_count >= 0, "topology.hole_count must be >= 0")
    _in_range(t.edge_density, 0.0, 1.0, "topology.edge_density")
    for name in ("horizontal_symmetry", "vertical_symmetry", "diagonal_symmetry_main",
                 "diagonal_symmetry_anti", "rotational_symmetry_180",
                 "motif_autocorrelation_peak"):
        _in_range(getattr(t, name), 0.0, 1.0, f"topology.{name}")
    _finite(t.motif_period_x, "topology.motif_period_x")
    _finite(t.motif_period_y, "topology.motif_period_y")
    _require(t.motif_period_x >= 0, "topology.motif_period_x must be >= 0")
    _require(t.motif_period_y >= 0, "topology.motif_period_y must be >= 0")
    _finite(t.fragmentation_index, "topology.fragmentation_index")
    _require(t.palette_k >= 1, "topology.palette_k must be >= 1")
    c = genome.color
    _require(c.palette_size >= 1, "color.palette_size must be >= 1")
    for i, v in enumerate(c.rgb_mean):
        _in_range(v, 0.0, 255.0, f"color.rgb_mean[{i}]")
    for i, v in enumerate(c.rgb_std):
        _finite(v, f"color.rgb_std[{i}]"); _require(v >= 0, f"color.rgb_std[{i}] must be >= 0")
    _in_range(c.lab_mean[0], 0.0, 100.0, "color.lab_mean[0] (L)")
    for i, v in enumerate(c.lab_mean[1:], 1):
        _finite(v, f"color.lab_mean[{i}]")
    for i, row in enumerate(c.lab_covariance):
        for j, v in enumerate(row):
            _finite(v, f"color.lab_covariance[{i}][{j}]")
    for name in ("lab_range_l", "lab_range_a", "lab_range_b"):
        _finite(getattr(c, name), f"color.{name}"); _require(getattr(c, name) >= 0, f"color.{name} must be >= 0")
    _finite(c.mean_pairwise_delta_e, "color.mean_pairwise_delta_e")
    _require(c.mean_pairwise_delta_e >= 0, "color.mean_pairwise_delta_e must be >= 0")
    _finite(c.max_pairwise_delta_e, "color.max_pairwise_delta_e")
    _require(c.max_pairwise_delta_e >= 0, "color.max_pairwise_delta_e must be >= 0")
    _in_range(c.luminance_contrast, 0.0, 1.0, "color.luminance_contrast")
    _in_range(c.chromatic_contrast, 0.0, 1.0, "color.chromatic_contrast")
    _finite(c.color_entropy, "color.color_entropy")
    _require(0.0 <= c.color_entropy <= float(np.log2(max(2, c.palette_size))) + TOLERANCE,
             f"color.color_entropy must be in [0, log2(palette_size)], got {c.color_entropy}")
    _require(len(c.dominant_palette) >= 1, "color.dominant_palette must be non-empty")
    for i, entry in enumerate(c.dominant_palette):
        _require("lab" in entry, f"color.dominant_palette[{i}] missing 'lab'")
        _require("fraction" in entry, f"color.dominant_palette[{i}] missing 'fraction'")
        _in_range(entry["fraction"], 0.0, 1.0, f"color.dominant_palette[{i}].fraction")
    g = genome.geometry
    _in_range(g.foreground_coverage_fraction, 0.0, 1.0, "geometry.foreground_coverage_fraction")
    _finite(g.edge_to_area_ratio, "geometry.edge_to_area_ratio")
    _require(g.edge_to_area_ratio >= 0, "geometry.edge_to_area_ratio must be >= 0")
    for name in ("mean_feature_width_px", "median_feature_width_px", "min_feature_width_px"):
        _finite(getattr(g, name), f"geometry.{name}"); _require(getattr(g, name) >= 0, f"geometry.{name} must be >= 0")
    _in_range(g.mean_feature_width_normalized, 0.0, 1.0, "geometry.mean_feature_width_normalized")
    _in_range(g.min_feature_width_normalized, 0.0, 1.0, "geometry.min_feature_width_normalized")
    _in_range(g.bbox_occupancy_fraction, 0.0, 1.0, "geometry.bbox_occupancy_fraction")
    _in_range(g.center_of_mass_x, 0.0, 1.0, "geometry.center_of_mass_x")
    _in_range(g.center_of_mass_y, 0.0, 1.0, "geometry.center_of_mass_y")
    _require(len(g.quadrant_energy) == 4, "geometry.quadrant_energy must have 4 values")
    for i, v in enumerate(g.quadrant_energy):
        _finite(v, f"geometry.quadrant_energy[{i}]")
    _finite(g.spatial_entropy, "geometry.spatial_entropy")
    _require(g.spatial_entropy >= 0, "geometry.spatial_entropy must be >= 0")
    _require(genome.quality.all_finite, "quality.all_finite must be True")
    validate_provenance(genome.provenance)
