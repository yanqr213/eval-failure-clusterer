import unittest

from eval_failure_clusterer.analyzer import analyze_records
from eval_failure_clusterer.config import load_config
from eval_failure_clusterer.parser import load_records


class AnalyzerTests(unittest.TestCase):
    def setUp(self):
        self.config = load_config()
        self.records = load_records("examples/eval_results.jsonl", self.config)
        self.result = analyze_records(self.records, self.config)

    def test_metrics_counts(self):
        self.assertEqual(self.result.metrics.total, 10)
        self.assertEqual(self.result.metrics.failed, 8)

    def test_clusters_generated(self):
        self.assertGreaterEqual(len(self.result.clusters), 5)

    def test_cluster_priority_sorted(self):
        scores = [cluster.priority_score for cluster in self.result.clusters]
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_model_summary(self):
        self.assertIn("gpt-lite", self.result.grouped_by_model)
        self.assertGreater(self.result.grouped_by_model["gpt-lite"]["failed"], 0)

    def test_tag_summary(self):
        self.assertIn("retrieval", self.result.grouped_by_tag)

    def test_case_summary_contains_failure_mode(self):
        self.assertEqual(self.result.grouped_by_case["qa-001"]["failure_mode"], "missing_field")

    def test_anomalies_detected(self):
        self.assertGreaterEqual(self.result.metrics.latency_anomalies, 1)
        self.assertGreaterEqual(self.result.metrics.cost_anomalies, 1)
