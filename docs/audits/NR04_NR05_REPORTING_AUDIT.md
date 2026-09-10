# NR-04 / NR-05 Reporting Audit (Pass A)

Date: 2026 (Pass A, Swarm NR-B). Basis: `docs/research/NORECOGNITION_REVIEW_2026-09-10.md`
(NR-04 stage outcomes and denominator integrity; NR-05 reports derived from one
evidence snapshot), RAC claim-scope contract (SPEC-13), RAC evidence-register
rules (`docs/RESEARCH_EVIDENCE_REGISTER.md`), and the report-compilation
architecture (`ruthless_pipeline/certification/report_compiler.py`,
`manuscript_export.py`).

Scope boundaries honored: no D2-0004/D2-0005 modification; no arming; no
held-out access; no synthetic→measured promotion; frozen schemas untouched;
D2-0004 log-attested gaps remain blank/disclosed. All new artifacts are
schema-versioned, hash-pinned, and exercised only with synthetic-labeled
fixtures.

## NR-04 — Stage outcomes and denominator integrity

| Requirement | Verdict | Evidence / Fix |
|---|---|---|
| (a) Distinguish direct stage measurements vs upstream-dependent outcomes vs not-evaluated stages | **GAP → FIXED** | `pipeline_stage.py` (SPEC-13) scoped *claims* to stages but no artifact recorded per-stage outcome provenance. Added `ruthless_pipeline/ctm/stage_outcomes.py` (`StageOutcome.outcome_kind ∈ {direct_measurement, upstream_dependent, not_evaluated}`) + `schemas/ctm_stage_outcomes_v1.schema.json`. Upstream-dependent outcomes must name `upstream_stages`; direct measurements must not. |
| (b) One upstream failure counted as two independent successes | **GAP → FIXED** | Audited `report_compiler.py`, `manuscript_export.py`, `scripts/export_dashboard_data.py`, claim-scope consumers: none could previously refuse this because no stage-dependency record existed. `StageOutcomeSet` now fails closed when any downstream outcome claims `success` over a failed upstream stage (single or multiple downstreams). Test: `test_upstream_failure_counted_as_two_successes_fails_closed`. |
| (c) A skipped stage receiving a fabricated numeric result | **GAP → FIXED** (reports) / **SATISFIED** (trial accounting) | Trial-level accounting already refused this: invalid trials never count as candidate success (`report_compiler.compile_report`; `tests/test_report_compiler.py::test_invalid_trials_never_candidate_success`, `test_all_invalid_condition_gets_no_rate`), and manuscript exporters emit header-only/`awaiting_data` blanks rather than placeholder numbers (`tests/test_manuscript_export.py` blank-safety guards, lines ~414–748). Stage-level fabrication was unguarded → `not_evaluated` outcomes now refuse any `measured_value`/`discrete_outcome`/`confidence_delta` (`test_skipped_stage_with_fabricated_number_fails_closed`). |
| Missing input to recognition is NOT a measured recognition score | **GAP → FIXED** | `StageOutcomeSet` refuses a measured value on an `upstream_dependent` stage whose input stages produced no result (`test_missing_input_is_not_a_measured_score_fails_closed`). |
| (d) Multi-model summaries identify shared specimen/cohort/conditions | **PARTIAL → FIXED** | `detector_science/transfer_matrix.py::surrogate_diversity_report` reported `n_shared_conditions` per pair but never labeled specimen/cohort sharing and tolerated unlabeled records. Added `multi_model_summary()` with explicit `specimen_shared` / `cohort_shared` / `conditions_shared` labels; records missing context are refused (fail closed). Tests: `test_shared_specimen_summary_is_labeled`, `test_unlabeled_multi_model_summary_fails_closed`. |
| (e) Confidence changes vs discrete task outcomes in separate fields | **GAP → FIXED** | No prior schema carried both as separate fields. `StageOutcome` keeps `confidence_delta` (finite-checked float) and `discrete_outcome` (`success/failure/inconclusive`) as disjoint fields; neither is derivable from the other. Test: `test_confidence_delta_and_discrete_outcome_are_separate_fields`. |

## NR-05 — Reports derived from one evidence snapshot

| Requirement | Verdict | Evidence / Fix |
|---|---|---|
| (a) Tables/narrative/counts from the same versioned evidence view | **GAP → FIXED** | `report_compiler` and `manuscript_export` each derive deterministically from one input bundle/registry, but nothing bound a report's tables, narrative, and counts to a single hash-pinned snapshot. Added `ruthless_pipeline/certification/report_consistency.py`: `EvidenceView` (schema-versioned `rac-evidence-view/1.0`, content-sha256 pinned) + `check_report_consistency` / `require_report_consistent` refusing mixed snapshots (`test_mixed_evidence_snapshots_fail_closed`, `test_report_pin_mismatch_fails_closed`). |
| (b) Display numerator, denominator, eligibility rules, cohort, specimen, measurement medium, metric definition, source version | **PARTIAL → FIXED** | `CompiledReport.markdown()` displayed valid/invalid counts, rates, preregistration hash, and evidence label, but had no field for eligibility rules, cohort, specimen, measurement medium, metric definition, or source version. These are now **required** fields of `EvidenceView` (empty → `ReportConsistencyError`); schema `schemas/rac_evidence_view_v1.schema.json` enforces presence. Tests: `test_view_display_fields_required`. |
| Inconsistent fraction/percentage pairs fail a report check | **GAP → FIXED** | `check_report_consistency` requires `percent == 100 * fraction` and `fraction == numerator/denominator` (tol 1e-9); denominator ≤ 0 with a fraction shown is refused. Tests: `test_inconsistent_fraction_percentage_pair_fails`, `test_fraction_must_match_numerator_denominator`. |
| Differing aggregation methods require explicit labels | **GAP → FIXED** | Summary rows with `aggregates_n > 1` must carry `aggregation_method ∈ {mean, median, min, max, sum}`. Test: `test_unlabeled_aggregation_fails_closed`. |
| Selected-best results retain selection history; median does not erase selection bias | **PARTIAL → FIXED** | `scripts/select_surrogate_candidate.py` already retains selection provenance (`surrogate-selection.json` with `selection_order`, `selection_boundary: SURROGATE_ONLY`). Reports had no check → rows with `selection: "best"` now require non-empty `selection_history`, including when `aggregation_method == "median"`. Test: `test_selected_best_requires_selection_history`. |
| External observations never enter internal totals | **SATISFIED** (pooling) / **FIXED** (report totals) | `ctm/external_cohort.py::build_analysis_pool` fails closed on pooling external-fabricated with digital-master cohorts without an explicit cohort term (`tests/ctm/test_external_cohort.py` lines ~96–129); external observations are class-pinned to `external_physical_observation` with an EXPLORATORY ceiling. Added the report-side guard: blocks containing `external_*` rows must declare `external_observations_excluded: true` and declared totals must equal the internal-row sum. Test: `test_external_observations_never_enter_internal_totals`. |
| (c) Evaluations vs independent participants vs experimental runs vs retained observations counted separately | **GAP → FIXED** | `EvidenceView.counts` requires exactly `n_evaluations`, `n_independent_participants`, `n_experimental_runs`, `n_retained_observations` (non-negative ints; merged/omitted refused). Test: `test_count_fields_are_separate_and_required`. |

## New artifacts

| Artifact | Purpose |
|---|---|
| `schemas/ctm_stage_outcomes_v1.schema.json` | Stage-outcome set schema (`rac-ctm-stage-outcomes/1.0`) |
| `ruthless_pipeline/ctm/stage_outcomes.py` | NR-04 stage-outcome records, set validation, multi-model shared-context summary |
| `schemas/rac_evidence_view_v1.schema.json` | Versioned evidence view schema (`rac-evidence-view/1.0`) |
| `ruthless_pipeline/certification/report_consistency.py` | NR-05 one-snapshot report-consistency checks |
| `tests/test_stage_outcomes_nr04.py` | NR-04 acceptance fixtures (synthetic-labeled) |
| `tests/test_report_consistency_nr05.py` | NR-05 acceptance fixtures (synthetic-labeled) |

All guards are additive and fail-closed; no frozen schema, frozen parameter, or
existing exporter behavior was modified.
