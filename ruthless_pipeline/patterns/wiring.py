"""D2-0007 Stage-0 landmark-free wiring smoke test (provenance-completeness lane).

Relationship to the existing Stage-0 gate: ``patterns/d2007_smoke.py``
(foreign lane) executes the CI surrogate-scoring smoke and its PASS receipt
is persisted at ``evidence/d2-0007/stage0-landmark-free-smoke-closure.json``.
This module is ADDITIVE to that gate — it does not replace or re-run it.
It covers the complementary provenance-completeness wiring the gate does
not: BOTH landmark-free generators (SaliencyEyeAttack + FeatureCollage)
instantiated from ``P0_GENERATORS`` via ``GeneratorRegistry``, routed through
the exposure ledger, observation-medium annotation, governed synthetic
transfer record, and provenance nodes/edges, with fail-closed regeneration
verification.

Purpose (declared in ``generations/RAC-PER-D2-0007.json`` and
``docs/PREREGISTRATION_D2-0007.md`` §4 Stage 0): prove that PATTERNS outputs
can become governed RAC candidates with complete provenance — routed through
the actual generation → evaluation path — rather than existing only as
library objects and tests. This is a WIRING/PROVENANCE gate only:

* NO detector efficacy is measured. The scoring surface is a deterministic
  synthetic development fixture (``SMOKE_FIXTURE_MODEL_ID``), explicitly
  hypothesis-screening infrastructure, never evidence. It is not
  PERSON-SUR-v3 and never touches PERSON-HO-v3 (hash-reference only).
* D2-0005 is not read, modified, or armed. D2-0004 is not rerun. No
  threshold is changed. D2-0007 steps 6/8/9 (bounded search, held-out
  evaluation, Alpha-002) are declared-only and untouched here.
* Every observation medium is recorded per
  ``ruthless_pipeline.certification.observation_medium`` — synthetic
  ``image_composite`` only; unknown stays unknown; no worn-fabric or any
  physical claim.

Wiring path (all existing machinery, reused — no parallel stack):

1. ``SaliencyEyeAttackGenerator`` and ``FeatureCollageGenerator`` are
   instantiated from ``P0_GENERATORS`` via ``GeneratorRegistry`` (never by
   direct internal import), generated with FIXED seeds and NO landmarks in
   ``GeneratorParams.mask_geometry``. FeatureCollage's eye-overlap block is
   a ``try/except MissingLandmarksError`` enhancement; with no landmarks
   supplied the anchor-independent core path is provably the one taken.
2. ``GeneratedPattern.to_candidate()`` (base.py) emits the governed
   candidate artifact: claim_state EXPLORATORY,
   physical_efficacy_claimed False, evidence_class digital_candidate.
3. The candidate image is routed through
   ``detector_science.adapters.SyntheticDetectionAdapter`` (the established
   capabilities-guarded evaluator-adapter surface) against a deterministic
   synthetic fixture detector — the development/surrogate-side evaluation
   path, labeled screening infrastructure.
4. Exposure is recorded in the NR-01 ledger
   (``governance.evaluation_exposure.EvaluationExposureLedger``) as a
   surrogate-evaluation exposure that influenced NO selection decision.
5. Observation medium is annotated via
   ``certification.observation_medium.build_medium_annotation``.
6. A governed physical-transfer record is emitted via
   ``physical_transfer.transfer_record.emit`` with
   ``synthetic_generator=True``, which forces evidence_class
   ``synthetic_pipeline_validation_only`` (never promotable).
7. Provenance nodes/edges per candidate are recorded in the smoke summary
   using the typing vocabulary of
   ``certification.provenance_graph`` (candidate / inference_record /
   document nodes; hash-pinned edges).

Fail-closed: :func:`verify_smoke_summary` regenerates every candidate from
the registry and rejects any tampered provenance/content hash.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

from ruthless_pipeline.certification.observation_medium import (
    IMAGE_COMPOSITE,
    build_medium_annotation,
    verify_annotation,
)
from ruthless_pipeline.detector_science.adapters import SyntheticDetectionAdapter
from ruthless_pipeline.governance.evaluation_exposure import (
    CohortOutputClass,
    EvaluationExposureLedger,
    ExposureEvent,
)
from ruthless_pipeline.pattern_genome.canonical import canonical_json, sha256_bytes
from ruthless_pipeline.patterns import P0_GENERATORS, GeneratorParams
from ruthless_pipeline.patterns.registry import GeneratorRegistry
from ruthless_pipeline.physical_transfer.transfer_record import (
    emit as emit_transfer_record,
)

SMOKE_SCHEMA_VERSION = "rac-d2007-wiring-smoke/1.0"
SMOKE_ID = "RAC-D2007-WIRING-SMOKE"
GENERATION_ID = "RAC-PER-D2-0007"
STAGE = "stage0_landmark_free_wiring_smoke"

#: Generators exercised landmark-free (per the Stage-0 directive).
SMOKE_GENERATORS: Tuple[str, str] = ("saliency_eye_attack", "feature_collage")

#: Fixed smoke seeds. Deliberately DISTINCT from the preregistered motif-
#: screening seed schedule [20270110, 20270111, 20270112] so the smoke test
#: can never contaminate screening inputs.
SMOKE_SEEDS: Tuple[int, ...] = (70000001, 70000002)

SMOKE_COHORT_ID = "RAC-COHORT-D2007-SMOKE"
SMOKE_DECISION_ID = "RAC-PER-D2-0007-stage0-wiring-smoke-gate"

#: Deterministic synthetic fixture "detector" identity. This is development/
#: hypothesis-screening infrastructure ONLY — not PERSON-SUR-v3, not a
#: surrogate of record, never evidence.
SMOKE_FIXTURE_MODEL_ID = "SMOKE-DEV-FIXTURE-v0"
SMOKE_FIXTURE_MODEL_FAMILY = "synthetic_development_fixture"

OUTPUT_SIZE: Tuple[int, int] = (256, 256)


class WiringSmokeError(RuntimeError):
    """Fail-closed error for the D2-0007 wiring smoke path."""


def build_smoke_registry() -> GeneratorRegistry:
    """Instantiate the generator registry from P0_GENERATORS (the frozen
    generator-set source declared in generations/RAC-PER-D2-0007.json)."""
    registry = GeneratorRegistry()
    for generator_class in P0_GENERATORS:
        registry.register(generator_class)
    return registry


def _assert_landmark_free(params: GeneratorParams) -> None:
    """Fail closed unless no landmarks/bboxes were supplied."""
    mg = params.mask_geometry
    if mg.get("landmarks") or mg.get("bboxes"):
        raise WiringSmokeError(
            "landmark-free smoke path violated: mask_geometry carries "
            "landmarks/bboxes"
        )


def _synthetic_fixture_detection(
    image: np.ndarray, seed: int
) -> Dict[str, Any]:
    """Deterministic synthetic fixture 'detection' derived from the pattern
    content hash. Development-surface scoring fixture only: the values are
    NOT a detector measurement and are never used as efficacy evidence."""
    digest = sha256_bytes(image.tobytes())
    sub_seed = int(hashlib.sha256(f"d2007-smoke|{seed}|{digest}".encode()).hexdigest(), 16) % (2**32)
    rng = np.random.default_rng(sub_seed)
    count = int(rng.integers(0, 3))
    h, w = image.shape[0], image.shape[1]
    boxes: List[List[float]] = []
    scores: List[float] = []
    for _ in range(count):
        x0 = float(rng.uniform(0, w / 2))
        y0 = float(rng.uniform(0, h / 2))
        boxes.append([x0, y0, x0 + float(rng.uniform(8, w / 2)),
                      y0 + float(rng.uniform(8, h / 2))])
        scores.append(float(rng.uniform(0.0, 1.0)))
    return {"boxes": boxes, "labels": [1] * count, "scores": scores}


def _smoke_params(seed: int) -> GeneratorParams:
    return GeneratorParams(
        seed=seed,
        mask_geometry={},  # landmark-free by construction
        output_size=OUTPUT_SIZE,
        color_space="RGB",
        params={},
    )


def run_wiring_smoke(
    seeds: Sequence[int] = SMOKE_SEEDS,
    generator_names: Sequence[str] = SMOKE_GENERATORS,
) -> Dict[str, Any]:
    """Run the full landmark-free wiring path and return the smoke summary.

    Deterministic: same inputs → byte-identical summary (modulo the
    ``summary_sha256`` field, which is itself deterministic).
    """
    registry = build_smoke_registry()
    ledger = EvaluationExposureLedger()
    adapter = SyntheticDetectionAdapter()
    candidates: List[Dict[str, Any]] = []
    nodes: List[Dict[str, Any]] = []
    edges: List[Dict[str, Any]] = []
    event_index = 0

    for generator_name in generator_names:
        generator = registry.get(generator_name)  # registry-sourced, not imported
        for seed in seeds:
            params = _smoke_params(seed)
            _assert_landmark_free(params)
            generator.assert_deterministic(params)  # two-run determinism gate
            pattern = generator.generate(params)
            generator.verify_provenance_strict(pattern)  # fail-closed

            candidate = pattern.to_candidate()
            candidate["generation_id"] = GENERATION_ID
            candidate["stage"] = STAGE
            candidate["landmark_free"] = True
            candidate["seed"] = seed

            # --- evaluation surface: synthetic development fixture ONLY ----
            detection = _synthetic_fixture_detection(pattern.image, seed)
            response = adapter.adapt(
                detection,
                model_id=SMOKE_FIXTURE_MODEL_ID,
                model_family=SMOKE_FIXTURE_MODEL_FAMILY,
                condition_id=STAGE,
                raw_provenance_ref=candidate["candidate_id"],
            )
            response_dict = response.validate()  # schema + fabrication guard
            response_sha = sha256_bytes(canonical_json(response_dict))

            # --- exposure ledger (NR-01): surrogate-surface exposure that
            # influenced NO selection decision --------------------------------
            event_index += 1
            event = ExposureEvent(
                event_id=f"RAC-GOV-EVT-D2007-SMOKE-{event_index:04d}",
                cohort_id=SMOKE_COHORT_ID,
                output_class=CohortOutputClass.SURROGATE_EVALUATION,
                output_hash=response_sha,
                decision_id=SMOKE_DECISION_ID,
                decision_influenced=False,
            )
            ledger.register(event)

            # --- observation medium: synthetic image_composite, never worn --
            annotation = build_medium_annotation(
                subject_ref=candidate["candidate_id"],
                observation_medium=IMAGE_COMPOSITE,
                basis=(
                    "Pattern image rendered in memory by the pattern library; "
                    "no physical substrate, display, or garment was observed."
                ),
                subject_sha256=candidate["pattern_sha256"],
            )
            verify_annotation(annotation)

            # --- governed transfer record: synthetic_generator=True forces
            # evidence_class synthetic_pipeline_validation_only ----------------
            image_bytes = pattern.image.tobytes()
            record = emit_transfer_record(
                artwork=image_bytes,
                template=b"d2007-smoke-template:none",
                mapping=b"d2007-smoke-mapping:identity",
                captured_frame=image_bytes,
                garment_sku="SMOKE-NO-GARMENT",
                fabric="none-synthetic",
                print_process="none-synthetic",
                capture_id=f"d2007-smoke-{generator_name}-{seed}",
                camera="none-synthetic",
                lighting="none-synthetic",
                pose="none",
                view="none",
                detector_response_refs=[response_sha],
                synthetic_generator=True,
                record_id=f"ptr-d2007-smoke-{generator_name}-{seed}",
            )

            candidates.append(
                {
                    "candidate": candidate,
                    "evaluation": {
                        "surface": "development_synthetic_fixture",
                        "surface_role": "hypothesis_screening_infrastructure_not_evidence",
                        "model_id": SMOKE_FIXTURE_MODEL_ID,
                        "model_family": SMOKE_FIXTURE_MODEL_FAMILY,
                        "detector_response": response_dict,
                        "detector_response_sha256": response_sha,
                        "efficacy_measured": False,
                    },
                    "exposure_event": event.to_dict(),
                    "observation_medium": annotation,
                    "transfer_record": record,
                }
            )

            # --- provenance nodes/edges (provenance_graph vocabulary) -------
            cid = candidate["candidate_id"]
            nodes.append({
                "id": f"candidate:{cid}",
                "type": "candidate",
                "sha256": candidate["pattern_sha256"],
                "label": f"D2-0007 smoke candidate ({generator_name}, seed {seed})",
            })
            nodes.append({
                "id": f"inference:{cid}.fixture_response",
                "type": "inference_record",
                "sha256": response_sha,
                "label": "synthetic development-fixture response (not evidence)",
            })
            nodes.append({
                "id": f"document:{cid}.medium_annotation",
                "type": "document",
                "sha256": annotation["annotation_sha256"],
            })
            edges.append({
                "id": f"candidate:{cid} -> inference:{cid}.fixture_response [evaluated_on]",
                "source": f"candidate:{cid}",
                "target": f"inference:{cid}.fixture_response",
                "edge_type": "evaluated_on",
                "expected_sha256": response_sha,
                "hash_pin_expected": True,
                "verify_mode": "content_hash",
            })
            edges.append({
                "id": f"candidate:{cid} -> document:{cid}.medium_annotation [annotated_by]",
                "source": f"candidate:{cid}",
                "target": f"document:{cid}.medium_annotation",
                "edge_type": "annotated_by",
                "expected_sha256": annotation["annotation_sha256"],
                "hash_pin_expected": True,
                "verify_mode": "content_hash",
            })

    summary: Dict[str, Any] = {
        "schema_version": SMOKE_SCHEMA_VERSION,
        "smoke_id": SMOKE_ID,
        "generation_id": GENERATION_ID,
        "stage": STAGE,
        "purpose": (
            "wiring/provenance gate only: prove PATTERNS outputs become "
            "governed RAC candidates with complete provenance; no efficacy, "
            "no transfer, no held-out anything"
        ),
        "generators": [
            {
                "name": name,
                "version": registry.get(name).version,
                "source": "P0_GENERATORS via GeneratorRegistry",
            }
            for name in generator_names
        ],
        "seeds": list(seeds),
        "landmark_free": True,
        "output_size": list(OUTPUT_SIZE),
        "candidates": candidates,
        "exposure_ledger_sha256": ledger.ledger_hash(),
        "provenance": {"nodes": nodes, "edges": edges},
        "boundaries": {
            "d2_0005_touched": False,
            "d2_0005_armed": False,
            "heldout_accessed": False,
            "heldout_reference": "PERSON-HO-v3 hash-reference only (benchmarks/frozen_surface_sha256.json)",
            "d2_0004_rerun": False,
            "thresholds_changed": False,
            "efficacy_claimed": False,
            "physical_efficacy_claimed": False,
            "claim_state": "EXPLORATORY",
            "synthetic_evidence_class": "synthetic_pipeline_validation_only",
        },
    }
    summary["verdict"] = _compute_verdict(summary)
    summary["summary_sha256"] = _summary_hash(summary)
    return summary


def _summary_hash(summary: Dict[str, Any]) -> str:
    body = {k: v for k, v in summary.items() if k != "summary_sha256"}
    return sha256_bytes(canonical_json(body))


def _compute_verdict(summary: Dict[str, Any]) -> str:
    try:
        _check_summary(summary)
    except WiringSmokeError:
        return "FAIL"
    return "PASS"


def _check_summary(summary: Dict[str, Any]) -> None:
    """Fail-closed completeness checks (raises WiringSmokeError)."""
    if summary.get("schema_version") != SMOKE_SCHEMA_VERSION:
        raise WiringSmokeError("unsupported schema_version")
    if not summary.get("landmark_free"):
        raise WiringSmokeError("landmark_free flag missing/false")
    if not summary.get("candidates"):
        raise WiringSmokeError("no candidates produced")
    for entry in summary["candidates"]:
        cand = entry["candidate"]
        for field_name in (
            "candidate_id", "pattern_sha256", "generator", "generator_version",
            "provenance_hash", "params", "claim_state",
        ):
            if not cand.get(field_name):
                raise WiringSmokeError(f"candidate missing {field_name}")
        if cand.get("claim_state") != "EXPLORATORY":
            raise WiringSmokeError("claim_state must be EXPLORATORY")
        if cand.get("physical_efficacy_claimed") is not False:
            raise WiringSmokeError("physical_efficacy_claimed must be False")
        if cand.get("landmark_free") is not True:
            raise WiringSmokeError("candidate landmark_free must be True")
        if "landmarks" in cand["params"].get("mask_geometry", {}):
            raise WiringSmokeError("landmarks present in candidate params")
        if entry["evaluation"].get("efficacy_measured") is not False:
            raise WiringSmokeError("efficacy_measured must be False")
        if entry["evaluation"].get("surface") != "development_synthetic_fixture":
            raise WiringSmokeError("evaluation surface must be the synthetic dev fixture")
        verify_annotation(entry["observation_medium"])
        record = entry["transfer_record"]
        if record.get("evidence_class") != "synthetic_pipeline_validation_only":
            raise WiringSmokeError("transfer record must stay synthetic_pipeline_validation_only")
        if record.get("physical_efficacy_claimed") is not False:
            raise WiringSmokeError("transfer record must not claim physical efficacy")
        event = entry["exposure_event"]
        if event.get("decision_influenced") is not False:
            raise WiringSmokeError("smoke exposure may never influence a decision")
    if not summary.get("provenance", {}).get("nodes"):
        raise WiringSmokeError("provenance nodes missing")


def verify_smoke_summary(summary: Dict[str, Any]) -> None:
    """Fail-closed verification: structural checks PLUS regeneration of every
    candidate from the registry — any tampered provenance or content hash is
    rejected (raises WiringSmokeError)."""
    _check_summary(summary)
    if summary.get("summary_sha256") != _summary_hash(summary):
        raise WiringSmokeError("summary_sha256 mismatch (tampered summary)")
    registry = build_smoke_registry()
    for entry in summary["candidates"]:
        cand = entry["candidate"]
        generator = registry.get(cand["generator"])
        params_dict = cand["params"]
        params = GeneratorParams(
            seed=params_dict["seed"],
            mask_geometry=params_dict["mask_geometry"],
            output_size=tuple(params_dict["output_size"]),
            color_space=params_dict.get("color_space", "RGB"),
            params=params_dict.get("params", {}),
        )
        _assert_landmark_free(params)
        regenerated = generator.generate(params)
        if regenerated.provenance_hash != cand["provenance_hash"]:
            raise WiringSmokeError(
                f"{cand['candidate_id']}: provenance hash does not regenerate"
            )
        if sha256_bytes(regenerated.image.tobytes()) != cand["pattern_sha256"]:
            raise WiringSmokeError(
                f"{cand['candidate_id']}: pattern content hash does not regenerate"
            )
        # exposure output hash pins the recorded fixture response
        response_sha = sha256_bytes(canonical_json(entry["evaluation"]["detector_response"]))
        if response_sha != entry["exposure_event"]["output_hash"]:
            raise WiringSmokeError(
                f"{cand['candidate_id']}: exposure ledger pin mismatch"
            )


def write_smoke_summary(summary: Dict[str, Any], path: Any) -> str:
    """Write the summary as canonical JSON bytes; return its file sha256."""
    data = (json.dumps(summary, indent=2, sort_keys=True) + "\n").encode("utf-8")
    with open(path, "wb") as fh:
        fh.write(data)
    return hashlib.sha256(data).hexdigest()
