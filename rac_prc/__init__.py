"""Prospective Robustness Characterization (PRC) v1.

This package is an additive, read-only scientific observer. It does not mutate
P1 authority, candidate lineage, or physical evidence.
"""

from .canonical import RACCanonicalSerializer

__all__ = ["RACCanonicalSerializer"]
