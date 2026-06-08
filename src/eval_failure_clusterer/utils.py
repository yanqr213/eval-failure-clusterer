"""Small utilities used across the package."""

from __future__ import annotations

import math
import re
from pathlib import Path
from statistics import median
from typing import Iterable, List, Optional, Sequence


def ensure_output_dir(path: str) -> Path:
    target = Path(path)
    target.mkdir(parents=True, exist_ok=True)
    return target


def safe_float(value: object) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def lower_text(text: str) -> str:
    return normalize_whitespace(text).lower()


def slugify(text: str) -> str:
    value = re.sub(r"[^a-z0-9]+", "-", lower_text(text))
    value = value.strip("-")
    return value or "cluster"


def median_or_zero(values: Sequence[Optional[float]]) -> float:
    clean = [value for value in values if value is not None]
    if not clean:
        return 0.0
    return float(median(clean))


def percentage(part: int, whole: int) -> float:
    if not whole:
        return 0.0
    return part / whole


def clamp(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    return max(lower, min(upper, value))


def shingle_tokens(text: str, size: int = 3) -> List[str]:
    normalized = lower_text(text)
    if not normalized:
        return []
    if len(normalized) <= size:
        return [normalized]
    return [normalized[index : index + size] for index in range(0, len(normalized) - size + 1)]


def hamming_distance(left: int, right: int) -> int:
    return (left ^ right).bit_count()


def similarity_from_distance(left: int, right: int, bits: int = 64) -> float:
    return 1.0 - (hamming_distance(left, right) / bits)


def stable_sample(items: Sequence[object], max_items: int) -> List[object]:
    if max_items <= 0:
        return []
    return list(items[:max_items])


def summarize_range(values: Iterable[Optional[float]]) -> str:
    clean = [value for value in values if value is not None]
    if not clean:
        return "n/a"
    return f"{min(clean):.2f}-{max(clean):.2f}"


def format_percent(value: float) -> str:
    return f"{value * 100:.1f}%"


def format_decimal(value: float) -> str:
    if math.isfinite(value):
        return f"{value:.3f}"
    return "0.000"
