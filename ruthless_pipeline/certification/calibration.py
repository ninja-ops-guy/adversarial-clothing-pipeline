from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PrintCalibration:
    profile_id: str
    printer: str
    ink_set: str
    textile_profile: str
    icc_profile_sha256: str
    measured_patch_set_sha256: str
    max_delta_e: float
    measured_delta_e: float

    def validate(self) -> None:
        for value in (self.icc_profile_sha256, self.measured_patch_set_sha256):
            if len(value) != 64:
                raise ValueError("calibration artifact hashes must be SHA-256 digests")
        if self.measured_delta_e > self.max_delta_e:
            raise ValueError("print calibration is outside allowed color tolerance")


@dataclass(frozen=True)
class TextileProfile:
    profile_id: str
    fabric: str
    construction: str
    basis_weight_gsm: float
    stretch_warp_pct: float
    stretch_weft_pct: float
    color_profile_id: str
