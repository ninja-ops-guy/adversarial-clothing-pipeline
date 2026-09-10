"""Public package-surface checks for certified Governance Pass 6."""
from __future__ import annotations

import ruthless_pipeline.governance as governance


PUBLIC_PASS6_NAMES = (
    "PopulationIdentity",
    "ExactProjectedPopulationBackend",
    "ExternalSamplerReply",
    "ProjectedSamplerAdapter",
    "CalibrationMetrics",
    "EmpiricalLaneModel",
    "build_sampling_manifest",
    "exact_distribution_diagnostics",
    "repeated_seed_instability",
    "select_backend_empirical",
)


def test_certified_pass6_surface_is_available_from_governance_namespace():
    for name in PUBLIC_PASS6_NAMES:
        assert hasattr(governance, name), name
        assert name in governance.__all__
