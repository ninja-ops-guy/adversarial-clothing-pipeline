# RAC System Diagrams

**Purpose:** provide a visual map of the Ruthless Adversarial Clothing (RAC) research platform without overstating software capability as physical efficacy.

These diagrams describe the implemented and planned system boundaries. A rendered diagram may describe a pathway that crosses an open experimental gate; consult `PROJECT_PROGRESS.md` for the authoritative live state.

## 1. Executive system topology

```mermaid
flowchart LR
    A[Design] --> B[Optimization]
    B --> C[Simulation]
    C --> D[Benchmark]
    D --> E[Certification]
    E --> F[Print]
    F --> G[Physical Trial]
    G --> H[Manufacturing Conformity]
```

The key idea is that candidate generation is upstream of evidence. No design becomes a product claim merely because it optimized well digitally.

## 2. Four-plane architecture

```mermaid
flowchart TB
    subgraph EP[Exploration Plane]
      PL[Pattern Lab]
      PG[Procedural generators]
      VH[Visual / heuristic analysis]
      EX[PNG / JSON / configuration export]
      PL --> PG
      PL --> VH
      PG --> EX
    end

    subgraph RP[Research Plane]
      TP[Texture prior / NAP]
      EA[Environment-adaptive optimizer]
      ND[Neural deformation]
      PC[Differentiable cloth physics]
      SC[Garment scene composition]
      EV[Evaluator adapters]
      TP --> ND
      EA --> ND
      ND --> PC
      PC --> SC
      SC --> EV
    end

    subgraph CP[Certification & Evidence Plane]
      FM[Frozen manifests / contracts]
      SH[Surrogate-held-out separation]
      NV[Independent numerical verification]
      PI[Provenance + integrity]
      SA[Sealed artifacts]
      PR[Promotion / refusal gates]
      FM --> SH --> NV --> PI --> SA --> PR
    end

    subgraph PP[Physical Validation Plane]
      MC[Matched candidate + control]
      CAL[Production / color calibration]
      CAP[Preregistered capture]
      MEAS[Measured detector outputs]
      STAT[Statistics + uncertainty]
      REP[Replication / durability]
      MFG[Manufacturing conformity]
      MC --> CAL --> CAP --> MEAS --> STAT --> REP --> MFG
    end

    EP --> RP
    RP --> CP
    CP --> PP
    PP -. measured evidence returns .-> CP
```

## 3. Candidate-generation topology

```mermaid
flowchart TD
    A[Pattern / textile seed] --> B{Generation path}
    B -->|NAP| C[Texture prior / optimizer]
    B -->|Environment adaptive| D[Palette extraction]
    D --> E[Pattern-color decomposition]
    E --> F[Palette-constrained allocation]
    C --> G[EOT / transforms]
    F --> G
    G --> H[Surrogate-only scoring]
    H --> I[CandidateArtifact]
    I --> J[Deformation]
    J --> K[Cloth simulation]
    K --> L[Scene composition]
```

Held-out certification models do not belong in the generation loop.

## 4. Evaluation and trust boundary

```mermaid
flowchart LR
    subgraph TRAIN[Optimization boundary]
      S[Surrogate model set]
      O[Optimizer]
      C[Candidate]
      S --> O --> C
      S --> O
    end

    C --> F[Freeze candidate + provenance]

    subgraph CERT[Certification boundary]
      H[Held-out model set]
      T[Frozen transforms]
      B[Benchmark]
      V[Verification]
      H --> B
      T --> B
      F --> B
      B --> V
    end

    V --> R{Gate}
    R -->|pass| P[Promotable evidence]
    R -->|fail| X[Retained negative / refusal]
```

The candidate must be frozen before held-out evaluation. Held-out results may inform a later generation, but not retroactively modify the candidate whose transfer they measure.

## 5. Evidence lifecycle

```mermaid
stateDiagram-v2
    [*] --> Exploratory
    Exploratory --> Candidate: candidate selected
    Candidate --> Frozen: hashes + manifests sealed
    Frozen --> D2: held-out benchmark executed
    D2 --> RetainedFail: gate fails
    D2 --> DigitalQualified: digital gate passes
    DigitalQualified --> ProductionAlpha: matched print package
    ProductionAlpha --> P1: physical trial executed
    P1 --> RetainedFail: physical gate fails
    P1 --> PhysicalQualified: physical gate passes
    PhysicalQualified --> Replication
    Replication --> Durability
    Durability --> Manufacturing
    Manufacturing --> ProductEvidence
```

Not every generation should reach the final state. Retained failure is a valid terminal research outcome.

## 6. Fail-closed certification flow

```mermaid
flowchart TD
    A[Incoming experiment artifact] --> B{Schema valid?}
    B -- no --> X[REFUSE]
    B -- yes --> C{Hashes / source pins valid?}
    C -- no --> X
    C -- yes --> D{Finite numerical outputs?}
    D -- no --> X
    D -- yes --> E{Candidate-control relationship valid?}
    E -- no --> X
    E -- yes --> F{Model membership / split valid?}
    F -- no --> X
    F -- yes --> G{Replay / seed / integrity checks pass?}
    G -- no --> X
    G -- yes --> H[Seal evidence bundle]
    H --> I{Promotion criteria met?}
    I -- no --> J[Retain measured failure]
    I -- yes --> K[Promote to next evidence stage]
```

## 7. Digital-to-physical translation flow

```mermaid
flowchart LR
    A[Frozen digital artwork] --> B[Provider template / placement map]
    B --> C[Candidate production file]
    A --> D[Matched control construction]
    D --> E[Control production file]
    C --> F[Order / manufacture]
    E --> F
    F --> G[Physical artifact IDs]
    G --> H[Calibration]
    H --> I[Capture sessions]
    I --> J[Raw camera media]
    J --> K[Measured inference]
    K --> L[Session-level statistics]
    L --> M[Physical evidence bundle]
```

Candidate and control identities must remain distinct and traceable through the entire chain.

## 8. Data and provenance topology

```mermaid
flowchart TD
    CODE[Source commit] --> RUN[Run manifest]
    MODELS[Model manifests] --> RUN
    CFG[Seeds / thresholds / transforms] --> RUN
    ART[Candidate artifact hash] --> RUN
    RUN --> RAW[Raw outputs]
    RAW --> MET[Metrics]
    MET --> REL[Sealed RAC experiment release]
    RUN --> REL
    CAL[Calibration artifacts] --> REL
    MEDIA[Physical media / session manifests] --> REL
    REL --> CLAIM[Claim review]
```

A quantitative claim should be traceable backward from the report to the release, raw outputs, run manifest, candidate identity, model manifest, and source commit.

## 9. Pattern Lab versus measured evidence

```mermaid
flowchart LR
    PL[Pattern Lab] --> H[Heuristic / visual exploration]
    PL --> E[Candidate config export]
    H --> UI[UI display only]
    E --> PY[Python research stack]
    PY --> BM[Measured benchmark]
    BM --> CE[Certified evidence import]
    CE --> UI
```

The UI may display both heuristic and measured information, but the provenance and evidence labels must make them visibly distinct.

## 10. Research feedback loop

```mermaid
flowchart LR
    Q[Research question] --> P[Preregister protocol]
    P --> G[Generate candidate]
    G --> E[Evaluate]
    E --> C[Certify / retain]
    C --> A[Analyze]
    A --> R[Research release / manuscript]
    R --> N[Next hypothesis]
    N --> Q
```

The loop is intentionally experimental rather than self-validating: a new hypothesis begins a new frozen generation instead of changing old evidence.

## 11. Deployment / repository topology

```mermaid
flowchart TB
    REPO[GitHub repository]
    REPO --> WEB[Static Pattern Lab / GitHub Pages]
    REPO --> PY[Python package]
    REPO --> CI[CI / certification checks]
    REPO --> DOC[Docs + preregistrations + manuscripts]
    REPO --> REL[Sealed release metadata]

    EXT[External evidence inputs]
    EXT -->|model weights / approved evaluators| PY
    EXT -->|print provider / physical artifacts| PHYS[Physical program]
    EXT -->|camera media / calibration| PHYS

    PY --> CI
    PHYS --> REL
    CI --> REL
    REL --> DOC
```

Large generated artifacts, model weights, raw datasets, credentials and sensitive environment material should remain outside normal source control and be referenced through approved manifests or retained evidence stores.

## Reading order

For a new technical reviewer:

1. `README.md` — project thesis and executive architecture.
2. `DIAGRAMS.md` — visual system map.
3. `ARCHITECTURE.md` — implementation boundaries and component responsibilities.
4. `CERTIFICATION_SYSTEM.md` — evidence ladder and refusal behavior.
5. `END_TO_END_RESEARCH_SOP.md` — operational experiment procedure.
6. `PROJECT_PROGRESS.md` — authoritative current state.
7. `papers/` — research questions and pre-results manuscripts.
