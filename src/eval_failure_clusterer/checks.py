"""CI gate evaluation."""

from __future__ import annotations

from typing import List, Optional, Sequence

from .models import AnalysisResult, Cluster, CompareResult


def collect_check_issues(
    result: AnalysisResult,
    compare_result: Optional[CompareResult] = None,
    *,
    open_clusters: Optional[Sequence[Cluster]] = None,
) -> List[str]:
    issues: List[str] = []
    clusters = list(result.clusters if open_clusters is None else open_clusters)
    open_failed = sum(cluster.size for cluster in clusters)
    if open_failed:
        if open_clusters is None:
            issues.append(f"{open_failed} failed records detected")
        else:
            issues.append(f"{open_failed} unreviewed failed records detected across {len(clusters)} clusters")
    if result.metrics.latency_anomalies:
        issues.append(f"{result.metrics.latency_anomalies} latency anomalies detected")
    if result.metrics.cost_anomalies:
        issues.append(f"{result.metrics.cost_anomalies} cost anomalies detected")
    if compare_result:
        if compare_result.regressions:
            issues.append(f"{len(compare_result.regressions)} regressed failure clusters")
        if compare_result.new_failure_modes:
            issues.append(f"{len(compare_result.new_failure_modes)} new failure modes")
        regressed_cases = [item for item in compare_result.case_changes if item["change"] == "regressed"]
        if regressed_cases:
            issues.append(f"{len(regressed_cases)} cases regressed against baseline")
    return issues
