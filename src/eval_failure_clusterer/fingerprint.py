"""Text fingerprinting helpers."""

from __future__ import annotations

import hashlib
from typing import Iterable

from .utils import shingle_tokens


def simhash(text: str, shingle_size: int = 3, bits: int = 64) -> int:
    shingles = shingle_tokens(text, size=shingle_size)
    if not shingles:
        return 0
    weights = [0] * bits
    for shingle in shingles:
        digest = hashlib.sha1(shingle.encode("utf-8")).digest()
        value = int.from_bytes(digest[:8], byteorder="big", signed=False)
        for bit in range(bits):
            mask = 1 << bit
            if value & mask:
                weights[bit] += 1
            else:
                weights[bit] -= 1
    output = 0
    for bit, weight in enumerate(weights):
        if weight >= 0:
            output |= 1 << bit
    return output


def fingerprint_many(texts: Iterable[str]) -> Iterable[int]:
    for text in texts:
        yield simhash(text)
