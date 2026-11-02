"""Characterisation: public-API numerics must equal the frozen pre-refactor values exactly.

``golden/characterisation.json`` was produced by ``golden/capture.py`` on the original code
(floats stored as ``repr`` strings, so the comparison is bit-for-bit).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

GOLDEN_DIR = Path(__file__).parent / "golden"
sys.path.insert(0, str(GOLDEN_DIR))
import capture  # noqa: E402

GOLDEN = json.loads((GOLDEN_DIR / "characterisation.json").read_text())


@pytest.fixture(scope="module")
def current() -> dict:
    return {k: capture.plain(v) for k, v in capture.capture().items()}


def test_same_keys(current):
    assert set(current) == set(GOLDEN)


@pytest.mark.parametrize("key", sorted(GOLDEN))
def test_matches_golden(current, key):
    assert current[key] == GOLDEN[key]
