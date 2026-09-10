from __future__ import annotations
import hashlib, json
from dataclasses import dataclass
from pathlib import Path
from .errors import PatternGenomeValidationError

@dataclass(frozen=True)
class PatternGenomeConfig:
    schema_version: str = "rac-pattern-genome-config/1.0"
    luminance_method: str = "rec709"
    fft_window: str = "hann"
    radial_bins: int = 8
    palette_method: str = "deterministic_kmeans"
    palette_max_colors: int = 8
    palette_seed: int = 1337
    palette_iterations: int = 20
    connectivity: int = 8
    spatial_hist_bins: int = 16
    max_image_dimension: int = 4096

    def validate(self) -> None:
        if self.radial_bins != 8: raise PatternGenomeValidationError("Pattern Genome v1 requires radial_bins=8")
        if self.palette_method != "deterministic_kmeans": raise PatternGenomeValidationError("unsupported palette_method")
        if not (1 <= self.palette_max_colors <= 32): raise PatternGenomeValidationError("palette_max_colors out of range")
        if self.palette_iterations <= 0: raise PatternGenomeValidationError("palette_iterations must be positive")
        if self.connectivity not in (4, 8): raise PatternGenomeValidationError("connectivity must be 4 or 8")
        if self.spatial_hist_bins <= 1: raise PatternGenomeValidationError("spatial_hist_bins must be >1")
        if self.max_image_dimension <= 0: raise PatternGenomeValidationError("max_image_dimension must be positive")

    def canonical_json(self) -> bytes:
        self.validate()
        return json.dumps(self.__dict__, sort_keys=True, separators=(",", ":")).encode()

    @property
    def sha256(self) -> str:
        return hashlib.sha256(self.canonical_json()).hexdigest()

def load_config(path: str | Path) -> PatternGenomeConfig:
    data=json.loads(Path(path).read_text())
    cfg=PatternGenomeConfig(**data)
    cfg.validate(); return cfg
