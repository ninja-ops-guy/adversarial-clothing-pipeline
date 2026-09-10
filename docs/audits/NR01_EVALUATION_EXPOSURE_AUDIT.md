# NR-01 Audit — Evaluation Exposure and Feature Provenance

Basis: Generic Holdout (Nakkiran & Błasiok) + RAC sealing/sentinel boundaries.
Audit HEAD: 672a2dbf8d73ba77076eb34f28acc2b379c88e1d (origin/main at clone).
Scope: ruthless_pipeline/governance/seal.py, governance/sentinel.py,
governance/adaptive.py, scripts/select_surrogate_candidate.py,
scripts/adapt_surrogate_shortlist.py, scripts/export_dashboard_data.py,
scripts/build_provenance_graph.py, ruthless_pipeline/ctm/contracts.py,
feature/outcome-derived covariate paths.

## Verdict table

| # | Requirement | Verdict | Fix / proof |
|---|-------------|---------|-------------|
| a | Discovery/selection/confirmation roles separated | SATISFIED (existing) | proofs below |
| b | Recorded which cohort outputs were available before each selection decision | GAP → FIXED (additive) | governance/evaluation_exposure.py ledger |
| c | Preprocessing/historical summaries fit only on permitted data, source cohorts+versions bound to seal | SATISFIED for sentinel/calibration path; GAP for general feature/covariate provenance → FIXED (additive) | FeatureProvenance review |
| d | Multiple-testing/sequential policy declared before use | SATISFIED (existing) | proofs below |
| i | Exposure-influenced cohort cannot get independent-confirmation label | FIXED (new gate) | issue_independent_confirmation_label |
| ii | Outcome-label-derived feature fails provenance review | FIXED (new review) | review_feature_provenance |
| iii | Identity disjointness and calibration isolation necessary-but-distinct | SATISFIED (existing) + regression-pinned | new tests |

## (a) Discovery/selection/confirmation role separation — SATISFIED

* scripts/select_surrogate_candidate.py lines 337-341 — selection report
  hard-records `selection_boundary: "SURROGATE_ONLY"`,
  `heldout_models_loaded: []`, `heldout_feedback_used: False`; evaluators are
  built with `roles={"surrogate"}` (line 259). The pool itself must declare
  `heldout_feedback_allowed is False` (lines 239-240).
* scripts/adapt_surrogate_shortlist.py lines 98-103 — the adaptive stage
  refuses any selection input that is not `SURROGATE_ONLY` or that shows
  held-out contamination; the comment at lines 121-123 documents that no
  held-out inference occurs.
* ruthless_pipeline/ctm/contracts.py lines 92-100 and 111-129 — claim maturity
  ladder (correlation → association requires ≥2 independent cohorts;
  controlled_effect additionally requires matched nulls) and
  `validate_anti_optimization_invariant` rejecting pre-outcome artifacts with
  `heldout_access` / `heldout_feedback_used`.
* Proof tests: tests/test_adaptive_selection_contract.py,
  tests/governance/test_pass4_hardening.py (test_blind_pipeline_rejects_prior_outcome_access),
  tests/governance/test_pass7_adaptive_chaos.py (test_current_wave_outcomes_cannot_tune_policy).

Residual: the CTM `independent_cohort_count` is self-declared; nothing verified
that the declaring cohort's own outputs had not influenced selection. That is
fixture (i), now closed by the exposure ledger gate (below).

## (b) Recording the pre-decision information set — WAS GAP, FIXED

The selection report records policies and hashes
(scripts/select_surrogate_candidate.py lines 335-361: stage policies, model
state hashes, provenance, objective) but there was **no machine-checkable
record of which cohort outputs (surrogate evaluations, dashboard feedback,
outcome-derived covariates) were available to and consumed by each selection
decision**.

Fix (additive, fail-closed): ruthless_pipeline/governance/evaluation_exposure.py

* `ExposureEvent` (schema `rac-evaluation-exposure/1.0`): cohort id
  (canonical `RAC-COHORT-*`), output class, sha256 of the exposed output,
  consuming decision id, and a `decision_influenced` flag. A held-out
  evaluation marked decision-influencing fails at event validation.
* `EvaluationExposureLedger`: append-only (duplicate event ids rejected),
  deterministic `ledger_hash()`.

## (c) Preprocessing fit on permitted data, bound to the seal

Sentinel/calibration path — SATISFIED:

* ruthless_pipeline/governance/sentinel.py lines 149 and 158-159 —
  `CalibrationState.outcome_labels_consumed=True` fails validation
  ("calibration state may not consume experimental outcome labels");
  lines 147 and 156 pin `source_manifest_hash`.
* sentinel.py lines 241-254 — `validate_blind_sentinel_evaluation` requires
  the pipeline's calibration binding to match the frozen state and rejects any
  membership overlap with sentinel/bridge/treatment/held-out ids.
* ruthless_pipeline/governance/seal.py lines 138-139 and 323-324 — the
  governed seal binds `calibration_id` and `calibration_version` (plus
  `pipeline_id` / `pipeline_version`) into the deterministic `seal_hash`;
  lines 300-307 re-verify the diagnostic threshold bytes and the diagnostics
  gate before sealing.
* Proof tests: tests/governance/test_pass4_hardening.py
  (test_calibration_is_disjoint_and_frozen,
  test_sentinel_is_bound_to_sealed_source_and_resampling_is_forbidden).

General feature/covariate provenance — WAS GAP, FIXED: outside the sentinel
path, nothing reviewed whether a feature/covariate was computed from
prohibited outcome labels. Fix: `FeatureProvenance` (schema
`rac-feature-provenance/1.0`) plus `review_feature_provenance` in
evaluation_exposure.py. Every source is sha256-pinned and role-classified;
`consumed_outcome_labels=True`, an `outcome_label` role, or a transitively
derived (`derived_feature`) source all fail closed. Synthetic features are
labeled `synthetic: true` and are never promoted by this review.

## (d) Multiple-testing/sequential policy declared before use — SATISFIED

* ruthless_pipeline/governance/adaptive.py lines 76-79 — `AllocationPolicy`
  requires preregistered `stopping_rule` and `reallocation_rule`;
  lines 126-129 reject any current-wave outcome container at freeze time
  (tripwire); lines 189-202 (`require_policy_frozen_before_sampling`) enforce
  a FROZEN policy bound to a sealed evidence hash before sampling.
* ruthless_pipeline/certification/objectives.py `ObjectiveSpec.validate` — the
  selection objective (mean / CVaR-alpha) is a preregistered, validated
  object; scripts/select_surrogate_candidate.py lines 226-230 validate it
  before any evaluation.
* Proof tests: tests/governance/test_pass7_adaptive_chaos.py
  (test_policy_is_frozen_before_sampling,
  test_current_wave_outcomes_cannot_tune_policy,
  test_unsealed_prior_wave_cannot_drive_policy),
  tests/test_select_surrogate_candidate_objective.py,
  tests/test_objective_telemetry.py.

## Acceptance fixtures

* (i) tests/governance/test_evaluation_exposure.py
  (test_selection_influenced_cohort_cannot_be_labeled_independent_confirmation
  plus dashboard-feedback and outcome-derived-covariate variants): a synthetic
  fixture cohort whose evaluation result influenced candidate selection cannot
  obtain an INDEPENDENT_CONFIRMATION label; an unexposed cohort can, with the
  label hash-bound to the ledger
  (test_unexposed_cohort_receives_label_bound_to_ledger_hash). Held-out
  evaluation influencing selection fails at event validation
  (test_heldout_evaluation_influencing_selection_fails_at_event_validation).
* (ii) test_feature_from_outcome_labels_fails_provenance_review,
  test_feature_with_clean_role_but_outcome_consumption_flag_fails,
  test_transitively_derived_feature_fails_closed_in_v1; a clean
  labeled-synthetic feature passes and is hash-pinned
  (test_clean_feature_passes_review_and_is_hash_pinned).
* (iii) test_identity_disjointness_alone_is_not_sufficient_outcome_label_consumption_fails,
  test_calibration_isolation_alone_is_not_sufficient_identity_overlap_fails,
  test_both_axes_satisfied_passes — pinned against the existing sentinel
  machinery (`validate_blind_sentinel_evaluation`), demonstrating the two axes
  are independently necessary.

## Boundary compliance

No D2-0004/D2-0005 frozen surfaces touched; no arming; no held-out access; no
synthetic→measured promotion (new artifacts are schema-versioned, hash-pinned,
and carry an explicit `synthetic` flag where applicable). Frozen schemas
unchanged — new schemas (`rac-evaluation-exposure/1.0`,
`rac-confirmation-label/1.0`, `rac-feature-provenance/1.0`) are additive only.
