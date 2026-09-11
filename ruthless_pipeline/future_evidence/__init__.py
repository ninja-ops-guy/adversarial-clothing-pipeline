"""Future-evidence infrastructure lane (SW-12..SW-15).

Additive infrastructure for FUTURE measured physical data. Everything here
operates on explicitly-labeled synthetic fixtures only; no artifact produced
by this package can be promoted to measured physical evidence.
"""
from ruthless_pipeline.future_evidence import (  # noqa: F401
    benchmark,
    discrepancy,
    errors,
    physical_dataset,
    temporal,
)
