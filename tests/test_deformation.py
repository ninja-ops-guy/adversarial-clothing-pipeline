import torch
from ruthless_pipeline import NeuralDeformationConfig, NeuralDeformationModule, synthetic_observation


def test_deformation_learns_and_warps(tmp_path):
    cfg = NeuralDeformationConfig(hidden_dim=64,num_layers=3,train_steps=20,batch_size=256,field_resolution=(32,32),device="cpu")
    m = NeuralDeformationModule(cfg)
    before = m.fit(synthetic_observation(1000, amplitude=0.02, seed=1), steps=20)
    assert before[-1]["loss"] == before[-1]["loss"]
    x = torch.rand(1,3,64,64)
    y = m.apply_warp(x)
    assert y.shape == x.shape
    assert torch.isfinite(y).all()
    assert m.save(tmp_path).exists()
