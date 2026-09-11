# RAC Experiment Pickup Guide

**Version:** 1.1.0  
**Updated:** 2026-09-11  
**Purpose:** short operational checklist for resuming the project after time away.

> **Canonical status:** use `docs/CURRENT_PROGRAM_STATE.md` first. This guide tells you what to do from the current state; frozen contracts and closure evidence outrank it.

## Current state at a glance

- D2-0003 — closed retained negative / RAC-D0; Alpha-001 remains bound here.
- D2-0004 — closed retained negative / RAC-D0.
- D2-0005 — preregistered, NOT armed.
- D2-0007 — closed `SCREENED_OUT_H0`; 64/64 Stage-1 compositions, zero survivors, no anchors/optimization/held-out/Alpha-002.
- Alpha-001 exact sealed source — recovered and hash-verified.
- P1 production software — ready for live Printful intake/build.
- P1 physical evidence — not yet executed.
- Authoritative P1 execution — frozen 144-trial schedule.

## If resuming today

1. Read `docs/CURRENT_PROGRAM_STATE.md`.
2. Verify current CI/readiness state.
3. Verify the recovered Alpha-001 kit hash.
4. Follow `docs/P1_PRODUCTION_RELEASE_GATE.md` for live vendor intake/build.
5. Follow `docs/USER_ACTION_NEXT_STEPS.md` for bind/readiness/procurement sequencing.
6. After physical specimens exist, follow `physical/p1/P1_OPERATOR_RUNBOOK.md` exactly.

## If starting live vendor work

- Keep the Printful token outside source control.
- Choose the actual garment size.
- Run `tools/p1_production_release.py intake` against live vendor data.
- Stop on product/variant/placement drift rather than guessing.
- Preserve untouched vendor bytes and hashes.
- Build only from the exact recovered Alpha-001 source.

## If production artwork has been built but nothing ordered

- Review product, variant, size, technique and panel geometry.
- Verify all generated artwork/archive hashes.
- Run `tools/p1_bind_ua_values.py --check-only`.
- Bind only after the dry check is clean.
- Re-run `tools/p1_no_spend_readiness_gate.py` and require PASS.
- Treat spend authorization as a separate human decision.

## If garments are in transit

- Generate/fabricate `RAC-CALT-P1-0001` at exact scale.
- Verify its 100 mm scale bar physically.
- Stage the camera/lighting rig and marked positions.
- Re-read the frozen 144-trial schedule and pairing/randomization contract.
- Prepare custody labels, storage, filenames and raw-media retention.
- Do not collect efficacy outcomes early.

## If garments just arrived

- Do not begin efficacy capture immediately.
- Run receipt QA and reconcile order/SKU/variant identity.
- Verify candidate/control pairing and manufacturing/material facts.
- Document seams, registration, defects and substitutions.
- Preserve chain of custody.
- Stop and resolve/reorder if the pair is not QA-admissible.
- Run calibration acceptance before the first P1 trial.

## If P1 is ready to run

Use only:

```text
physical/p1/P1_OPERATOR_RUNBOOK.md
physical/p1/P1_CAPTURE_SCHEDULE.json
physical/p1/PAIRING_RANDOMIZATION_CONTRACT.json
physical/p1/P1_READINESS_FREEZE.json
```

The schedule is **144 frozen trials**. Do not use the historical 108-row planning sheet.

During execution:

- preserve exact order/pairing/randomization;
- preserve original media and filenames;
- record invalid conditions honestly;
- do not change thresholds after seeing outcomes;
- do not improvise replacement trials outside the runbook.

## If P1 has closed

- Validate ingestion and file/hash completeness.
- Seal the physical evidence package before analysis.
- Run the preregistered paired/statistical analysis.
- Retain PASS, FAIL, negative or inconclusive exactly as produced.
- Promote evidence only if the frozen gate permits it.
- Start durability/replication work only from a valid physical baseline.

## If considering another digital generation

Do not reopen or mutate a closed lineage simply because the result was negative.

- D2-0007 is a completed screened-out null.
- D2-0005 remains separately frozen/unarmed.
- A new motif/optimization hypothesis should receive a new generation identity and preregistration.
- Held-out data observed by an earlier generation cannot silently become development feedback for that same generation.

## Never do these

- regenerate or retune Alpha-001 while calling it the same artifact;
- silently rebind Alpha-001 to a later generation;
- inject a new pool into frozen D2-0005;
- optimize against held-out feedback outside an approved new experiment;
- change thresholds after viewing outcomes;
- count control-undetected/invalid conditions as candidate success;
- promote synthetic/rehearsal data to physical evidence;
- treat a vendor mismatch as a value to guess;
- execute the old 108-row plan instead of the frozen 144-trial schedule;
- generalize a bounded detector/condition result to arbitrary surveillance;
- delete or rewrite negative results.
