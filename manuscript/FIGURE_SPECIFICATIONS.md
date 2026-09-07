# Manuscript Figure Specifications (Papers 1 and 5)

**Status:** scaffolds only — every figure input in `manuscript/figures/` is an
explicit empty scaffold (`status: "awaiting_data"`, `data: []`). No figure
contains numbers yet, and none may until a renderer populates it from the
sealed artifacts named in its `sources` block, exactly per its `fill_rule`.
Invented results are forbidden; empty scaffolds are the only legal pre-data
state.

**Producer module:** `ruthless_pipeline/certification/manuscript_export.py`
(`figure_scaffolds()`, `write_figure_scaffolds()`). The scaffolds on disk are
canonical JSON (sorted keys, compact separators, trailing newline) and are
byte-identical to what the module emits.

**Table exports** (same governance): `paper1_longitudinal.csv`,
`paper5_arms.csv`, `paper5_comparison.json` — see the module docstring. All
three are header/scaffold-only until closed experiments exist.

---

## F1 — Surrogate-vs-held-out transfer scatter (`F1_transfer_scatter.json`, Paper 1)

- **Purpose / claim:** Supports Paper 1 RQ1 (does surrogate performance
  predict held-out transfer?). One point per closed generation: frozen
  surrogate mean detection rate vs. the held-out mean detection rate sealed
  after closure.
- **Data lineage:** sealed `TelemetryRecord` per closed experiment
  (release `stages/optimization_telemetry/`, StageRef.sha256 ==
  `frozen_sha256()`): `pre.surrogate_mean_detection_rate`,
  `outcome.heldout_detection_rates`, `outcome.verdict`,
  `pre.candidate_sha256`.
- **Empty state:** `data: []`, `status: awaiting_data`. Records without an
  attached outcome are skipped — never plotted as estimates.

## F2 — Generation timeline (`F2_generation_timeline.json`, Paper 1)

- **Purpose / claim:** Longitudinal view of closed generations (Paper 1's
  generation-based design): closure date vs. held-out mean rate, series per
  generation.
- **Data lineage:** `experiment.json` (`ExperimentArtifact`: `experiment_id`,
  `generation_id`, `created_utc`, `evidence_label`) plus the sealed
  `TelemetryRecord` outcome fields `outcome.recorded_utc` and
  `outcome.heldout_detection_rates`.
- **Empty state:** `data: []`; no markers before the first generation closes.

## F3 — Architecture disagreement (`F3_architecture_disagreement.json`, Paper 1)

- **Purpose / claim:** Supports Paper 1 RQ2 (cross-model disagreement as a
  transfer predictor). Per candidate: variance, spread, and max pairwise
  delta of per-surrogate detection rates.
- **Data lineage:** frozen pre-held-out telemetry
  `pre.cross_model_disagreement.{variance, spread, max_pairwise_delta}` keyed
  by `pre.candidate_sha256`. These fields are recomputed inside
  `PreHeldOutTelemetry.validate()` from `per_surrogate_detection_rates`, so
  sealed values cannot drift.
- **Empty state:** `data: []`. Pre-held-out records suffice (outcome not
  required), but none exist yet, so the scaffold stays empty.

## F4 — Transformation robustness (`F4_transformation_robustness.json`, Paper 1)

- **Purpose / claim:** Supports Paper 1 RQ3 (transformation variance adds
  predictive value). Heatmap of per-transform candidate detection rates per
  experiment.
- **Data lineage:** the sealed `transformation_rates` mapping
  ({transform_id: rate}) that feeds
  `failure_taxonomy.classify_failure`; row annotation from telemetry
  `pre.transformation_sweep_variance`.
- **Empty state:** `data: []`; experiments lacking a sealed
  `transformation_rates` mapping are omitted — cells are never imputed.

## F5 — Objective trajectories (`F5_objective_trajectories.json`, Paper 5)

- **Purpose / claim:** Paper 5 secondary endpoint "optimization stability":
  mean / CVaR / worst-model loss per optimization checkpoint, per arm.
- **Data lineage:** objective-telemetry JSON from
  `scripts/select_surrogate_candidate.py --objective-telemetry`
  (`build_objective_telemetry`): `objective.name`, `objective.alpha`,
  `checkpoints[].checkpoint`, `checkpoints[].candidate_id`,
  `checkpoints[].losses.{mean, cvar, worst_model}`.
- **Empty state:** `data: []`; D2-0005 has not run, so no checkpoint series
  exists.

## F6 — CVaR tail-membership turnover (`F6_cvar_tail_turnover.json`, Paper 5)

- **Purpose / claim:** Shows how the worst-k tail (the CVaR objective's
  active set) churns during optimization — evidence for the arm-C mechanism
  in Paper 5.
- **Data lineage:** objective-telemetry JSON
  `checkpoints[].cvar_tail.{alpha, k, member_ids}` and
  `checkpoints[].tail_turnover.{entered, left}`. The sealed entered/left
  lists are authoritative; turnover is never recomputed by the renderer.
- **Empty state:** `data: []`.

## F7 — Mean-vs-CVaR candidate rank changes (`F7_mean_vs_cvar_rank_changes.json`, Paper 5)

- **Purpose / claim:** Directly evidences Paper 5's premise that the choice
  of objective changes which candidate wins: dumbbell plot of `mean_rank` vs
  `cvar_rank` with `rank_delta` per candidate at the final checkpoint.
- **Data lineage:** objective-telemetry JSON
  `checkpoints[].candidate_ranks.<candidate_id>.{mean_rank, cvar_rank, rank_delta}`
  (final checkpoint), `checkpoints[].candidate_id`.
- **Empty state:** `data: []`.

## F8 — Paired-arm outcome (`F8_paired_arm_outcome.json`, Paper 5)

- **Purpose / claim:** Paper 5's primary endpoint figure: Arm M and Arm C
  held-out rates with Wilson intervals, plus Δ = R_M − R_C with its
  deterministic-bootstrap interval against the preregistered decision
  regions (success / negative / null / inconclusive-at-width-> 0.20).
- **Data lineage:** canonical JSON from
  `paired_arm_statistics.to_canonical_json` (carried verbatim under
  `statistics` in `paper5_comparison.json`): `observation_units`,
  `arm_m.{rate, interval}`, `arm_c.{rate, interval}`, `risk_difference`,
  `risk_difference_interval`, `interval_width`, `decision`,
  `inconclusive_width`.
- **Empty state:** `data: []`; the comparison does not exist until both
  D2-0005 arms close. The `decision` string is rendered verbatim from the
  sealed statistics, never restated by the renderer.
