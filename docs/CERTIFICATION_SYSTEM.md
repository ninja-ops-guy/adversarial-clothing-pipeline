# RAC Evidence Certification System

The certification layer converts a pattern experiment into a reproducible evidence object. It is an internal verification framework, not an independent accredited certification and not a guarantee against arbitrary surveillance systems.

The normative engineering rules are defined in [`ENGINEERING_CONSTITUTION.md`](ENGINEERING_CONSTITUTION.md). If documentation conflicts, the constitution and fail-closed implementation take precedence.

## Evidence states

- RAC-D0: design candidate
- RAC-D1: surrogate-model evidence
- RAC-D2: frozen held-out digital evidence
- RAC-P1: controlled physical evidence
- RAC-P2: durability/retest evidence
- RAC-M1: verified production golden sample
- RAC-M2: verified production lot conformity

Digital evidence may never satisfy a physical or manufacturing state. Physical evidence may never satisfy a manufacturing state without manufacturing evidence.

## Fail-closed issuance

A certificate requires a preregistered protocol, distinct surrogate/held-out model sets, a pattern/master hash, source commit, baseline-qualified held-out results, acceptable invalid-condition fraction, and a sealed evidence bundle. Physical/manufacturing states additionally require their corresponding evidence.

The implementation enforces evidence state/type boundaries in `ruthless_pipeline/certification/evidence.py`. Certificate issuance separately requires physical evidence for RAC-P/RAC-M states and manufacturing evidence for RAC-M states.

## Required evidence record

Every evidence record must carry:

- RAC state and evidence type;
- source and fixture type;
- ISO-8601 creation timestamp;
- source-code commit;
- exact configuration;
- SHA-256 hashes for referenced artifacts;
- model/preprocessing/threshold metadata when model evidence is present.

## Observation validity

Benchmark observations are explicitly `valid`, `invalid`, or `excluded`. Invalid conditions require a reason and are not eligible for aggregates. Conditions where the control is not detectable are invalid and cannot count as adversarial success.

## Required evidence bundle

A production bundle should retain:

- pattern manifest and immutable master art hash;
- frozen model manifests and model-set IDs;
- benchmark raw rows and summary;
- protocol version;
- calibration/textile/print records where applicable;
- physical trials where applicable;
- manufacturing conformity results where applicable;
- `hashes.sha256` and `certificate.json`.

## Physical rig contract

Physical trials must compare a control garment and candidate under matched conditions. Record camera identity, distance, angles, pose, lighting, wash state, and any calibration IDs.

## Manufacturing conformity

A golden sample certificate does not automatically transfer to a production lot. Sample units must remain within frozen color, scale, placement, and registration tolerances.

## CI enforcement

`pytest` includes explicit fail-closed tests for evidence-state/type mismatches, illegal RAC transitions, malformed hashes, invalid-observation exclusion, physical-evidence requirements, and manufacturing-evidence requirements.

## Operational command

`python tools/certify_bundle.py issue ...` issues a certificate from completed evidence. `verify` checks bundle hashes.

Real detector weights, physical measurements, ICC profiles, and production-lot observations are external evidence inputs and must never be fabricated by the software.
