"""Report writers."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional
from xml.etree.ElementTree import Element, ElementTree, SubElement

from .models import AnalysisResult, CompareResult
from .utils import ensure_output_dir, format_percent


def write_cluster_reports(
    result: AnalysisResult,
    output_dir: str,
    formats: Iterable[str],
    source_uri: str = "eval-results",
) -> List[Path]:
    target = ensure_output_dir(output_dir)
    written: List[Path] = []
    normalized_formats = {item.strip().lower() for item in formats}
    if "brief" in normalized_formats:
        written.append(write_text(target / "brief.md", render_cluster_brief(result)))
    if "markdown" in normalized_formats:
        written.append(write_text(target / "summary.md", render_cluster_markdown(result)))
    if "json" in normalized_formats:
        payload = {
            "metrics": result.metrics.__dict__,
            "clusters": [cluster_to_dict(cluster) for cluster in result.clusters],
            "by_model": result.grouped_by_model,
            "by_tag": result.grouped_by_tag,
        }
        written.append(write_json(target / "clusters.json", payload))
    if "csv" in normalized_formats:
        written.append(write_clusters_csv(target / "clusters.csv", result))
    if "junit" in normalized_formats:
        written.append(write_junit(target / "junit.xml", result))
    if "sarif" in normalized_formats:
        written.append(write_json(target / "clusters.sarif", cluster_sarif_payload(result, source_uri=source_uri)))
    return written


def write_compare_reports(result: CompareResult, output_dir: str) -> List[Path]:
    target = ensure_output_dir(output_dir)
    written = [
        write_text(target / "compare.md", render_compare_markdown(result)),
        write_json(
            target / "compare.json",
            {
                "baseline_metrics": result.baseline_metrics.__dict__,
                "candidate_metrics": result.candidate_metrics.__dict__,
                "regressions": result.regressions,
                "improvements": result.improvements,
                "new_failure_modes": result.new_failure_modes,
                "resolved_failure_modes": result.resolved_failure_modes,
                "case_changes": result.case_changes,
            },
        ),
        write_compare_csv(target / "compare.csv", result),
    ]
    return written


def write_sample_reports(samples: List[Dict[str, Any]], output_dir: str) -> List[Path]:
    target = ensure_output_dir(output_dir)
    return [
        write_json(target / "samples.json", {"clusters": samples}),
        write_text(target / "samples.md", render_samples_markdown(samples)),
    ]


def write_check_report(result: AnalysisResult, output_dir: str, compare_result: Optional[CompareResult] = None) -> List[Path]:
    target = ensure_output_dir(output_dir)
    payload: Dict[str, Any] = {
        "metrics": result.metrics.__dict__,
        "clusters": [cluster_to_dict(cluster) for cluster in result.clusters],
    }
    if compare_result:
        payload["compare"] = {
            "regressions": compare_result.regressions,
            "new_failure_modes": compare_result.new_failure_modes,
            "case_changes": compare_result.case_changes,
        }
    return [
        write_text(target / "check.md", render_check_markdown(result, compare_result)),
        write_json(target / "check.json", payload),
    ]


def render_cluster_markdown(result: AnalysisResult) -> str:
    lines = [
        "# Eval Failure Summary",
        "",
        f"- Total records: {result.metrics.total}",
        f"- Failed records: {result.metrics.failed} ({format_percent(result.metrics.failure_rate)})",
        f"- Latency median: {result.metrics.latency_median:.2f} ms",
        f"- Cost median: ${result.metrics.cost_median:.4f}",
        f"- Latency anomalies: {result.metrics.latency_anomalies}",
        f"- Cost anomalies: {result.metrics.cost_anomalies}",
        "",
        "## Clusters",
    ]
    for cluster in result.clusters:
        lines.extend(
            [
                "",
                f"### {cluster.cluster_id}",
                f"- Failure mode: `{cluster.failure_mode}`",
                f"- Reason: {cluster.normalized_reason}",
                f"- Size: {cluster.size}",
                f"- Priority: {cluster.priority_score:.3f}",
                f"- Models: {', '.join(f'{key}={value}' for key, value in sorted(cluster.models.items())) or 'n/a'}",
                f"- Tags: {', '.join(f'{key}={value}' for key, value in sorted(cluster.tags.items())) or 'n/a'}",
            ]
        )
        for example in cluster.examples[:3]:
            lines.append(f"- Example `{example.case_id}`: {example.error or example.output[:120]}")
    return "\n".join(lines) + "\n"


def render_cluster_brief(result: AnalysisResult) -> str:
    decision = "FIX" if result.metrics.failed else "PASS"
    if result.metrics.latency_anomalies or result.metrics.cost_anomalies:
        decision = "INVESTIGATE" if decision == "PASS" else "FIX+INVESTIGATE"
    lines = [
        "# Eval Failure Triage Brief",
        "",
        f"Decision: {decision}",
        (
            "Scope: "
            f"{result.metrics.failed}/{result.metrics.total} failed "
            f"({format_percent(result.metrics.failure_rate)}), "
            f"{len(result.clusters)} clusters, "
            f"{result.metrics.latency_anomalies} latency anomalies, "
            f"{result.metrics.cost_anomalies} cost anomalies."
        ),
        "",
        "Top clusters:",
    ]
    for cluster in result.clusters[:5]:
        models = ", ".join(f"{key}={value}" for key, value in sorted(cluster.models.items())[:4]) or "n/a"
        tags = ", ".join(f"{key}={value}" for key, value in sorted(cluster.tags.items())[:4]) or "n/a"
        lines.append(
            f"- {cluster.cluster_id} `{cluster.failure_mode}`: "
            f"{cluster.size} cases, priority {cluster.priority_score:.3f}, models [{models}], tags [{tags}]"
        )
        lines.append(f"  Reason: {cluster.normalized_reason}")
        if cluster.missing_fields:
            missing = ", ".join(f"{key}={value}" for key, value in sorted(cluster.missing_fields.items())[:4])
            lines.append(f"  Missing fields: {missing}")
        sample = cluster.examples[0] if cluster.examples else None
        if sample:
            lines.append(f"  First sample: {sample.case_id}")
    if not result.clusters:
        lines.append("- No failure clusters detected.")
    lines.extend(["", "Agent handoff:"])
    if result.clusters:
        lines.append("- Fix the highest-priority cluster first, then rerun evals and compare against the baseline.")
        lines.append("- Export samples for top clusters with `eval-failure-clusterer sample ...` before editing prompts, retrieval, tools, or datasets.")
    else:
        lines.append("- No failure fix is required; continue monitoring latency and cost anomalies.")
    lines.append("")
    return "\n".join(lines)


def render_compare_markdown(result: CompareResult) -> str:
    lines = [
        "# Eval Comparison",
        "",
        f"- Baseline failures: {result.baseline_metrics.failed} ({format_percent(result.baseline_metrics.failure_rate)})",
        f"- Candidate failures: {result.candidate_metrics.failed} ({format_percent(result.candidate_metrics.failure_rate)})",
        "",
        "## Regressions",
    ]
    if result.regressions:
        for item in result.regressions:
            lines.append(f"- {item['failure_key']}: +{item['delta']} ({item['baseline_size']} -> {item['candidate_size']})")
    else:
        lines.append("- None")
    lines.append("")
    lines.append("## New Failure Modes")
    if result.new_failure_modes:
        for item in result.new_failure_modes:
            lines.append(f"- {item['failure_key']}: {item['candidate_size']}")
    else:
        lines.append("- None")
    return "\n".join(lines) + "\n"


def render_samples_markdown(samples: List[Dict[str, Any]]) -> str:
    lines = ["# Failure Samples", ""]
    for cluster in samples:
        lines.append(f"## {cluster['cluster_id']}")
        lines.append(f"- Reason: {cluster['normalized_reason']}")
        lines.append(f"- Priority: {cluster['priority_score']:.3f}")
        for case in cluster["sampled_cases"]:
            lines.append(f"- `{case['case_id']}` {case['model']} tags={','.join(case['tags'])}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def render_check_markdown(result: AnalysisResult, compare_result: Optional[CompareResult]) -> str:
    lines = [
        "# Eval Gate Check",
        "",
        f"- Failed records: {result.metrics.failed}",
        f"- Latency anomalies: {result.metrics.latency_anomalies}",
        f"- Cost anomalies: {result.metrics.cost_anomalies}",
    ]
    if compare_result:
        regressions = len(compare_result.regressions) + len(compare_result.new_failure_modes)
        lines.append(f"- Regression signals: {regressions}")
    return "\n".join(lines) + "\n"


def cluster_to_dict(cluster: Any) -> Dict[str, Any]:
    return {
        "cluster_id": cluster.cluster_id,
        "failure_mode": cluster.failure_mode,
        "normalized_reason": cluster.normalized_reason,
        "fingerprint": cluster.fingerprint,
        "size": cluster.size,
        "failure_rate": cluster.failure_rate,
        "models": cluster.models,
        "tags": cluster.tags,
        "missing_fields": cluster.missing_fields,
        "latency_anomalies": cluster.latency_anomalies,
        "cost_anomalies": cluster.cost_anomalies,
        "priority_score": cluster.priority_score,
        "examples": [
            {
                "case_id": item.case_id,
                "error": item.error,
                "model": item.model,
                "tags": item.tags,
                "latency_ms": item.latency_ms,
                "cost_usd": item.cost_usd,
            }
            for item in cluster.examples
        ],
    }


def cluster_sarif_payload(result: AnalysisResult, source_uri: str = "eval-results") -> Dict[str, Any]:
    rules = {
        "eval-failure-cluster": {
            "id": "eval-failure-cluster",
            "name": "Eval Failure Cluster",
            "shortDescription": {"text": "Clustered AI eval failures need triage."},
            "fullDescription": {"text": "One or more LLM eval cases failed with a shared normalized reason, failure mode, or anomaly signal."},
            "help": {"text": "Inspect sampled cases, fix the highest-priority cluster, and rerun evals before merging."},
            "defaultConfiguration": {"level": "warning"},
        }
    }
    results = []
    for cluster in result.clusters:
        message = (
            f"{cluster.cluster_id} {cluster.failure_mode}: {cluster.size} failures, "
            f"priority {cluster.priority_score:.3f}. {cluster.normalized_reason}"
        )
        locations = []
        for example in cluster.examples[:5]:
            locations.append(
                {
                    "physicalLocation": {
                        "artifactLocation": {"uri": source_uri},
                        "region": {"startLine": 1},
                    },
                    "logicalLocations": [{"fullyQualifiedName": example.case_id}],
                }
            )
        results.append(
            {
                "ruleId": "eval-failure-cluster",
                "level": "warning",
                "message": {"text": message},
                "locations": locations or [
                    {
                        "physicalLocation": {
                            "artifactLocation": {"uri": source_uri},
                            "region": {"startLine": 1},
                        }
                    }
                ],
                "properties": cluster_to_dict(cluster),
            }
        )
    return {
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "version": "2.1.0",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "eval-failure-clusterer",
                        "informationUri": "https://github.com/yanqr213/eval-failure-clusterer",
                        "rules": list(rules.values()),
                    }
                },
                "results": results,
                "properties": {
                    "total": result.metrics.total,
                    "failed": result.metrics.failed,
                    "failure_rate": result.metrics.failure_rate,
                    "cluster_count": len(result.clusters),
                },
            }
        ],
    }


def write_clusters_csv(path: Path, result: AnalysisResult) -> Path:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "cluster_id",
                "failure_mode",
                "normalized_reason",
                "size",
                "failure_rate",
                "priority_score",
                "models",
                "tags",
                "latency_anomalies",
                "cost_anomalies",
            ],
        )
        writer.writeheader()
        for cluster in result.clusters:
            writer.writerow(
                {
                    "cluster_id": cluster.cluster_id,
                    "failure_mode": cluster.failure_mode,
                    "normalized_reason": cluster.normalized_reason,
                    "size": cluster.size,
                    "failure_rate": f"{cluster.failure_rate:.6f}",
                    "priority_score": f"{cluster.priority_score:.6f}",
                    "models": json.dumps(cluster.models, ensure_ascii=False),
                    "tags": json.dumps(cluster.tags, ensure_ascii=False),
                    "latency_anomalies": cluster.latency_anomalies,
                    "cost_anomalies": cluster.cost_anomalies,
                }
            )
    return path


def write_compare_csv(path: Path, result: CompareResult) -> Path:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["kind", "failure_key", "baseline_size", "candidate_size", "delta"])
        writer.writeheader()
        for kind, items in [
            ("regression", result.regressions),
            ("improvement", result.improvements),
            ("new_failure_mode", result.new_failure_modes),
            ("resolved_failure_mode", result.resolved_failure_modes),
        ]:
            for item in items:
                writer.writerow({"kind": kind, **item})
    return path


def write_junit(path: Path, result: AnalysisResult) -> Path:
    testsuite = Element(
        "testsuite",
        attrib={
            "name": "eval-failure-clusterer",
            "tests": str(result.metrics.total),
            "failures": str(result.metrics.failed),
        },
    )
    for record in result.all_records:
        testcase = SubElement(testsuite, "testcase", attrib={"name": record.case_id, "classname": record.model})
        if not record.passed:
            failure = SubElement(testcase, "failure", attrib={"message": record.normalized_reason or record.error or "failed"})
            failure.text = record.error or record.output
        if record.latency_anomaly or record.cost_anomaly:
            system_out = SubElement(testcase, "system-out")
            system_out.text = f"latency_anomaly={record.latency_anomaly} cost_anomaly={record.cost_anomaly}"
    ElementTree(testsuite).write(path, encoding="utf-8", xml_declaration=True)
    return path


def write_json(path: Path, payload: Dict[str, Any]) -> Path:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def write_text(path: Path, content: str) -> Path:
    path.write_text(content, encoding="utf-8")
    return path
