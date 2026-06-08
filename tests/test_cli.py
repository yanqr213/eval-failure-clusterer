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
        self.assertIn("eval-failure-clusterer 0.3.0", result.stdout)

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
            self.assertTrue((Path(tmp) / "cluster" / "brief.md").exists())
            self.assertTrue((Path(tmp) / "cluster" / "clusters.json").exists())

    def test_baseline_command(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "reviewed-baseline.json"
            result = self.run_cli("baseline", "examples/eval_results.jsonl", "--output", str(output))
            self.assertEqual(result.returncode, 0)
            payload = json.loads(output.read_text(encoding="utf-8"))
            self.assertIn("clusters", payload)
            self.assertGreater(payload["cluster_count"], 0)

    def test_cluster_sarif_format(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = self.run_cli(
                "cluster",
                "examples/eval_results.jsonl",
                "--output",
                str(Path(tmp) / "cluster"),
                "--format",
                "sarif",
            )
            self.assertEqual(result.returncode, 0)
            payload = json.loads((Path(tmp) / "cluster" / "clusters.sarif").read_text(encoding="utf-8"))
            self.assertEqual(payload["version"], "2.1.0")
            uri = payload["runs"][0]["results"][0]["locations"][0]["physicalLocation"]["artifactLocation"]["uri"]
            self.assertEqual(uri, "examples/eval_results.jsonl")

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

    def test_check_with_reviewed_baseline_suppresses_failed_cluster_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            input_path = Path(tmp) / "eval.jsonl"
            input_path.write_text(
                "\n".join(
                    [
                        json.dumps({"id": "case-1", "status": "fail", "error": "Expected citation field missing", "model": "gpt-test"}),
                        json.dumps({"id": "case-2", "status": "pass", "model": "gpt-test"}),
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            baseline = Path(tmp) / "baseline.json"
            baseline_result = self.run_cli("baseline", str(input_path), "--output", str(baseline))
            self.assertEqual(baseline_result.returncode, 0, baseline_result.stderr)

            result = self.run_cli(
                "check",
                str(input_path),
                "--reviewed-baseline",
                str(baseline),
                "--output",
                str(Path(tmp) / "check"),
                "--check",
                "error",
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            payload = json.loads((Path(tmp) / "check" / "check.json").read_text(encoding="utf-8"))
            self.assertEqual(1, payload["reviewed_baseline"]["suppressed_cluster_count"])
