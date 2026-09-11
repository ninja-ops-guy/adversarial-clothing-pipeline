# RAC End-to-End Research SOP

**Version:** 1.1.0  
**Last updated:** 2026-09-11  
**Purpose:** pick-up-and-run procedure from research hypothesis through digital closure, exact production release, matched physical P1, sealed evidence, and later durability/manufacturing work.

> **Authority:** frozen preregistrations, closure artifacts, model/protocol contracts, and physical execution surfaces outrank this SOP. For current status, start with `docs/CURRENT_PROGRAM_STATE.md`.

> **Critical boundary:** browser design/heuristic surfaces are not measured evidence. Software completion is not physical efficacy. Negative and screened-out results are retained rather than rewritten.

## 0. Identify the current state before doing work

Read:

```text
docs/CURRENT_PROGRAM_STATE.md
docs/PROJECT_PROGRESS_CURRENT.md
```

Then identify whether the task is:

- a new prospective digital generation;
- a closed-generation evidence/reporting task;
- Production Alpha / P1 physical work;
- post-P1 durability/manufacturing work.

Do not reopen a closed generation merely because its result was negative.

## 1. New digital research generation

Before outcome-bearing held-out access, preregister at minimum:

- generation / hypothesis identity;
- directional hypothesis and endpoints;
- surrogate and fresh held-out sets;
- model/weight/preprocessing/threshold manifests;
- candidate-generation policy;
- screening/optimization objective;
- candidate/search budget and stopping rule;
- seeds and EOT/transformation policy;
- invalid-condition rule;
- statistical unit and practical effect threshold;
- PASS / FAIL / INCONCLUSIVE regions;
- allowed post-freeze amendments/appends;
- evidence label.

A generation may use early surrogate-only screening to decide whether more expensive machinery is scientifically earned.

### Current examples

- D2-0005 is separately preregistered and **NOT armed**.
- D2-0007 is **closed `SCREENED_OUT_H0`** after 64/64 Stage-1 compositions produced zero survivors. It authorizes no Stage-2 anchors, optimization, held-out run, or Alpha-002.

## 2. Candidate generation / screening

Use the declared creative/computational path while preserving deterministic provenance:

- candidate ID;
- generation ID;
- family/motif/product;
- seed and configuration;
- source commit;
- exported artifact hashes;
- Pattern Genome sidecar where the governed path requires it;
- surrogate-only measurements and telemetry.

Held-out models are forbidden during generation/ranking/mutation unless a new frozen contract explicitly says otherwise.

## 3. Earned downstream complexity

If an early preregistered screen fails, close the generation and retain the result.

If it passes, only then implement/use the minimum downstream machinery authorized by the protocol, such as:

- body/garment anchor abstraction;
- bounded optimization;
- EOT/deformation integration;
- governed selection;
- immutable candidate freeze.

Infrastructure existing in the repository does not by itself authorize its use in a generation.

## 4. Candidate freeze before held-out access

Before held-out evaluation:

1. verify candidate/artifact hashes;
2. verify source commit and frozen configuration;
3. verify surrogate/held-out model-set identities;
4. verify held-out feedback has not entered selection;
5. seal required telemetry/provenance;
6. prohibit candidate mutation.

Any scientific candidate-byte change after freeze creates a new artifact/generation.

## 5. Held-out digital evaluation

Use the governed Python benchmark/workflow rather than browser heuristics.

Rules:

- use the frozen held-out set exactly as authorized;
- do not change thresholds after observing outcomes;
- do not regenerate the candidate;
- retain raw rows, manifests, transformation conditions and failures;
- append results without rewriting pre-held-out history;
- permanently treat the evaluated held-out set as observed for that generation.

PASS, FAIL, INCONCLUSIVE, and screened-out/null outcomes are all valid research results.

## 6. Close and retain the generation

At closure:

- verify candidate/protocol/model hashes;
- verify held-out boundary;
- verify bundle/receipt integrity;
- classify the result under the frozen rule;
- retain negative/null evidence;
- mint/update governed evidence/release artifacts where applicable;
- update `docs/PROJECT_PROGRESS_CURRENT.md` and `docs/CURRENT_PROGRAM_STATE.md` rather than rewriting historical preregistrations.

Do not reconstruct unavailable pre-outcome telemetry from post-outcome knowledge.

## 7. Production Alpha identity

The current physical test article is **not D2-0007** and not a newly regenerated candidate.

Production target:

```text
Release: RAC-PRINT-ALPHA-001
Candidate lineage: RAC-PER-D2-0003
Primary product: Printful 388 — All-Over Print Recycled Unisex Hoodie
Size: operator-selected from live supported variants
Control: matched flat/control artwork on the same production configuration
```

The exact Alpha-001 source was recovered from the original historical Actions artifact.

```text
sealed print-test-kit.zip SHA-256:
b22b022fd98bc8587251099464010dbc3288f8da70756e183f8e366be06f0548

pattern_tile_4096.png SHA-256:
b07b617fe6dbe178330fff2d9f65c2b720948b641e2bd4865e43ebd62c261546
```

Recovery provenance: `evidence/p1/alpha001-source-recovery.json`.

Do not regenerate or retune Alpha-001.

## 8. Live Printful intake

Use the strict release wrapper:

```bash
export PF_TOKEN='<secret>'
python tools/p1_production_release.py intake \
  --fetch \
  --size M \
  --output-dir production_alpha/vendor_intake
```

Replace `M` with the actual chosen size.

The wrapper must validate live product identity, variant, required placements, raw vendor bytes and deterministic vendor archives. Unexpected or conflicting vendor state is a stop condition, not permission to guess.

The fallback/reserve product-257 tee metadata may still be required by the current binder contract; it is not the primary first-order SKU.

## 9. Exact production-art build

```bash
python tools/p1_production_release.py build \
  --intake production_alpha/vendor_intake/vendor-intake.json \
  --print-test-kit /secure/path/print-test-kit.zip \
  --recorded-by '<operator>'
```

The build verifies vendor evidence and the frozen Alpha-001 source, creates exact-size candidate/control panel artwork, deterministic archives, and binder-ready UA values. It does not authorize spend or place an order.

## 10. Bind and readiness transition

Review live variant/geometry/artwork/hash information first.

Then:

```bash
python tools/p1_bind_ua_values.py \
  --values production_alpha/vendor_intake/ua-values.generated.json \
  --check-only

python tools/p1_bind_ua_values.py \
  --values production_alpha/vendor_intake/ua-values.generated.json

python tools/p1_no_spend_readiness_gate.py
```

Require clean binding/readiness receipts. Successful software readiness remains separate from human procurement authorization.

## 11. Matched procurement

Minimum first order:

```text
1 × PA-HOODIE-CAND-001
1 × PA-HOODIE-CTRL-001
```

Candidate/control must be matched on every practical production variable except artwork: product, live variant, size, substrate, technique, order window, and intended fulfillment conditions.

Record order IDs, uploaded artwork hashes, live product/variant information, date, and manufacturing/fulfillment region when available.

## 12. Calibration target and rig

While garments are in transit:

- generate/use `RAC-CALT-P1-0001`;
- print/fabricate at 100% scale / 300 DPI;
- physically verify the 100 mm scale bar;
- stage camera/lighting/background/marks and storage;
- prepare custody and raw-media retention.

Do not collect efficacy outcomes early.

## 13. Receipt QA

Before P1:

- reconcile order/SKU/variant identity;
- verify candidate/control pairing;
- record material and fulfillment/manufacturing facts;
- inspect placement, registration, seams and defects;
- preserve chain of custody;
- stop/reorder/escalate if the pair is not QA-admissible.

Manufacturing defects are not candidate successes.

## 14. P1 execution authority

Use only the frozen execution package:

```text
physical/p1/P1_OPERATOR_RUNBOOK.md
physical/p1/P1_CAPTURE_SCHEDULE.json        # 144 trials
physical/p1/PAIRING_RANDOMIZATION_CONTRACT.json
physical/p1/P1_READINESS_FREEZE.json
```

The historical 108-row planning sheet is not execution authority.

Run calibration acceptance first. Then execute the frozen 144-trial schedule exactly, preserving raw captures, filenames, metadata, hashes and invalid-condition dispositions.

Never alter thresholds after seeing candidate outcomes.

## 15. Physical evidence ingestion / analysis

After capture:

1. validate expected media and hashes;
2. preserve raw captures and invalid-condition records;
3. complete ingestion/session records;
4. seal the physical evidence package;
5. run preregistered paired/statistical analysis;
6. retain PASS / FAIL / negative / inconclusive outcome exactly as produced.

Do not promote rehearsal/synthetic data into RAC-P evidence.

## 16. Durability / manufacturing

Only after a valid P1 baseline:

- execute preregistered wash/durability conditions;
- retain the same evidence/provenance discipline;
- establish a golden physical sample if warranted;
- measure lot conformity rather than assuming repeatability;
- bound any product/public claims to the actually supported evidence state.

## 17. Reporting / publication

Every report should distinguish:

- exploratory observation;
- internally measured digital result;
- physical result;
- manufacturing result;
- negative/null result;
- open/speculative hypothesis.

Publication tooling must consume verified evidence; it must not promote claims from a mutable status flag.

## Non-negotiable invariants

Never:

- rewrite a frozen preregistration to make history look current;
- inject a new pool into D2-0005;
- reopen D2-0007 after its screened-out closure under the same identity;
- silently replace/rebind Alpha-001;
- access held-out data early;
- change thresholds after outcome observation;
- guess missing vendor values;
- treat software readiness as physical efficacy;
- delete negative results.
