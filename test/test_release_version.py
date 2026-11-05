"""Release numbering follows ISO weeks, including year boundaries."""

import datetime
import importlib.util
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "version.py"


def load_version_module():
    spec = importlib.util.spec_from_file_location("release_version", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("value", ["2026.45.0", "2026.1.12", "2020.53.0"])
def test_valid_versions(value):
    assert load_version_module().valid(value)


@pytest.mark.parametrize(
    "value", ["2026.045.0", "2026.0.0", "2026.54.0", "2026.45.01", "2021.53.0"]
)
def test_invalid_versions(value):
    assert not load_version_module().valid(value)


def test_next_version_uses_iso_year():
    module = load_version_module()
    assert module.next_version(datetime.date(2021, 1, 1), "2020.53.2") == "2020.53.3"
    assert module.next_version(datetime.date(2026, 11, 5), "2026.44.9") == "2026.45.0"


def test_repository_versions_match():
    assert load_version_module().check() == 0
