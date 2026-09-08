"""D2-0005 non-held-out rehearsal harness (queue step 6, outcome-free).

GOVERNANCE STATUS: this module is a REHEARSAL harness for the D2-0005 freeze
candidate (docs/D2-0005_FREEZE_CANDIDATE.json, status
FREEZE_CANDIDATE_NOT_ARMED_PENDING_REHEARSAL_AND_AUDIT; amendment draft
docs/PREREGISTRATION_D2-0005_AMENDMENT_A5.md). It exists to prove that the
planned selection -> freeze -> cluster-robust paired analysis -> evidence
sealing -> release -> manuscript-export chain is exercisable and fails CLOSED,
BEFORE any arming decision. It does NOT arm D2-0005, changes no threshold,
touches no generation record, and never accesses the held-out model set.

Everything this module emits is explicitly labelled
``evidence_class = "synthetic_pipeline_validation_only"`` with
``rac_evidence_eligible = False`` and is structurally incapable of promotion
to RAC-P1 (see :func:`promote_to_rac_p1`, which refuses such artifacts).

Documented substitutions (mock adapters; no real fixtures/models/records):

* Synthetic "base images" are deterministic hash-seeded PNG arrays written
  under the caller-supplied scratch output directory, SHA-256-pinned into a
  disposable fixture manifest (schema ``d2-0005-fixture-manifest`` 1.0). No
  real fixture (in particular not ``source-zidane.jpg`` or any planned
  ``fixtures/d20005_base_images/`` content) is read or written.
* Surrogate selection scores come from a SHA-256-seeded generator, not from
  the real PERSON-SUR-v3 models; the selection objective (CVaR, alpha = 0.5
  per the pinned ``cvar_alpha``) is evaluated over those synthetic scores.
* Held-out confirmation scores come from a SHA-256-seeded MOCK generator
  keyed by the two held-out model NAMES ONLY. ``model_sets/PERSON-HO-v3.json``
  (sha256 ad1127659a...) is referenced by identity and hash exactly as the
  freeze candidate does; it is never opened for scoring and no held-out
  inference is performed or implied.
* No active-generation code paths (``scripts/select_surrogate_candidate.py``,
  ``scripts/freeze_adaptive_candidate.py``) are executed, because exercising
  them would touch generation records. The selection/freeze stages are
  re-expressed here over the synthetic pool with the same frozen seeds
  (candidate_pool_seed 1337, bootstrap seed 20260907, z pinned).

Determinism: every byte derives from SHA-256 over stable identifiers; the
only timestamp is the caller-stamped ``created_utc`` (fixed default). A rerun
into a fresh directory is byte-identical (fail-closed rerun semantics).
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .cluster_paired_arm_statistics import (
    ABSOLUTE_MIN_CLUSTERS,
    cluster_paired_arm_statistics,
    intracluster_diagnostics,
    to_canonical_json,
)
from .paired_arm_statistics import (
    DEFAULT_BOOTSTRAP_RESAMPLES,
    DEFAULT_BOOTSTRAP_SEED,
    DEFAULT_Z,
    INCONCLUSIVE_WIDTH_MAX,
)
from .release_format import (
    ReleaseManifest,
    ReleaseRevisionLog,
    compute_content_hash,
    verify_release,
)
from .schema_version import SchemaVersionError, require_schema_version

# ---------------------------------------------------------------------------
# Constants (all analysis parameters are the FROZEN pins; nothing is moved)
# ---------------------------------------------------------------------------

EVIDENCE_CLASS = "synthetic_pipeline_validation_only"
SCHEMA_VERSION = "1.0"
FIXTURE_SCHEMA_ID = "d2-0005-fixture-manifest"
SEALED_SCHEMA_ID = "d2-0005-cluster-paired-arm-statistics"
JOURNAL_SCHEMA_ID = "d2-0005-rehearsal-journal"

#: Frozen preregistered parameters (docs/D2-0005_FREEZE_CANDIDATE.json).
Z = DEFAULT_Z  # 1.959963984540054
BOOTSTRAP_SEED = DEFAULT_BOOTSTRAP_SEED  # 20260907
BOOTSTRAP_RESAMPLES = DEFAULT_BOOTSTRAP_RESAMPLES  # 10000
WIDTH_GATE = INCONCLUSIVE_WIDTH_MAX  # 0.20
CVAR_ALPHA = 0.5
CANDIDATE_POOL_SEED = 1337
MIN_CLUSTERS = ABSOLUTE_MIN_CLUSTERS  # 8
MEMBERS_PER_CLUSTER = 36  # 18 transformation views x 2 held-out models

#: Rehearsal ICC gate of amendment A5.5: arm only if realized ICC <= 0.25.
ICC_GATE_MAX = 0.25

#: Model identities only. Surrogate set PERSON-SUR-v3 (sha256 2f06c19e...);
#: held-out set PERSON-HO-v3 (sha256 ad112765...). The held-out names are
#: used ONLY as hash-seed keys for the mock score generator; no held-out
#: model file is read, no held-out inference performed.
SURROGATE_MODEL_SET_ID = "PERSON-SUR-v3"
HELDOUT_MODEL_SET_ID = "PERSON-HO-v3"
SURROGATE_MODELS = (
    "yolov8n",
    "fasterrcnn_mobilenet_v3_320",
    "detr_resnet50",
    "ssdlite320_mobilenet_v3",
    "retinanet_resnet50_fpn_v2",
    "fcos_resnet50_fpn",
)
HELDOUT_MODELS = (
    "fasterrcnn_resnet50_fpn_v2",
    "maskrcnn_resnet50_fpn_v2",
)

TRANSFORM_IDS = tuple(f"t{index:02d}" for index in range(18))

RELEASE_ID = "RAC-EXP-2026-905"
DEFAULT_CREATED_UTC = "2026-01-01T00:00:00Z"
RESULT_LINE = "RESULT: synthetic_pipeline_validation_only — not RAC evidence"

#: release_format semantics: RELEASE.json stores the manifest content hash,
#: so both files are excluded from content addressing.
RELEASE_EXCLUDE = ("MANIFEST.json", "RELEASE.json")

STAGES = (
    "fixture",
    "selection",
    "freeze",
    "analysis",
    "seal",
    "release",
    "export",
)


class RehearsalCrash(RuntimeError):
    """Deliberately injected mid-pipeline crash (failure-injection testing)."""


class PromotionRefusedError(ValueError):
    """A synthetic rehearsal artifact may never be promoted to RAC-P1."""


# ---------------------------------------------------------------------------
# Deterministic primitives
# ---------------------------------------------------------------------------

def _canonical(payload: Any) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()


def _sha256_bytes(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest()


def _unit_interval(key: str) -> float:
    """Deterministic uniform in [0, 1) from SHA-256 of a stable string."""
    digest = hashlib.sha256(key.encode()).digest()
    return int.from_bytes(digest[:8], "big") / 2**64


def _write_json(path: Path, payload: dict) -> str:
    """Write canonical JSON (+newline) and return its SHA-256."""
    path.parent.mkdir(parents=True, exist_ok=True)
    blob = _canonical(payload) + b"\n"
    path.write_bytes(blob)
    return _sha256_bytes(blob)


def _label(payload: dict) -> dict:
    """Every emitted artifact is stamped synthetic-only, never RAC evidence."""
    payload.setdefault("schema_version", SCHEMA_VERSION)
    payload["evidence_class"] = EVIDENCE_CLASS
    payload["rac_evidence_eligible"] = False
    return payload


# ---------------------------------------------------------------------------
# 1. Synthetic fixture: >= 8 hash-seeded "base images", SHA-256-pinned
# ---------------------------------------------------------------------------

def _synthetic_png_bytes(key: str) -> bytes:
    """Deterministic 64x64 RGB PNG derived from a stable string hash."""
    import io

    import numpy as np
    from PIL import Image

    seed = int.from_bytes(hashlib.sha256(key.encode()).digest()[:8], "big")
    rng = np.random.default_rng(seed)
    arr = rng.integers(0, 256, size=(64, 64, 3), dtype=np.uint8)
    buf = io.BytesIO()
    Image.fromarray(arr, "RGB").save(buf, format="PNG")
    return buf.getvalue()


def build_synthetic_fixture(
    images_dir: Path,
    *,
    k: int = MIN_CLUSTERS,
) -> dict:
    """Generate ``k`` synthetic base images and a disposable hash manifest.

    The images are generated arrays (never photographic sources), pinned by
    SHA-256 of the exact bytes, schema ``d2-0005-fixture-manifest`` 1.0 —
    mirroring the planned pinning procedure without touching any real fixture.
    """
    images_dir = Path(images_dir)
    images_dir.mkdir(parents=True, exist_ok=True)
    images: list[dict[str, str]] = []
    for index in range(k):
        image_id = f"synthetic-base-{index:03d}"
        blob = _synthetic_png_bytes(f"d20005-rehearsal|{image_id}")
        rel = f"{image_id}.png"
        (images_dir / rel).write_bytes(blob)
        images.append({"image_id": image_id, "path": rel, "sha256": _sha256_bytes(blob)})
    return _label({
        "schema_id": FIXTURE_SCHEMA_ID,
        "generation_id": "RAC-PER-D2-0005",
        "status": "SYNTHETIC_REHEARSAL_DISPOSABLE",
        "synthetic": True,
        "note": (
            "Disposable synthetic rehearsal fixture: generated arrays pinned by "
            "SHA-256, exercising the A5.5/A5.6 manifest mechanics only. Not the "
            "planned fixtures/d20005_base_images/manifest.json; no real image "
            "was read or written; incapable of serving as D2-0005 evidence."
        ),
        "images": images,
        "cluster_count": len(images),
        "members_per_cluster": MEMBERS_PER_CLUSTER,
    })


# ---------------------------------------------------------------------------
# 2. Surrogate-selection arm (mock surrogate scores, CVaR objective)
# ---------------------------------------------------------------------------

def _synthetic_candidate_pool(pool_size: int = 100) -> list[dict]:
    """Synthetic candidate pool keyed by the frozen pool seed 1337."""
    pool = []
    for index in range(pool_size):
        candidate_id = f"synthetic-cand-{index:03d}"
        pool.append({
            "candidate_id": candidate_id,
            "candidate_sha256": _sha256_bytes(
                f"pool|{CANDIDATE_POOL_SEED}|{candidate_id}".encode()
            ),
        })
    return pool


def surrogate_selection_arm(
    *,
    pool_size: int = 100,
    alpha: float = CVAR_ALPHA,
) -> dict:
    """Mock surrogate selection: CVaR_alpha of synthetic surrogate scores.

    The real selection script (scripts/select_surrogate_candidate.py) is NOT
    executed because it would touch generation records; this mock adapter
    reproduces the selection SEMANTICS (pick the candidate minimizing the
    CVaR_alpha tail of surrogate detection scores) over hash-seeded scores.
    """
    pool = _synthetic_candidate_pool(pool_size)
    scored = []
    tail = max(1, int(round(pool_size * alpha / 10)))  # worst-10% tail per model set
    for candidate in pool:
        scores = sorted(
            _unit_interval(f"sur|{model}|{candidate['candidate_id']}")
            for model in SURROGATE_MODELS
        )
        cvar = sum(scores[-tail:]) / tail  # tail of DETECTION score (lower wins)
        scored.append((cvar, candidate["candidate_id"], candidate["candidate_sha256"]))
    scored.sort()
    cvar, winner_id, winner_sha = scored[0]
    return _label({
        "schema_id": "d2-0005-rehearsal-selection",
        "arm": "surrogate_selection",
        "objective": {"name": "cvar", "alpha": alpha},
        "candidate_pool_seed": CANDIDATE_POOL_SEED,
        "pool_size": pool_size,
        "winner_candidate_id": winner_id,
        "winner_candidate_sha256": winner_sha,
        "winner_cvar": cvar,
        "mock_adapter": True,
        "substitution_note": (
            "Synthetic surrogate scores from a SHA-256-seeded generator; the real "
            "selection entry point is not executed because it would touch "
            "generation records. Selection semantics (CVaR minimization, frozen "
            "seed 1337) are preserved."
        ),
    })


# ---------------------------------------------------------------------------
# 3. Held-out-confirmation arm (MOCK held-out scores; HO-v3 untouched)
# ---------------------------------------------------------------------------

def mock_heldout_cluster_outcomes(
    fixture: dict,
    *,
    base_rate_m: float = 0.55,
    base_rate_c: float = 0.35,
    cluster_jitter: float = 0.15,
) -> dict[str, dict[str, tuple[bool, bool]]]:
    """Hash-seeded mock paired outcomes grouped by base-image cluster.

    Returns ``{cluster_id: {"model_id|transform_id": (arm_m, arm_c)}}`` with
    exactly MEMBERS_PER_CLUSTER members per cluster (2 mock held-out models x
    18 transforms). Cluster jitter induces a mild realistic ICC. No held-out
    artifact is accessed; the model names are hash keys only.
    """
    outcomes: dict[str, dict[str, tuple[bool, bool]]] = {}
    for image in fixture["images"]:
        cluster_id = image["image_id"]
        jitter = cluster_jitter * (2.0 * _unit_interval(f"jitter|{cluster_id}") - 1.0)
        members: dict[str, tuple[bool, bool]] = {}
        for model in HELDOUT_MODELS:
            for transform in TRANSFORM_IDS:
                key = f"{model}|{transform}"
                draw_key = f"ho|{cluster_id}|{key}"
                arm_m = _unit_interval(f"m|{draw_key}") < base_rate_m + jitter
                arm_c = _unit_interval(f"c|{draw_key}") < base_rate_c + jitter
                members[key] = (arm_m, arm_c)
        outcomes[cluster_id] = members
    return outcomes


# ---------------------------------------------------------------------------
# 4. Cluster-robust paired analysis (the REAL pinned module)
# ---------------------------------------------------------------------------

def run_cluster_analysis(cluster_outcomes, *, min_clusters: int = MIN_CLUSTERS):
    """Run the pinned cluster-robust comparison (fails closed < 8 clusters)."""
    return cluster_paired_arm_statistics(
        cluster_outcomes,
        z=Z,
        bootstrap_resamples=BOOTSTRAP_RESAMPLES,
        bootstrap_seed=BOOTSTRAP_SEED,
        width_max=WIDTH_GATE,
        min_clusters=min_clusters,
    )


def seal_evidence(stats, *, fixture_manifest_sha256: str, selection: dict,
                  created_utc: str) -> dict:
    """Hash-bound sealed evidence artifact with schema_version.

    The payload embeds the canonical JSON of the pinned statistics module
    (``to_canonical_json``) plus its SHA-256, so any post-seal tampering is
    detectable both by content re-hash and by the release verifier.
    """
    canonical = to_canonical_json(stats)
    sealed = _label({
        "schema_id": SEALED_SCHEMA_ID,
        "generation_id": "RAC-PER-D2-0005",
        "status": "SYNTHETIC_REHEARSAL_SEALED",
        "created_utc": created_utc,
        "analysis_module": "ruthless_pipeline/certification/cluster_paired_arm_statistics.py",
        "parameters": {
            "z": Z,
            "bootstrap_seed": BOOTSTRAP_SEED,
            "bootstrap_resamples": BOOTSTRAP_RESAMPLES,
            "width_gate": WIDTH_GATE,
            "min_clusters": MIN_CLUSTERS,
        },
        "fixture_manifest_sha256": fixture_manifest_sha256,
        "winner_candidate_sha256": selection["winner_candidate_sha256"],
        "canonical_result_sha256": _sha256_bytes(canonical.encode()),
        "result": json.loads(canonical),
    })
    sealed["sealed_sha256"] = _sha256_bytes(_canonical(sealed))
    return sealed


# ---------------------------------------------------------------------------
# 5. Release object + verifier + promotion guard
# ---------------------------------------------------------------------------

def build_release(release_dir: Path, files: dict[str, bytes], *,
                  created_utc: str) -> dict:
    """Publication-style release object: MANIFEST.json + RELEASE.json.

    ``files`` maps relative names to bytes. The release is content-addressed
    (release_format.ReleaseManifest) and frozen via a ReleaseRevisionLog;
    RELEASE.json carries the content hash and the synthetic-only label.
    """
    release_dir = Path(release_dir)
    release_dir.mkdir(parents=True, exist_ok=True)
    for rel, blob in files.items():
        path = release_dir / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(blob)
    manifest = ReleaseManifest.build(release_dir, exclude=RELEASE_EXCLUDE)
    manifest.write(release_dir)
    revision_log = ReleaseRevisionLog(release_id=RELEASE_ID)
    for stage in ("candidate", "generation", "optimization_telemetry"):
        revision_log = revision_log.record(stage, created_utc, detail="synthetic rehearsal stage")
    revision_log = revision_log.freeze(
        created_utc, stage="optimization_telemetry", detail="synthetic rehearsal freeze"
    )
    release_payload = _label({
        "release_id": RELEASE_ID,
        "created_utc": created_utc,
        "status": "SYNTHETIC_REHEARSAL_RELEASE",
        "revision_log": json.loads(revision_log.to_json()),
        "content_hash": compute_content_hash(manifest),
        "note": (
            "Publication-style release object for pipeline validation ONLY; "
            "verify with verify_release(exclude=('MANIFEST.json','RELEASE.json')). "
            "Not a RAC-EXP research release; promotion to RAC-P1 is refused."
        ),
    })
    _write_json(release_dir / "RELEASE.json", release_payload)
    return release_payload


def verify_release_dir(release_dir: Path):
    """Re-hash the release directory against MANIFEST.json (fail closed)."""
    return verify_release(release_dir, exclude=RELEASE_EXCLUDE)


def promote_to_rac_p1(release_dir: Path) -> None:
    """Refuse to promote any synthetic rehearsal artifact to RAC-P1.

    Fail-closed: a release that fails verification, is missing its synthetic
    label, or carries ``rac_evidence_eligible = False`` is refused. This
    harness NEVER promotes; the function only ever raises.
    """
    release_dir = Path(release_dir)
    release_path = release_dir / "RELEASE.json"
    if not release_path.is_file():
        raise PromotionRefusedError(f"missing RELEASE.json in {release_dir}")
    payload = json.loads(release_path.read_text())
    require_schema_version(payload, SCHEMA_VERSION, label=str(release_path))
    result = verify_release_dir(release_dir)
    if not result.ok:
        raise PromotionRefusedError(
            "release verification failed "
            f"(tampered={result.tampered}, missing={result.missing}, extra={result.extra}); "
            "refusing RAC-P1 promotion"
        )
    if payload.get("evidence_class") == EVIDENCE_CLASS or payload.get("rac_evidence_eligible") is False:
        raise PromotionRefusedError(
            f"release {payload.get('release_id')!r} is labelled {EVIDENCE_CLASS!r} "
            "with rac_evidence_eligible=False; promotion to RAC-P1 is REFUSED"
        )
    raise PromotionRefusedError(
        "the D2-0005 rehearsal harness never promotes artifacts to RAC-P1"
    )


# ---------------------------------------------------------------------------
# 6. Manuscript export row (scratch path ONLY; manuscript/ never written)
# ---------------------------------------------------------------------------

def export_manuscript_rows(export_dir: Path, cluster_outcomes,
                           *, winner_candidate_sha256: str,
                           telemetry_sha256: str) -> dict:
    """Run the REAL manuscript exporter on rehearsal arms into a scratch path.

    Uses ruthless_pipeline.certification.manuscript_export.paper5_arm_rows /
    paper5_arms_csv with Paper5Arm inputs built from the synthetic paired
    outcomes. The CSV is written under ``export_dir`` (a scratch path labelled
    synthetic), NEVER under manuscript/exports/.
    """
    from .manuscript_export import Paper5Arm, paper5_arm_rows, paper5_arms_csv

    export_dir = Path(export_dir)
    if "manuscript" in export_dir.resolve().parts:
        raise ValueError(
            f"refusing to write rehearsal export under manuscript/: {export_dir}"
        )
    arm_m: dict[str, bool] = {}
    arm_c: dict[str, bool] = {}
    for cluster_id in sorted(cluster_outcomes):
        for unit in sorted(cluster_outcomes[cluster_id]):
            m, c = cluster_outcomes[cluster_id][unit]
            key = f"{cluster_id}|{unit}"
            arm_m[key] = bool(m)
            arm_c[key] = bool(c)
    arms = [
        Paper5Arm(
            arm_id="arm_m_surrogate_selection_synthetic",
            objective_name="cvar",
            objective_alpha=CVAR_ALPHA,
            winner_candidate_sha256=winner_candidate_sha256,
            heldout_outcomes=arm_m,
            telemetry_sha256=telemetry_sha256,
        ),
        Paper5Arm(
            arm_id="arm_c_control_synthetic",
            objective_name="cvar",
            objective_alpha=CVAR_ALPHA,
            winner_candidate_sha256=winner_candidate_sha256,
            heldout_outcomes=arm_c,
            telemetry_sha256=telemetry_sha256,
        ),
    ]
    rows = paper5_arm_rows(arms)
    csv_text = paper5_arms_csv(arms)
    export_dir.mkdir(parents=True, exist_ok=True)
    csv_path = export_dir / "paper5_arms_rehearsal_synthetic.csv"
    csv_path.write_text(csv_text)
    wrapper = _label({
        "schema_id": "d2-0005-rehearsal-manuscript-export",
        "note": (
            "Scratch manuscript-export row proving the exporter handles the "
            "rehearsal row. Written OUTSIDE manuscript/exports/; committed "
            "manuscript outputs are untouched."
        ),
        "rows": rows,
        "csv_path": csv_path.name,
        "csv_sha256": _sha256_bytes(csv_text.encode()),
    })
    wrapper_sha = _write_json(export_dir / "export-row.json", wrapper)
    return {"rows": rows, "csv_sha256": wrapper["csv_sha256"], "export_sha256": wrapper_sha}


# ---------------------------------------------------------------------------
# 7. Rehearsal ICC gate (A5.5): synthetic ICC probes above and below 0.25
# ---------------------------------------------------------------------------

def make_icc_probe_clusters(mode: str, *, k: int = MIN_CLUSTERS,
                            members: int = MEMBERS_PER_CLUSTER,
                            seed_key: str = "d20005-icc-probe"):
    """Synthetic cluster outcomes with ICC known by construction.

    ``mode="high"``: every member of a cluster shares one cluster-level delta
    sign (maximal clustering -> rho ~ 1, above the 0.25 gate).
    ``mode="low"``: member deltas are i.i.d. (no clustering -> rho ~ 0, below
    the gate). Deltas +/-1 are expressed as (arm_m, arm_c) discordant pairs.
    """
    if mode not in {"high", "low"}:
        raise ValueError(f"unknown probe mode {mode!r}")
    outcomes: dict[str, dict[str, tuple[bool, bool]]] = {}
    for c in range(k):
        cluster_id = f"probe-cluster-{c:03d}"
        cluster_sign = _unit_interval(f"{seed_key}|sign|{cluster_id}") < 0.5
        members_out: dict[str, tuple[bool, bool]] = {}
        for i in range(members):
            unit = f"probe-model|t{i:02d}"
            if mode == "high":
                positive = cluster_sign
            else:
                positive = _unit_interval(f"{seed_key}|{cluster_id}|{unit}") < 0.5
            members_out[unit] = (True, False) if positive else (False, True)
        outcomes[cluster_id] = members_out
    return outcomes


def realized_icc(cluster_outcomes):
    """Realized ICC via the pinned ANOVA rho-hat diagnostic (NA -> None)."""
    from .cluster_paired_arm_statistics import _validated_clusters

    rho, design_effect, n_eff = intracluster_diagnostics(
        _validated_clusters(cluster_outcomes)
    )
    return rho, design_effect, n_eff


def icc_gate_decision(rho, *, gate: float = ICC_GATE_MAX) -> dict:
    """A5.5 rehearsal gate: arm only if realized ICC <= 0.25 (NA blocks)."""
    passed = rho is not None and rho <= gate
    return _label({
        "schema_id": "d2-0005-rehearsal-icc",
        "gate": gate,
        "realized_icc": rho,
        "gate_passed": passed,
        "arming_effect": (
            "ICC <= 0.25 confirmed: gate would permit arming (rehearsal only; "
            "nothing is armed by this harness)"
            if passed else
            "ICC gate BLOCKS arming: realized ICC above 0.25 or NA; K must be "
            "raised by a further pre-arming amendment before arming"
        ),
    })


# ---------------------------------------------------------------------------
# 8. Rehearsal state machine: selection -> ... -> export, crash-safe
# ---------------------------------------------------------------------------

def _journal_load(journal_path: Path) -> dict:
    payload = json.loads(journal_path.read_text())
    require_schema_version(payload, SCHEMA_VERSION, label=str(journal_path))
    stages = payload["completed_stages"]
    if len(stages) != len(set(stages)):
        raise ValueError("journal lists a stage twice; refusing to double-emit")
    if stages != list(STAGES[: len(stages)]):
        raise ValueError("journal stage order violates the rehearsal state machine")
    return payload


def _journal_save(journal_path: Path, journal: dict) -> None:
    blob = _canonical(journal) + b"\n"
    tmp = journal_path.with_suffix(".tmp")
    tmp.write_bytes(blob)
    tmp.replace(journal_path)  # atomic: a crash never leaves a half journal


def run_rehearsal(
    output_dir: Path,
    *,
    k: int = MIN_CLUSTERS,
    created_utc: str = DEFAULT_CREATED_UTC,
    crash_after: str | None = None,
) -> dict:
    """Run BOTH rehearsal arms end to end under a crash-safe state machine.

    Stage order: fixture -> selection -> freeze -> analysis -> seal -> release
    -> export. A journal records completed stages with their artifact hashes;
    on rerun, completed stages are verified (hash mismatch fails closed) and
    skipped, so a mid-pipeline crash followed by recovery never double-emits
    and never promotes partial results. ``crash_after`` injects a deliberate
    :class:`RehearsalCrash` after the named stage (failure injection only).
    """
    if crash_after is not None and crash_after not in STAGES:
        raise ValueError(f"unknown crash stage {crash_after!r}")
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    journal_path = output_dir / "rehearsal_journal.json"
    if journal_path.exists():
        journal = _journal_load(journal_path)
    else:
        journal = _label({
            "schema_id": JOURNAL_SCHEMA_ID,
            "note": "Crash-safe rehearsal state journal; append-only, fail-closed on resume.",
            "completed_stages": [],
            "artifacts": {},
        })

    context: dict[str, Any] = {"output_dir": output_dir, "created_utc": created_utc, "k": k}

    def maybe_crash(stage: str) -> None:
        if crash_after == stage:
            raise RehearsalCrash(f"injected crash after stage {stage!r}")

    def complete(stage: str, artifacts: dict[str, str]) -> None:
        journal["artifacts"].setdefault(stage, {}).update(artifacts)
        journal["completed_stages"].append(stage)
        _journal_save(journal_path, journal)

    def resume_check(stage: str) -> bool:
        """True if the stage already completed with intact artifacts."""
        if stage not in journal["completed_stages"]:
            return False
        for rel, expected in journal["artifacts"][stage].items():
            path = output_dir / rel
            if not path.is_file() or _sha256_bytes(path.read_bytes()) != expected:
                raise ValueError(
                    f"stage {stage!r} artifact {rel!r} missing or hash-mismatched on "
                    "resume; failing closed rather than re-emitting over tampered state"
                )
        return True

    # --- stage: fixture ---
    if not resume_check("fixture"):
        fixture = build_synthetic_fixture(output_dir / "fixture_images", k=k)
        sha = _write_json(output_dir / "fixture-manifest.json", fixture)
        artifacts = {"fixture-manifest.json": sha}
        artifacts.update({
            f"fixture_images/{img['path']}": img["sha256"] for img in fixture["images"]
        })
        complete("fixture", artifacts)
    maybe_crash("fixture")

    # --- stage: selection (surrogate-selection arm) ---
    if not resume_check("selection"):
        selection = surrogate_selection_arm()
        sha = _write_json(output_dir / "selection-report.json", selection)
        complete("selection", {"selection-report.json": sha})
    maybe_crash("selection")

    selection = json.loads((output_dir / "selection-report.json").read_text())

    # --- stage: freeze (telemetry frozen and hashed before outcomes) ---
    if not resume_check("freeze"):
        frozen_telemetry = _label({
            "schema_id": "telemetry-contract",
            "generation_id": "RAC-PER-D2-0005",
            "arm": "heldout_confirmation",
            "note": (
                "Synthetic per-candidate telemetry frozen and hashed BEFORE mock "
                "held-out outcomes are drawn (append-only outcome discipline)."
            ),
            "winner_candidate_sha256": selection["winner_candidate_sha256"],
            "fixture_manifest_sha256": journal["artifacts"]["fixture"]["fixture-manifest.json"],
            "heldout_model_set_id": HELDOUT_MODEL_SET_ID,
            "heldout_access": "NONE — mock scores only; PERSON-HO-v3 referenced by identity/hash",
        })
        frozen_telemetry["frozen_sha256"] = _sha256_bytes(_canonical(frozen_telemetry))
        sha = _write_json(output_dir / "frozen-telemetry.json", frozen_telemetry)
        complete("freeze", {"frozen-telemetry.json": sha})
    maybe_crash("freeze")

    frozen_telemetry = json.loads((output_dir / "frozen-telemetry.json").read_text())

    # --- stage: analysis (held-out-confirmation arm, cluster-robust) ---
    if not resume_check("analysis"):
        cluster_outcomes = mock_heldout_cluster_outcomes(
            json.loads((output_dir / "fixture-manifest.json").read_text())
        )
        stats = run_cluster_analysis(cluster_outcomes)
        analysis_payload = _label({
            "schema_id": "d2-0005-rehearsal-analysis",
            "canonical_result_sha256": _sha256_bytes(to_canonical_json(stats).encode()),
            "decision": stats.decision,
            "clusters": stats.clusters,
            "observation_units": stats.observation_units,
            "intracluster_rho": stats.intracluster_rho,
        })
        outcomes_payload = _label({
            "schema_id": "d2-0005-rehearsal-outcomes",
            "cluster_outcomes": {
                cid: {u: [bool(m), bool(c)] for u, (m, c) in members.items()}
                for cid, members in cluster_outcomes.items()
            },
        })
        sha_a = _write_json(output_dir / "analysis.json", analysis_payload)
        sha_o = _write_json(output_dir / "cluster-outcomes.json", outcomes_payload)
        complete("analysis", {"analysis.json": sha_a, "cluster-outcomes.json": sha_o})
    maybe_crash("analysis")

    outcomes_payload = json.loads((output_dir / "cluster-outcomes.json").read_text())
    cluster_outcomes = {
        cid: {u: (bool(m), bool(c)) for u, (m, c) in members.items()}
        for cid, members in outcomes_payload["cluster_outcomes"].items()
    }
    stats = run_cluster_analysis(cluster_outcomes)

    # --- stage: seal ---
    if not resume_check("seal"):
        sealed = seal_evidence(
            stats,
            fixture_manifest_sha256=journal["artifacts"]["fixture"]["fixture-manifest.json"],
            selection=selection,
            created_utc=created_utc,
        )
        sha = _write_json(output_dir / "sealed-evidence.json", sealed)
        complete("seal", {"sealed-evidence.json": sha})
    maybe_crash("seal")

    # --- stage: release ---
    if not resume_check("release"):
        release_dir = output_dir / "release" / RELEASE_ID
        files = {
            name: (output_dir / name).read_bytes()
            for name in (
                "fixture-manifest.json",
                "selection-report.json",
                "frozen-telemetry.json",
                "analysis.json",
                "cluster-outcomes.json",
                "sealed-evidence.json",
            )
        }
        build_release(release_dir, files, created_utc=created_utc)
        result = verify_release_dir(release_dir)
        if not result.ok:
            raise ValueError(f"freshly built release failed verification: {result}")
        artifacts = {
            f"release/{RELEASE_ID}/{name}": _sha256_bytes((release_dir / name).read_bytes())
            for name in sorted(files) + ["MANIFEST.json", "RELEASE.json"]
        }
        complete("release", artifacts)
    maybe_crash("release")

    # --- stage: export (manuscript export row to scratch path only) ---
    if not resume_check("export"):
        export = export_manuscript_rows(
            output_dir / "export_synthetic",
            cluster_outcomes,
            winner_candidate_sha256=selection["winner_candidate_sha256"],
            telemetry_sha256=frozen_telemetry["frozen_sha256"],
        )
        artifacts = {
            "export_synthetic/paper5_arms_rehearsal_synthetic.csv": export["csv_sha256"],
            "export_synthetic/export-row.json": export["export_sha256"],
        }
        complete("export", artifacts)
    maybe_crash("export")

    result = verify_release_dir(output_dir / "release" / RELEASE_ID)
    summary = _label({
        "schema_id": "d2-0005-rehearsal-summary",
        "stages_completed": list(journal["completed_stages"]),
        "release_verified": result.ok,
        "decision": stats.decision,
        "intracluster_rho": stats.intracluster_rho,
        "artifact_hashes": {
            stage: dict(hashes) for stage, hashes in journal["artifacts"].items()
        },
    })
    summary["summary_sha256"] = _sha256_bytes(_canonical(summary))
    _write_json(output_dir / "rehearsal-summary.json", summary)
    return summary
