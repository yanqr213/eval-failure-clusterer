"""Baseline comparison helpers."""

from __future__ import annotations

from typing import Any, Dict, List

from .analyzer import cluster_snapshot
from .models import AnalysisResult, CompareResult


def compare_analysis(baseline: AnalysisResult, candidate: AnalysisResult) -> CompareResult:
    baseline_snapshot = cluster_snapshot(baseline.clusters)
    candidate_snapshot = cluster_snapshot(candidate.clusters)

    regressions: List[Dict[str, Any]] = []
    improvements: List[Dict[str, Any]] = []
    new_failure_modes: List[Dict[str, Any]] = []
    resolved_failure_modes: List[Dict[str, Any]] = []

    for key, value in candidate_snapshot.items():
        baseline_size = int(baseline_snapshot.get(key, {}).get("size", 0))
        delta = int(value["size"]) - baseline_size
        item = {"failure_key": key, "candidate_size": int(value["size"]), "baseline_size": baseline_size, "delta": delta}
        if key not in baseline_snapshot:
            new_failure_modes.append(item)
        elif delta > 0:
            regressions.append(item)
        elif delta < 0:
            improvements.append(item)

    for key, value in baseline_snapshot.items():
        if key not in candidate_snapshot:
            resolved_failure_modes.append(
                {"failure_key": key, "candidate_size": 0, "baseline_size": int(value["size"]), "delta": -int(value["size"])}
            )

    case_changes = compare_cases(baseline, candidate)
    regressions.sort(key=lambda item: (-item["delta"], item["failure_key"]))
    improvements.sort(key=lambda item: (item["delta"], item["failure_key"]))
    new_failure_modes.sort(key=lambda item: (-item["candidate_size"], item["failure_key"]))
    resolved_failure_modes.sort(key=lambda item: (-item["baseline_size"], item["failure_key"]))
    return CompareResult(
        baseline_metrics=baseline.metrics,
        candidate_metrics=candidate.metrics,
        regressions=regressions,
        improvements=improvements,
        new_failure_modes=new_failure_modes,
        resolved_failure_modes=resolved_failure_modes,
        case_changes=case_changes,
    )


def compare_cases(baseline: AnalysisResult, candidate: AnalysisResult) -> List[Dict[str, Any]]:
    changes: List[Dict[str, Any]] = []
    baseline_cases = baseline.grouped_by_case
    candidate_cases = candidate.grouped_by_case
    keys = sorted(set(baseline_cases) | set(candidate_cases))
    for case_id in keys:
        base = baseline_cases.get(case_id)
        cand = candidate_cases.get(case_id)
        if base is None:
            changes.append({"case_id": case_id, "change": "new_case", "candidate_passed": cand["passed"]})
            continue
        if cand is None:
            changes.append({"case_id": case_id, "change": "removed_case", "baseline_passed": base["passed"]})
            continue
        if base["passed"] != cand["passed"]:
            if base["passed"] and not cand["passed"]:
                change = "regressed"
            else:
                change = "improved"
            changes.append(
                {
                    "case_id": case_id,
                    "change": change,
                    "baseline_passed": base["passed"],
                    "candidate_passed": cand["passed"],
                    "candidate_failure_mode": cand.get("failure_mode"),
                }
            )
    return changes
