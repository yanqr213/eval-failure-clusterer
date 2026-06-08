import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class CLITests(unittest.TestCase):
    def run_cli(self, *args):
        command = [sys.executable, "-m", "eval_failure_clusterer", *args]
        return subprocess.run(command, cwd=ROOT, capture_output=True, text=True)

    def test_help(self):
        result = self.run_cli("--help")
        self.assertEqual(result.returncode, 0)
        self.assertIn("cluster", result.stdout)

    def test_version(self):
        result = self.run_cli("--version")
        self.assertEqual(result.returncode, 0)
        self.assertIn("eval-failure-clusterer 0.1.0", result.stdout)

    def test_init_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config" / "tool.json"
            result = self.run_cli("init-config", str(path))
            self.assertEqual(result.returncode, 0)
            self.assertTrue(path.exists())

    def test_cluster_command(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = self.run_cli("cluster", "examples/eval_results.jsonl", "--output", str(Path(tmp) / "cluster"))
            self.assertEqual(result.returncode, 0)
            self.assertTrue((Path(tmp) / "cluster" / "clusters.json").exists())

    def test_sample_command(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = self.run_cli(
                "sample",
                "examples/eval_results.jsonl",
                "--output",
                str(Path(tmp) / "samples"),
                "--max-per-cluster",
                "1",
            )
            self.assertEqual(result.returncode, 0)
            payload = json.loads((Path(tmp) / "samples" / "samples.json").read_text(encoding="utf-8"))
            self.assertIn("clusters", payload)

    def test_compare_command(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = self.run_cli(
                "compare",
                "examples/baseline_eval.jsonl",
                "examples/eval_results.jsonl",
                "--output",
                str(Path(tmp) / "compare"),
            )
            self.assertEqual(result.returncode, 0)
            self.assertTrue((Path(tmp) / "compare" / "compare.md").exists())

    def test_check_warning_exits_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = self.run_cli(
                "check",
                "examples/eval_results.jsonl",
                "--output",
                str(Path(tmp) / "check"),
                "--check",
                "warning",
            )
            self.assertEqual(result.returncode, 0)

    def test_check_error_exits_two(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = self.run_cli(
                "check",
                "examples/eval_results.jsonl",
                "--baseline",
                "examples/baseline_eval.jsonl",
                "--output",
                str(Path(tmp) / "check"),
                "--check",
                "error",
            )
            self.assertEqual(result.returncode, 2)
