"""Shared data models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class EvalRecord:
    case_id: str
    passed: bool
    status: str
    error: str
    output: str
    model: str
    tags: List[str]
    latency_ms: Optional[float]
    cost_usd: Optional[float]
    expected: str
    actual: str
    raw: Dict[str, Any] = field(default_factory=dict)
    normalized_reason: str = ""
    fingerprint_text: str = ""
    fingerprint: int = 0
    failure_mode: str = ""
    missing_fields: List[str] = field(default_factory=list)
    latency_anomaly: bool = False
    cost_anomaly: bool = False


@dataclass
class Cluster:
    cluster_id: str
    failure_mode: str
    normalized_reason: str
    fingerprint: int
    size: int
    failure_rate: float
    examples: List[EvalRecord]
    models: Dict[str, int]
    tags: Dict[str, int]
    missing_fields: Dict[str, int]
    latency_anomalies: int
    cost_anomalies: int
    priority_score: float


@dataclass
class DatasetMetrics:
    total: int
    passed: int
    failed: int
    failure_rate: float
    latency_median: float
    cost_median: float
    latency_anomalies: int
    cost_anomalies: int


@dataclass
class AnalysisResult:
    metrics: DatasetMetrics
    clusters: List[Cluster]
    failed_records: List[EvalRecord]
    all_records: List[EvalRecord]
    grouped_by_model: Dict[str, Dict[str, float]]
    grouped_by_tag: Dict[str, Dict[str, float]]
    grouped_by_case: Dict[str, Dict[str, Any]]


@dataclass
class CompareResult:
    baseline_metrics: DatasetMetrics
    candidate_metrics: DatasetMetrics
    regressions: List[Dict[str, Any]]
    improvements: List[Dict[str, Any]]
    new_failure_modes: List[Dict[str, Any]]
    resolved_failure_modes: List[Dict[str, Any]]
    case_changes: List[Dict[str, Any]]
