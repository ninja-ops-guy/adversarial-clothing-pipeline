import torch

from ruthless_pipeline import EnvironmentAdaptiveConfig
from ruthless_pipeline.candidate_optimizer import (
    CandidateGenerationConfig,
    DetectorDrivenCandidateOptimizer,
)


def test_detector_driven_candidate_optimizer_records_surrogate_boundary(tmp_path):
    cfg = CandidateGenerationConfig(
        candidate_id="RAC-CAP-TEST",
        environment_profile="warehouse_dark",
    )
    adaptive = EnvironmentAdaptiveConfig(
        num_iterations=2,
        eot_samples=1,
        max_palette_pixels=256,
        kmeans_iterations=3,
        seed=3,
    )
    optimizer = DetectorDrivenCandidateOptimizer(cfg, adaptive)
    seed = torch.rand((1, 3, 24, 24))
    env = [torch.rand((1, 3, 32, 32))]

    def surrogate(x):
        return {"sur-a": x.mean(), "sur-b": (x**2).mean()}

    artifact = optimizer.optimize(seed, env, surrogate, ["sur-a", "sur-b"])
    assert artifact.metadata["evidence_class"] == "candidate_generation_only"
    assert artifact.metadata["surrogate_model_ids"] == ["sur-a", "sur-b"]
    assert artifact.metadata["heldout_models_used"] == []
    png, meta = artifact.save(tmp_path)
    assert png.exists()
    assert meta.exists()


def test_duplicate_surrogate_ids_are_rejected():
    optimizer = DetectorDrivenCandidateOptimizer(
        adaptive=EnvironmentAdaptiveConfig(num_iterations=1, eot_samples=1)
    )
    seed = torch.rand((1, 3, 16, 16))
    env = [torch.rand((1, 3, 16, 16))]

    def surrogate(x):
        return {"sur-a": x.mean()}

    try:
        optimizer.optimize(seed, env, surrogate, ["sur-a", "sur-a"])
    except ValueError as exc:
        assert "duplicate surrogate_model_id" in str(exc)
    else:
        raise AssertionError("duplicate model ids must be rejected")
