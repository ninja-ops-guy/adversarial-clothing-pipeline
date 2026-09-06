from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ModelManifest:
    model_id: str
    architecture: str
    weights_id: str
    weights_sha256: str
    framework: str
    framework_version: str
    preprocessing: dict[str, Any]
    target_class: str
    class_label: int
    decision_threshold: float
    nms_threshold: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        if not self.model_id:
            raise ValueError("model_id is required")
        if len(self.weights_sha256) != 64:
            raise ValueError(f"{self.model_id}: weights_sha256 must be a SHA-256 digest")
        if not 0 <= self.decision_threshold <= 1:
            raise ValueError(f"{self.model_id}: decision_threshold must be within [0,1]")


class ModelRegistry:
    def __init__(self, manifests: list[ModelManifest]):
        self._items = {m.model_id: m for m in manifests}
        if len(self._items) != len(manifests):
            raise ValueError("duplicate model_id")
        for manifest in manifests:
            manifest.validate()

    def require(self, model_ids: list[str] | tuple[str, ...]) -> list[ModelManifest]:
        missing = [model_id for model_id in model_ids if model_id not in self._items]
        if missing:
            raise KeyError(f"missing model manifests: {missing}")
        return [self._items[model_id] for model_id in model_ids]

    @classmethod
    def from_directory(cls, directory: str | Path) -> "ModelRegistry":
        items: list[ModelManifest] = []
        for path in sorted(Path(directory).glob("*.json")):
            payload = json.loads(path.read_text())
            items.append(ModelManifest(**payload))
        return cls(items)
