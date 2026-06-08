import json
import tempfile
import unittest
from pathlib import Path

from eval_failure_clusterer.analyzer import analyze_records
from eval_failure_clusterer.baseline import load_reviewed_baseline, render_reviewed_baseline, split_reviewed_clusters
from eval_failure_clusterer.config import load_config
from eval_failure_clusterer.parser import load_records


class BaselineTests(unittest.TestCase):
    def setUp(self):
        self.config = load_config()
        self.result = analyze_records(load_records("examples/eval_results.jsonl", self.config), self.config)

    def test_render_reviewed_baseline_contains_cluster_keys(self):
        data = json.loads(render_reviewed_baseline(self.result))

        self.assertEqual(1, data["schema_version"])
        self.assertEqual(len(self.result.clusters), data["cluster_count"])
        self.assertTrue(data["clusters"][0]["cluster_key"])
        self.assertIn("review", data["clusters"][0])

    def test_load_reviewed_baseline_accepts_object_shape(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "baseline.json"
            path.write_text(render_reviewed_baseline(self.result), encoding="utf-8")

            keys = load_reviewed_baseline(str(path))

        self.assertEqual(len(self.result.clusters), len(keys))

    def test_split_reviewed_clusters_suppresses_matching_clusters(self):
        data = json.loads(render_reviewed_baseline(self.result))
        first_key = data["clusters"][0]["cluster_key"]

        split = split_reviewed_clusters(self.result, {first_key})

        self.assertEqual(1, len(split["suppressed"]))
        self.assertEqual(len(self.result.clusters) - 1, len(split["open"]))


if __name__ == "__main__":
    unittest.main()
