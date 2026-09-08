# RAC Experiment Pickup Guide

**Version:** 1.0.0  
**Purpose:** A short operational checklist for resuming the project after time away.

> **Current state (2026-09-08):** D2-0004 has **CLOSED — FAIL / RAC-D0, log-attested** (see `docs/D2-0004_CLOSURE_NOTE.md`); release `releases/RAC-EXP-2026-001/` is sealed and the Paper 1 longitudinal export includes D2-0004. The "If D2-0004 has closed" checklist below is therefore **complete** for D2-0004; the generation is immutable. D2-0005 remains preregistered but **NOT armed**; do not open/arm it without explicit user governance.

## If a D2 generation is running

- Do not touch candidate/generation artifacts.
- Check workflow only.
- Continue Production Alpha, calibration, P1 dry-run, papers, and preregistration work independently.

## When a D2 generation has closed (completed for D2-0004 on 2026-09-08)

- Verify candidate/protocol/model hashes.
- Verify no held-out feedback.
- Retain PASS/FAIL/INCONCLUSIVE unchanged.
- Run closed-generation ingester.
- Mint canonical RAC-EXP release.
- Run report compiler.
- Run failure taxonomy when applicable.
- Update Project Progress ledger.
- Add the release to Paper 1 dataset.
- Only then open D2-0005.

## If you have a frozen texture but no garment

- Open Product Studio and verify design manifest/hash.
- Resolve Printful IDs.
- Download/hash exact template.
- Map in Production Mapper.
- Freeze SKU manifest.
- Create matched control.
- Order pair/reserves.

## If garments are in transit

- Finish calibration target.
- Build/mark P1 rig.
- Freeze camera/light/condition IDs.
- Freeze stopping rule.
- Run synthetic P1 dry run.
- Verify report/release path.

## If garments just arrived

- Run receipt QA.
- Assign physical artifact IDs.
- Capture calibration.
- Accept/reject calibration profile.
- Run W0/P1 only after preregistration is frozen.
- Preserve garments for wash/model-aging program.

## If P1 has closed

- Run paired statistics.
- Seal physical release.
- Update evidence state only if gates are met.
- Update Paper 2/physical manuscripts.
- Start W1 durability state.
- Feed calibration forward only into a NEW digital generation.

## Never do these

- optimize against a fresh held-out model;
- change thresholds after viewing candidate outcomes;
- mutate a frozen candidate;
- treat frame count as independent physical sample size;
- count control-undetected conditions as candidate success;
- promote synthetic dry-run data to evidence;
- call a generic template vendor-ready;
- generalize a tested detector result to arbitrary surveillance;
- delete negative results.
