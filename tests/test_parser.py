import tempfile
import unittest
from pathlib import Path

from eval_failure_clusterer.config import load_config
from eval_failure_clusterer.parser import infer_pass_fail, load_records


class ParserTests(unittest.TestCase):
    def setUp(self):
        self.config = load_config()

    def test_infer_pass_fail_from_status_string(self):
        self.assertFalse(infer_pass_fail({"status": "fail"}, self.config))
        self.assertTrue(infer_pass_fail({"status": "pass"}, self.config))

    def test_infer_pass_fail_from_bool(self):
        self.assertTrue(infer_pass_fail({"passed": True}, self.config))
        self.assertFalse(infer_pass_fail({"success": False}, self.config))

    def test_infer_pass_fail_from_error_fallback(self):
        self.assertFalse(infer_pass_fail({"error": "assertion failed"}, self.config))

    def test_load_jsonl_records(self):
        records = load_records("examples/eval_results.jsonl", self.config)
        self.assertEqual(len(records), 10)
        self.assertEqual(records[0].case_id, "qa-001")

    def test_load_csv_records(self):
        records = load_records("examples/eval_results.csv", self.config)
        self.assertEqual(len(records), 3)
        self.assertEqual(records[0].case_id, "csv-001")

    def test_parse_tags_from_list_and_delimited_string(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "rows.jsonl"
            path.write_text(
                "\n".join(
                    [
                        '{"id":"a","status":"fail","tags":["one","two"],"error":"x"}',
                        '{"id":"b","status":"fail","tags":"alpha;beta","error":"y"}',
                    ]
                ),
                encoding="utf-8",
            )
            records = load_records(str(path), self.config)
            self.assertEqual(records[0].tags, ["one", "two"])
            self.assertEqual(records[1].tags, ["alpha", "beta"])

    def test_unsupported_extension_raises(self):
        with self.assertRaises(ValueError):
            load_records("input.txt", self.config)
