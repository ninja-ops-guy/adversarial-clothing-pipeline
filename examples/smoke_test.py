import torch
from ruthless_pipeline import (
    BlackBoxNAPConfig, EnhancedBlackBoxNAP,
    CandidateGenerationConfig, DetectorDrivenCandidateOptimizer, EnvironmentAdaptiveConfig,
    NeuralDeformationConfig, NeuralDeformationModule, synthetic_observation,
    DifferentiablePhysicsConfig, DifferentiablePhysicsPipeline,
    BenchmarkConfig, CallableEvaluator, ComparativeBenchmark,
)

nap = EnhancedBlackBoxNAP(BlackBoxNAPConfig(target_size=(64,64),num_iterations=2,device="cpu"))
nap.optimize(lambda x:{"lab_proxy":x.mean()})
pattern=nap.texture.detach()

deform=NeuralDeformationModule(NeuralDeformationConfig(hidden_dim=48,num_layers=3,train_steps=5,batch_size=128,device="cpu"))
deform.fit(synthetic_observation(500),steps=5)
warped=deform.apply_warp(pattern)

physics=DifferentiablePhysicsPipeline(DifferentiablePhysicsConfig(grid_size=(8,8),simulation_steps=3,device="cpu"))
renders=physics.forward(warped,brightness_values=(1.0,))["renders"]

bench=ComparativeBenchmark(BenchmarkConfig(brightness=(1.0,),scales=(1.0,),blur_sigmas=(0.0,),device="cpu"), [CallableEvaluator("proxy",lambda x:x.mean((1,2,3)))])
print(bench.run(pattern,renders[:1]))


cap = DetectorDrivenCandidateOptimizer(
    CandidateGenerationConfig(candidate_id="RAC-SMOKE-CAP"),
    EnvironmentAdaptiveConfig(
        num_iterations=1,
        eot_samples=1,
        max_palette_pixels=256,
        kmeans_iterations=2,
        seed=9,
    ),
)
seed = torch.rand((1,3,32,32))
env = [torch.rand((1,3,32,32))]
artifact = cap.optimize(seed, env, lambda x: {"proxy": x.mean()}, ["proxy"])
assert artifact.metadata["heldout_models_used"] == []
