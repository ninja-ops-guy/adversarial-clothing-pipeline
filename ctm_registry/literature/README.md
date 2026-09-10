# ctm_registry/literature — CTM Living-Corpus Registry (SPEC-4 / SPEC-15)

A versioned, content-addressed registry of near-miss and boundary papers.
Manuscript negative claims are bounded by snapshots of this registry
(SPEC-3 lint), and the manuscript positioning block pins a verified snapshot
(SPEC-18). Quarterly re-validation creates NEW snapshots; snapshots are
immutable.

Layout:

```
ctm_registry/literature/
  entries/<entry_id>.json        # rac-ctm-corpus-entry/1.0 records
  snapshots/<sha256>.json        # rac-ctm-corpus-snapshot/1.0, content-addressed
```

Rules:
- `entry_id = "RAC-CTM-LIT-" + sha256(canonical entry content)[:16]` and
  snapshot files live at their own canonical sha256 (canonical JSON:
  `json.dumps(obj, sort_keys=True, separators=(",",":"), ensure_ascii=False,
  allow_nan=False)`). Ids are derived, never asserted.
- Registration is idempotent and fail-closed: identical content re-registers
  byte-identically; different content under the same id raises
  `CorpusConflictError` (see `ruthless_pipeline/ctm/corpus.py`).
- Every entry records `verification_status`
  (`abstract_only | full_text_verified | reproduced_internally`, SPEC-6) and
  a `survey_taxonomy` node (SPEC-15: the category scheme is seeded from the
  survey taxonomies — Wang et al. Neurocomputing 2026 media-based FR
  categories; ACM CSUR 2026 physical-world task-based categories — not grown
  ad hoc). When a new survey edition appears, diff its taxonomy against this
  registry to reveal coverage gaps mechanically.
- Seed entries (SPEC-4): Voronoi (arXiv 2606.17711), MVPatch, AdvART, CAPGen
  as near-miss entries; Zhang et al. 2025 as the quadrant-1 boundary and
  defense-side seed (L18); GaP and AdvHat as FR cross-domain boundary
  entries (SPEC-13: they do NOT inherit person-detection claims without an
  explicit bridge); Sharif 2016 as a foundational anchor (L15,
  full_text_verified); the three surveys as taxonomy seeds.
- Nothing here is a physical efficacy claim. Corpus entries bound negative
  claims; they are not evidence of efficacy.
