"""Deliverable 1 entrypoint. Core implementation lives in ruthless_pipeline.nap."""
import torch
from ruthless_pipeline import BlackBoxMode, BlackBoxNAPConfig, EnhancedBlackBoxNAP


def main():
    cfg = BlackBoxNAPConfig(target_size=(128,128), num_iterations=8, black_box_mode=BlackBoxMode.PURE_TRANSFER)
    pipe = EnhancedBlackBoxNAP(cfg)
    def surrogate(x):
        # Differentiable CI smoke evaluator only; replace with authorized lab model adapters.
        return {"contrast_proxy": x.var(dim=(1,2,3)).mean()}
    pipe.optimize(surrogate)
    out = pipe.save("outputs/nap")
    print(out)

if __name__ == "__main__":
    main()
