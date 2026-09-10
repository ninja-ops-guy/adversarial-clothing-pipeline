"""Genome extraction orchestrator. Fail-closed on any invalid input."""
from __future__ import annotations
import hashlib
import io
import numpy as np
from PIL import Image, ImageOps
from .canonical import genome_sha256
from .color import extract_color
from .config import PatternGenomeConfig
from .errors import PatternGenomeInputError
from .geometry import extract_geometry
from .provenance import build_provenance, validate_provenance
from .schema import SCHEMA_VERSION, GenomeQuality, GenomeSource, PatternGenome
from .spectral import extract_spectral
from .topology import extract_topology

MAX_DIM = 4096

def _decode_image(candidate_bytes: bytes) -> np.ndarray:
    try:
        img = Image.open(io.BytesIO(candidate_bytes))
    except Exception as exc:
        raise PatternGenomeInputError(f"cannot decode image: {exc}") from exc
    try:
        img = ImageOps.exif_transpose(img)
    except Exception:
        pass
    if img.mode not in ("RGB", "RGBA", "L", "P"):
        raise PatternGenomeInputError(f"unsupported image mode: {img.mode}")
    if img.mode == "RGBA":
        bg = Image.new("RGB", img.size, (255, 255, 255))
        bg.paste(img, mask=img.split()[3]); img = bg
    elif img.mode == "P":
        img = img.convert("RGBA")
        bg = Image.new("RGB", img.size, (255, 255, 255))
        bg.paste(img, mask=img.split()[3]); img = bg
    elif img.mode == "L":
        img = img.convert("RGB")
    rgb = np.array(img, dtype=np.uint8)
    if rgb.ndim != 3 or rgb.shape[2] != 3:
        raise PatternGenomeInputError(f"unexpected array shape: {rgb.shape}")
    h, w = rgb.shape[:2]
    if h == 0 or w == 0:
        raise PatternGenomeInputError("zero-size image")
    if h > MAX_DIM or w > MAX_DIM:
        raise PatternGenomeInputError(f"image too large: {w}x{h} > {MAX_DIM}x{MAX_DIM}")
    return rgb

def extract_genome(candidate, *, candidate_sha256: str, source_artifact_ref: str,
                   source_commit: str, runtime_lock_sha256: str,
                   config: PatternGenomeConfig,
                   extracted_utc: str = "2026-01-01T00:00:00Z") -> PatternGenome:
    if isinstance(candidate, bytes):
        rgb = _decode_image(candidate)
        actual_sha = hashlib.sha256(candidate).hexdigest()
    else:
        raw = np.asarray(candidate)
        if raw.ndim != 3 or raw.shape[2] != 3:
            raise PatternGenomeInputError(f"expected (H,W,3) array, got {raw.shape}")
        if raw.dtype != np.uint8:
            raise PatternGenomeInputError(f"array input must be uint8 RGB; got dtype {raw.dtype}")
        if not np.isfinite(raw).all():
            raise PatternGenomeInputError("array input contains non-finite values")
        rgb = raw
        h, w = rgb.shape[:2]
        if h == 0 or w == 0:
            raise PatternGenomeInputError("zero-size image")
        if h > MAX_DIM or w > MAX_DIM:
            raise PatternGenomeInputError(f"image too large: {w}x{h} > {MAX_DIM}x{MAX_DIM}")
        actual_sha = hashlib.sha256(rgb.tobytes()).hexdigest()
    if candidate_sha256 != actual_sha:
        raise PatternGenomeInputError(
            f"candidate_sha256 mismatch: expected {candidate_sha256}, got {actual_sha}")
    h, w = rgb.shape[:2]
    source = GenomeSource(artifact_ref=source_artifact_ref, width_px=w, height_px=h, channels=3)
    spectral = extract_spectral(rgb, config)
    color = extract_color(rgb, config)
    topology = extract_topology(rgb, config)
    geometry = extract_geometry(rgb, config)
    provenance = build_provenance(
        candidate_sha256=candidate_sha256, source_artifact_ref=source_artifact_ref,
        source_commit=source_commit, runtime_lock_sha256=runtime_lock_sha256,
        extractor_config_sha256=config.config_sha256, extracted_utc=extracted_utc)
    validate_provenance(provenance)
    genome = PatternGenome(
        schema_version=SCHEMA_VERSION, genome_id="", candidate_sha256=candidate_sha256,
        source=source, spectral=spectral, topology=topology, color=color, geometry=geometry,
        quality=GenomeQuality(all_finite=True, warnings=()), provenance=provenance)
    g_sha = genome_sha256(genome)
    object.__setattr__(genome, "genome_id", f"RAC-GENOME-{g_sha[:16]}")
    return genome
