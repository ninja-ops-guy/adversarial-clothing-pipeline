from pathlib import Path


def test_adaptive_selector_is_explicitly_surrogate_only():
    text = Path("scripts/adapt_surrogate_shortlist.py").read_text()
    assert 'roles={"surrogate"}' in text
    assert '"heldout_models_loaded": []' in text
    assert '"heldout_feedback_used": False' in text
    assert "fresh held-out generation" in text


def test_adaptive_selector_uses_reference_fidelity_as_design_tiebreak():
    text = Path("scripts/adapt_surrogate_shortlist.py").read_text()
    assert "reference_fidelity_score" in text
    assert "candidate_detection_rate" in text
    assert "candidate_mean" in text
