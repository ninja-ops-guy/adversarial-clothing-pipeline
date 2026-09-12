# From SAT Solving to Experimental Governance: Integrating Formal Reasoning into Adversarial Textile Research

**Status:** Pre-results methods manuscript  
**Evidence state:** IMPLEMENTED METHOD; physical efficacy RESULTS PENDING  
**RAC paper:** 7  
**Scope:** CIC-derived formal reasoning, constraint verification, sampling governance, and experimental design in the Ruthless Adversarial Clothing platform

## Abstract

Physical adversarial-vision research combines two difficult problems: searching a large design space for unusual model behavior and constructing experiments whose controls, manufacturing constraints, sampling procedures, and evidence lineage remain scientifically interpretable. These problems should not be solved by the same mechanism. Optimization is useful for discovery, but an optimizer is a poor authority for deciding whether an experimental design is logically feasible, whether a returned solver result is trustworthy, whether a control population satisfies its declared invariants, or whether two experimental waves remain comparable after their constraints change.

This paper describes the integration of formal-reasoning ideas and tools from the CIC satisfiability and structural-analysis research program into the Ruthless Adversarial Clothing (RAC) platform. The integration deliberately does not use SAT solving as an adversarial-pattern oracle. Instead, CIC-derived machinery occupies a bounded verification role: scientific requirements are compiled into discrete constraint representations; SAT witnesses are independently checked; ambiguous solver outcomes fail closed as `UNKNOWN`; UNSAT conclusions require independent verification evidence; semantic and compiled problem identities are separately hash-bound; structurally equivalent encodings can be differentially checked; and structural instance metrics inform sampler-backend routing without being treated as predictors of adversarial efficacy.

The same separation extends into RAC's sampling and adaptive-governance architecture. A satisfying assignment is not treated as a representative experimental specimen. RAC distinguishes feasibility from population sampling, records the scientific projection independently from auxiliary solver variables, diagnoses sampler representativeness, seals cohorts before CTM intake, and permits later-wave adaptation only from sealed prior-wave evidence. Constraint or evaluation-pipeline migrations require explicit overlap or bridge handling before cross-wave comparison. This architecture converts formal reasoning from an optimization novelty into an experimental control plane.

The contribution is therefore methodological rather than efficacy-based: formal methods can improve adversarial physical-AI research by separating generation from verification, feasibility from representativeness, and solver correctness from scientific semantic correctness. No claim is made here that CIC-derived reasoning improves adversarial garment performance; physical transfer remains an empirical question.

## 1. Introduction

Adversarial-example research is naturally optimization-heavy. A candidate is generated, evaluated against one or more models, modified, and evaluated again. In physical settings the process becomes more complicated because the candidate must eventually survive printing, garment geometry, deformation, camera conditions, motion, and measurement protocols.

A second problem exists underneath the optimization problem: **what exactly constitutes a valid experiment?**

Examples include:

- whether a requested matched-null population is logically non-empty;
- whether a candidate satisfies manufacturing and experimental constraints simultaneously;
- whether a solver's claimed assignment actually satisfies the compiled formula;
- whether an UNSAT response means logical impossibility rather than timeout or backend ambiguity;
- whether auxiliary encoding variables accidentally redefine the population being sampled;
- whether a control cohort is representative of its declared feasible population;
- whether a changed constraint set makes two experimental waves incomparable;
- whether current-wave outcomes have leaked into current-wave sampling decisions.

These are not primarily computer-vision optimization questions. They are questions about formal specification, verification, sampling, provenance, and experimental governance.

RAC therefore separates two responsibilities:

```text
DISCOVERY / MEASUREMENT                     FORMAL CONTROL PLANE

pattern generators                          scientific constraints
continuous optimizers                       discrete encodings
simulation                                  satisfiability checks
physical experiments                        witness verification
CTM outcomes                                structural analysis
transfer inference                          sampling governance
                                            migration / comparability gates
```

CIC contributes to the right-hand side of this boundary.

## 2. Design Principle: Generation Is Not Verification

The central architectural idea inherited from CIC and related verified-planning work is that the component proposing an answer should not automatically be the component trusted to certify it.

For RAC:

```text
scientific requirement
        ↓
constraint semantics
        ↓
CNF / PB / SMT representation
        ↓
solver backend
        ↓
SAT / UNSAT / UNKNOWN
        ↓
independent RAC verification
        ↓
governed result
```

The optimizer remains free to explore unusual regions of design space. Formal verification determines whether a discrete experimental contract has actually been satisfied.

This distinction is especially important in adversarial research because the objective of the research is often to discover unexpected behavior. Over-constraining the generator can suppress discovery, while under-verifying the resulting experiment can make the evidence uninterpretable. RAC therefore retains a discovery or chaos lane while applying formal controls before a discovery can enter confirmatory physical evaluation.

## 3. The CIC–RAC Boundary

### 3.1 CIC is not the adversarial optimizer

RAC does not ask a SAT solver to produce the "best adversarial shirt." Continuous appearance optimization, evolutionary search, latent search, transformation-aware objectives, and later physical measurements remain separate concerns.

The formal layer instead answers questions of the form:

> Does at least one design or experimental assignment exist that satisfies this declared set of discrete requirements?

A simplified matched-null specification might require:

```text
MATCH_COLOR_CLASS
AND MATCH_PRINT_PROCESS
AND MATCH_GARMENT_REGION
AND NOT SHARE_TREATMENT_TOPOLOGY
AND NOT SHARE_TREATMENT_SPECTRAL_CLASS
AND MANUFACTURABLE
AND SEAM_SAFE
```

The formal system can establish whether these requirements are jointly satisfiable before expensive optimization or manufacturing begins.

### 3.2 Bounded trust

RAC treats solver backends as bounded dependencies rather than unquestioned authorities. The CIC adapter normalizes backend behavior into three governed states:

```text
SAT
UNSAT
UNKNOWN
```

A backend-specific ambiguous return is never silently promoted to UNSAT. This is important because an implementation may use the same sentinel value for timeout, resource exhaustion, unsupported cases, or true unsatisfiability.

The rule is therefore:

```text
ambiguous / incomplete backend result
                 ↓
              UNKNOWN
```

`UNKNOWN` preserves the feasible design space rather than incorrectly deleting it.

## 4. SAT Witness Verification

A SAT result contains a constructive object: an assignment. RAC can independently evaluate that assignment against the compiled problem.

Let a compiled constraint problem be \(F\), and let a backend return assignment \(a\). RAC accepts the solver's SAT claim only when:

\[
F(a) = \mathrm{true}.
\]

If the backend claims SAT but the assignment does not satisfy the compiled problem, the result is rejected.

This creates a useful asymmetry:

- **SAT** can be checked by evaluating the witness.
- **UNSAT** requires stronger evidence because there is no satisfying witness to inspect.

The adapter therefore separates solver execution from result certification.

## 5. Fail-Closed UNSAT Handling

A false UNSAT result is particularly dangerous in RAC. It can silently remove a region of the experimental design space and make a feasible control or candidate family appear impossible.

Accordingly, a backend's bare `UNSAT` assertion is insufficient for governed evidence. RAC requires independently verified contradiction evidence or corroboration according to the active verification policy. Otherwise the result is downgraded to `UNKNOWN`.

This policy can be represented as:

```text
backend says UNSAT
       ↓
verification evidence available?
       ├── yes → verify against compiled problem → governed UNSAT
       └── no  → UNKNOWN
```

Any UNSAT proof is explicitly scoped to the **compiled problem**. It does not by itself prove that the compiled problem faithfully represents the intended scientific semantics.

That distinction is fundamental.

## 6. Scientific Semantics Versus Compiled Correctness

Formal solvers can perfectly solve the wrong formula. RAC therefore records two different identities:

```text
semantic constraint identity
compiled problem identity
```

The semantic hash represents the intended scientific rule set. The compiled hash represents the concrete CNF, pseudo-Boolean, SMT, or other solver representation.

This prevents the statement

> "the solver proved the formula"

from being confused with

> "the formula is a correct encoding of the scientific hypothesis."

RAC addresses the second problem through several complementary mechanisms.

### 6.1 Reference semantic behavior

Important constraints can have direct reference implementations that evaluate semantic assignments without going through the solver encoding.

### 6.2 Property-based and boundary tests

Generated assignments and deliberately difficult boundary cases are checked against both semantic and encoded behavior.

### 6.3 Metamorphic relations

Where scientifically justified, transformations that should preserve a property can be tested for invariance. These relations must be constraint-specific. A spectral property may be rotation-invariant while a seam or weave-direction constraint may not be.

### 6.4 Cross-encoding differential validation

The same semantic constraint set can be represented through distinct computational forms:

```text
scientific semantics
      ↓
 ┌────┼────┐
CNF   PB   SMT
 └────┼────┘
      ↓
projected scientific behavior
```

Disagreement among independent representations is treated as evidence of an encoding or backend problem, not as a scientific finding.

RAC's differential validation is intentionally scoped: finite probe agreement increases confidence but is not presented as a mathematical proof of global semantic equivalence.

## 7. Scientific Projection and Auxiliary Variables

SAT encodings frequently introduce auxiliary variables. These variables are computational conveniences, not scientific dimensions of the textile design.

RAC therefore separates:

- \(P\): the scientific projection, consisting of semantic genome or experimental variables;
- \(A\): auxiliary variables introduced by the encoding;
- \(I \subseteq P\): an optional independent support used for efficient hashing or structural reasoning.

The intended population is defined over \(P\), not over all assignments to \(P \cup A\).

This distinction matters because a solver may admit multiple auxiliary assignments for the same scientific genome. Sampling all solver variables can therefore distort the scientific population.

The governing invariant is:

```text
scientific population = distinct feasible assignments over P
auxiliary variables   = implementation detail
```

Independent-support analysis may reduce the variables used internally for hashing, but it does not redefine the scientific population.

## 8. From Satisfiability to Sampling

One of the most important conclusions of the CIC–RAC integration is that **SAT is not enough**.

Suppose a constraint set admits one million feasible genomes. Asking a SAT solver for twenty solutions does not imply that those twenty are representative. Branching heuristics can repeatedly return assignments from a small corner of the solution space.

RAC therefore separates:

```text
FEASIBILITY
"Does a solution exist?"

from

SAMPLING
"What distribution over feasible scientific genomes are we drawing from?"
```

A satisfying assignment is not automatically an experimental specimen.

The sampling layer records the target population, scientific projection, seed, backend, target distribution, diagnostics, and diagnostic policy. Exact finite-population sampling is available as a calibration oracle for tractable spaces; external hashing, stratified, or proposal-based samplers can be integrated behind bounded adapters for larger spaces.

## 9. CIC Structural Analysis as a Routing Signal

CIC research also contributes structural characterization of constraint problems. Features such as graph width, density, clause structure, and related instance statistics can help predict which computational backend is likely to be practical.

RAC deliberately restricts the interpretation of these metrics.

They may answer:

> Which verification, counting, or sampling backend should RAC try for this constraint instance?

They do **not** answer:

> Is this pattern likely to fool a detector?

Thus:

```text
constraint instance
      ↓
CIC structural metrics
      ↓
empirical routing model
      ↓
exact / hashing / stratified / degraded sampler
```

The routing model is empirical rather than a frozen universal threshold such as "treewidth below X always uses backend Y." Backend performance is calibrated against RAC instances and can evolve independently from the scientific claims.

This is a more defensible use of structural SAT research than treating syntactic solver properties as natural measures of adversarial transfer.

## 10. Why SAT Backdoors Are Not Treated as Transfer Explanations

An early hypothesis considered whether SAT backdoor variables—variables whose assignment dramatically simplifies a constraint instance—might correspond to high-leverage adversarial design variables.

RAC does not assume this relationship.

Backdoor structure can depend strongly on encoding choices, auxiliary variables, and solver behavior. A correlation between SAT backdoor membership and CTM transfer importance could therefore be an artifact of the representation rather than a property of the underlying textile design space.

If studied, this question must be treated as a falsifiable secondary research question and tested across semantically equivalent but computationally distinct formulations. Persistence across CNF, cardinality or pseudo-Boolean, and SMT representations would be more informative than persistence under trivial variable renaming or clause permutation.

The production architecture does not depend on such a correlation existing.

## 11. Null and Control Construction

The most direct scientific application of formal constraints in RAC is control construction.

Adversarial-textile experiments can be confounded when a nominal control unintentionally shares treatment properties. For example, a "color-matched" control might also inherit topology, spectral organization, or optimization history from the treatment.

RAC can define null families explicitly:

```text
COLOR_MATCHED_NULL
SPECTRAL_MATCHED_NULL
TOPOLOGY_MATCHED_NULL
MANUFACTURING_MATCHED_NULL
```

Each family has declared invariants and exclusions. The constraint layer can verify that a requested control family is feasible and that generated controls satisfy the declared relationship to the treatment.

Formal feasibility does not guarantee statistical representativeness. The resulting feasible null population must still be sampled under an explicit distribution and diagnosed before confirmatory use.

This gives RAC a two-stage control guarantee:

1. **semantic validity** — the control satisfies its formal definition;
2. **sampling validity** — the cohort adequately represents the declared feasible control population under the preregistered policy.

## 12. Contradiction Explanation and MUS-Style Analysis

A binary UNSAT response is operationally useful but scientifically incomplete. When a requested experiment is impossible, the next question is often which requirements are jointly responsible.

CIC-derived minimal-unsatisfiable-subset and counterexample reasoning can support this analysis.

For example, suppose RAC requests:

```text
spectral match ≤ ε
palette colors ≤ 4
large topology distance
high deformation stability
specific print process
```

and the conjunction is unsatisfiable. A contradiction explanation can identify a smaller subset of requirements that remains impossible.

This does not prove that the scientific hypothesis is false. It establishes that the current formal specification cannot satisfy all of those requirements simultaneously.

Such explanations are useful for:

- identifying over-constrained null definitions;
- distinguishing manufacturing impossibility from optimization failure;
- deciding which requirement needs scientific reconsideration;
- documenting why an experimental arm could not be constructed.

The explanation must remain tied to the exact semantic and compiled constraint versions from which it was derived.

## 13. Constraint Lineage and Cross-Wave Comparability

Constraint definitions evolve. A manufacturing capability may change, a semantic bug may be corrected, or a null definition may be refined.

RAC treats these changes as potential experimental population changes rather than ordinary software updates.

Each governed constraint set has immutable identity and lineage. When two CTM cohorts use different constraint sets, default cross-wave comparison requires an explicit overlap analysis. Depending on the result, RAC may permit common-support comparison, require a bridge cohort, or declare a new experimental regime.

Pipeline changes are treated similarly. A changed evaluation pipeline requires an explicit migration classification; a bridge may be required before old and new measurements can be combined.

The formal layer therefore affects not only whether a specimen can be generated but whether two bodies of evidence still refer to comparable populations.

## 14. Temporal Firewall and Adaptive Experimentation

RAC permits later waves to learn from earlier waves, but it forbids outcome information from the wave currently being constructed from influencing that same wave's sampling policy.

The permitted flow is:

```text
Wave N cohort
    ↓
sealed measurement
    ↓
sealed CTM evidence
    ↓
freeze Wave N+1 allocation / sampling policy
    ↓
construct Wave N+1 cohort
```

The forbidden flow is:

```text
Wave N outcomes
      ↕
Wave N sampling policy
```

The adaptive policy binds its source evidence hash and source seal. Even an explicitly supplied empty current-wave outcome container is rejected, making the boundary fail closed rather than relying on conventions about whether an empty structure counts as "access."

This extends the CIC principle of verified state transitions into experimental adaptation.

## 15. Chaos Lane and Physical Admissibility

Formal constraints should not become a gatekeeper for hypothesis generation. Adversarial discoveries can occur in unusual regions that violate current assumptions about feasible or useful designs.

RAC therefore preserves a chaos lane for weakly constrained exploration.

A chaos discovery may be simulated even when it is not currently manufacturable. However, before it can enter confirmatory physical testing it must pass a minimal physical-admissibility gate.

Failed candidates are not deleted. They remain in an append-only archive with failure reasons. If manufacturing capabilities later change, the candidate can be re-screened under the new state, but the original failure remains immutable.

Promotion depends on the **latest** re-screen result, preventing a stale historical admissibility event from resurrecting a candidate that subsequently failed.

RAC also reports how the physical gate filters the chaos population