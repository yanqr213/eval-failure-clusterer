"""Input parsers and record normalization."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from .models import EvalRecord
from .utils import safe_float


def _first_present(row: Dict[str, Any], names: Iterable[str], default: Any = "") -> Any:
    for name in names:
        if name in row and row[name] not in (None, ""):
            return row[name]
    return default


def _parse_tags(value: Any, delimiters: List[str]) -> List[str]:
    if value is None or value == "":
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    text = str(value)
    tags = [text]
    for delimiter in delimiters:
        if delimiter in text:
            tags = [piece.strip() for piece in text.split(delimiter)]
            break
    return [tag for tag in tags if tag]


def infer_pass_fail(row: Dict[str, Any], config: Dict[str, Any]) -> bool:
    status_fields = config["fields"]["status"]
    value = _first_present(row, status_fields, default=None)
    pass_values = {item.lower() for item in config["pass_values"]}
    fail_values = {item.lower() for item in config["fail_values"]}
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return float(value) >= 1.0
    if value is not None:
        lowered = str(value).strip().lower()
        if lowered in pass_values:
            return True
        if lowered in fail_values:
            return False
    error_value = _first_present(row, config["fields"]["error"], default="")
    if error_value:
        return False
    score = row.get("score")
    if isinstance(score, (int, float)):
        return float(score) >= 1.0
    return True


def _make_record(row: Dict[str, Any], config: Dict[str, Any], index: int) -> EvalRecord:
    fields = config["fields"]
    passed = infer_pass_fail(row, config)
    case_id = str(_first_present(row, fields["id"], default=f"row-{index + 1}"))
    status = "pass" if passed else "fail"
    error = str(_first_present(row, fields["error"], default=""))
    output = str(_first_present(row, fields["output"], default=""))
    model = str(_first_present(row, fields["model"], default="unknown"))
    tags = _parse_tags(_first_present(row, fields["tags"], default=[]), config["tag_delimiters"])
    expected = str(_first_present(row, fields["expected"], default=""))
    actual = str(_first_present(row, fields["actual"], default=""))
    latency_ms = safe_float(_first_present(row, fields["latency_ms"], default=None))
    cost_usd = safe_float(_first_present(row, fields["cost_usd"], default=None))
    return EvalRecord(
        case_id=case_id,
        passed=passed,
        status=status,
        error=error,
        output=output,
        model=model,
        tags=tags,
        latency_ms=latency_ms,
        cost_usd=cost_usd,
        expected=expected,
        actual=actual,
        raw=row,
    )


def load_records(path: str, config: Dict[str, Any]) -> List[EvalRecord]:
    source = Path(path)
    suffix = source.suffix.lower()
    if suffix == ".jsonl":
        return load_jsonl(source, config)
    if suffix == ".csv":
        return load_csv(source, config)
    raise ValueError(f"Unsupported input format: {source.suffix}")


def load_jsonl(path: Path, config: Dict[str, Any]) -> List[EvalRecord]:
    records: List[EvalRecord] = []
    with path.open("r", encoding="utf-8") as handle:
        for index, line in enumerate(handle):
            stripped = line.strip()
            if not stripped:
                continue
            row = json.loads(stripped)
            records.append(_make_record(row, config, index))
    return records


def load_csv(path: Path, config: Dict[str, Any]) -> List[EvalRecord]:
    records: List[EvalRecord] = []
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for index, row in enumerate(reader):
            records.append(_make_record(dict(row), config, index))
    return records
