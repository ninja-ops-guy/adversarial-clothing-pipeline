# RAC World-Class Acceptance Matrix

**HEAD:** `b50f6b0` · **Date:** 2026-09-09 · Classes: COMPLETE / PARTIAL / MISSING / BLOCKED / USER_ACTION_REQUIRED / OWNED_BY_OTHER_SWARM

| ID | Charter requirement | Class | Evidence (path · tests) | Known limitations |
|---|---|---|---|---|
| §5-A1 | print-alpha charter tree | MISSING | — | tree + charter-named files absent |
| §5-A2 | control/candidate matched pair | PARTIAL | docs/PRODUCTION_ALPHA_SKU.md · production_alpha/SKU_MANIFEST.json | variant IDs PENDING-API-FETCH (UA-1) |
| §5-A3 | candidate byte-identical to frozen source | PARTIAL | SKU_MANIFEST expected_pattern_sha256 + print_test_kit_sha256 | per-placement artwork hashes pending (UA-1) |
| §5-A4 | physical_efficacy_claimed=false flag | MISSING | 0 hits | prose disclaimers only |
| §5-A5 | evidence_class=experimental_print_specimen | MISSING | 0 hits | class not in taxonomy |
| §5-A6 | capture protocol set | PARTIAL | CAPTURE_LAB.md · P1_CAPTURE_RIG_SPEC.md · physical/p1/* · physical_protocol.py (test_print_test_pipeline.py) | charter filenames + trial-sheet.csv absent |
| §5-A7 | QA set | PARTIAL | RECEIPT_QA_FORM.md · RAC-PHYSICAL-PRINT-TEST-1.0.md | pairing checklist + chain-of-custody absent |
| §5-A8 | user-action packets | COMPLETE | ORDER_WORKSHEET.md · TEMPLATE_INGESTION_CHECKLIST.md · VENDOR_QUESTIONS.md · calibration_target.py guard | — |
| §6 | Optimization Engine V3 | PARTIAL | nap.py · candidate_optimizer.py (test_candidate_optimizer.py) · certification/objectives.py CVaR (test_objectives.py) | no optimization/ namespace, registry, backends, trajectory, constraints, schemas; no NaN/divergence refusal, checkpoint hashing, resume integrity, FD gradient checks, parity tests |
| §7 | Expectation over Transformation | MISSING | adjacent: benchmark.py fixed grid | no distribution contract, no robustness surfaces |
| §8 | Detector response schema | PARTIAL | evaluators.py DetectionBatch · benchmark.py invalid-condition accounting · model_manifests/ | no detector_science/, no family registry/transfer matrix/LOFO/diversity/concentration |
| §9 | Pareto search | MISSING | prose only | no frontier computation or candidate classes |
| §10 | Style-constrained optimization | PARTIAL | design_profiles/ruthless_reference_v1.json (5 families) · JS studio style scorer | no Python coupling, no tracking, no style-Pareto |
| §11 | Deformation/physics T0–T3 + benchmark | PARTIAL | deformation.py (T1) · physics.py (T2) · tests (smoke) | T0 implicit, T3 missing, no tier interface, no artifacts/deformation_benchmark/, no DEFORMATION_VALIDATION.md |
| §12 | printability_loss API | MISSING | adjacent: telemetry printability scalar; calibration_ingest MTF/ΔE00 | all 6 sub-metrics + versioned vendor store absent (UA-4 for measured values) |
| §13 | physical_transfer_record | MISSING | synthetic flag exists on experiment journal (experiment_state_machine.py:78) | schema + record tooling absent |
| §14 | Calibration feedback model | PARTIAL | CALIBRATION_TARGET_SPEC.md · calibration_target.py (test_calibration_target_contract.py) · calibration_ingest.py (test_calibration_ingest.py) | no measured data (UA-3), no feedback consumer, no uncertainty model; SCAFFOLD_ONLY enforced ✓ |
| §15 | Ablation lab (9 comparisons) | PARTIAL | rehearsal_d20005.py + design_analysis_d20005* artifacts + paired/cluster statistics + tests | 1 of 9 comparisons covered; no general registry |
| §16 | Mechanism analysis | MISSING | narrative plans only | all six mechanism metrics + hypotheses harness absent |
| §17 | RAC-R3 reproducibility | PARTIAL | runtime_lock.json (test_runtime_lock.py) · model manifests (test_model_lock.py) · frozen_surface_sha256.json (test_frozen_surface_integrity.py) · releases MANIFEST.json · provenance graph + graph.json (test_provenance_graph.py) | no consolidated RAC-R3 manifest; source commit, seed manifest, optimizer/transformation/candidate/analysis hashes not explicitly pinned; D2-0004 log-attested gap (inherited) |
| §18 | Acceptance/test coverage | PARTIAL | 64 test files + 5 e2e specs | common/evaluators/physical_protocol + 6 certification modules lack direct tests; physics spine smoke-level |
| §2/§21 | Scientific boundary integrity | OWNED_BY_OTHER_SWARM | confirmed intact at b50f6b0 (see gap analysis §0/§15) | this swarm: document-only near these surfaces |

## Legend of evidence columns
"tests" = direct test files. PARTIAL never means "code exists"; it means a verifiable subset of the charter properties holds, with limitations listed.
