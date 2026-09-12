# Acknowledgments

RAC stands on research and pattern work published by others. This file is the
canonical attribution record. It is kept at repository root, next to the
README, because lineage is part of the evidence surface — not a footnote.

---

## Bill Swearingen — hevnsnt / noRecognition

**Primary attribution.** The pattern families implemented in
`ruthless_pipeline/patterns/` — including `op_art_chevrons`,
`interference_lines`, `checkerboard`, `fractal_noise`, `perlin_noise`,
`hf_noise`, `simple_shapes`, and `gradient` — follow the design vocabulary
of the noRecognition pattern library published by Bill Swearingen
([github.com/hevnsnt/norecognition](https://github.com/hevnsnt/norecognition),
[sandbox.norecognition.org](https://sandbox.norecognition.org)).

RAC's generators are independent implementations, informed by his public
pattern catalog and research narrative. No code, images, datasets, or
generated outputs from noRecognition are distributed in this repository.

**License boundary.** The noRecognition project is distributed under
NRSAL v7.0, which expressly restricts commercial use and contains terms
concerning rights in generated outputs. RAC respects that boundary:
- No noRecognition code has been copied into RAC.
- No noRecognition pattern images have been imported into RAC.
- No noRecognition dataset material has been accessed or reused.
- The pattern families above are original implementations guided by the
  *published design vocabulary*, treated as research leads, not licensed
  assets.

Commercial licensing inquiries for noRecognition material belong with the
author: **bill@seckc.org** (per the NRSAL license text).

**Research lineage.** Two documents carry the detailed review:
- `docs/research/NORECOGNITION_REVIEW_2026-09-10.md` — capability
  comparison, methodological lessons, and integration decisions.
- `docs/research/NORECOGNITION_ARCHITECTURE_AND_DATA_ACCESS.md` — verified
  public-tree inventory, dataset availability findings, and publisher
  information requirements.

Both reviews are snapshot-anchored and treat external outcomes as
author-reported observations requiring independent replication, consistent
with RAC's evidence labels.

---

## Academic literature

The adversarial-clothing research program engages a broad published corpus.
Key load-bearing sources, each verified to the depth recorded in
`ctm_registry/literature/`:

| Thread | Anchor works | Role in RAC |
| --- | --- | --- |
| Physical adversarial patches | Sharif et al. 2016; Brown et al. 2017; Athalye et al. 2018; Demontis et al. 2019 | NPS colorimetry, physical-realizability grounding, EOT lineage |
| Garment-scale attacks | Xu et al. 2019 (Adversarial T-shirt); Zhang et al. 2025 | Deformation handling; nine-defense garment-scale result |
| Factorial decomposition | CAPGen (2025); adversarial Voronoi camouflage (arXiv 2606.17711); MVPatch; AdvART | Pattern/color decomposition leads; near-miss corpus entries |
| FR-adjacent attacks | AdvHat; GaP; DiffAM | Cascade-stage scope labels; symmetry-enforcement deltas |
| Evaluation methodology | Carlini et al. 2019; Nakkiran & Błasiok 2018 | Capability specification; holdout-reuse discipline |
| Defense-side brittleness | Glaze break (Hönig et al.); Zhang et al. 2025 | Defense-dual tracking; brittleness-as-measurement |
| Measurement infrastructure | NIST FRVT; RobustBench | Analogues for CTM's positioning as measurement infrastructure |

The living corpus registry at `ctm_registry/literature/` carries per-entry
verification status (`abstract_only` / `full_text_verified` /
`reproduced_internally`), quadrant classification, failure axes, and
re-check dates. Load-bearing claims cite `full_text_verified` entries only
(SPEC-6, fail-closed).

---

## External datasets

No external dataset has been imported into RAC. The AdvT-shirt-1K public
dataset is registered as a *planned* external-validation adapter
(SPEC-16) and has not been ingested. The noRecognition corpus is not
established as publicly downloadable; access status is
`UNKNOWN_PENDING_PUBLISHER_RESPONSE` and permitted use is
`NOT_ESTABLISHED` (see the architecture and data-access note).

---

*This file is part of the evidence surface. Changes to attribution claims
are reviewed with the same discipline as scientific-surface changes.*
