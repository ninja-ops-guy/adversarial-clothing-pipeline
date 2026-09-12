from __future__ import annotations

from collections import defaultdict
from typing import Any, Iterable

PredictionKey = tuple[str, str, str]


def prediction_key(record: dict[str, Any]) -> PredictionKey:
    return (str(record["condition_id"]), str(record["evaluator_id"]), str(record["endpoint_id"]))


def group_digital_observations(records: Iterable[dict[str, Any]]) -> dict[PredictionKey, list[dict[str, Any]]]:
    """Group valid digital observations without deriving post-unblinding predictions."""
    grouped: dict[PredictionKey, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        if record.get("valid", True):
            grouped[prediction_key(record)].append(dict(record))
    return dict(grouped)
