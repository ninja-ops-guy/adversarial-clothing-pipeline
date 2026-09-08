# RAC-EXP-2026-001 — RAC-PER-D2-0004 closed-generation report (log-attested)

- Verdict: **FAIL** (evidence state RAC-D0; benchmark run 34175028944)
- Certificate id: `RAC-PER-D2-0004-1.0.0-1.2`
- Source commit: `b4fe0e5942b56b7fffb8de6f1cb3172744269f59`
- Failure classification: `cross_architecture_transfer_failure` (confidence high)
- Provenance: log_attested: true; bundle validated in CI steps 19-21 but never archived (packaging step 22 failed on schema guard; infra fix 5cdce1b; no re-run authorized); evidence extracted from run logs uploaded by maintainer

## Step-18 measured benchmark aggregate (n=144)

- Baseline detection rate: 1.0
- Candidate detection rate (aggregate): 0.7777777777777778
- Relative detection suppression: 0.2222222222222222
- Relative confidence reduction: 0.26430541006882546

## Step-19 held-out outcome (PERSON-HO-v3, n=36)

- Baseline detection rate: 1.0
- Candidate detection rate: 1.0
- Baseline mean confidence: 0.9947303864690993
- Candidate mean confidence: 0.8959943834278319
- Mean delta: -0.0987360030412674

The scientific outcome FAIL / RAC-D0 is final and was not modified.
