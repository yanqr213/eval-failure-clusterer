import json
import tempfile
import unittest
from pathlib import Path

from eval_failure_clusterer.config import DEFAULT_CONFIG, deep_merge, dump_default_config, load_config


class ConfigTests(unittest.TestCase):
    def test_deep_merge_nested(self):
        merged = deep_merge({"a": {"b": 1, "c": 2}}, {"a": {"c": 3}, "d": 4})
        self.assertEqual(merged["a"]["b"], 1)
        self.assertEqual(merged["a"]["c"], 3)
        self.assertEqual(merged["d"], 4)

    def test_load_default_config(self):
        config = load_config()
        self.assertEqual(config["fields"]["id"], DEFAULT_CONFIG["fields"]["id"])

    def test_dump_and_load_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "nested" / "config.json"
            dump_default_config(str(path))
            self.assertTrue(path.exists())
            loaded = load_config(str(path))
            self.assertIn("priority_weights", loaded)

    def test_load_config_override(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            path.write_text(json.dumps({"min_text_similarity": 0.8}), encoding="utf-8")
            loaded = load_config(str(path))
            self.assertEqual(loaded["min_text_similarity"], 0.8)
