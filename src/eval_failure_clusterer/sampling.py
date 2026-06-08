"""Sampling helpers for representative failure exports."""

from __future__ import annotations

import random
from typing import Any, Dict, List

from .models import AnalysisResult, Cluster


def export_samples(result: AnalysisResult, max_per_cluster: int = 3, seed: int = 7) -> List[Dict[str, Any]]:
    generator = random.Random(seed)
    exported: List[Dict[str, Any]] = []
    for cluster in result.clusters:
        items = list(cluster.examples)
        items.sort(key=lambda record: record.case_id)
        if len(items) > max_per_cluster:
            items = sorted(generator.sample(items, max_per_cluster), key=lambda record: record.case_id)
        exported.append(_cluster_sample(cluster, items))
    return exported


def _cluster_sample(cluster: Cluster, items: List[Any]) -> Dict[str, Any]:
    return {
        "cluster_id": cluster.cluster_id,
        "failure_mode": cluster.failure_mode,
        "normalized_reason": cluster.normalized_reason,
        "priority_score": cluster.priority_score,
        "sampled_cases": [
            {
                "case_id": item.case_id,
                "model": item.model,
                "tags": item.tags,
                "error": item.error,
                "output": item.output,
                "latency_ms": item.latency_ms,
                "cost_usd": item.cost_usd,
            }
            for item in items
        ],
    }
