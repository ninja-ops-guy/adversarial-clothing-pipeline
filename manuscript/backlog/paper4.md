# Paper 4 Backlog — Research OS / Certification Infrastructure

> Fill-in protocol: see `README.md` in this directory. NO invented results.
> Every numeric placeholder is marked `[AWAITING: <source artifact>]`.

## 1. Working title and contribution claim

**Working title:** *A Fail-Closed Research Operating System for Adversarial-Pattern Science: Content-Addressed Evidence Lineage, Preregistered Statistics, and Append-Only Releases*

**Contribution claim (one paragraph):** We describe the RAC Research OS — the
`ruthless_pipeline/certification/` infrastructure that turns adversarial-pattern
experiments into reproducible, cryptographically verifiable evidence objects. The system
binds each research claim to a single machine-readable lineage contract
(candidate → generation → optimization_telemetry → calibration_profile → sku →
physical_session → certificate) in which every stage reference is a SHA-256-addressed
immutable artifact and the lineage hash is computed, never stored, so any retroactive edit
is detectable. On top of this substrate sit a frozen telemetry contract with pre-held-out
hash commitments and append-only outcomes, preregistered deterministic statistics modules
(Wilson intervals, hash-seeded bootstraps that never touch `random` state, stopping rules
evaluated only against frozen configs), a transparent rule-based failure taxonomy that
accumulates a longitudinal "failure atlas", and a content-addressed research-release
format with two permitted append-only post-freeze operations. Certificates are issued
fail-closed across a seven-state evidence ladder (RAC-D0…RAC-M2) in which digital evidence
can never satisfy a physical state — an internal verification framework, explicitly not an
accredited certification.

## 2. Methods skeleton

### 2.1 Design goals and threat model
- Fail-closed issuance requirements (preregistered protocol, distinct surrogate/held-out sets, pattern/master hash, source commit, baseline-qualified held-out results, invalid-condition fraction, sealed bundle) ← `docs/CERTIFICATION_SYSTEM.md` Fail-closed issuance.
- Explicit non-claims (internal verification, not accredited certification, no guarantee against arbitrary surveillance) ← `docs/CERTIFICATION_SYSTEM.md` preamble.
- Normative precedence of the engineering constitution ← `docs/CERTIFICATION_SYSTEM.md`; `docs/ENGINEERING_CONSTITUTION.md`.

### 2.2 Evidence states and type boundaries
- Seven-state ladder RAC-D0/D1/D2/P1/P2/M1/M2 and the digital/physical/manufacturing boundary rules ← `docs/CERTIFICATION_SYSTEM.md` Evidence states; enforced in `ruthless_pipeline/certification/evidence.py`.
- Required evidence record fields and observation validity (valid/invalid/excluded; control-undetected invalid) ← `docs/CERTIFICATION_SYSTEM.md`.

### 2.3 Lineage contract and registry
- ExperimentArtifact stage binding, StageRef (artifact id + SHA-256), computed-never-stored lineage_hash, pipeline-order constraint ← `ruthless_pipeline/certification/experiment.py` docstring.
- ExperimentRegistry append-only semantics (rejects duplicate experiment_id and duplicate lineage_hash; reverse lookup by stage artifact) ← `ruthless_pipeline/certification/experiment.py` docstring.
- Six-label evidence governance ← `ruthless_pipeline/certification/experiment.py` docstring; `docs/PREREGISTRATION_D2-0005.md` §9 A1.

### 2.4 Telemetry contract
- Two-phase record: PreHeldOutTelemetry frozen via `frozen_sha256()` before held-out inference; HeldOutOutcome append-only, immutability guarantees, tamper detectability ← `ruthless_pipeline/certification/telemetry_contract.py` docstring.
- Cross-model disagreement recomputation inside `validate()` ← `manuscript/FIGURE_SPECIFICATIONS.md` F3.

### 2.5 Preregistered statistics modules
- `statistics.py` / `trial_statistics.py`: paired physical comparisons, Wilson intervals, deterministic bootstrap, Haldane odds ratio, minimum-sample planning, PreregisteredStoppingRule evaluation ← `ruthless_pipeline/certification/trial_statistics.py` docstring.
- `paired_arm_statistics.py`: digital two-arm ablation statistics; deliberate separation from trial_statistics; SHA-256-derived draws, no `random` state ← `ruthless_pipeline/certification/paired_arm_statistics.py` docstring.
- `calibration_ingest.py`: CIEDE2000 (CIE 142-2001 / Sharma formulation), PrintCameraProfile acceptance ← `ruthless_pipeline/certification/calibration_ingest.py`.

### 2.6 Failure taxonomy
- Rule-based deterministic classifier; metric keys; categories incl. CROSS_ARCHITECTURE_TRANSFER_FAILURE / SURROGATE_OVERFIT; longitudinal failure atlas ← `ruthless_pipeline/certification/failure_taxonomy.py` docstring.

### 2.7 Release format
- Bundle layout (experiment.json, MANIFEST.json, RELEASE.json, REVISIONS.json, REPORT.md, optional FAILURE.json, stages/) ← `docs/RESEARCH_RELEASE_FORMAT.md` §2.
- Content addressing (per-artifact SHA-256; release content_hash over MANIFEST.json) and the two append-only post-freeze operations ← `docs/RESEARCH_RELEASE_FORMAT.md` §§4–5; `ruthless_pipeline/certification/release_format.py` docstring.
- What the format does NOT claim (validity, completeness, payload inclusion by URI) ← `docs/RESEARCH_RELEASE_FORMAT.md` §1.

### 2.8 Runtime and contract locking
- benchmarks/runtime_lock.json as single source of truth; `verify_runtime_lock.py` hard gate; the 19-minute version-drift incident as motivation ← `docs/AMENDMENT_D2-0004_INFRA-001.md` §§1, 6.
- Manuscript automation exports (header-only CSVs / `awaiting_data` scaffolds until closed experiments exist) ← `ruthless_pipeline/certification/manuscript_export.py` docstring.

### 2.9 Limitations
- Verification proves integrity, not validity; a verifying release may describe a failed experiment (FAILURE.json) ← `docs/RESEARCH_RELEASE_FORMAT.md` §1.

## 3. Figure caption drafts

No F1–F8 scaffold is allocated to Paper 4 (scaffolds serve Papers 1 and 5). Paper-specific
figure placeholders:

- **Fig P4-1 — Evidence-state ladder and type boundaries.** Diagram of RAC-D0…RAC-M2 with
  the digital/physical/manufacturing boundary arrows and fail-closed gates. From
  `docs/CERTIFICATION_SYSTEM.md` — no numeric data required.
- **Fig P4-2 — Lineage contract of one experiment.** Stage chain with StageRef hashes and
  the computed lineage_hash; tamper-detection annotation. Example hashes:
  [AWAITING: first closed release id (D2-0004)].
- **Fig P4-3 — Release bundle anatomy.** Directory tree of one frozen release with the
  MANIFEST.json/content_hash addressing overlay. Layout from
  `docs/RESEARCH_RELEASE_FORMAT.md` §2; concrete digests [AWAITING: first frozen
  RAC-EXP-YYYY-NNN release].

## 4. Citation placeholder list

- [CITE: reproducible research infrastructure — computational provenance and content-addressable storage]
- [CITE: hash-chained / append-only audit logs and tamper-evident systems]
- [CITE: preregistration platforms and registered reports infrastructure]
- [CITE: fail-closed / fail-safe design principles in safety- and security-critical systems]
- [CITE: statistical practice — Wilson score intervals, deterministic/reproducible bootstrap procedures]
- [CITE: failure taxonomies and negative-result atlases in ML robustness research]
- [CITE: FAIR / reproducibility artifact standards for ML (model cards, datasheets, artifact evaluation)]
- [CITE: ML pipeline lineage tracking and experiment management systems]
