# noRecognition public architecture and dataset access specification

**Date:** 2026-09-10  
**Scope:** hevnsnt/norecognition and the linked public research website  
**External repository snapshot:** `09dbc4332fbb965991dfa0f5f8f1eaad1d0c12ec`  
**Assessment:** descriptive architecture and data-access findings; not a reconstruction of the private research software.

## Findings

The current public repository contains documentation, illustrations, and README publication automation. It does not contain the current research engine or its complete experimental corpus. Public material supports a conceptual architecture, but not a complete executable specification of the newer system.

The large research dataset is **not established as publicly downloadable**. The small image collection in GitHub is a different object. Author permission and an actual delivery offer would be needed to establish access to any larger unpublished dataset.

## 1. Public repository inventory

The [recursive Git tree](https://api.github.com/repos/hevnsnt/norecognition/git/trees/09dbc4332fbb965991dfa0f5f8f1eaad1d0c12ec?recursive=1) returned a complete, untruncated listing of 61 files:

| Group | Files | Role |
| --- | ---: | --- |
| Markdown | 5 | README, persona documentation, pattern catalog, hardware discussion, historical roadmap |
| License | 1 | NRSAL v7.0 terms |
| Python | 1 | README image-table updater |
| Workflow YAML | 1 | Scheduled/manual publication workflow |
| Git ignore file | 1 | Repository hygiene |
| Persona images | 12 | Six named personas, two views each |
| Pattern sample images | 9 | Selected illustrative outputs |
| Report images | 26 | Rendered plots; not the underlying experiment table |
| Other root images/animations | 5 | Presentation assets |
| **Total** | **61** | |

Inventory establishes file presence, not image quality, rights, or the validity of illustrated results. The current tree has no CSV, JSONL, Parquet, database dump, or model-checkpoint files. This is a statement about this snapshot, not every historical commit or private repository.

The [README](https://github.com/hevnsnt/norecognition/blob/09dbc4332fbb965991dfa0f5f8f1eaad1d0c12ec/README.md) marks the repository deprecated and directs readers to the current website. Historical descriptions of modules must not be mistaken for files currently shipped.

## 2. What the executable public portion does

| Component | Input | Behavior | Output |
| --- | --- | --- | --- |
| [Publication workflow](https://github.com/hevnsnt/norecognition/blob/09dbc4332fbb965991dfa0f5f8f1eaad1d0c12ec/.github/workflows/update-anomalies.yml) | Public gallery metadata | Defines a six-hour schedule and manual trigger; selects nine recent gallery items and runs the formatter. | Updated README commit when content changes |
| [README formatter](https://github.com/hevnsnt/norecognition/blob/09dbc4332fbb965991dfa0f5f8f1eaad1d0c12ec/.github/scripts/update_readme_images.py) | A local list of image links | Builds a three-column table, limits display to nine items, and replaces content between README markers. | Modified README text |

The formatter handles missing input or missing markers as errors, pads short lists with empty cells, and leaves the README unchanged when there are no links. This is publication plumbing, not pattern generation, model training, or a dataset export interface. Workflow existence does not prove that its external dependency is currently operational; it was not executed.

## 3. Conceptual research architecture

The [historical roadmap](https://github.com/hevnsnt/norecognition/blob/09dbc4332fbb965991dfa0f5f8f1eaad1d0c12ec/roadmap.md) describes separate baseline and analysis workers, per-worker model state and logging, recorded observations, and reporting. These descriptions provide historical design context; corresponding research modules are absent from the inspected tree.

The [current about page](https://sandbox.norecognition.org/about) describes consolidating prior experimental records, deduplicating them, learning relationships between experimental inputs and outcomes, and moving to newer learned representations. It reports approximately 82 GB of raw research material and 5.7 million unique labeled examples after consolidation. Those are author-reported corpus descriptions, not a downloadable release manifest.

At the data level, the described system distinguishes:

- source scenes and garment context;
- candidate artifacts and their provenance;
- model-specific observations;
- historical experiment collections;
- learned model artifacts;
- summary reports and public illustrations.

These objects need distinct identifiers and versions for independent interpretation. The public prose does not supply their complete schemas, join keys, checksums, or release boundaries.

## 4. Dataset availability matrix

| Data object | What is established | Access finding |
| --- | --- | --- |
| Legacy persona illustrations | Twelve files in the public tree; [persona documentation](https://github.com/hevnsnt/norecognition/blob/09dbc4332fbb965991dfa0f5f8f1eaad1d0c12ec/personas.md) describes six synthetic identities. | Publicly visible; reuse rights need clarification for RAC. |
| Example output illustrations | Nine selected images in the public tree. | Public examples, not a complete or representative labeled dataset. |
| Rendered research plots | Twenty-six report images. | Public figures; underlying rows, exclusions, and cohort definitions are not supplied by these images. |
| Larger experiment corpus | Described on the about page. | No verified download release or delivery offer found. |
| Newer complete persona/capture collection | Referenced by the broader research narrative. | No complete public manifest identified in the inspected repository. |
| Current winning artifacts | [Research page](https://sandbox.norecognition.org/research) says champion patterns are withheld until fabric ships. | Not established as an available dataset; a planned future release is not present access. |
| Current learned-model checkpoints | Mentioned conceptually by the research narrative. | No checkpoint files or release assets identified. |

The persona document says its historical images are synthetic and describes consistent fixture conditions. That does not establish the provenance or permitted uses of every later dataset edition.

**Checks performed:** complete current Git tree; repository releases listing (empty); all-state issue/PR listing (two entries, neither announcing a dataset release); public README, persona documentation, license, publication scripts, roadmap, and current research/about pages. GitHub repository searches for `DarkCogswell` and `user:hevnsnt dataset` returned no repositories. General web discovery did not establish another authoritative dataset distribution.

**Search limits:** repository history, private storage, unadvertised services, and restricted endpoints were not searched. No corpus download was attempted. “Not found” is not proof that the author cannot share it.

## 5. Rights and acquisition status

The [license](https://github.com/hevnsnt/norecognition/blob/09dbc4332fbb965991dfa0f5f8f1eaad1d0c12ec/LICENSE) expressly restricts commercial use of the software/source and contains terms concerning rights in generated outputs. It lists **bill@seckc.org** for commercial licensing inquiries. This is a public project contact, not confirmation of dataset availability or any offer.

For RAC, establish the scope of a separate data license before reuse. Clarify whether it covers images, labels, derived statistics, publication, redistribution, and any intended commercial research. This note reports the text and an unresolved permission question; it does not determine legal enforceability.

No contact has been sent, no agreement accepted, and no access or payment commitment made.

## 6. Information needed from the publisher

A useful first inquiry is whether an independently shareable dataset edition exists. If so, request:

| Information | Why it matters |
| --- | --- |
| Dataset title, version, release date, and data card | Identifies what is actually being offered |
| Exact included modalities and record counts | Separates images, evaluations, experiments, identities, and report summaries |
| Provenance and per-component permissions | Establishes which materials the publisher can license |
| Intended-use and commercial restrictions | Determines whether the offer fits RAC |
| Schema documentation and anonymized example records | Allows assessment without assuming field semantics |
| Split membership and duplicate/identity definitions | Helps interpret independence and leakage risks |
| Model, preprocessing, and observation-medium versions | Prevents pooling incompatible measurements |
| Inclusion/exclusion and selection history | Distinguishes a selected showcase from a broader corpus |
| Checksums, delivery format, costs, and access expiry | Makes any eventual handoff concrete and verifiable |
| Publication, attribution, and redistribution terms | Defines what can be reported or shared afterwards |

This is an acquisition-information specification. Availability remains **UNKNOWN_PENDING_PUBLISHER_RESPONSE**; permitted RAC use remains **NOT_ESTABLISHED**.

## 7. Implications for RAC documentation

- Keep the earlier [RAC capability comparison](NORECOGNITION_REVIEW_2026-09-10.md) linked to its inspected source snapshot.
- Describe the external system's private components as author-reported, not source-verified.
- Keep images, raw observations, derived summaries, and learned models as distinct asset categories.
- Do not label gallery illustrations or report images as the full dataset.
- Revisit this access note when an actual dataset card, release, license, or publisher response becomes available.

**Completed:** public architecture inventory, publication-code review, dataset availability check, and acquisition information requirements.  
**Unresolved:** access to a larger dataset, its exact contents, its license for RAC, and the current private implementation.
