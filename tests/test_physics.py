import torch
from ruthless_pipeline import DifferentiablePhysicsConfig, DifferentiablePhysicsPipeline


def test_physics_has_texture_gradients(tmp_path):
    cfg = DifferentiablePhysicsConfig(grid_size=(8,8),simulation_steps=4,device="cpu")
    p = DifferentiablePhysicsPipeline(cfg)
    x = torch.rand(1,3,64,64,requires_grad=True)
    out = p.forward(x, brightness_values=(1.0,))
    assert out["renders"].shape == x.shape
    out["renders"].mean().backward()
    assert x.grad is not None
    assert torch.isfinite(x.grad).all()
    assert p.save(tmp_path).exists()
