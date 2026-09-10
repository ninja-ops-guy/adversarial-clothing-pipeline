from __future__ import annotations
import math
from dataclasses import fields, is_dataclass
from .errors import PatternGenomeNonFiniteError, PatternGenomeSchemaError, PatternGenomeValidationError
from .provenance import validate_provenance
from .schema import PatternGenome, SCHEMA_VERSION

def _walk(x):
    if is_dataclass(x):
        for f in fields(x): yield from _walk(getattr(x,f.name))
    elif isinstance(x,dict):
        for v in x.values(): yield from _walk(v)
    elif isinstance(x,(list,tuple)):
        for v in x: yield from _walk(v)
    else: yield x

def validate_genome(g: PatternGenome) -> None:
    if g.schema_version != SCHEMA_VERSION: raise PatternGenomeSchemaError("schema_version mismatch")
    if not g.genome_id.startswith("RAC-GENOME-") or len(g.genome_id)!=(len("RAC-GENOME-")+16): raise PatternGenomeValidationError("invalid genome_id")
    if g.candidate_sha256 != g.provenance.candidate_sha256: raise PatternGenomeValidationError("candidate/provenance sha mismatch")
    vals=list(_walk(g))
    for v in vals:
        if isinstance(v,float) and not math.isfinite(v): raise PatternGenomeNonFiniteError("non-finite value")
    r=g.spectral.radial_energy
    if len(r)!=8: raise PatternGenomeValidationError("radial_energy must have 8 bins")
    if abs(sum(r)-1.0)>1e-6: raise PatternGenomeValidationError("radial_energy must sum to 1")
    if any(v<0 or v>1 for v in r): raise PatternGenomeValidationError("radial_energy out of range")
    for name in ("horizontal_symmetry","vertical_symmetry","diagonal_symmetry_main","diagonal_symmetry_anti","rotational_symmetry_180"):
        v=getattr(g.topology,name)
        if not (0<=v<=1): raise PatternGenomeValidationError(f"{name} out of range")
    if g.color.palette_size<1: raise PatternGenomeValidationError("palette_size must be >=1")
    if not (0<=g.color.lab_mean[0]<=100): raise PatternGenomeValidationError("L* mean out of range")
    if not g.quality.all_finite: raise PatternGenomeValidationError("quality.all_finite must be true")
    for v in (g.geometry.foreground_coverage_fraction,g.geometry.bbox_occupancy_fraction,g.geometry.center_of_mass_x,g.geometry.center_of_mass_y,g.geometry.spatial_entropy):
        if not (0<=v<=1): raise PatternGenomeValidationError("geometry normalized value out of range")
    validate_provenance(g.provenance)
