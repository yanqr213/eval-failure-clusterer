"""Core analysis pipeline."""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any, Dict, List

from .fingerprint import simhash
from .models import AnalysisResult, Cluster, DatasetMetrics, EvalRecord
from .normalize import normalize_failure
from .utils import clamp, format_decimal, median_or_zero, percentage, similarity_from_distance, slugify


def analyze_records(records: List[EvalRecord], config: Dict[str, Any]) -> AnalysisResult:
    latency_median = median_or_zero([record.latency_ms for record in records])
    cost_median = median_or_zero([record.cost_usd for record in records])

    for record in records:
        record.latency_anomaly = bool(
            record.latency_ms is not None
            and latency_median > 0
            and record.latency_ms > latency_median * float(config["latency_anomaly_multiplier"])
        )
        record.cost_anomaly = bool(
            record.cost_usd is not None
            and cost_median > 0
            and record.cost_usd > cost_median * float(config["cost_anomaly_multiplier"])
        )

    failed_records = [normalize_failure(record) for record in records if not record.passed]
    for record in failed_records:
        record.fingerprint = simhash(record.fingerprint_text)

    clusters = cluster_failures(failed_records, len(records), config)
    metrics = DatasetMetrics(
        total=len(records),
        passed=sum(1 for record in records if record.passed),
        failed=len(failed_records),
        failure_rate=percentage(len(failed_records), len(records)),
        latency_median=latency_median,
        cost_median=cost_median,
        latency_anomalies=sum(1 for record in records if record.latency_anomaly),
        cost_anomalies=sum(1 for record in records if record.cost_anomaly),
    )
    return AnalysisResult(
        metrics=metrics,
        clusters=clusters,
        failed_records=failed_records,
        all_records=records,
        grouped_by_model=summarize_by_model(records),
        grouped_by_tag=summarize_by_tag(records),
        grouped_by_case=summarize_by_case(records),
    )


def cluster_failures(failed_records: List[EvalRecord], total_records: int, config: Dict[str, Any]) -> List[Cluster]:
    threshold = float(config["min_text_similarity"])
    grouped: List[List[EvalRecord]] = []
    for record in failed_records:
        placed = False
        for bucket in grouped:
            head = bucket[0]
            similarity = similarity_from_distance(record.fingerprint, head.fingerprint)
            if record.failure_mode == head.failure_mode and similarity >= threshold:
                bucket.append(record)
                placed = True
                break
        if not placed:
            grouped.append([record])

    clusters: List[Cluster] = []
    for index, bucket in enumerate(
        sorted(grouped, key=lambda items: (-len(items), items[0].failure_mode, items[0].case_id)),
        start=1,
    ):
        models = Counter(record.model for record in bucket)
        tags = Counter(tag for record in bucket for tag in record.tags)
        missing_fields = Counter(field for record in bucket for field in record.missing_fields)
        latency_anomalies = sum(1 for record in bucket if record.latency_anomaly)
        cost_anomalies = sum(1 for record in bucket if record.cost_anomaly)
        cluster = Cluster(
            cluster_id=f"cluster-{index:03d}-{slugify(bucket[0].failure_mode)}",
            failure_mode=bucket[0].failure_mode,
            normalized_reason=bucket[0].normalized_reason,
            fingerprint=bucket[0].fingerprint,
            size=len(bucket),
            failure_rate=percentage(len(bucket), total_records),
            examples=bucket,
            models=dict(models),
            tags=dict(tags),
            missing_fields=dict(missing_fields),
            latency_anomalies=latency_anomalies,
            cost_anomalies=cost_anomalies,
            priority_score=0.0,
        )
        cluster.priority_score = compute_priority(cluster, total_records, config)
        clusters.append(cluster)

    clusters.sort(key=lambda item: (-item.priority_score, -item.size, item.cluster_id))
    return clusters


def compute_priority(cluster: Cluster, total_records: int, config: Dict[str, Any]) -> float:
    weights = config["priority_weights"]
    failure_count_score = percentage(cluster.size, max(1, total_records))
    recurrence_score = clamp((cluster.size - 1) / 5.0)
    latency_score = percentage(cluster.latency_anomalies, max(1, cluster.size))
    cost_score = percentage(cluster.cost_anomalies, max(1, cluster.size))
    score = (
        float(weights["failure_count"]) * failure_count_score
        + float(weights["failure_rate"]) * cluster.failure_rate
        + float(weights["recurrence"]) * recurrence_score
        + float(weights["latency_anomaly"]) * latency_score
        + float(weights["cost_anomaly"]) * cost_score
    )
    return round(score, 6)


def summarize_by_model(records: List[EvalRecord]) -> Dict[str, Dict[str, float]]:
    grouped: Dict[str, List[EvalRecord]] = defaultdict(list)
    for record in records:
        grouped[record.model].append(record)
    summary: Dict[str, Dict[str, float]] = {}
    for model, items in grouped.items():
        failed = sum(1 for item in items if not item.passed)
        summary[model] = {
            "total": float(len(items)),
            "failed": float(failed),
            "failure_rate": percentage(failed, len(items)),
        }
    return summary


def summarize_by_tag(records: List[EvalRecord]) -> Dict[str, Dict[str, float]]:
    grouped: Dict[str, List[EvalRecord]] = defaultdict(list)
    for record in records:
        tags = record.tags or ["untagged"]
        for tag in tags:
            grouped[tag].append(record)
    summary: Dict[str, Dict[str, float]] = {}
    for tag, items in grouped.items():
        failed = sum(1 for item in items if not item.passed)
        summary[tag] = {
            "total": float(len(items)),
            "failed": float(failed),
            "failure_rate": percentage(failed, len(items)),
        }
    return summary


def summarize_by_case(records: List[EvalRecord]) -> Dict[str, Dict[str, Any]]:
    summary: Dict[str, Dict[str, Any]] = {}
    for record in records:
        summary[record.case_id] = {
            "passed": record.passed,
            "model": record.model,
            "tags": record.tags,
            "latency_ms": record.latency_ms,
            "cost_usd": record.cost_usd,
            "latency_anomaly": record.latency_anomaly,
            "cost_anomaly": record.cost_anomaly,
        }
        if not record.passed:
            summary[record.case_id]["failure_mode"] = record.failure_mode
            summary[record.case_id]["normalized_reason"] = record.normalized_reason
    return summary


def cluster_snapshot(clusters: List[Cluster]) -> Dict[str, Dict[str, Any]]:
    snapshot: Dict[str, Dict[str, Any]] = {}
    for cluster in clusters:
        key = f"{cluster.failure_mode}:{cluster.normalized_reason}"
        snapshot[key] = {
            "cluster_id": cluster.cluster_id,
            "size": cluster.size,
            "priority_score": format_decimal(cluster.priority_score),
        }
    return snapshot
