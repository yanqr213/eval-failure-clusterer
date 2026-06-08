"""Configuration management for eval failure clustering."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, Optional


DEFAULT_CONFIG: Dict[str, Any] = {
    "fields": {
        "id": ["id", "case_id", "test_name"],
        "status": ["status", "passed", "success", "score"],
        "error": ["error", "failure_reason", "assertion_message"],
        "output": ["output", "model_output", "response"],
        "model": ["model"],
        "tags": ["tags"],
        "latency_ms": ["latency_ms", "latency", "duration_ms"],
        "cost_usd": ["cost_usd", "cost"],
        "expected": ["expected"],
        "actual": ["actual"],
    },
    "tag_delimiters": [";", ","],
    "pass_values": ["pass", "passed", "true", "success", "ok"],
    "fail_values": ["fail", "failed", "false", "error"],
    "latency_anomaly_multiplier": 1.8,
    "cost_anomaly_multiplier": 1.8,
    "min_text_similarity": 0.52,
    "priority_weights": {
        "failure_count": 0.45,
        "failure_rate": 0.20,
        "recurrence": 0.15,
        "latency_anomaly": 0.10,
        "cost_anomaly": 0.10,
    },
}


def deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    merged = deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def load_config(path: Optional[str] = None) -> Dict[str, Any]:
    config = deepcopy(DEFAULT_CONFIG)
    if not path:
        return config
    loaded = json.loads(Path(path).read_text(encoding="utf-8"))
    return deep_merge(config, loaded)


def dump_default_config(path: str) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(DEFAULT_CONFIG, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return target
