# Manuscript Backlog — Fill-In Protocol

This directory contains backlog skeletons for five planned papers
(`paper1.md` … `paper5.md`). They contain **methods, claims structure, figure
caption drafts, and citation placeholders only**. No results exist here, and
none may be added except under the protocol below.

## The one absolute rule

**No datum enters a paper file without a closed RAC release reference.**

Concretely, every number, rate, interval, hash, date, or decision string in a
paper file must either:

1. be copied verbatim from a repository artifact that already exists and is
   cited by path (e.g. `protocols/RAC-PERSON-DETECT-1.2.json`,
   `physical/p1/STOPPING_RULE.json`, `docs/PREREGISTRATION_D2-0005.md`), with
   the commit SHA at which it was read recorded next to it; or
2. remain an explicit placeholder of the form
   `[AWAITING: <source artifact>]`, where `<source artifact>` names the
   sealed release or stage artifact that will eventually supply the value
   (e.g. `[AWAITING: D2-0005 paper5_comparison.json from closed releases]`).

A placeholder may be resolved **only** when:

- the named source artifact exists in a **closed, frozen research release**
  (`RAC-EXP-YYYY-NNN/` per `docs/RESEARCH_RELEASE_FORMAT.md`), and
- the value is copied from that release verbatim, with the release id and the
  artifact's SHA-256 (as recorded in the release's `MANIFEST.json`) cited
  inline where the placeholder stood.

Invented, estimated, interpolated, or "expected" values are forbidden at all
times — including in prose, tables, figure captions, and axis annotations.
This mirrors the repo-wide rule in `manuscript/FIGURE_SPECIFICATIONS.md`:
empty scaffolds (`status: "awaiting_data"`, `data: []`) are the only legal
pre-data state.

## Evidence labels travel with the numbers

Every carried value keeps the repo's six-label governance semantics
(`ruthless_pipeline/certification/experiment.py`). In particular:

- Closed D2/P1 results are `internally_measured` (never `published_observation`
  — that label denotes external published sources; see D2-0005 amendment A1).
- Design-analysis simulation outputs (e.g. `docs/DESIGN_ANALYSIS_D2-0005.md`)
  are `scenario_assumption` and must never be restated as experimental results.
- Mechanistic interpretations are `speculative_open`; cross-architecture
  transfer claims beyond the tested held-out set are `external_replication_needed`.

## Figure captions

Captions keyed to the F1–F8 scaffolds (`manuscript/figures/F*.json`) are
complete except for data values, which stay `[AWAITING: <release id>]` until
the sealed artifacts named in each scaffold's `sources` block exist. Figures
are populated only by renderers reading those sealed artifacts per the
scaffold `fill_rule` — never by hand-typed numbers. Papers 2–4 have no
allocated F1–F8 scaffolds; their paper-specific placeholders (Fig P2-*,
P3-*, P4-*) follow the same protocol.

## Citations

`[CITE: <topic>]` entries mark related-work claims that need external
literature support. They are replaced with real, verified references at
writing time; a `[CITE: ...]` marker must never be silently converted into a
citation that has not been checked.

## Paper mapping

| File | Subject | Primary source docs |
|---|---|---|
| `paper1.md` | Longitudinal D2 program (D2-0003 negative → D2-0004 closure → D2-0005 ablation → D2-0006 replication policy) | `docs/PREREGISTRATION_D2-0006_DRAFT.md`, `docs/AMENDMENT_D2-0004_INFRA-001.md`, `protocols/RAC-PERSON-DETECT-1.2.json` |
| `paper2.md` | Physical P1 garment study | `physical/p1/STOPPING_RULE.json`, `physical/p1/CALIBRATION_MANIFEST.json` |
| `paper3.md` | Capture Lab methodology | `docs/CAPTURE_LAB.md` |
| `paper4.md` | Research OS / certification infrastructure | `docs/CERTIFICATION_SYSTEM.md`, `docs/RESEARCH_RELEASE_FORMAT.md`, `ruthless_pipeline/certification/` docstrings |
| `paper5.md` | D2-0005 mean-vs-CVaR objective ablation | `docs/PREREGISTRATION_D2-0005.md`, `docs/DESIGN_ANALYSIS_D2-0005.md` |

## Editing hygiene

- Docs-only. Never edit `generations/`, `protocols/`, `model_manifests/`,
  `model_sets/`, `design_profiles/`, `benchmarks/`, or `.github/workflows/`
  from paper work.
- Do not weaken or remove a `[AWAITING: ...]` marker except by resolving it
  per the protocol above.
- A paper may report a published external study's result only as a cited
  external observation. RAC-specific claims require RAC evidence. A FAIL,
  null, negative, or inconclusive generation is a result, not a missing
  result.
