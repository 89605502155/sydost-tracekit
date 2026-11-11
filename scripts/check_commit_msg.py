"""Check git commit messages: the subject at most LIMIT characters and no body.

The project keeps commit messages to one short line. Subject is the first
line, body is everything after it, without git comment lines (starting with
'#') and without surrounding whitespace. Characters are counted as Unicode
code points.

Usage: check_commit_msg.py FILE           (commit-msg hook)
       check_commit_msg.py --rev RANGE    (CI, e.g. origin/main..HEAD)
"""

from __future__ import annotations

import subprocess
import sys

LIMIT = 8


def split_message(text: str) -> tuple[str, str]:
    """Return the subject and the body of a commit message."""
    lines = [ln for ln in text.splitlines() if not ln.startswith("#")]
    while lines and not lines[0].strip():
        lines.pop(0)
    if not lines:
        return "", ""
    subject = lines[0].strip()
    body = "\n".join(lines[1:]).strip()
    return subject, body


def problems(text: str, limit: int = LIMIT) -> list[str]:
    """Return the list of rule violations of one commit message (empty if none)."""
    subject, body = split_message(text)
    out = []
    if not subject:
        out.append("empty subject")
    if len(subject) > limit:
        out.append(f"subject has {len(subject)} chars, limit {limit}: {subject!r}")
    if body:
        out.append(f"body is not allowed: {body[:40]!r}")
    return out


def _messages(rev: str) -> list[tuple[str, str]]:
    shas = subprocess.run(
        ["git", "rev-list", rev], capture_output=True, text=True, check=True
    ).stdout.split()
    return [
        (
            sha,
            subprocess.run(
                ["git", "log", "-1", "--format=%B", sha],
                capture_output=True,
                text=True,
                check=True,
            ).stdout,
        )
        for sha in shas
    ]


def main(argv: list[str]) -> int:
    """Check a commit message file or a revision range; return the exit status."""
    if len(argv) == 2 and argv[0] == "--rev":
        items = _messages(argv[1])
    elif len(argv) == 1:
        with open(argv[0], encoding="utf-8") as fh:
            items = [("message", fh.read())]
    else:
        print(__doc__, file=sys.stderr)
        return 2
    bad = 0
    for ref, text in items:
        for problem in problems(text):
            print(f"{ref[:12]}: {problem}", file=sys.stderr)
            bad += 1
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
