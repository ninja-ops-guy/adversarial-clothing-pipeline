# RAC-PRINT-ALPHA-001 — Independent Print Alpha Audit (Swarm A / PA)

- **Audit date:** 2025 (repository state as audited)
- **Audited HEAD:** `a00fe1d` (origin/main at audit time; RAC-C Barrier 2 part 1/2)
- **Auditor role:** independent verification (Swarm A item 1). No scientific
  content was repaired or altered; this document reports findings only.
- **Scope:** `print-alpha/` tree, `production_alpha/` digital side,
  `schemas/print_alpha_manifest.schema.json`, `scripts_print_alpha/`,
  `tests/print_alpha/`, calibration references (`docs/CALIBRATION_TARGET_SPEC.md`,
  `physical/p1/CALIBRATION_MANIFEST.json`).

## Verdict

**VALID_WITH_NONBLOCKER_GAPS**

RAC-PRINT-ALPHA-001 exists at the audited HEAD and is structurally complete,
schema-conformant, deterministic, and fail-closed. No blocking defect was
found. The gaps listed below are all expected-by-design pending states
(physical/vendor inputs gated behind user actions UA-1..UA-4) plus minor
non-blocker observations; none can silently promote synthetic material to
measured physical evidence.

## Checklist results

| Area | Result | Evidence |
|---|---|---|
| Directory completeness | PASS | `print-alpha/{CANDIDATE,CONTROL,CALIBRATION,CAPTURE,MANIFESTS,QA}` all present; each carries a README/protocol/QA document. Artwork PNGs are intentionally absent (placement dirs contain READMEs only) because per-placement artwork cannot exist before UA-1 (template download). |
| Manifest/schema conformity | PASS | All 5 manifests validate: primary against FROZEN `schemas/print_alpha_manifest.schema.json` (rc=0 from `scripts_print_alpha/validate_manifests.py`); 4 supporting manifests against embedded structural schemas. `tests/print_alpha/test_print_alpha.py` asserts the same. |
| Artwork provenance | PASS | `expected_pattern_sha256 = b07b617f…c261546` is byte-identical across `artwork-manifest.json`, `print-alpha-manifest.json`, `production_alpha/SKU_MANIFEST.json` (`candidate_source.expected_pattern_sha256`) and `print-test-kit-status.json`. Kit sha `b22b022f…6f0548` likewise consistent. Candidate is frozen RAC-PER-D2-0003 with explicit "no regeneration or retuning" rule. |
| Candidate/control distinction | PASS | Artwork manifest carries 8 candidate + 8 control entries with disjoint paths (`CANDIDATE/` vs `CONTROL/`); pairing checklist includes an explicit candidate≠control anti-swap check; control rule = unmodified base texture / mid-gray fill marked `scenario_assumption`. |
| SHA-256 correctness | PASS (format) / N/A (physical) | All hash fields are either 64-hex or the literal `PENDING_USER_ACTION`; the fail-closed near-miss scan (`_check_pending_literals`) passes. Per-placement `artwork_sha256` values are correctly NOT fabricated — all `PENDING_USER_ACTION` until UA-1. |
| Trial-sheet determinism | PASS | Re-export via `scripts_print_alpha/export_trial_sheet.py` is byte-identical to the committed CSV (sha256 `774c2ad6…d14eaa`, 25116 bytes, both copies equal under `cmp`). |
| 108-row trial geometry | PASS | Exactly 108 data rows, 108 unique trial_ids, 36 conditions × 3 repeats; grid = distances {2,5,8 m} × yaw {−30,0,+30°} × pose {standing,walking} × lighting {indoor-even,daylight-even}; pitch locked 0°, wash W0. Matches `capture-protocol.md` §1. |
| Calibration references | PASS (references) | `CALIBRATION/README.md` correctly references `docs/CALIBRATION_TARGET_SPEC.md` and `physical/p1/CALIBRATION_MANIFEST.json` (both exist); receipt QA §C wires ΔE00 ≤ 6.0 to the calibration manifest's acceptance machinery. |
| Capture protocol | PASS | `CAPTURE/capture-protocol.md` defers to authoritative sources (`P1_CAPTURE_RIG_SPEC.md`, `CAMERA_LIGHTING_SETUP.md`, `STOPPING_RULE.json`, `physical_protocol.capture_rows`); camera-lighting sheet present. |
| Invalid-condition definitions | PASS | `invalid-condition-rules.json` derives from `physical/p1/STOPPING_RULE.json` (RAC-P1-STOP-2026-001), covers ≥4 condition classes, and pins the rule that control-undetected trials are invalid measurement conditions, never candidate successes (min_valid_trials=93, max=144, interval width 0.2, z=1.959963984540054). |
| Receipt QA | PASS | `QA/receipt-qa.md` condensed from authoritative `production_alpha/RECEIPT_QA_FORM.md`; defect classes D0–D3 with quarantine semantics; 3.0 mm registration tolerance matches `template-manifest.json`. |
| Chain-of-custody | PASS | `QA/chain-of-custody.md` defines labeling, photo log with sha256, storage/quarantine, append-only handoff log; custody breaks invalidate session data as invalid conditions (never silently dropped). |
| Pairing checklist | PASS | `QA/garment-pairing-checklist.md` enforces matched-pair rule (same product/variant/size/substrate/vendor/batch) and declares any unresolved `PENDING_USER_ACTION` blocks capture (fail-closed). |
| physical_efficacy_claimed=false | PASS | `const false` in the frozen schema and verified false in all 5 manifests by parametrized tests. |
| evidence_class | PASS | `experimental_print_specimen` const in frozen schema and in every manifest, capture ruleset, and all print-alpha QA/procedure docs. |
| Unresolved vendor fields | PASS | Every unresolved field is the literal `PENDING_USER_ACTION` (fail-closed scan passes); `user_action_refs` = UA-1..UA-4 present. No `PENDING_USER_ACTION` is ever converted to PASS by repo machinery (readiness checker regression-tested). |
| No synthetic→measured promotion | PASS | Manifests declare specimens as manufacturing specimens only; calibration feedback model is `SCAFFOLD_ONLY` until measured captures via UA-3; `byte_identical_to_frozen_source` is `false` (honest) rather than fabricated true. |

## Non-blocker gaps / observations (none blocking)

1. **Physical artifacts absent (expected).** No garment, no per-placement
   artwork PNGs, no downloaded template archive, no physical calibration
   print. All correctly represented as `PENDING_USER_ACTION`, gated on
   UA-1..UA-4. Manufacturing cannot proceed until these resolve — see
   `artifacts/print-alpha/readiness.json` (verdict `USER_ACTION_REQUIRED`).
2. **`print-test-kit.zip` is not committed to the repo.** Only its sha256
   (`print-test-kit-status.json`, `SKU_MANIFEST.json`) is recorded. The frozen
   pattern hash is therefore not byte-recomputable from repo content alone;
   the status file also records `d2_decision: FAIL` / `d2_evidence_state:
   RAC-D0`, i.e. the candidate is a design-stage (non-efficacy) specimen —
   consistent with `physical_efficacy_claimed=false`, but the kit archive
   should be preserved out-of-band for provenance re-verification.
3. **Placeholder-vocabulary mismatch across trees.** `production_alpha/`
   uses `PENDING_TEMPLATE_DOWNLOAD` while `print-alpha/` uses
   `PENDING_USER_ACTION`. Both are fail-closed and neither collides with the
   print-alpha literal scan, but a shared canonical token would reduce drift
   risk. Non-blocking.
4. **`manufacturing_batch: null`** in the primary manifest. Schema-permitted
   (`anyOf` string|null) and semantically "not yet manufactured"; flagged
   only so it is not later mistaken for a resolved value.

## Boundary compliance statement

This audit did not modify D2-0004 evidence or D2-0005 design parameters
(K≥72, ICC≤0.25, Δ≥0.2, bootstrap, independence definition, held-out model
sets, frozen candidate-selection rules); did not arm/execute D2-0005; did not
access held-out evidence or rerun D2-0004; did not convert any synthetic
artifact to measured physical evidence; and did not convert any
`PENDING_USER_ACTION` into PASS. No scientific content was repaired.
