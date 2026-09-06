"""Deliverable 3 entrypoint. Core implementation lives in ruthless_pipeline.physics."""
import torch
from ruthless_pipeline import DifferentiablePhysicsConfig, DifferentiablePhysicsPipeline


def main():
    cfg = DifferentiablePhysicsConfig(grid_size=(12,12), image_resolution=(128,128), simulation_steps=8)
    pipe = DifferentiablePhysicsPipeline(cfg)
    texture = torch.rand(1,3,128,128,device=pipe.device,requires_grad=True)
    out = pipe.forward(texture)
    loss = out["renders"].mean(); loss.backward()
    assert texture.grad is not None and torch.isfinite(texture.grad).all()
    print(pipe.save("outputs/physics"))

if __name__ == "__main__":
    main()
