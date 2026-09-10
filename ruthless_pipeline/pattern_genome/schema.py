from __future__ import annotations
from dataclasses import asdict, dataclass
from typing import Any

SCHEMA_VERSION = "rac-pattern-genome/1.0"
EVIDENCE_CLASS = "derived_digital_measurement"

@dataclass(frozen=True)
class GenomeSource:
    artifact_ref: str
    width_px: int
    height_px: int
    channels: int = 3

@dataclass(frozen=True)
class SpectralGenome:
    radial_energy: tuple[float, ...]
    low_frequency_ratio: float
    mid_frequency_ratio: float
    high_frequency_ratio: float
    spectral_centroid: float
    spectral_entropy: float
    dominant_orientation_deg: float
    orientation_strength: float

@dataclass(frozen=True)
class TopologyGenome:
    connected_component_count: int
    largest_component_fraction: float
    mean_component_fraction: float
    median_component_fraction: float
    component_area_std: float
    hole_count: int
    euler_characteristic: int
    edge_density: float
    horizontal_symmetry: float
    vertical_symmetry: float
    diagonal_symmetry_main: float
    diagonal_symmetry_anti: float
    rotational_symmetry_180: float
    motif_autocorrelation_peak: float
    motif_period_x: float
    motif_period_y: float
    fragmentation_index: float

@dataclass(frozen=True)
class ColorGenome:
    palette_size: int
    rgb_mean: tuple[float, float, float]
    rgb_std: tuple[float, float, float]
    lab_mean: tuple[float, float, float]
    lab_covariance: tuple[tuple[float, float, float], tuple[float, float, float], tuple[float, float, float]]
    lab_range_l: float
    lab_range_a: float
    lab_range_b: float
    mean_pairwise_delta_e: float
    max_pairwise_delta_e: float
    luminance_contrast: float
    chromatic_contrast: float
    color_entropy: float
    dominant_palette: tuple[dict[str, Any], ...]

@dataclass(frozen=True)
class GeometryGenome:
    foreground_coverage_fraction: float
    edge_to_area_ratio: float
    mean_feature_width_px: float
    median_feature_width_px: float
    min_feature_width_px: float
    mean_feature_width_normalized: float
    min_feature_width_normalized: float
    bbox_occupancy_fraction: float
    center_of_mass_x: float
    center_of_mass_y: float
    quadrant_energy: tuple[float, float, float, float]
    spatial_entropy: float

@dataclass(frozen=True)
class GenomeQuality:
    all_finite: bool
    warnings: tuple[str, ...] = ()

@dataclass(frozen=True)
class GenomeProvenance:
    candidate_sha256: str
    source_artifact_ref: str
    extractor_version: str
    genome_schema: str
    source_commit: str
    runtime_lock_sha256: str
    extractor_config_sha256: str
    extracted_utc: str
    evidence_class: str = EVIDENCE_CLASS

@dataclass(frozen=True)
class PatternGenome:
    schema_version: str
    genome_id: str
    candidate_sha256: str
    source: GenomeSource
    spectral: SpectralGenome
    topology: TopologyGenome
    color: ColorGenome
    geometry: GeometryGenome
    quality: GenomeQuality
    provenance: GenomeProvenance

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
