"""Deliverable 4 entrypoint. Core implementation lives in ruthless_pipeline.benchmark."""
import torch
from ruthless_pipeline import BenchmarkConfig, CallableEvaluator, ComparativeBenchmark


def main():
    def luminance_score(x):
        return x.mean(dim=(1,2,3))
    evals = [CallableEvaluator("lab_proxy_a", luminance_score), CallableEvaluator("lab_proxy_b", lambda x: x.std(dim=(1,2,3)))]
    cfg = BenchmarkConfig(surrogate_models=("lab_proxy_a",), heldout_models=("lab_proxy_b",), brightness=(1.0,), scales=(1.0,), blur_sigmas=(0.0,))
    bench = ComparativeBenchmark(cfg, evals)
    baseline = torch.full((1,3,64,64),0.7)
    candidate = torch.full((1,3,64,64),0.4)
    print(bench.run(baseline,candidate))
    print(bench.save("outputs/benchmark"))

if __name__ == "__main__":
    main()
