"""Reviewed baseline helpers for accepted eval failure clusters."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Set

from . import __version__
from .models import AnalysisResult, Cluster


def cluster_key(cluster: Cluster) -> str:
    """Return the stable reviewed-baseline key for a cluster."""

    return f"{cluster.failure_mode}:{cluster.normalized_reason}:{cluster.fingerprint}"


def load_reviewed_baseline(path: str) -> Set[str]:
    """Load accepted cluster keys from a reviewed baseline JSON file."""

    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(data, list):
        entries = data
    elif isinstance(data, dict):
        entries = data.get("clusters", [])
    else:
        raise ValueError("reviewed baseline must be a JSON object or list")
    keys: Set[str] = set()
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        key = entry.get("cluster_key")
        if isinstance(key, str) and key:
            keys.add(key)
    return keys


def split_reviewed_clusters(result: AnalysisResult, reviewed_keys: Iterable[str]) -> Dict[str, List[Cluster]]:
    """Split clusters into open and reviewed groups without mutating the analysis result."""

    accepted = set(reviewed_keys)
    suppressed: List[Cluster] = []
    open_clusters: List[Cluster] = []
    for cluster in result.clusters:
        if cluster_key(cluster) in accepted:
            suppressed.append(cluster)
        else:
            open_clusters.append(cluster)
    return {"open": open_clusters, "suppressed": suppressed}


def render_reviewed_baseline(result: AnalysisResult) -> str:
    """Render a reviewed baseline JSON document for the current failure clusters."""

    payload = {
        "schema_version": 1,
        "generated_by": "eval-failure-clusterer",
        "tool_version": __version__,
        "description": "Reviewed eval failure clusters. Review before committing; CI can use this file to fail only on new or unreviewed clusters.",
        "cluster_count": len(result.clusters),
        "failed_record_count": result.metrics.failed,
        "clusters": [_cluster_baseline_entry(cluster) for cluster in result.clusters],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def _cluster_baseline_entry(cluster: Cluster) -> Dict[str, Any]:
    return {
        "cluster_key": cluster_key(cluster),
        "cluster_id": cluster.cluster_id,
        "failure_mode": cluster.failure_mode,
        "normalized_reason": cluster.normalized_reason,
        "fingerprint": cluster.fingerprint,
        "size": cluster.size,
        "priority_score": cluster.priority_score,
        "models": dict(cluster.models),
        "tags": dict(cluster.tags),
        "examples": [
            {
                "case_id": item.case_id,
                "model": item.model,
                "tags": list(item.tags),
                "error": item.error,
            }
            for item in cluster.examples[:5]
        ],
        "review": {
            "status": "reviewed",
            "owner": "",
            "reason": "",
            "expires": "",
        },
    }
