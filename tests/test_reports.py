import json
import tempfile
import unittest
from pathlib import Path

from eval_failure_clusterer.analyzer import analyze_records
from eval_failure_clusterer.compare import compare_analysis
from eval_failure_clusterer.config import load_config
from eval_failure_clusterer.parser import load_records
from eval_failure_clusterer.reports import write_check_report, write_cluster_reports, write_compare_reports, write_sample_reports
from eval_failure_clusterer.sampling import export_samples


class ReportTests(unittest.TestCase):
    def setUp(self):
        self.config = load_config()
        self.result = analyze_records(load_records("examples/eval_results.jsonl", self.config), self.config)
        baseline = analyze_records(load_records("examples/baseline_eval.jsonl", self.config), self.config)
        self.compare = compare_analysis(baseline, self.result)

    def test_write_cluster_reports(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = write_cluster_reports(self.result, tmp, ["markdown", "json", "csv", "junit"])
            self.assertEqual(len(paths), 4)
            self.assertTrue((Path(tmp) / "summary.md").exists())

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
