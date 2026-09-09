"""Deformation tiers T0-T3 behind a common interface.

Common interface (class ``Tier``):

- ``name``: tier identifier.
- ``cost_estimate``: rough relative cost label (documented, not calibrated).
- ``apply(uv, texture, params) -> warped``: deterministic warp of an HxWx3
  float texture given an HxWx2 uv grid (normalized coords in [0, 1],
  row-major (y, x)) and tier-specific params.

Tiers:

- ``T0ExplicitWarp``: explicit affine (2x3) or projective (3x3) warp in
  pure numpy. Fully deterministic.
- ``T1NeuralDeformation``: adapter wrapping
  ``ruthless_pipeline.deformation.NeuralDeformationModule``. The import is
  LAZY (inside the method); if torch is unavailable a
  ``TierUnavailableError`` is raised. Never imports torch at module level.
- ``T2ClothPhysics``: adapter wrapping
  ``ruthless_pipeline.physics.NativeDifferentiableCloth``; same lazy-import /
  ``TierUnavailableError`` guard.
- ``T3EmpiricallyCalibrated``: SCAFFOLD_ONLY. Construction without measured
  calibration data raises ``CalibratedDataRequiredError`` (fail-closed).
  When measured data exists (future), it fits a correction field on top of a
  base tier.

``run_tier_benchmark(tiers, fixtures)`` produces an artifacts-compatible
dict per tier: cost (wall time), determinism (repeat-run bitwise equality),
fidelity (MSE/PSNR vs a reference warp on synthetic ground truth), and a
``predictive_value`` placeholder that is ALWAYS None with a note (requires a
physical detector loop — future work, never fabricated).
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

import numpy as np


class TierError(Exception):
    pass


class TierUnavailableError(TierError):
    """Raised when a tier's backing dependency (e.g. torch) is unavailable."""


class CalibratedDataRequiredError(TierError):
    """Raised when T3 is constructed without measured calibration data."""


def make_uv_grid(h: int, w: int) -> np.ndarray:
    """Normalized (y, x) uv grid in [0, 1], shape HxWx2."""
    ys, xs = np.meshgrid(
        np.linspace(0.0, 1.0, h), np.linspace(0.0, 1.0, w), indexing="ij"
    )
    return np.stack([ys, xs], axis=-1)


def bilinear_sample(texture: np.ndarray, uv: np.ndarray) -> np.ndarray:
    """Sample ``texture`` (HxWxC) at normalized uv coords (HxWx2, (y, x)).

    Out-of-range coords are clamped to the border. Pure numpy, deterministic.
    """
    tex = np.asarray(texture, dtype=np.float64)
    h, w = tex.shape[:2]
    y = np.clip(uv[..., 0], 0.0, 1.0) * (h - 1)
    x = np.clip(uv[..., 1], 0.0, 1.0) * (w - 1)
    y0 = np.floor(y).astype(int)
    x0 = np.floor(x).astype(int)
    y1 = np.minimum(y0 + 1, h - 1)
    x1 = np.minimum(x0 + 1, w - 1)
    wy = (y - y0)[..., None]
    wx = (x - x0)[..., None]
    c00 = tex[y0, x0]
    c01 = tex[y0, x1]
    c10 = tex[y1, x0]
    c11 = tex[y1, x1]
    return (
        c00 * (1 - wy) * (1 - wx)
        + c01 * (1 - wy) * wx
        + c10 * wy * (1 - wx)
        + c11 * wy * wx
    )


class Tier:
    """Common deformation tier interface."""

    name: str = "abstract"
    cost_estimate: str = "unknown"
    status: str = "OK"

    def apply(
        self, uv: np.ndarray, texture: np.ndarray, params: dict
    ) -> np.ndarray:
        raise NotImplementedError


class T0ExplicitWarp(Tier):
    """T0: explicit affine/projective warp (numpy only, deterministic).

    ``params`` carries either ``affine`` (2x3) or ``projective`` (3x3) —
    a matrix mapping OUTPUT normalized (x, y) coords to INPUT normalized
    coords (inverse-mapping convention, as required for resampling).
    """

    name = "T0_explicit_affine_projective"
    cost_estimate = "O(H*W) numpy resampling; cheapest tier"
    status = "OK"

    def apply(self, uv: np.ndarray, texture: np.ndarray, params: dict) -> np.ndarray:
        y = uv[..., 0]
        x = uv[..., 1]
        ones = np.ones_like(x)
        if "affine" in params:
            m = np.asarray(params["affine"], dtype=np.float64)
            if m.shape != (2, 3):
                raise TierError(f"affine must be 2x3, got {m.shape}")
            sx = m[0, 0] * x + m[0, 1] * y + m[0, 2]
            sy = m[1, 0] * x + m[1, 1] * y + m[1, 2]
        elif "projective" in params:
            m = np.asarray(params["projective"], dtype=np.float64)
            if m.shape != (3, 3):
                raise TierError(f"projective must be 3x3, got {m.shape}")
            sx = m[0, 0] * x + m[0, 1] * y + m[0, 2]
            sy = m[1, 0] * x + m[1, 1] * y + m[1, 2]
            den = m[2, 0] * x + m[2, 1] * y + m[2, 2]
            if np.any(np.abs(den) < 1e-12):
                raise TierError("projective warp has singular denominator")
            sx = sx / den
            sy = sy / den
        else:
            raise TierError("params must carry 'affine' (2x3) or 'projective' (3x3)")
        return bilinear_sample(texture, np.stack([sy, sx], axis=-1))


class T1NeuralDeformation(Tier):
    """T1: adapter wrapping deformation.NeuralDeformationModule (lazy torch).

    ``params`` may carry ``learned_weight`` and ``time_value``. If torch is
    unavailable, ``apply`` raises ``TierUnavailableError``; construction of
    the backing module is also lazy so importing this module never needs
    torch.
    """

    name = "T1_neural_deformation_field"
    cost_estimate = "MLP field fit + sample; GPU-recommended, torch required"
    status = "OK"

    def __init__(self, config: dict | None = None):
        self._config = config or {}
        self._module = None

    def _ensure_module(self):
        if self._module is not None:
            return self._module
        try:
            import torch  # noqa: F401
            from ruthless_pipeline.deformation import (
                NeuralDeformationConfig,
                NeuralDeformationModule,
                synthetic_observation,
            )
        except ImportError as exc:
            raise TierUnavailableError(
                f"T1 requires torch-backed deformation module: {exc}"
            ) from exc
        torch.manual_seed(0)  # deterministic tier interface: fixed init + fit
        cfg = NeuralDeformationConfig(**self._config)
        module = NeuralDeformationModule(cfg)
        module.fit(synthetic_observation(seed=0))
        torch.manual_seed(0)  # reset any RNG consumed by fit
        self._module = module
        return module

    def apply(self, uv: np.ndarray, texture: np.ndarray, params: dict) -> np.ndarray:
        module = self._ensure_module()
        import torch

        learned_weight = float((params or {}).get("learned_weight", 0.5))
        seed = int((params or {}).get("seed", 0))
        h, w = texture.shape[:2]
        # Deterministic: seeded generator for the fabric-prior sample; the
        # learned field is a fixed MLP evaluation.
        gen = torch.Generator(device="cpu").manual_seed(seed)
        with torch.no_grad():
            learned, _ = module.predict_field(1, h, w)
            prior = module.fabric_prior.sample_field(1, h, w, generator=gen)
            disp = (learned_weight * learned + (1.0 - learned_weight) * prior)[0]
            tex_t = torch.from_numpy(
                np.asarray(texture, dtype=np.float32)
            ).permute(2, 0, 1)[None]
            warped = module.apply_warp(tex_t, disp[None])
        return warped[0].permute(1, 2, 0).cpu().numpy().astype(np.float64)


class T2ClothPhysics(Tier):
    """T2: adapter wrapping physics.NativeDifferentiableCloth (lazy torch)."""

    name = "T2_native_differentiable_cloth"
    cost_estimate = "mass-spring rollout; most expensive tier, torch required"
    status = "OK"

    def __init__(self, config: dict | None = None):
        self._config = config or {}

    def apply(self, uv: np.ndarray, texture: np.ndarray, params: dict) -> np.ndarray:
        try:
            import torch
            from ruthless_pipeline.physics import (
                DifferentiablePhysicsConfig,
                NativeDifferentiableCloth,
            )
        except ImportError as exc:
            raise TierUnavailableError(
                f"T2 requires torch-backed cloth physics: {exc}"
            ) from exc
        steps = int((params or {}).get("steps", 5))
        h, w = texture.shape[:2]
        cfg = DifferentiablePhysicsConfig(grid_size=(h, w), **self._config)
        cloth = NativeDifferentiableCloth(cfg)
        with torch.no_grad():
            pos = cloth.rest.clone()
            vel = torch.zeros_like(pos)
            for _ in range(steps):
                f = cloth.forces(pos, vel)
                vel = vel + f * cfg.dt
                pos = torch.where(cloth.pinned[:, None], cloth.rest, pos + vel * cfg.dt)
            disp_xy = (pos - cloth.rest)[:, :2].reshape(h, w, 2).cpu().numpy()
        warped_uv = uv + disp_xy[..., ::-1]  # (x, y) -> (y, x) channel order
        return bilinear_sample(np.asarray(texture, dtype=np.float64), warped_uv)


class T3EmpiricallyCalibrated(Tier):
    """T3: empirically calibrated correction tier — SCAFFOLD ONLY.

    Construction without measured calibration data raises
    ``CalibratedDataRequiredError`` (fail-closed): there is currently no
    measured print/capture data (UA-3/UA-4 gate), so this tier cannot exist
    yet. When measured data is supplied (future work), it fits an additive
    uv-correction field on top of a base tier.
    """

    name = "T3_empirically_calibrated"
    cost_estimate = "base tier + fitted correction field; requires measured data"
    status = "SCAFFOLD_ONLY"

    def __init__(self, measured_calibration: dict | None = None, base_tier: Tier | None = None):
        if not measured_calibration:
            raise CalibratedDataRequiredError(
                "T3 requires measured calibration data (status SCAFFOLD_ONLY); "
                "no measured captures exist yet (UA-3/UA-4 gate)"
            )
        self.measured_calibration = measured_calibration
        self.base_tier = base_tier or T0ExplicitWarp()
        # Future: fit correction field from measured_calibration here.
        self.correction_uv = np.asarray(
            measured_calibration.get("correction_uv_field", 0.0), dtype=np.float64
        )

    def apply(self, uv: np.ndarray, texture: np.ndarray, params: dict) -> np.ndarray:
        corrected_uv = np.clip(uv + self.correction_uv, 0.0, 1.0)
        return self.base_tier.apply(corrected_uv, texture, params)


def reference_warp(uv: np.ndarray, texture: np.ndarray, affine: np.ndarray) -> np.ndarray:
    """Deterministic ground-truth warp used as benchmark reference."""
    return T0ExplicitWarp().apply(uv, texture, {"affine": np.asarray(affine)})


def run_tier_benchmark(
    tiers: list[Tier],
    fixtures: list[dict],
) -> dict:
    """Cross-tier benchmark over synthetic fixtures.

    Each fixture: ``{"uv": HxWx2, "texture": HxWx3, "params": {...},
    "reference": HxWx3}`` (reference from ``reference_warp``).

    Returns an artifacts-compatible dict::

        {
          "benchmark": "deformation_tiers",
          "evidence_class": "synthetic_pipeline_validation_only",
          "tiers": {name: {
              "status": "OK"|"UNAVAILABLE"|"ERROR",
              "cost_seconds_mean": float|None,
              "determinism_bitwise_equal": bool|None,
              "fidelity_mse_vs_reference": float|None,
              "fidelity_psnr_vs_reference": float|None,
              "predictive_value": None,
              "predictive_value_note": str,
          }},
        }

    ``predictive_value`` is ALWAYS None: predicting physical detector
    observations requires a detector + measured captures (future work) and
    is never fabricated.
    """
    note = (
        "requires physical detector loop + measured captures; future work, "
        "never fabricated"
    )
    out = {
        "benchmark": "deformation_tiers",
        "evidence_class": "synthetic_pipeline_validation_only",
        "tiers": {},
    }
    for tier in tiers:
        entry = {
            "status": "OK",
            "cost_seconds_mean": None,
            "determinism_bitwise_equal": None,
            "fidelity_mse_vs_reference": None,
            "fidelity_psnr_vs_reference": None,
            "predictive_value": None,
            "predictive_value_note": note,
        }
        try:
            times = []
            mses = []
            deterministic = True
            for fx in fixtures:
                t0 = time.perf_counter()
                warped1 = tier.apply(fx["uv"], fx["texture"], fx["params"])
                times.append(time.perf_counter() - t0)
                warped2 = tier.apply(fx["uv"], fx["texture"], fx["params"])
                if not np.array_equal(
                    np.ascontiguousarray(warped1), np.ascontiguousarray(warped2)
                ):
                    deterministic = False
                ref = fx.get("reference")
                if ref is not None:
                    mse = float(np.mean((warped1 - np.asarray(ref)) ** 2))
                    mses.append(mse)
            entry["cost_seconds_mean"] = float(np.mean(times))
            entry["determinism_bitwise_equal"] = deterministic
            if mses:
                mse = float(np.mean(mses))
                entry["fidelity_mse_vs_reference"] = mse
                entry["fidelity_psnr_vs_reference"] = (
                    float("inf") if mse == 0 else float(10.0 * np.log10(1.0 / mse))
                )
        except TierUnavailableError as exc:
            entry["status"] = "UNAVAILABLE"
            entry["error"] = str(exc)
        except Exception as exc:  # noqa: BLE001 - report, don't crash harness
            entry["status"] = "ERROR"
            entry["error"] = f"{type(exc).__name__}: {exc}"
        out["tiers"][tier.name] = entry
    return out
