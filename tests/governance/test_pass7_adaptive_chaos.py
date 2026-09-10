from __future__ import annotations
import pytest
from ruthless_pipeline.governance.adaptive import AdaptiveGovernanceError, EvidenceSeal, propose_next_wave_policy, require_policy_frozen_before_sampling
from ruthless_pipeline.governance.chaos import ChaosArchive, ChaosGovernanceError, ChaosStatus
from ruthless_pipeline.governance.bridge_overlap import BridgeGovernanceError, RegimeDecision, require_pooling_legal


def seal(state="SEALED"):
    return EvidenceSeal("WAVE-N","RAC-SEAL-001","a"*64,state)

def test_unsealed_prior_wave_cannot_drive_policy():
    with pytest.raises(AdaptiveGovernanceError, match="unsealed"):
        propose_next_wave_policy(prior=seal("RUNNING"), target_wave_id="WAVE-N+1", policy={"lane":"stratified"})

def test_current_wave_outcomes_cannot_tune_policy():
    with pytest.raises(AdaptiveGovernanceError, match="current-wave"):
        propose_next_wave_policy(prior=seal(), target_wave_id="WAVE-N+1", policy={"lane":"stratified"}, current_wave_outcomes={"score":1})

def test_policy_is_frozen_before_sampling():
    p=propose_next_wave_policy(prior=seal(), target_wave_id="WAVE-N+1", policy={"lane":"stratified"})
    require_policy_frozen_before_sampling(p,"WAVE-N+1")
    with pytest.raises(AdaptiveGovernanceError): require_policy_frozen_before_sampling(p,"WAVE-X")

def test_regime_reset_forbids_default_pooling():
    with pytest.raises(BridgeGovernanceError, match="pooling forbidden"):
        require_pooling_legal(RegimeDecision.REGIME_RESET)

def test_chaos_failures_remain_visible_after_rescreen_and_promotion():
    a=ChaosArchive(); a.add_failure("C-1","SIM_GEOMETRY_ONLY")
    a.rescreen("C-1",admissible=True,reason_code="CAPABILITY_CHANGED")
    a.promote_to_hypothesis("C-1",physically_admissible=True)
    assert a.candidates["C-1"].original_status is ChaosStatus.FAILED
    assert a.yield_report()=={"archived":1,"original_failures":1,"rescreens":1,"promotions":1}

def test_rescreen_does_not_rewrite_original_failure():
    a=ChaosArchive(); a.add_failure("C-2","PRINTABILITY")
    event=a.rescreen("C-2",admissible=False,reason_code="NEW_ENCODER")
    assert event.new_status is ChaosStatus.SIMULATION_ONLY
    assert a.candidates["C-2"].original_status is ChaosStatus.FAILED

def test_physical_admissibility_gate_blocks_promotion():
    a=ChaosArchive(); a.add_failure("C-3","SIMULATION_ONLY")
    a.rescreen("C-3",admissible=True,reason_code="NEW_CAPABILITY")
    with pytest.raises(ChaosGovernanceError, match="physical-admissibility"):
        a.promote_to_hypothesis("C-3",physically_admissible=False)
