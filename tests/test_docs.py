"""The Python examples of the documentation run, and the two languages show the same code.

All ``python`` code blocks of a document run in order in one namespace, in a temporary
working directory, and must print something.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
PAIRS = [
    (ROOT / "README.md", ROOT / "README.ru.md"),
    *[
        (ROOT / "docs" / "en" / name, ROOT / "docs" / "ru" / name)
        for name in [
            "quickstart.md",
            "trace-format.md",
            "bounds.md",
            "recorder-deployment.md",
            "api.md",
            "cli.md",
        ]
    ],
]
BLOCK = re.compile(r"```python\n(.*?)```", re.DOTALL)


def _blocks(path: Path) -> list[str]:
    return BLOCK.findall(path.read_text(encoding="utf-8"))


DOCUMENTS = [english for english, _ in PAIRS] + [russian for _, russian in PAIRS]


@pytest.mark.parametrize("document", DOCUMENTS, ids=lambda p: str(p.relative_to(ROOT)))
def test_code_blocks_run(
    document: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    blocks = _blocks(document)
    if not blocks:
        pytest.skip(f"{document.name} has no Python examples")
    monkeypatch.chdir(tmp_path)
    namespace: dict[str, object] = {"__name__": "__docs__"}
    for number, code in enumerate(blocks, start=1):
        try:
            exec(compile(code, f"{document.name}[{number}]", "exec"), namespace)  # noqa: S102
        except Exception as error:  # pragma: no cover - reported as a failure
            pytest.fail(f"{document.name}, code block {number} failed: {error!r}\n{code}")
    assert capsys.readouterr().out


def _code_without_text(code: str) -> str:
    """The code with comments, strings and whitespace removed."""
    code = re.sub(r"#.*|\"[^\"]*\"", "", code)
    return re.sub(r"\s+", "", code)


@pytest.mark.parametrize("pair", PAIRS, ids=lambda p: p[0].name)
def test_both_languages_show_the_same_code(pair: tuple[Path, Path]) -> None:
    english, russian = pair
    en = [_code_without_text(b) for b in _blocks(english)]
    ru = [_code_without_text(b) for b in _blocks(russian)]
    assert en == ru
