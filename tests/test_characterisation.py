"""Characterisation: public-API numerics must equal the frozen pre-refactor values (to 1e-9 relative).

``golden/characterisation.json`` was produced by ``golden/capture.py`` on the original code
(floats stored as ``repr`` strings). Structure, keys and strings must match exactly; numbers
are compared to a relative tolerance of 1e-9 because libm/BLAS differ in the last few ulps
between platforms (macOS vs the Linux CI runner), which is far tighter than any model change.
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


def _as_float(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def assert_close(actual, expected, path="") -> None:
    """Recursive equality: identical structure/strings, numeric strings within rel 1e-9."""
    if isinstance(expected, dict):
        assert isinstance(actual, dict) and set(actual) == set(expected), path
        for k in expected:
            assert_close(actual[k], expected[k], f"{path}/{k}")
    elif isinstance(expected, list):
        assert isinstance(actual, list) and len(actual) == len(expected), path
        for i, (a, e) in enumerate(zip(actual, expected)):
            assert_close(a, e, f"{path}[{i}]")
    elif actual == expected:
        return
    else:
        fa, fe = _as_float(actual), _as_float(expected)
        assert fa is not None and fe is not None, f"{path}: {actual!r} != {expected!r}"
        assert fa == pytest.approx(fe, rel=1e-9, abs=1e-8), f"{path}: {actual!r} != {expected!r}"


@pytest.fixture(scope="module")
def current() -> dict:
    return {k: capture.plain(v) for k, v in capture.capture().items()}


def test_same_keys(current):
    assert set(current) == set(GOLDEN)


@pytest.mark.parametrize("key", sorted(GOLDEN))
def test_matches_golden(current, key):
    assert_close(current[key], GOLDEN[key], key)
