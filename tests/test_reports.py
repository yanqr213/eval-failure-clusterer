import json
import tempfile
import unittest
from pathlib import Path

from eval_failure_clusterer.analyzer import analyze_records
from eval_failure_clusterer.baseline import render_reviewed_baseline, split_reviewed_clusters
from eval_failure_clusterer.compare import compare_analysis
from eval_failure_clusterer.config import load_config
from eval_failure_clusterer.parser import load_records
from eval_failure_clusterer.reports import (
    cluster_sarif_payload,
    render_cluster_brief,
    write_check_report,
    write_cluster_reports,
    write_compare_reports,
    write_sample_reports,
)
from eval_failure_clusterer.sampling import export_samples


class ReportTests(unittest.TestCase):
    def setUp(self):
        self.config = load_config()
        self.result = analyze_records(load_records("examples/eval_results.jsonl", self.config), self.config)
        baseline = analyze_records(load_records("examples/baseline_eval.jsonl", self.config), self.config)
        self.compare = compare_analysis(baseline, self.result)

    def test_write_cluster_reports(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = write_cluster_reports(self.result, tmp, ["brief", "markdown", "json", "csv", "junit", "sarif"])
            self.assertEqual(len(paths), 6)
            self.assertTrue((Path(tmp) / "brief.md").exists())
            self.assertTrue((Path(tmp) / "summary.md").exists())
            self.assertTrue((Path(tmp) / "clusters.sarif").exists())

    def test_render_cluster_brief_contains_handoff(self):
        brief = render_cluster_brief(self.result)

        self.assertIn("# Eval Failure Triage Brief", brief)
        self.assertIn("Decision:", brief)
        self.assertIn("Agent handoff:", brief)

    def test_cluster_sarif_payload_shape(self):
        payload = cluster_sarif_payload(self.result, source_uri="fixtures/eval.jsonl")

        self.assertEqual(payload["version"], "2.1.0")
        run = payload["runs"][0]
        self.assertEqual(run["tool"]["driver"]["name"], "eval-failure-clusterer")
        self.assertTrue(run["results"])
        self.assertEqual(run["results"][0]["ruleId"], "eval-failure-cluster")
        uri = run["results"][0]["locations"][0]["physicalLocation"]["artifactLocation"]["uri"]
        self.assertEqual(uri, "fixtures/eval.jsonl")

    def test_write_compare_reports(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = write_compare_reports(self.compare, tmp)
            self.assertEqual(len(paths), 3)
            payload = json.loads((Path(tmp) / "compare.json").read_text(encoding="utf-8"))
            self.assertIn("regressions", payload)

    def test_write_sample_reports(self):
        with tempfile.TemporaryDirectory() as tmp:
            samples = export_samples(self.result, max_per_cluster=2)
            paths = write_sample_reports(samples, tmp)
            self.assertEqual(len(paths), 2)
            self.assertTrue((Path(tmp) / "samples.md").exists())

    def test_write_check_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = write_check_report(self.result, tmp, self.compare)
            self.assertEqual(len(paths), 2)
            payload = json.loads((Path(tmp) / "check.json").read_text(encoding="utf-8"))
            self.assertIn("compare", payload)
            self.assertIn("reviewed_baseline", payload)

    def test_write_check_report_includes_suppressed_clusters(self):
        data = json.loads(render_reviewed_baseline(self.result))
        split = split_reviewed_clusters(self.result, {data["clusters"][0]["cluster_key"]})
        with tempfile.TemporaryDirectory() as tmp:
            write_check_report(
                self.result,
                tmp,
                open_clusters=split["open"],
                suppressed_clusters=split["suppressed"],
            )
            payload = json.loads((Path(tmp) / "check.json").read_text(encoding="utf-8"))
            self.assertEqual(1, payload["reviewed_baseline"]["suppressed_cluster_count"])
            text = (Path(tmp) / "check.md").read_text(encoding="utf-8")
            self.assertIn("Suppressed by reviewed baseline", text)
