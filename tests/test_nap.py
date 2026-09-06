import torch
from ruthless_pipeline import BlackBoxMode, BlackBoxNAPConfig, EnhancedBlackBoxNAP


def test_nap_shape_gradient_and_query_budget(tmp_path):
    cfg = BlackBoxNAPConfig(target_size=(64,64), num_iterations=3, black_box_mode=BlackBoxMode.QUERY_EFFICIENT, max_queries=4, query_interval=1, query_directions=1, prior_backend="procedural", aesthetic_backend="disabled", device="cpu")
    p = EnhancedBlackBoxNAP(cfg)
    def surrogate(x): return {"proxy": x.mean()}
    def query(x): return float(x.mean())
    hist = p.optimize(surrogate, query)
    assert p.texture.shape == (1,3,64,64)
    assert len(hist) == 3
    assert p.query_count <= 4
    path = p.save(tmp_path)
    assert path.exists()
