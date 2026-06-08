import unittest

from eval_failure_clusterer.analyzer import analyze_records
from eval_failure_clusterer.compare import compare_analysis
from eval_failure_clusterer.config import load_config
from eval_failure_clusterer.parser import load_records


class CompareTests(unittest.TestCase):
    def setUp(self):
        self.config = load_config()
        baseline = analyze_records(load_records("examples/baseline_eval.jsonl", self.config), self.config)
        candidate = analyze_records(load_records("examples/eval_results.jsonl", self.config), self.config)
        self.result = compare_analysis(baseline, candidate)

    def test_candidate_has_more_failures(self):
        self.assertGreater(self.result.candidate_metrics.failed, self.result.baseline_metrics.failed)

    def test_regressions_present(self):
        self.assertTrue(self.result.regressions or self.result.new_failure_modes)

    def test_case_changes_include_regression(self):
        changes = {item["case_id"]: item["change"] for item in self.result.case_changes}
        self.assertEqual(changes["qa-001"], "regressed")

    def test_resolved_failure_modes_type(self):
        self.assertIsInstance(self.result.resolved_failure_modes, list)
