from __future__ import annotations

import json
import logging
import os
import random
import tempfile
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any, Mapping

import numpy as np
import torch


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s"))
        logger.addHandler(handler)
    logger.setLevel(os.getenv("RUTHLESS_LOG_LEVEL", "INFO").upper())
    return logger


def seed_everything(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def resolve_device(device: str | None = None) -> torch.device:
    if device is None or device == "auto":
        return torch.device("cuda" if torch.cuda.is_available() else "cpu")
    requested = torch.device(device)
    if requested.type == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA was requested but is not available")
    return requested


def ensure_dir(path: str | Path) -> Path:
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def atomic_json_dump(path: str | Path, payload: Mapping[str, Any]) -> None:
    path = Path(path)
    ensure_dir(path.parent)
    serializable = _to_jsonable(payload)
    with tempfile.NamedTemporaryFile("w", dir=path.parent, suffix=".tmp", delete=False) as tmp:
        json.dump(serializable, tmp, indent=2, sort_keys=True)
        tmp.flush()
        os.fsync(tmp.fileno())
        tmp_name = tmp.name
    os.replace(tmp_name, path)


def _to_jsonable(value: Any) -> Any:
    if is_dataclass(value):
        return _to_jsonable(asdict(value))
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, torch.device):
        return str(value)
    if isinstance(value, torch.Tensor):
        if value.numel() == 1:
            return value.detach().cpu().item()
        return value.detach().cpu().tolist()
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, Mapping):
        return {str(k): _to_jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_jsonable(v) for v in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def validate_image_tensor(x: torch.Tensor, channels: int = 3) -> None:
    if x.ndim != 4:
        raise ValueError(f"Expected BCHW tensor, got shape {tuple(x.shape)}")
    if x.shape[1] != channels:
        raise ValueError(f"Expected {channels} channels, got {x.shape[1]}")
    if not torch.isfinite(x).all():
        raise ValueError("Image tensor contains NaN or Inf")


def image_tensor_to_uint8(x: torch.Tensor) -> np.ndarray:
    validate_image_tensor(x)
    img = x.detach().clamp(0, 1).cpu()[0].permute(1, 2, 0).numpy()
    return (img * 255.0 + 0.5).astype(np.uint8)
