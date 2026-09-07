from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import asdict, dataclass, field

_PROFILE_ID_RE = re.compile(r"^RAC-PCP-[A-Za-z0-9._-]+-[0-9]+$")


def delta_e_2000(
    lab1: tuple[float, float, float],
    lab2: tuple[float, float, float],
    kL: float = 1.0,
    kC: float = 1.0,
    kH: float = 1.0,
) -> float:
    """CIEDE2000 color difference (CIE 142-2001 / Sharma et al. formulation)."""
    L1, a1, b1 = lab1
    L2, a2, b2 = lab2

    C1 = math.hypot(a1, b1)
    C2 = math.hypot(a2, b2)
    C_bar = (C1 + C2) / 2.0
    C_bar7 = C_bar**7
    G = 0.5 * (1.0 - math.sqrt(C_bar7 / (C_bar7 + 25.0**7))) if C_bar > 0 else 0.0

    a1p = (1.0 + G) * a1
    a2p = (1.0 + G) * a2
    C1p = math.hypot(a1p, b1)
    C2p = math.hypot(a2p, b2)

    def hp(ap: float, b: float) -> float:
        if ap == 0.0 and b == 0.0:
            return 0.0
        h = math.degrees(math.atan2(b, ap))
        return h + 360.0 if h < 0.0 else h

    h1p = hp(a1p, b1)
    h2p = hp(a2p, b2)

    dLp = L2 - L1
    dCp = C2p - C1p
    if C1p * C2p == 0.0:
        dhp = 0.0
    else:
        dhp = h2p - h1p
        if dhp > 180.0:
            dhp -= 360.0
        elif dhp < -180.0:
            dhp += 360.0
    dHp = 2.0 * math.sqrt(C1p * C2p) * math.sin(math.radians(dhp) / 2.0)

    Lp_bar = (L1 + L2) / 2.0
    Cp_bar = (C1p + C2p) / 2.0
    if C1p * C2p == 0.0:
        hp_bar = h1p + h2p
    else:
        dh = abs(h1p - h2p)
        if dh <= 180.0:
            hp_bar = (h1p + h2p) / 2.0
        elif h1p + h2p < 360.0:
            hp_bar = (h1p + h2p + 360.0) / 2.0
        else:
            hp_bar = (h1p + h2p - 360.0) / 2.0

    T = (
        1.0
        - 0.17 * math.cos(math.radians(hp_bar - 30.0))
        + 0.24 * math.cos(math.radians(2.0 * hp_bar))
        + 0.32 * math.cos(math.radians(3.0 * hp_bar + 6.0))
        - 0.20 * math.cos(math.radians(4.0 * hp_bar - 63.0))
    )
    dtheta = 30.0 * math.exp(-(((hp_bar - 275.0) / 25.0) ** 2))
    R_C = 2.0 * math.sqrt(Cp_bar**7 / (Cp_bar**7 + 25.0**7)) if Cp_bar > 0 else 0.0
    S_L = 1.0 + (0.015 * (Lp_bar - 50.0) ** 2) / math.sqrt(20.0 + (Lp_bar - 50.0) ** 2)
    S_C = 1.0 + 0.045 * Cp_bar
    S_H = 1.0 + 0.015 * Cp_bar * T
    R_T = -math.sin(math.radians(2.0 * dtheta)) * R_C

    return math.sqrt(
        (dLp / (kL * S_L)) ** 2
        + (dCp / (kC * S_C)) ** 2
        + (dHp / (kH * S_H)) ** 2
        + R_T * (dCp / (kC * S_C)) * (dHp / (kH * S_H))
    )


def _require_finite(values: tuple[float, ...] | list[float], label: str) -> None:
    if not values or any(not math.isfinite(v) for v in values):
        raise ValueError(f"{label} must contain only finite values")


@dataclass(frozen=True)
class PatchMeasurement:
    patch_id: str
    reference_lab: tuple[float, float, float]
    measured_lab: tuple[float, float, float]

    def delta_e_2000(self) -> float:
        return delta_e_2000(self.reference_lab, self.measured_lab)

    def validate(self) -> None:
        if not self.patch_id:
            raise ValueError("patch_id is required")
        for lab, label in (
            (self.reference_lab, "reference_lab"),
            (self.measured_lab, "measured_lab"),
        ):
            if len(lab) != 3:
                raise ValueError(f"{label} must be a (L, a, b) triple")
            _require_finite(list(lab), label)
            L, a, b = lab
            if not 0.0 <= L <= 100.0:
                raise ValueError(f"{label} L* must be in [0, 100]")
            if not -200.0 <= a <= 200.0 or not -200.0 <= b <= 200.0:
                raise ValueError(f"{label} a*/b* out of sane range")


@dataclass(frozen=True)
class ScaleMeasurement:
    ruler_id: str
    nominal_cm: float
    measured_px: float
    distance_m: float

    @property
    def px_per_cm(self) -> float:
        return self.measured_px / self.nominal_cm

    def validate(self) -> None:
        if not self.ruler_id:
            raise ValueError("ruler_id is required")
        _require_finite([self.nominal_cm, self.measured_px, self.distance_m], "scale fields")
        if self.nominal_cm <= 0.0:
            raise ValueError("nominal_cm must be positive")
        if self.measured_px <= 0.0:
            raise ValueError("measured_px must be positive")
        if self.distance_m <= 0.0:
            raise ValueError("distance_m must be positive")


@dataclass(frozen=True)
class ResolutionMeasurement:
    lp_mm_steps: list[tuple[float, float]]

    def cutoff(self, contrast_threshold: float = 0.20) -> float:
        separable = [
            lp_mm
            for lp_mm, contrast in self.lp_mm_steps
            if contrast >= contrast_threshold
        ]
        return max(separable) if separable else 0.0

    def validate(self) -> None:
        if not self.lp_mm_steps:
            raise ValueError("lp_mm_steps must be non-empty")
        for lp_mm, contrast in self.lp_mm_steps:
            _require_finite([lp_mm, contrast], "lp_mm_steps entry")
            if lp_mm <= 0.0:
                raise ValueError("lp/mm step must be positive")
            if not 0.0 <= contrast <= 1.0:
                raise ValueError("Michelson contrast must be in [0, 1]")


@dataclass(frozen=True)
class RegistrationMeasurement:
    mark_id: str
    nominal_xy_mm: tuple[float, float]
    measured_xy_mm: tuple[float, float]

    @property
    def error_mm(self) -> float:
        return math.hypot(
            self.measured_xy_mm[0] - self.nominal_xy_mm[0],
            self.measured_xy_mm[1] - self.nominal_xy_mm[1],
        )

    def validate(self) -> None:
        if not self.mark_id:
            raise ValueError("mark_id is required")
        for xy, label in (
            (self.nominal_xy_mm, "nominal_xy_mm"),
            (self.measured_xy_mm, "measured_xy_mm"),
        ):
            if len(xy) != 2:
                raise ValueError(f"{label} must be an (x, y) pair")
            _require_finite(list(xy), label)


@dataclass(frozen=True)
class PrintCameraProfile:
    profile_id: str
    camera_id: str
    lighting_id: str
    created_utc: str
    patches: list[PatchMeasurement] = field(default_factory=list)
    scales: list[ScaleMeasurement] = field(default_factory=list)
    resolutions: list[ResolutionMeasurement] = field(default_factory=list)
    registrations: list[RegistrationMeasurement] = field(default_factory=list)

    def summary(self) -> dict:
        self.validate()
        delta_es = [p.delta_e_2000() for p in self.patches]
        nominal_px_per_cm = sum(s.px_per_cm for s in self.scales) / len(self.scales) if self.scales else None
        scale_error_pct: dict[str, float] = {}
        for s in self.scales:
            if nominal_px_per_cm:
                scale_error_pct[f"{s.ruler_id}@{s.distance_m}m"] = (
                    (s.px_per_cm - nominal_px_per_cm) / nominal_px_per_cm * 100.0
                )
        return {
            "profile_id": self.profile_id,
            "camera_id": self.camera_id,
            "lighting_id": self.lighting_id,
            "n_patches": len(self.patches),
            "mean_delta_e": sum(delta_es) / len(delta_es),
            "max_delta_e": max(delta_es),
            "scale_error_pct": scale_error_pct,
            "resolution_cutoff_lp_mm": [
                r.cutoff() for r in self.resolutions
            ],
            "max_registration_error_mm": max(
                (r.error_mm for r in self.registrations), default=0.0
            ),
        }

    def validate(self) -> None:
        if not _PROFILE_ID_RE.match(self.profile_id):
            raise ValueError("profile_id must match RAC-PCP-<version>-<seq>")
        if not self.camera_id or not self.lighting_id:
            raise ValueError("camera_id and lighting_id are required")
        if not self.created_utc:
            raise ValueError("created_utc is required")
        if not self.patches:
            raise ValueError("patches must be non-empty")
        for item in (*self.patches, *self.scales, *self.resolutions, *self.registrations):
            item.validate()

    def to_profile_json(self) -> str:
        return json.dumps(asdict(self), sort_keys=True, indent=2)

    def profile_sha256(self) -> str:
        return hashlib.sha256(self.to_profile_json().encode("utf-8")).hexdigest()

    def acceptance(
        self,
        max_delta_e: float = 6.0,
        max_scale_error_pct: float = 2.0,
        max_registration_mm: float = 3.0,
    ) -> tuple[bool, list[str]]:
        summary = self.summary()
        failures: list[str] = []
        if summary["mean_delta_e"] > max_delta_e:
            failures.append(
                f"mean_delta_e {summary['mean_delta_e']:.3f} exceeds {max_delta_e}"
            )
        for label, pct in summary["scale_error_pct"].items():
            if abs(pct) > max_scale_error_pct:
                failures.append(
                    f"scale error {label} {pct:.3f}% exceeds {max_scale_error_pct}%"
                )
        if summary["max_registration_error_mm"] > max_registration_mm:
            failures.append(
                f"max registration error {summary['max_registration_error_mm']:.3f} mm "
                f"exceeds {max_registration_mm} mm"
            )
        return (not failures, failures)
