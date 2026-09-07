import torch

from ruthless_pipeline import EnvironmentAdaptiveConfig
from ruthless_pipeline.candidate_optimizer import (
    CandidateGenerationConfig,
    DetectorDrivenCandidateOptimizer,
)


# CI-safe demonstration. Replace this proxy with the owned/authorized surrogate
# ensemble adapter used by your experiment runner.
def surrogate_ensemble(x: torch.Tensor):
    return {
        "surrogate_texture_mean": x.mean(),
        "surrogate_texture_energy": (x**2).mean(),
    }


seed = torch.rand((1, 3, 64, 64))
environment = [torch.rand((1, 3, 96, 96))]

optimizer = DetectorDrivenCandidateOptimizer(
    CandidateGenerationConfig(
        candidate_id="RAC-CAP-DEMO",
        environment_profile="demo_environment",
    ),
    EnvironmentAdaptiveConfig(
        num_iterations=4,
        eot_samples=2,
        max_palette_pixels=2048,
        seed=118,
    ),
)

artifact = optimizer.optimize(
    seed,
    environment,
    surrogate_ensemble,
    ["surrogate_texture_mean", "surrogate_texture_energy"],
)
artifact.save("artifacts/capgen-demo")
