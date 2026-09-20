#!/usr/bin/env python3
"""Refuse a translation that no longer matches the file it was made from.

A skill is written for an agent and the working version is English. A translation is a convenience for
a human observer, kept in `references/` so it costs nothing in the always-on catalogue and cannot
compete for the skill's trigger. **But a stale translation is worse than none**, because it reads as the
skill: an operator opens it, believes it, and the English it was supposed to describe has moved on.

So every translated file names its source and the source's FINGERPRINT, and this refuses the pair when
they disagree. The fingerprint is a hash of the source's bytes, so any edit at all invalidates it -
whitespace included, deliberately, because a translation is only trustworthy against an exact revision.

    python check-translations.py <skill-folder> [<skill-folder>...]

Header, in the first ten lines of the translated file:

    translated-from: SKILL.md
    translated-fingerprint: <sha256 of SKILL.md, first 16 hex>

Re-record it with --accept after redoing the translation. Nothing here translates anything; it only
makes the drift visible.
"""
from __future__ import annotations

import hashlib
import re
import sys
from pathlib import Path

SOURCE = re.compile(r"^translated-from:\s*(\S+)\s*$", re.M)
PRINT = re.compile(r"^translated-fingerprint:\s*([0-9a-f]+)\s*$", re.M)


def fingerprint(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


def main(folders: list[str], accept: bool) -> int:
    problems = 0
    checked = 0
    for name in folders:
        folder = Path(name)
        for translated in sorted(folder.rglob("*.ru.md")):
            checked += 1
            head = "\n".join(translated.read_text(encoding="utf-8").splitlines()[:10])
            source_match = SOURCE.search(head)
            print_match = PRINT.search(head)
            if not source_match or not print_match:
                print(f"  NO HEADER  {translated}: name the source and its fingerprint")
                problems += 1
                continue
            source = folder / source_match.group(1)
            if not source.exists():
                print(f"  NO SOURCE  {translated} names {source_match.group(1)}, which is not there")
                problems += 1
                continue
            current = fingerprint(source)
            if current == print_match.group(1):
                print(f"  ok         {translated.name} matches {source.name} at {current}")
                continue
            if accept:
                text = translated.read_text(encoding="utf-8")
                text = PRINT.sub(f"translated-fingerprint: {current}", text, count=1)
                translated.write_text(text, encoding="utf-8")
                print(f"  ACCEPTED   {translated.name} re-stamped to {current}")
                continue
            print(f"  STALE      {translated.name} was made from {source.name} at "
                  f"{print_match.group(1)}, which is now {current}")
            print(f"             redo the translation, or re-stamp it if the change did not "
                  f"touch anything it describes")
            problems += 1
    print(f"  {checked} translation(s) checked, {problems} with a problem")
    return 1 if problems else 0


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a != "--accept"]
    raise SystemExit(main(args, "--accept" in sys.argv))
