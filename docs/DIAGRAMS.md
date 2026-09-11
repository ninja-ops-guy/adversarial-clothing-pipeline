# RAC System Diagrams

**Reviewed:** 2026-09-11  
**Purpose:** visual map of the current Ruthless Adversarial Clothing research and production system without overstating software capability as physical efficacy.

These diagrams are explanatory. Frozen contracts, preregistrations, closure artifacts, and physical execution surfaces outrank them. Consult [`CURRENT_PROGRAM_STATE.md`](CURRENT_PROGRAM_STATE.md) for the canonical live program state.

## 1. Executive system topology

```mermaid
flowchart LR
    A[Design / hypothesis] --> B[Surrogate screening / optimization]
    B --> C[Simulation / EOT]
    C --> D[Digital evaluation]
    D --> E[Evidence gate]
    E --> F[Production release]
    F --> G[Matched physical trial]
    G --> H[Durability / manufacturing conformity]
```

Candidate generation is upstream of evidence. No design becomes a physical claim because it looks adversarial or scores well digitally.

## 2. Four-plane architecture

```mermaid
flowchart TB
    subgraph EP[Exploration Plane]
      PL[Pattern Lab / Product Studio]
      PG[Procedural generators]
      VH[Visual / heuristic analysis]
      EX[Artwork / config export]
      PL --> PG --> EX
      PL --> VH
    end

    subgraph RP[Research Plane]
      SC[Surrogate screening]
      OP[Bounded optimization]
      DF[Deformation]
      PH[Physics / EOT]
      EV[Evaluator adapters]
      SC --> OP --> DF --> PH --> EV
    end

    subgraph CP[Certification & Evidence Plane]
      FM[Frozen contracts]
      HB[Surrogate / held-out boundary]
      NV[Numerical verification]
      PI[Provenance + integrity]
      SE[Sealed evidence]
      PR[Promotion / refusal]
      FM --> HB --> NV --> PI --> SE --> PR
    end

    subgraph PP[Physical Validation Plane]
      VI[Live vendor intake]
      PB[Exact panel build]
      MC[Matched candidate + control]
      CAL[Calibration]
      CAP[Frozen P1 capture]
      STAT[Statistics + uncertainty]
      DUR[Durability]
      MFG[Manufacturing conformity]
      VI --> PB --> MC --> CAL --> CAP --> STAT --> DUR --> MFG
    end

    EP --> RP --> CP --> PP
    PP -. measured evidence .-> CP
```

## 3. Earned-complexity research path

RAC supports early scientific screening so expensive downstream machinery is built only when a hypothesis earns it.

```mermaid
flowchart TD
    H[Preregistered hypothesis] --> S0[Wiring / execution smoke]
    S0 --> S1[Surrogate-only screening]
    S1 --> G{Preregistered survivor rule passes?}
    G -- no --> N[Close screened-out / retained negative]
    G -- yes --> A[Minimum necessary representation / anchors]
    A --> O[Bounded optimization / EOT]
    O --> SEL[Governed selection]
    SEL --> F[Immutable candidate freeze]
    F --> HO[Held-out evaluation]
    HO --> P{Promotion criteria?}
    P -- no --> R[Retain negative]
    P -- yes --> PH[Physical-lineage candidate]
```

D2-0007 followed this topology and stopped at the Stage-1 screen with zero survivors.

## 4. D2-0007 actual closure

```mermaid
flowchart LR
    A[Stage 0 landmark-free smoke PASS] --> B[Stage 1: 8 families × 8 compositions]
    B --> C[64 / 64 observed on PERSON-SUR-v3]
    C --> D{Need ≥0.15 mean reduction + ≥4/6 improved + invalid ≤0.10}
    D -- no motif passes all rules --> E[CLOSED_SCREENED_OUT_H0]
    E --> F[No anchors]
    E --> G[No optimization]
    E --> H[No candidate freeze]
    E --> I[No held-out access]
    E --> J[No Alpha-002]
```

This is a terminal scientific result for that preregistered generation, not an unfinished pipeline.

## 5. Surrogate / held-out trust boundary

```mermaid
flowchart LR
    subgraph DEV[Development boundary]
      S[Surrogate model set] --> O[Screen / optimize]
      O --> C[Candidate]
    end

    C --> F[Freeze candidate + provenance]

    subgraph CERT[Held-out boundary]
      H[Held-out model set] --> B[Benchmark]
      T[Frozen transforms / thresholds] --> B
      F --> B
      B --> V[Verification]
    end

    V --> G{Gate}
    G -- pass --> P[Promotable digital evidence]
    G -- fail --> N[Retained negative]
```

Held-out feedback does not flow backward into the same candidate.

## 6. Alpha-001 identity and recovery

```mermaid
flowchart TD
    D3[RAC-PER-D2-0003 retained negative] --> A1[RAC-PRINT-ALPHA-001]
    W[Historical workflow run 34078238095] --> ART[GitHub Actions artifact]
    ART --> KIT[Exact print-test-kit.zip]
    KIT --> H1[SHA-256 b22b022f…f0548]
    KIT --> PAT[4096×4096 pattern]
    PAT --> H2[SHA-256 b07b617f…c261546]
    H1 --> A1
    H2 --> A1
    A1 --> P1[Physical P1 production path]
```

Alpha-001 remains bound to D2-0003. The recovered source was not regenerated or retuned.

## 7. Production release flow

```mermaid
flowchart TD
    V[Live Printful API responses] --> I[p1_production_release.py intake]
    I --> V1{Product / placement / raw-byte integrity valid?}
    V1 -- no --> X[REFUSE]
    V1 -- yes --> R[Vendor-intake receipt + deterministic archives]
    K[Exact recovered Alpha-001 kit] --> B[p1_production_release.py build]
    R --> B
    B --> V2{Kit hash + vendor evidence valid?}
    V2 -- no --> X
    V2 -- yes --> P[Exact candidate/control panels + UA values]
    P --> C[Binder --check-only]
    C --> D[Controlled bind]
    D --> G[P1 no-spend readiness]
    G --> H{Human spend authorization}
    H -- no --> STOP[Stop]
    H -- yes --> O[Matched garment order]
```

The production release wrapper never places an order by itself.

## 8. Physical P1 flow

```mermaid
flowchart TD
    O[Matched garments arrive] --> Q[Receipt QA + custody]
    T[RAC-CALT-P1-0001] --> C[Calibration acceptance]
    Q --> C
    C --> S[Authoritative 144-trial schedule]
    S --> M[Raw captures + metadata + hashes]
    M --> I[Validated ingestion]
    I --> E[Sealed physical evidence]
    E --> A[Preregistered physical analysis]
    A --> R{P1 result}
    R -->|fail / negative / inconclusive| N[Retain result]
    R -->|pass| P[Eligible for later replication / durability gates]
```

Older 108-row planning material is not execution authority.

## 9. P1 authority stack

```mermaid
flowchart TB
    R[P1_OPERATOR_RUNBOOK.md] --> X[Physical execution]
    S[P1_CAPTURE_SCHEDULE.json — 144 trials] --> X
    P[PAIRING_RANDOMIZATION_CONTRACT.json] --> X
    F[P1_READINESS_FREEZE.json] --> X
    G[p1_no_spend_readiness_gate.py] --> X
    B[p1_bind_ua_values.py] --> X
```

All explanatory docs are subordinate to this frozen execution surface.

## 10. Fail-closed evidence flow

```mermaid
flowchart TD
    A[Incoming artifact / receipt] --> B{Schema + semantics valid?}
    B -- no --> X[REFUSE]
    B -- yes --> C{Hashes / source pins valid?}
    C -- no --> X
    C -- yes --> D{Numerical outputs finite / reproducible?}
    D -- no --> X
    D -- yes --> E{Scientific boundary valid?}
    E -- no --> X
    E -- yes --> F{Candidate/control or generation identity valid?}
    F -- no --> X
    F -- yes --> G[Seal / retain evidence]
    G --> H{Promotion criteria met?}
    H -- no --> N[Retained negative]
    H -- yes --> P[Promote to next evidence level]
```

## 11. Evidence lifecycle

```mermaid
stateDiagram-v2
    [*] --> Exploratory
    Exploratory --> Screened
    Screened --> ScreenedOut: early gate fails
    Screened --> Candidate: early gate passes
    Candidate --> Frozen: provenance sealed
    Frozen --> DigitalEvaluated: authorized held-out run
    DigitalEvaluated --> RetainedFail: digital gate fails
    DigitalEvaluated --> ProductionReady: digital / governance path allows physical production
    ProductionReady --> PhysicalEvaluated: matched P1 executed
    PhysicalEvaluated --> RetainedFail: physical gate fails
    PhysicalEvaluated --> PhysicalQualified: physical gate passes
    PhysicalQualified --> Durability
    Durability --> Manufacturing
    Manufacturing --> BoundedClaim
```

Retained failure and screened-out states are valid terminal research outcomes.

## 12. Claim-to-source provenance

```mermaid
flowchart TD
    CLAIM[Claim] --> REL[Sealed release / closure]
    REL --> MET[Metric / decision]
    MET --> RAW[Raw outputs]
    RAW --> RUN[Run manifest]
    RUN --> MOD[Model-set / threshold / transform contract]
    RUN --> ART[Candidate / artwork hash]
    ART --> SRC[Source commit / exact source bytes]
    PHYS[Physical artifact IDs] --> CLAIM
    CAL[Calibration evidence] --> CLAIM
    VEN[Vendor source bytes / production mapping] --> PHYS
```

A physical claim adds manufacturing, custody, calibration, and raw-media provenance to the digital chain.

## 13. Current terminal/open states

```mermaid
flowchart LR
    D3[D2-0003: negative] --> A1[Alpha-001 production path OPEN]
    D4[D2-0004: negative]
    D5[D2-0005: preregistered / not armed]
    D7[D2-0007: screened out H0]
    A1 --> P1[P1 physical evidence OPEN]
    P1 --> P2[P2 durability OPEN]
    P2 --> M[M1/M2 manufacturing OPEN]
```

The next program-defining milestone is admissible P1 physical evidence.
