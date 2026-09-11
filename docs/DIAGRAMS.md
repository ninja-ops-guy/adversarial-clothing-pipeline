# RAC System Diagrams

**Purpose:** provide a visual map of the Ruthless Adversarial Clothing (RAC) research platform without overstating software capability as physical efficacy.

These diagrams describe system boundaries and evidence flow. A diagram may show a pathway that crosses an open experimental gate; consult [`CURRENT_PROGRAM_STATE.md`](CURRENT_PROGRAM_STATE.md) for the authoritative live program state. Frozen experiment/physical contracts and hash-pinned artifacts outrank explanatory diagrams.

The supplied diagram set has been normalized into maintainable SVG assets under `docs/assets/diagrams/`. The SVGs are explanatory renders; the Mermaid blocks below remain the editable topology source.

## 1. Executive system topology

![RAC executive pipeline](assets/diagrams/executive-pipeline.svg)

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

![RAC four-plane architecture](assets/diagrams/four-plane-architecture.svg)

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

![RAC candidate-generation topology](assets/diagrams/candidate-generation.svg)

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

![RAC evaluation trust boundary](assets/diagrams/evaluation-trust-boundary.svg)

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

![RAC evidence lifecycle](assets/diagrams/evidence-lifecycle.svg)

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

Not every generation should reach the final state. Retained failure is a valid terminal research outcome. This is a **timeless lifecycle diagram**, not a current-generation status board; use `CURRENT_PROGRAM_STATE.md` for current D2/P1 state.

## 6. Fail-closed certification flow

![RAC fail-closed certification flow](assets/diagrams/fail-closed-certification.svg)

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

Candidate and control identities must remain distinct and traceable through the entire chain. For P1 execution authority, use the frozen P1 schedule/runbook rather than this explanatory flow.

## 8. Data and provenance topology

![RAC data and provenance topology](assets/diagrams/data-provenance.svg)

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

![RAC Pattern Lab versus measured evidence](assets/diagrams/pattern-lab-vs-measured.svg)

```mermaid
flowchart LR
    PL[Pattern Lab] --> H[Heuristic / visual exploration]
    PL --> E[Candidate config export]
    H --> UIH[UI display: exploratory]
    E --> PY[Python research stack]
    PY --> BM[Measured benchmark]
    BM --> CE[Certified evidence import]
    CE --> UIM[UI display: measured]
```

The UI may display both heuristic and measured information, but the provenance and evidence labels must make them visibly distinct.

## 10. Research feedback loop

![RAC research feedback loop](assets/diagrams/research-feedback-loop.svg)

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

## Rendered asset inventory

| Asset | Purpose |
| --- | --- |
| `assets/diagrams/executive-pipeline.svg` | executive design-to-manufacturing flow |
| `assets/diagrams/four-plane-architecture.svg` | exploration / research / evidence / physical planes |
| `assets/diagrams/candidate-generation.svg` | candidate-generation topology |
| `assets/diagrams/evaluation-trust-boundary.svg` | surrogate vs held-out trust boundary |
| `assets/diagrams/evidence-lifecycle.svg` | generic evidence lifecycle; not live generation status |
| `assets/diagrams/fail-closed-certification.svg` | certification refusal / promotion flow |
| `assets/diagrams/data-provenance.svg` | backward provenance topology |
| `assets/diagrams/pattern-lab-vs-measured.svg` | heuristic vs measured UI separation |
| `assets/diagrams/research-feedback-loop.svg` | preregistered research feedback loop |

## Reading order

For a new technical reviewer:

1. `README.md` — project thesis and executive architecture.
2. `CURRENT_PROGRAM_STATE.md` — authoritative current program-level state.
3. `DIAGRAMS.md` — visual system map.
4. `ARCHITECTURE.md` — implementation boundaries and component responsibilities.
5. `CERTIFICATION_SYSTEM.md` — evidence ladder and refusal behavior.
6. `END_TO_END_RESEARCH_SOP.md` — operational experiment procedure.
7. `PROJECT_PROGRESS_CURRENT.md` — detailed current workstreams and verification state.
8. `papers/` — research questions and pre-results manuscripts.
