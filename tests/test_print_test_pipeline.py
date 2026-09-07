from ruthless_pipeline.physical_protocol import capture_rows


def test_capture_matrix_contains_108_unique_matched_pairs() -> None:
    rows = capture_rows()
    assert len(rows) == 108
    assert len({row["trial_id"] for row in rows}) == 108
    assert {row["distance_m"] for row in rows} == {2.0, 5.0, 8.0}
    assert {row["yaw_deg"] for row in rows} == {-30.0, 0.0, 30.0}
    assert {row["pitch_deg"] for row in rows} == {0.0}
    assert {row["pose"] for row in rows} == {"standing", "walking"}
    assert {row["lighting_id"] for row in rows} == {"indoor-even", "daylight-even"}
    assert {row["repeat"] for row in rows} == {1, 2, 3}
    assert {row["wash_state"] for row in rows} == {"W0"}


def test_capture_matrix_has_matched_control_and_candidate_names() -> None:
    for row in capture_rows():
        assert row["control_file"].endswith(f"{row['trial_id']}__control.jpg")
        assert row["candidate_file"].endswith(f"{row['trial_id']}__candidate.jpg")
        assert row["control_file"] != row["candidate_file"]
