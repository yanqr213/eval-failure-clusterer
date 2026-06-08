"""Failure reason normalization."""

from __future__ import annotations

import re
from typing import List, Tuple

from .models import EvalRecord
from .utils import lower_text, normalize_whitespace


RULES: List[Tuple[str, str, str]] = [
    (r"missing.*citation|citation.*missing", "missing_citation", "missing citation"),
    (r"missing final answer|never provide the final", "missing_final_answer", "missing final answer"),
    (r"json parse error|invalid json|json decode", "invalid_json", "invalid json"),
    (r"timed out|timeout", "timeout", "timeout"),
    (r"cost spike|too expensive|cost regression", "cost_spike", "cost spike"),
    (r"refused when answer was allowed|over-refus", "over_refusal", "over refusal"),
    (r"missing field|field.*missing", "missing_field", "missing required field"),
]


def detect_missing_fields(record: EvalRecord) -> List[str]:
    missing: List[str] = []
    if record.expected and not record.actual and not record.output:
        missing.append("actual")
    output_lower = lower_text(record.output)
    if "citation" in lower_text(record.error) and not any(marker in output_lower for marker in ("[", "http", "source:", "ref")):
        missing.append("citation")
    if "json" in lower_text(record.error):
        if "{" not in record.output or "}" not in record.output:
            missing.append("json_structure")
    if "final answer" in lower_text(record.error) and "final answer" not in lower_text(record.output):
        missing.append("final_answer")
    return missing


def normalize_failure(record: EvalRecord) -> EvalRecord:
    text = normalize_whitespace(" ".join([record.error, record.output, record.expected, record.actual]))
    lowered = lower_text(text)
    record.missing_fields = detect_missing_fields(record)
    if record.missing_fields:
        record.failure_mode = "missing_field"
        record.normalized_reason = f"missing fields: {', '.join(sorted(record.missing_fields))}"
        record.fingerprint_text = lowered
        return record
    for pattern, mode, reason in RULES:
        if re.search(pattern, lowered):
            record.failure_mode = mode
            record.normalized_reason = reason
            record.fingerprint_text = lowered
            return record
    if record.error:
        record.failure_mode = "assertion_failure"
        record.normalized_reason = normalize_whitespace(record.error).lower()
    else:
        record.failure_mode = "unknown_failure"
        record.normalized_reason = "unknown failure"
    record.fingerprint_text = lowered
    return record
