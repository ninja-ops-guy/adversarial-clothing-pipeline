# ctm_registry — CTM Pattern Registry (skeleton)

Layout:

```
ctm_registry/
  patterns/<pattern_id>/
    master.sha256.json   # sha256 sidecar for the master candidate (NO binary masters committed)
    genome.json          # canonical pattern-genome bytes (rac-pattern-genome/1.0) + newline
    provenance.json      # genome provenance record (derived_digital_measurement)
  physical_artifacts/    # physical artifact records (PENDING UA-1/UA-3; placeholders only)
  target_panels/         # target panel records
  channels/              # channel definitions
  experiments/           # experiment manifests (owned by other lanes)
  heuristics/            # heuristic records (never evidence; always EXPLORATORY)
  snapshots/             # registry snapshots
```

Rules:
- `pattern_id = "RAC-CTM-PAT-" + sha256(canonical genome bytes without
  self-referential fields + b"rac-pattern-genome/1.0")[:16].lower()`
  (canonical definition lives in `ruthless_pipeline/ctm/ids.py`).
- Large `master.*` binaries must NOT be committed — use `master.sha256.json`
  sidecars instead.
- Registration is idempotent and fail-closed: identical content re-registers
  byte-identically; different content under the same pattern_id raises
  RegistryConflictError.
- Everything here is measurement only: `physical_efficacy_claimed: false`,
  evidence class `derived_digital_measurement`, claim state EXPLORATORY.
