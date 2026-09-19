# RESIDUAL integration for RAC

Status: experimental integration contract v1

This integration lets RESIDUAL orchestrate RAC improvement experiments without
moving scientific authority into RESIDUAL. RAC remains authoritative for
measurement, evidence classification, held-out boundaries, and physical
execution rules.

## Boundary

RESIDUAL may:

- propose a bounded hypothesis;
- create an immutable `RACImprovementSpec`;
- coordinate implementation workers;
- request RAC experiments;
- collect hash-addressed evidence bundles;
- ask independent verifiers to evaluate them;
- produce an advisory improvement decision.

RESIDUAL may not:

- use held-out outcomes to select or optimize candidates;
- execute or arm RAC physical experiments;
- rewrite a frozen evaluation version;
- discard negative or inconclusive evidence;
- act as its own independent verifier;
- automatically promote a scientific result.

Those prohibitions are encoded in
`ruthless_pipeline.residual_integration.RACImprovementSpec` and cannot be
removed from an ImprovementSpec.

## Contract flow

```text
Observation / retained result
        |
        v
Hypothesis
        |
        v
RACImprovementSpec
  - baseline source revision
  - frozen evaluation version
  - acceptance criteria
  - falsification criteria
  - forbidden capabilities
        |
        v
RESIDUAL bounded implementation run
        |
        v
RAC experiment execution
        |
        +--> RACEvidenceBundle (primary)
        |
        +--> RACEvidenceBundle (replication)
                 |
                 v
          evaluate_improvement()
                 |
       +---------+-----------+
       |                     |
   REJECTED             INCONCLUSIVE
       |
       +---------------------+
                 |
                 v
             PROMOTABLE
                 |
                 v
        HUMAN PROMOTION GATE
```

`PROMOTABLE` is deliberately not a promotion receipt. It only means the
provided evidence meets the v1 orchestration contract. The returned decision
always has:

```json
{
  "human_gate_required": true,
  "automation_may_promote": false
}
```

## Promotion prerequisites

The v1 advisory decision requires all of the following before it can return
`PROMOTABLE`:

1. every supplied evidence bundle references the exact ImprovementSpec hash;
2. every evidence bundle uses the ImprovementSpec's frozen evaluation version;
3. no retained bundle is FAIL or INCONCLUSIVE;
4. at least two successful replication identities **and** distinct replication-receipt hashes are present;
5. at least two independent verifier labels, verifier-identity hashes, and verifier-receipt hashes are present;
6. producer and independent-verifier labels and identity hashes differ.

A FAIL always produces `REJECTED` and remains referenced in the decision.
Evaluation-version drift is refused rather than coerced.

## RAC evidence binding

Each `RACEvidenceBundle` binds:

- ImprovementSpec SHA-256;
- RAC source revision;
- evaluation version;
- experiment manifest SHA-256;
- provenance-firewall attestation SHA-256;
- result artifact SHA-256 values;
- PASS / FAIL / INCONCLUSIVE;
- producer label and host-bound identity SHA-256;
- independent verifier label, identity SHA-256, and verification-receipt SHA-256;
- replication label and replication-receipt SHA-256.

This is designed to sit above RAC's current CTM manifest, provenance firewall,
Pattern Genome, negative-result, and certification machinery. It does not
replace those components.

## Suggested RESIDUAL mission

A first experimental mission should be narrow and non-scientific: improve a
piece of RAC infrastructure while proving the orchestration path.

Example objective:

> Reduce deterministic runtime or memory use of a RAC preprocessing component
> without changing its canonical outputs, evaluation version, held-out
> boundary, or evidence semantics.

Recommended RESIDUAL checks:

1. **mechanical** — exact output/hash parity on frozen fixtures;
2. **mechanical** — test suite and schema validation pass;
3. **structural** — ImprovementSpec/evidence hashes are internally consistent;
4. **structural** — provenance firewall attestation is present;
5. **structural** — two replication IDs and two independent verifier IDs exist;
6. **judge (optional)** — review the bounded change for maintainability only,
   never for scientific efficacy.

## Initial experiment sequence

### RRI-001 — contract conformance
Create a synthetic ImprovementSpec and two synthetic evidence bundles. Verify
that mutation, self-verification, missing replication, evaluation drift, and
automatic promotion all fail closed.

### RRI-002 — deterministic infrastructure optimization
Choose a RAC component whose outputs are already deterministic. Freeze baseline
fixtures and acceptance thresholds. Allow RESIDUAL to propose an implementation
change. Require byte/hash parity plus a measurable runtime or memory
improvement.

### RRI-003 — negative-control mission
Inject a controlled regression. The experiment must retain the failure and
produce `REJECTED`, never repair the evidence record into a PASS.

### RRI-004 — verifier independence
Run the same candidate through two independently identified verifier paths.
Promotion must remain INCONCLUSIVE if both receipts resolve to one verifier
identity.

Only after those four experiments pass should the integration be considered for
a RAC research-improvement mission.

## Implementation

Current implementation:

- `ruthless_pipeline/residual_integration.py`
- `tests/test_residual_integration.py`

No RESIDUAL package is required to import RAC. The boundary is a JSON-compatible
candidate envelope returned by `build_residual_candidate()`. RESIDUAL should
hash that envelope into its own receipts and verify it without mutating RAC's
underlying scientific artifacts.
