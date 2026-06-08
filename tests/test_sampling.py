import unittest

from eval_failure_clusterer.analyzer import analyze_records
from eval_failure_clusterer.config import load_config
from eval_failure_clusterer.parser import load_records
from eval_failure_clusterer.sampling import export_samples


class SamplingTests(unittest.TestCase):
    def setUp(self):
        config = load_config()
        records = load_records("examples/eval_results.jsonl", config)
        self.result = analyze_records(records, config)

    def test_export_samples_returns_one_group_per_cluster(self):
        samples = export_samples(self.result, max_per_cluster=2, seed=3)
        self.assertEqual(len(samples), len(self.result.clusters))

    def test_export_samples_respects_limit(self):
        samples = export_samples(self.result, max_per_cluster=1, seed=3)
        self.assertTrue(all(len(item["sampled_cases"]) <= 1 for item in samples))
