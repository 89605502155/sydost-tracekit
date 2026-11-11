"""Package metadata is consistent and every exported name exists."""

import tomllib
from pathlib import Path

import sydost_tracekit

ROOT = Path(__file__).parent.parent


def test_version_matches_pyproject():
    meta = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert sydost_tracekit.__version__ == meta["project"]["version"]


def test_citation_and_changelog_carry_the_version():
    version = sydost_tracekit.__version__
    assert f"version: {version}" in (ROOT / "CITATION.cff").read_text(encoding="utf-8")
    assert f"## [{version}]" in (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")


def test_all_exports_exist():
    for name in sydost_tracekit.__all__:
        assert hasattr(sydost_tracekit, name), name
