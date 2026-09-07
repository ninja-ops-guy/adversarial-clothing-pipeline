import torch

from ruthless_pipeline.capgen import (
    EnvironmentAdaptiveConfig,
    EnvironmentAdaptivePatchGenerator,
    extract_base_colors,
    initialize_pattern_logits,
    render_palette_patch,
)


def test_palette_extraction_is_deterministic_and_sorted():
    env = torch.zeros((1, 3, 32, 32))
    env[:, :, :16] = torch.tensor([0.1, 0.2, 0.3]).view(1, 3, 1, 1)
    env[:, :, 16:] = torch.tensor([0.8, 0.7, 0.6]).view(1, 3, 1, 1)
    a = extract_base_colors([env], num_colors=2, seed=7)
    b = extract_base_colors([env], num_colors=2, seed=7)
    assert torch.allclose(a, b)
    lum = 0.2126 * a[:, 0] + 0.7152 * a[:, 1] + 0.0722 * a[:, 2]
    assert torch.all(lum[:-1] <= lum[1:])


def test_pattern_logits_can_be_recolored_without_changing_allocation():
    seed = torch.linspace(0, 1, 64).view(1, 1, 8, 8).repeat(1, 3, 1, 1)
    logits = initialize_pattern_logits(seed, 3)
    palette_a = torch.tensor([[0.05, 0.05, 0.05], [0.4, 0.4, 0.4], [0.9, 0.9, 0.9]])
    palette_b = torch.tensor([[0.0, 0.2, 0.6], [0.7, 0.1, 0.2], [0.95, 0.9, 0.1]])
    a = render_palette_patch(logits, palette_a)
    b = render_palette_patch(logits, palette_b)
    assert a.shape == b.shape == seed.shape
    assert not torch.allclose(a, b)
    assert torch.equal(logits.argmax(dim=1), logits.argmax(dim=1))


def test_environment_adaptive_optimizer_uses_only_supplied_surrogate():
    seed = torch.rand((1, 3, 32, 32))
    env = [torch.rand((1, 3, 48, 48))]
    calls = {"count": 0}

    def surrogate(x):
        calls["count"] += 1
        return {"surrogate_a": x.mean(), "surrogate_b": (x**2).mean()}

    cfg = EnvironmentAdaptiveConfig(
        num_base_colors=3,
        num_iterations=3,
        eot_samples=2,
        max_palette_pixels=1024,
        kmeans_iterations=5,
        seed=11,
    )
    gen = EnvironmentAdaptivePatchGenerator(cfg)
    result = gen.optimize(seed, env, surrogate)

    assert result.patch.shape == seed.shape
    assert result.logits.shape == (1, 3, 32, 32)
    assert result.base_colors.shape == (3, 3)
    assert len(result.history) == 3
    assert calls["count"] == 6
    assert torch.isfinite(result.patch).all()
    assert result.patch.min() >= 0
    assert result.patch.max() <= 1


def test_fast_recolor_preserves_pattern_logits():
    seed = torch.rand((1, 3, 24, 24))
    logits = initialize_pattern_logits(seed, 3)
    env_a = [torch.zeros((1, 3, 32, 32)) + torch.tensor([0.1, 0.2, 0.3]).view(1, 3, 1, 1)]
    env_b = [torch.zeros((1, 3, 32, 32)) + torch.tensor([0.8, 0.6, 0.2]).view(1, 3, 1, 1)]
    gen = EnvironmentAdaptivePatchGenerator(EnvironmentAdaptiveConfig(num_base_colors=3, max_palette_pixels=256))
    patch_a, colors_a = gen.recolor(logits, env_a)
    patch_b, colors_b = gen.recolor(logits, env_b)
    assert patch_a.shape == patch_b.shape
    assert not torch.allclose(colors_a, colors_b)
