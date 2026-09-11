# RAC User Action — Next Steps to Physical P1

**Document ID:** RAC-USER-ACTION-NEXT-001  
**Audience:** Mike / human operator  
**Status:** CURRENT OPERATOR CHECKLIST  
**Purpose:** State exactly what the human operator must do next, in dependency order, without rewriting or mutating frozen/hash-pinned historical artifacts.

> **Authority note:** `docs/USER_ACTION_REQUIRED_PRINT_ALPHA.md` is retained as a hash-pinned historical packet and contains an older 108-row P1 instruction. **Do not execute that 108-row plan.** For P1 execution, the frozen `physical/p1/P1_CAPTURE_SCHEDULE.json` and `physical/p1/P1_OPERATOR_RUNBOOK.md` are authoritative and require **144 trials**.

> **Scientific boundary:** Completing this checklist does not establish physical efficacy. `physical_efficacy_claimed` remains false until measured physical evidence is collected, sealed, and evaluated under the preregistered rules. D2-0004 stays CLOSED/NEGATIVE and immutable. D2-0005 stays PREREGISTERED/NOT ARMED unless a separate governance action explicitly changes it.

## Where you are now

Engineering Barriers 0–3 are closed for their declared scope. RAC-G has completed the independent Barrier-3 audit with `PASS_WITH_NONBLOCKING_GAPS`. P1 no-spend readiness is PASS and the UA binder is implemented. The remaining critical path is external/vendor input → physical specimens → receipt QA/calibration → frozen P1 execution.

## Phase 1 — Collect real vendor values (no spend required)

### 1. Authenticate to Printful locally

- Log in to Printful and create/verify a private API token.
- Keep the token **only on your local machine**. Never commit it or paste it into `UA_VALUES_TEMPLATE.json`.
- Verify the token works before continuing.

**Done when:** live Printful API calls succeed and no credential has entered the repository.

### 2. Download and preserve the live production templates

The current binder requires real template evidence for both:

- Hoodie: Printful catalog product 388.
- Tee reserve/fallback: Printful catalog product 257.

Keep the downloaded template/archive bytes unchanged. Record the source and acquisition date outside the credential itself, and compute SHA-256 for the exact files you will treat as authoritative.

**Done when:** you have byte-exact hoodie and tee template files plus their SHA-256 values.

### 3. Record panel geometry from the live templates

Populate real `width_mm`, `height_mm`, and `dpi` values for:

**Hoodie:** `back`, `front`, `hood`, `label_inside`, `label_panel`, `pocket`, `sleeve_left`, `sleeve_right`.

**Tee:** `back`, `front`, `sleeve_left`, `sleeve_right`.

Do not infer or guess missing geometry. Stop if a required placement cannot be resolved from the vendor source.

**Done when:** every geometry field required by `physical/p1/UA_VALUES_TEMPLATE.json` has a real positive value.

### 4. Resolve the garment variants you actually intend to use

Choose one size that is supported by the required garments. Record:

- `garments.size`
- `garments.hoodie_variant_id`
- `garments.tee_variant_id`
- `garments.printer_vendor`
- `garments.print_technology`

The binder verifies the expected v1 variant maps unless an explicit drift override is used. If Printful's live variant mapping differs, treat that as a review event rather than silently forcing it through.

**Done when:** the selected size and live variant IDs are known and internally consistent.

## Phase 2 — Prepare the exact artwork and mapping evidence

### 5. Export the candidate/control production artwork

Create the exact production files for the candidate and matched control using the live template geometry. Preserve the experimental pairing rule: candidate and control should differ in artwork, not garment identity, size, substrate, fulfillment conditions, or other avoidable variables.

Compute SHA-256 for every required candidate/control placement and for each article-level assembled artwork package.

The intake currently requires article hashes for:

- `PA-HOODIE-CAND-001`
- `PA-HOODIE-CTRL-001`
- `PA-HOODIE-CAND-R01`
- `PA-HOODIE-CTRL-R01`
- `PA-TEE-CAND-R01`
- `PA-TEE-CTRL-R01`

**Done when:** all required per-placement hashes, article hashes, and mapping filenames are known and reproducible.

### 6. Fill a copy of the UA intake template

Copy, do not edit in-place as scratch work:

```bash
cp physical/p1/UA_VALUES_TEMPLATE.json my_ua_values.json
```

Replace **every** `PENDING_USER_ACTION` leaf in your copy with a real value. Required groups are:

- identity metadata: `values_id`, `recorded_by`, `recorded_utc`
- hoodie/tee template SHA-256 values
- hoodie/tee panel geometry
- candidate/control placement SHA-256 values
- six article artwork SHA-256 values
- candidate/control mapping filenames
- garment size, hoodie variant, tee variant, vendor, print technology

Never put the Printful API token in this file.

**Stop condition:** if any field is unknown, keep working upstream. Do not invent, approximate, use `TBD`, or bypass the binder.

## Phase 3 — Validate and bind the production evidence

### 7. Run the binder in check-only mode first

```bash
python3 tools/p1_bind_ua_values.py --values my_ua_values.json --check-only
```

The check must succeed without missing fields, pending markers, placeholder-shaped values, malformed hashes, variant mismatches, or candidate/control-artwork equality problems.

**If it refuses:** fix the source value. Do not modify the frozen schedule, pairing contract, stopping rule, scientific thresholds, D2 state, or readiness logic to make the check pass.

### 8. Perform the atomic bind

Only after check-only succeeds:

```bash
python3 tools/p1_bind_ua_values.py --values my_ua_values.json
```

The binder is expected to update only its allowlisted manifests/readiness evidence and emit:

`artifacts/p1-readiness/ua-binding-receipt.json`

Successful binding **does not authorize spend** and **does not arm D2-0005**.

### 9. Re-run the no-spend readiness gate

Run the repository's P1 no-spend readiness gate and require **PASS** before procurement. Preserve the generated receipt/report and confirm the frozen 144-trial schedule and protected scientific surfaces have not changed.

**Do not order anything if the readiness gate fails.**

## Phase 4 — Human spend authorization and procurement

### 10. Make a separate human go/no-go decision on spend

Before placing an order, verify:

- UA binding completed successfully.
- P1 no-spend readiness is PASS.
- Candidate/control product, size, and variant match.
- Candidate/control artwork hashes are intentionally different.
- Template/artwork hashes match the files you will actually upload.
- Shipping/fulfillment conditions are as matched as practical.
- You are satisfied with cost and reserve/fallback quantities.

This decision is intentionally outside the binder.

### 11. Place the matched Printful order

Order at minimum:

- 1× candidate hoodie
- 1× matched control hoodie

Use the same product/variant/size and comparable fulfillment conditions. Reserve/fallback garments may be ordered if you choose, but do not substitute them silently for the primary pair later.

Record order IDs, order date, fulfillment region/conditions, and the exact uploaded-artwork hashes in the existing Production Alpha records.

**Done when:** a matched physical pair has been ordered and its identity is traceable to the bound manifests.

## Phase 5 — Prepare calibration while garments are in transit

### 12. Fabricate the calibration target

Use the repository's deterministic calibration-target generator/reference. Print the target at the required scale and verify the physical scale bar with a ruler. Do not stretch, crop, recolor, or otherwise modify the reference image.

Keep the physical target with the capture rig.

**Done when:** the calibration target is physically available and dimensionally verified.

### 13. Prepare the capture rig, but do not collect experimental trials yet

Read and stage:

- `physical/p1/P1_OPERATOR_RUNBOOK.md`
- `physical/p1/P1_CAPTURE_SCHEDULE.json`
- `physical/p1/PAIRING_RANDOMIZATION_CONTRACT.json`
- `physical/p1/CAMERA_LIGHTING_SETUP.md`
- `physical/p1/P1_READINESS_FREEZE.json`

Confirm storage space, camera/lighting availability, naming workflow, custody materials, and the ability to retain original capture files and hashes.

**Critical rule:** the execution plan is **144 frozen trials**, not the historical 108-row planning sheet.

## Phase 6 — Receipt QA before P1

### 14. Inspect every delivered specimen before testing

Keep the garments at the required initial wash state. Verify identity, size/variant, print placement, registration, seam continuity, defects, and candidate/control pairing. Photograph specimens with the calibration target as required by the existing QA procedure and begin chain of custody.

If the pair is mismatched, materially defective, or otherwise inadmissible, **stop**. Reorder/escalate rather than accepting the defect into P1.

**Done when:** the intended pair is explicitly QA-admissible and traceable to the bound production records.

## Phase 7 — Execute physical P1

### 15. Run calibration acceptance first

Set up the locked rig according to the authoritative P1 runbook. Run the required calibration exposure and acceptance checks before garment measurements.

If calibration fails, fix the rig/environment and repeat calibration. Do not change scientific thresholds in response to the failure.

### 16. Execute the frozen 144-trial schedule exactly

Use:

`physical/p1/P1_CAPTURE_SCHEDULE.json`

Follow its order/pairing/randomization and the operator runbook. Preserve original files, filenames, session metadata, invalid-condition records, and hashes. Invalid trials are handled by the preregistered rules; they are not silently counted as favorable outcomes.

**Do not:**

- use the old 108-row plan;
- change thresholds after seeing results;
- arm D2-0005 as part of P1;
- access new held-out data outside the approved process;
- rewrite D2-0004;
- promote synthetic/rehearsal evidence as measured physical evidence.

## Phase 8 — Seal evidence and analyze under the preregistration

### 17. Validate ingestion and seal the measured evidence

After capture:

- complete session/ingestion records;
- validate expected files and hashes;
- preserve invalid-condition records;
- create/seal the physical evidence package through the existing repository workflow;
- retain the raw captures.

### 18. Run only the preregistered physical analysis

Evaluate the sealed P1 evidence using the frozen/preregistered rules. Report the measured result even if it is negative or inconclusive. Physical efficacy remains unsupported until this process yields admissible evidence satisfying the defined claim rules.

## The short version

Your next actions, in exact dependency order:

1. Verify Printful API access locally.
2. Download live hoodie + tee templates and hash them.
3. Record real panel geometry.
4. Select/verify live hoodie + tee variant IDs and size.
5. Export exact candidate/control production artwork and hash every required file/package.
6. Fill a copy of `physical/p1/UA_VALUES_TEMPLATE.json` completely.
7. Run `p1_bind_ua_values.py --check-only`.
8. Run the actual atomic bind.
9. Require P1 no-spend readiness to remain PASS.
10. Make the separate human spend decision.
11. Order the matched pair (plus reserves only if desired).
12. Fabricate/verify the calibration target and stage the rig.
13. Perform receipt QA and custody logging when garments arrive.
14. Require calibration acceptance.
15. Execute the authoritative frozen **144-trial** P1 schedule.
16. Validate, ingest, and seal measured evidence.
17. Run preregistered analysis and report the result without post-hoc threshold changes.

## Non-negotiable stop conditions

Stop and investigate if any of the following occurs:

- a required UA value is unknown or guessed;
- binder check-only refuses;
- the actual binder refuses;
- the no-spend readiness gate is not PASS;
- a bound hash no longer matches the file being used;
- candidate/control garment identity is mismatched;
- receipt QA fails;
- calibration acceptance fails;
- the frozen 144-trial schedule/pairing contract changes unexpectedly;
- D2-0004 changes;
- D2-0005 becomes armed without its separate explicit governance authorization;
- a scientific threshold changes after outcome access;
- new held-out access appears outside the authorized protocol;
- synthetic or rehearsal evidence is being treated as measured physical evidence.

## Protected-state checkpoint

Before procurement and again before P1 execution, confirm:

- `D2-0004 = CLOSED / NEGATIVE / immutable`
- `D2-0005 = PREREGISTERED / NOT ARMED`
- `physical_efficacy_claimed = false`
- authoritative P1 schedule = **144 trials**
- readiness gate = **PASS**
- spend authorization is a separate human decision

This checklist is a navigation/operator document only. Frozen contracts, hash-pinned artifacts, barrier handoffs, audit records, and the P1 operator/run schedule remain authoritative over it.