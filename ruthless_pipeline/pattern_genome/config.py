"""Frozen extraction configuration for Pattern Genome v1."""
from __future__ import annotations
import json
from dataclasses import dataclass
from pathlib import Path
from .canonical import sha256_bytes
from .errors import PatternGenomeSchemaError

CONFIG_SCHEMA = "rac-pattern-genome-config/1.0"

@dataclass(frozen=True)
class PatternGenomeConfig:
    luminance_method: str
    fft_window: str
    radial_bins: int
    palette_method: str
    palette_max_colors: int
    palette_seed: int
    palette_iterations: int
    connectivity: int
    symmetry_method: str
    autocorrelation_method: str

    def validate(self) -> None:
        if self.luminance_method != "rec709":
            raise PatternGenomeSchemaError(f"unsupported luminance_method: {self.luminance_method!r}")
        if self.fft_window not in {"hann", "none"}:
            raise PatternGenomeSchemaError(f"unsupported fft_window: {self.fft_window!r}")
        if self.radial_bins != 8:
            raise PatternGenomeSchemaError("Pattern Genome v1 requires radial_bins=8")
        if self.palette_method != "deterministic_kmeans":
            raise PatternGenomeSchemaError(f"unsupported palette_method: {self.palette_method!r}")
        if not (1 <= self.palette_max_colors <= 32):
            raise PatternGenomeSchemaError("palette_max_colors must be in [1,32]")
        if self.palette_iterations <= 0:
            raise PatternGenomeSchemaError("palette_iterations must be positive")
        if self.connectivity not in {4, 8}:
            raise PatternGenomeSchemaError("connectivity must be 4 or 8")
        if not self.symmetry_method:
            raise PatternGenomeSchemaError("symmetry_method is required")
        if not self.autocorrelation_method:
            raise PatternGenomeSchemaError("autocorrelation_method is required")

    @property
    def config_sha256(self) -> str:
        return sha256_bytes(json.dumps({
            "luminance_method": self.luminance_method, "fft_window": self.fft_window,
            "radial_bins": self.radial_bins, "palette_method": self.palette_method,
            "palette_max_colors": self.palette_max_colors, "palette_seed": self.palette_seed,
            "palette_iterations": self.palette_iterations, "connectivity": self.connectivity,
            "symmetry_method": self.symmetry_method,
            "autocorrelation_method": self.autocorrelation_method,
        }, sort_keys=True, separators=(",", ":")).encode("utf-8"))

def load_config(path):
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if raw.get("schema_version") != CONFIG_SCHEMA:
        raise PatternGenomeSchemaError(f"unknown config schema: {raw.get('schema_version')!r}")
    config = PatternGenomeConfig(
        luminance_method=raw["luminance_method"], fft_window=raw["fft_window"],
        radial_bins=int(raw["radial_bins"]), palette_method=raw["palette_method"],
        palette_max_colors=int(raw["palette_max_colors"]),
        palette_seed=int(raw["palette_seed"]),
        palette_iterations=int(raw["palette_iterations"]),
        connectivity=int(raw["connectivity"]), symmetry_method=raw["symmetry_method"],
        autocorrelation_method=raw["autocorrelation_method"],
    )
    config.validate()
    return config
