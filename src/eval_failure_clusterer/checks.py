"""CI gate evaluation."""

from __future__ import annotations

from typing import List, Optional

from .models import AnalysisResult, CompareResult


def collect_check_issues(result: AnalysisResult, compare_result: Optional[CompareResult] = None) -> List[str]:
    issues: List[str] = []
    if result.metrics.failed:
        issues.append(f"{result.metrics.failed} failed records detected")
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
