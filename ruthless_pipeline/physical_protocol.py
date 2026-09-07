from __future__ import annotations


def capture_rows() -> list[dict]:
    """Return the preregistered RAC W0 matched physical capture matrix."""
    rows: list[dict] = []
    for distance in (2, 5, 8):
        for yaw in (0, 30, -30):
            for pose in ("standing", "walking"):
                for lighting in ("indoor-even", "daylight-even"):
                    condition = (
                        f"D{distance:02d}_Y{yaw:+03d}_P0_"
                        f"{pose.upper()}_{lighting.upper().replace('-', '_')}"
                    )
                    for repeat in (1, 2, 3):
                        trial_id = f"{condition}__R{repeat}"
                        rows.append(
                            {
                                "trial_id": trial_id,
                                "condition_id": condition,
                                "repeat": repeat,
                                "distance_m": float(distance),
                                "yaw_deg": float(yaw),
                                "pitch_deg": 0.0,
                                "pose": pose,
                                "lighting_id": lighting,
                                "wash_state": "W0",
                                "control_file": f"captures/{trial_id}__control.jpg",
                                "candidate_file": f"captures/{trial_id}__candidate.jpg",
                            }
                        )
    return rows
