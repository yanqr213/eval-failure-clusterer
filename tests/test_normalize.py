import unittest

from eval_failure_clusterer.models import EvalRecord
from eval_failure_clusterer.normalize import detect_missing_fields, normalize_failure


class NormalizeTests(unittest.TestCase):
    def test_detect_missing_citation(self):
        record = EvalRecord(
            case_id="a",
            passed=False,
            status="fail",
            error="Expected citation field missing",
            output="Answer only",
            model="m",
            tags=[],
            latency_ms=None,
            cost_usd=None,
            expected="",
            actual="",
        )
        self.assertIn("citation", detect_missing_fields(record))

    def test_detect_missing_json_structure(self):
        record = EvalRecord(
            case_id="b",
            passed=False,
            status="fail",
            error="JSON parse error",
            output="tool: search",
            model="m",
            tags=[],
            latency_ms=None,
            cost_usd=None,
            expected="",
            actual="",
        )
        self.assertIn("json_structure", detect_missing_fields(record))

    def test_normalize_missing_fields_takes_precedence(self):
        record = EvalRecord(
            case_id="c",
            passed=False,
            status="fail",
            error="Expected citation field missing",
            output="Answer only",
            model="m",
            tags=[],
            latency_ms=None,
            cost_usd=None,
            expected="",
            actual="",
        )
        normalized = normalize_failure(record)
        self.assertEqual(normalized.failure_mode, "missing_field")

    def test_normalize_invalid_json(self):
        record = EvalRecord(
            case_id="d",
            passed=False,
            status="fail",
            error="JSON parse error at line 1",
            output='{"tool": lookup, bad}',
            model="m",
            tags=[],
            latency_ms=None,
            cost_usd=None,
            expected="",
            actual="",
        )
        normalized = normalize_failure(record)
        self.assertEqual(normalized.failure_mode, "invalid_json")

    def test_normalize_unknown(self):
        record = EvalRecord(
            case_id="e",
            passed=False,
            status="fail",
            error="Something odd happened",
            output="",
            model="m",
            tags=[],
            latency_ms=None,
            cost_usd=None,
            expected="",
            actual="",
        )
        normalized = normalize_failure(record)
        self.assertEqual(normalized.failure_mode, "assertion_failure")
