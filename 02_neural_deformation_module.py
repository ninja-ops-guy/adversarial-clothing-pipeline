"""Deliverable 2 entrypoint. Core implementation lives in ruthless_pipeline.deformation."""
import torch
from ruthless_pipeline import NeuralDeformationConfig, NeuralDeformationModule, synthetic_observation


def main():
    cfg = NeuralDeformationConfig(train_steps=30, field_resolution=(64,64))
    module = NeuralDeformationModule(cfg)
    module.fit(synthetic_observation(2000, seed=cfg.seed))
    texture = torch.rand(1,3,128,128,device=module.device)
    warped = module.apply_warp(texture)
    assert warped.shape == texture.shape
    print(module.save("outputs/deformation"))

if __name__ == "__main__":
    main()
