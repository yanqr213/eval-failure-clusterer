"""Command line interface."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import List, Optional

from .analyzer import analyze_records
from . import __version__
from .checks import collect_check_issues
from .compare import compare_analysis
from .config import dump_default_config, load_config
from .parser import load_records
from .reports import write_check_report, write_cluster_reports, write_compare_reports, write_sample_reports
from .sampling import export_samples


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="eval-failure-clusterer", description="Offline AI eval failure clustering CLI")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    cluster_parser = subparsers.add_parser("cluster", help="Cluster eval failures and write reports")
    cluster_parser.add_argument("input", help="Path to JSONL or CSV eval results")
    cluster_parser.add_argument("--config", help="Optional config JSON path")
    cluster_parser.add_argument("--output", default="outputs/cluster", help="Directory for generated reports")
    cluster_parser.add_argument(
        "--format",
        default="markdown,json,csv,junit",
        help="Comma-separated output formats: markdown,json,csv,junit",
    )
    cluster_parser.set_defaults(func=run_cluster)

    sample_parser = subparsers.add_parser("sample", help="Sample cases from failure clusters")
    sample_parser.add_argument("input", help="Path to JSONL or CSV eval results")
    sample_parser.add_argument("--config", help="Optional config JSON path")
    sample_parser.add_argument("--output", default="outputs/sample", help="Directory for sample exports")
    sample_parser.add_argument("--max-per-cluster", type=int, default=3, help="Maximum examples per cluster")
    sample_parser.add_argument("--seed", type=int, default=7, help="Sampling seed")
    sample_parser.set_defaults(func=run_sample)

    compare_parser = subparsers.add_parser("compare", help="Compare baseline and candidate eval results")
    compare_parser.add_argument("baseline", help="Path to baseline JSONL or CSV")
    compare_parser.add_argument("candidate", help="Path to candidate JSONL or CSV")
    compare_parser.add_argument("--config", help="Optional config JSON path")
    compare_parser.add_argument("--output", default="outputs/compare", help="Directory for comparison reports")
    compare_parser.set_defaults(func=run_compare)

    config_parser = subparsers.add_parser("init-config", help="Write a default config JSON file")
    config_parser.add_argument("path", nargs="?", default="eval-failure-clusterer.json", help="Config output path")
    config_parser.set_defaults(func=run_init_config)

    check_parser = subparsers.add_parser("check", help="Run CI gate checks")
    check_parser.add_argument("input", help="Path to JSONL or CSV eval results")
    check_parser.add_argument("--baseline", help="Optional baseline JSONL or CSV for regression checks")
    check_parser.add_argument("--config", help="Optional config JSON path")
    check_parser.add_argument("--output", default="outputs/check", help="Directory for generated check reports")
    check_parser.add_argument("--check", choices=["warning", "error"], default="error", help="Gate severity")
    check_parser.set_defaults(func=run_check)

    return parser


def load_analysis(input_path: str, config_path: Optional[str]):
    config = load_config(config_path)
    records = load_records(input_path, config)
    return analyze_records(records, config), config


def run_cluster(args: argparse.Namespace) -> int:
    result, _ = load_analysis(args.input, args.config)
    formats = [item.strip() for item in args.format.split(",") if item.strip()]
    write_cluster_reports(result, args.output, formats)
    print(f"Clustered {result.metrics.failed} failures into {len(result.clusters)} clusters at {Path(args.output)}")
    return 0


def run_sample(args: argparse.Namespace) -> int:
    result, _ = load_analysis(args.input, args.config)
    samples = export_samples(result, max_per_cluster=args.max_per_cluster, seed=args.seed)
    write_sample_reports(samples, args.output)
    print(f"Wrote {len(samples)} cluster sample groups to {Path(args.output)}")
    return 0


def run_compare(args: argparse.Namespace) -> int:
    baseline, config = load_analysis(args.baseline, args.config)
    candidate_records = load_records(args.candidate, config)
    candidate = analyze_records(candidate_records, config)
    result = compare_analysis(baseline, candidate)
    write_compare_reports(result, args.output)
    print(
        "Compared baseline and candidate: "
        f"{result.baseline_metrics.failed} -> {result.candidate_metrics.failed} failures at {Path(args.output)}"
    )
    return 0


def run_init_config(args: argparse.Namespace) -> int:
    path = dump_default_config(args.path)
    print(f"Wrote default config to {path}")
    return 0


def run_check(args: argparse.Namespace) -> int:
    result, config = load_analysis(args.input, args.config)
    compare_result = None
    if args.baseline:
        baseline_records = load_records(args.baseline, config)
        baseline = analyze_records(baseline_records, config)
        compare_result = compare_analysis(baseline, result)
    issues = collect_check_issues(result, compare_result)
    write_check_report(result, args.output, compare_result)
    if issues:
        for issue in issues:
            print(f"ISSUE: {issue}")
    else:
        print("No blocking issues detected")
    if issues and args.check == "error":
        return 2
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))
