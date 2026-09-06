import torch
from ruthless_pipeline import BenchmarkConfig, CallableEvaluator, ComparativeBenchmark


def test_benchmark_heldout_and_save(tmp_path):
    evals = [CallableEvaluator("s", lambda x:x.mean((1,2,3))), CallableEvaluator("h",lambda x:x.mean((1,2,3)))]
    cfg = BenchmarkConfig(surrogate_models=("s",),heldout_models=("h",),brightness=(1.0,),scales=(1.0,),blur_sigmas=(0.0,),device="cpu")
    b = ComparativeBenchmark(cfg,evals)
    summary=b.run(torch.ones(1,3,32,32)*0.8,torch.ones(1,3,32,32)*0.2)
    assert summary["heldout"]["candidate_mean"] < summary["heldout"]["baseline_mean"]
    a,j=b.save(tmp_path)
    assert a.exists() and j.exists()
