"""Each script in examples/ runs and prints its result."""

import runpy
from pathlib import Path

import pytest

EXAMPLES = sorted((Path(__file__).parent.parent / "examples").glob("*.py"))


@pytest.mark.parametrize("script", EXAMPLES, ids=lambda p: p.name)
def test_example_runs(script: Path, tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.chdir(tmp_path)
    runpy.run_path(str(script), run_name="__main__")
    assert capsys.readouterr().out.strip()
