from __future__ import annotations
import hashlib, io
import numpy as np
from PIL import Image, ImageOps
from .canonical import genome_sha256
from .color import extract_color
from .config import PatternGenomeConfig
from .errors import PatternGenomeInputError
from .geometry import extract_geometry
from .provenance import build_provenance
from .schema import GenomeQuality, GenomeSource, PatternGenome, SCHEMA_VERSION
from .spectral import extract_spectral
from .topology import extract_topology
from .validation import validate_genome

def _decode_image(data: bytes, max_dim:int) -> np.ndarray:
    try:
        im=Image.open(io.BytesIO(data)); im.load(); im=ImageOps.exif_transpose(im)
    except Exception as e: raise PatternGenomeInputError(f"image decode failed: {e}") from e
    if im.width<=0 or im.height<=0: raise PatternGenomeInputError("zero-size image")
    if max(im.width,im.height)>max_dim: raise PatternGenomeInputError(f"image exceeds max dimension {max_dim}")
    if "A" in im.getbands():
        rgba=im.convert("RGBA"); bg=Image.new("RGBA",rgba.size,(255,255,255,255)); im=Image.alpha_composite(bg,rgba).convert("RGB")
    else: im=im.convert("RGB")
    arr=np.asarray(im,dtype=np.uint8)
    if arr.ndim!=3 or arr.shape[2]!=3: raise PatternGenomeInputError("decoded image is not RGB")
    return arr

def extract_genome(image_bytes: bytes, *, candidate_sha256:str, source_artifact_ref:str, source_commit:str, runtime_lock_sha256:str, config:PatternGenomeConfig, extracted_utc:str|None=None) -> PatternGenome:
    config.validate(); actual=hashlib.sha256(image_bytes).hexdigest()
    if actual!=candidate_sha256: raise PatternGenomeInputError("candidate_sha256 does not match input bytes")
    rgb=_decode_image(image_bytes,config.max_image_dimension)
    spectral=extract_spectral(rgb,config.radial_bins,config.fft_window)
    color=extract_color(rgb,config.palette_max_colors,config.palette_seed,config.palette_iterations)
    topology=extract_topology(rgb,config.palette_max_colors,config.palette_seed,config.palette_iterations,config.connectivity)
    geometry=extract_geometry(rgb,config.palette_max_colors,config.palette_seed,config.palette_iterations,config.spatial_hist_bins)
    prov=build_provenance(candidate_sha256=actual,source_artifact_ref=source_artifact_ref,source_commit=source_commit,runtime_lock_sha256=runtime_lock_sha256,extractor_config_sha256=config.sha256,extracted_utc=extracted_utc)
    src=GenomeSource(source_artifact_ref,rgb.shape[1],rgb.shape[0],3)
    draft=PatternGenome(SCHEMA_VERSION,"",actual,src,spectral,topology,color,geometry,GenomeQuality(True,()),prov)
    gid="RAC-GENOME-"+genome_sha256(draft)[:16]
    g=PatternGenome(SCHEMA_VERSION,gid,actual,src,spectral,topology,color,geometry,GenomeQuality(True,()),prov)
    validate_genome(g); return g
