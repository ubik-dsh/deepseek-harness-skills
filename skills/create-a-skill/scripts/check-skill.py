#!/usr/bin/env python3
"""Check a skill against the mechanical rules of the Agent Skills format.

Written because the failures this catches are cheap to find and expensive to
discover later, once the skill is trusted: a name that does not match its folder
is silently ignored by the loader, a stale relative path breaks the one time it
is needed, an absolute path works on exactly one machine.

Standard library only, so it runs anywhere Python does.

    python check-skill.py <skill-directory>
    python check-skill.py <skills-root> --recursive

Exit code 0 when nothing failed, 1 when something did. Warnings never fail the
run: a judgement call is reported as a judgement call.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
MAX_NAME = 64
MAX_DESCRIPTION = 1024
MAX_BODY_LINES = 500
COMFORTABLE_BODY_LINES = 100

# A file an agent has no reason to open.
FORBIDDEN_AT_ROOT = re.compile(
    r"^(readme|changelog|changes|installation|install|contributing|history|"
    r"notes|todo|license\.md|.*\.txt)$",
    re.IGNORECASE,
)

ABSOLUTE_PATH = re.compile(r"(?:[A-Za-z]:\\|/home/|/Users/|/root/|/var/|/etc/)")

TIME_SENSITIVE = re.compile(
    r"\b(as of (q[1-4]|20\d\d)|in (january|february|march|april|may|june|july|"
    r"august|september|october|november|december) 20\d\d|currently (as of|the)|"
    r"latest version is|at the time of writing)\b",
    re.IGNORECASE,
)

UNEXPECTED_BINARY = re.compile(r"\.(pyc|pyo|exe|dll|so|dylib|class|jar|bin)$", re.IGNORECASE)

# The `(?<![A-Za-z0-9])` guard is load-bearing: without it "subscripts/superscripts"
# matches `scripts/superscripts`, and the checker reports a broken link in a skill
# that has none. A word boundary is the difference between a finding and noise.
REFERENCE = re.compile(r"(?<![A-Za-z0-9])(?:references|scripts|assets)/[A-Za-z0-9._/-]+")
MARKDOWN_LINK = re.compile(r"\[[^\]]*\]\(([^)#\s]+)")
PLACEHOLDER = re.compile(r"(<[^>]*>|\$\{?[A-Za-z_]|\{\{|%s|\{name\})")

# A line that is teaching by counter-example. `references/x.md`, never
# `references/a/b/c.md` mentions a path that is supposed to be missing, and
# "As of Q4 2024" rots is a warning about dating a skill, not an instance of it.
# Skipping these lines costs a little coverage and removes a whole class of lie.
EXAMPLE_MARKER = re.compile(
    r"\b(never|avoid|don't|do not|not |instead|rots?|bad|wrong|anti-?pattern|"
    r"counter-?example|for example|e\.g\.)\b",
    re.IGNORECASE,
)


class Result:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.failures: list[str] = []
        self.warnings: list[str] = []
        self.notes: list[str] = []

    def fail(self, message: str) -> None:
        self.failures.append(message)

    def warn(self, message: str) -> None:
        self.warnings.append(message)

    def note(self, message: str) -> None:
        self.notes.append(message)


def split_frontmatter(text: str) -> tuple[dict[str, object], str]:
    """Return the top-level frontmatter mapping and the body.

    A deliberately small parser: the format only needs `key: value`, quoted
    strings, and the `>`/`|` block scalars. Pulling in a YAML library for that
    would make the checker harder to run than the thing it checks.
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, text
    end = None
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            end = index
            break
    if end is None:
        return {}, text

    data: dict[str, object] = {}
    index = 1
    while index < end:
        line = lines[index]
        match = re.match(r"^([A-Za-z][A-Za-z0-9_-]*):(.*)$", line)
        if match is None:
            index += 1
            continue
        key, raw = match.group(1), match.group(2).strip()
        if raw in (">", "|", ">-", "|-"):
            block: list[str] = []
            index += 1
            while index < end and (lines[index].startswith((" ", "\t")) or lines[index].strip() == ""):
                block.append(lines[index].strip())
                index += 1
            data[key] = " ".join(part for part in block if part)
            continue
        data[key] = raw.strip("'\"")
        index += 1

    return data, "\n".join(lines[end + 1 :])


def check(path: Path) -> Result:
    result = Result(path)
    skill_file = path / "SKILL.md"

    if not skill_file.is_file():
        # A flat skill is legal: `<name>.md` directly inside a skills root.
        flat = sorted(p for p in path.glob("*.md") if p.name != "SKILL.md")
        if len(flat) == 1:
            skill_file = flat[0]
            result.note(f"flat skill file: {skill_file.name}")
        else:
            result.fail("no SKILL.md (and no single flat .md file) in the folder")
            return result

    text = skill_file.read_text(encoding="utf-8", errors="replace")
    front, body = split_frontmatter(text)
    if not front:
        result.fail("no YAML frontmatter delimited by --- at the top of the file")
        return result

    # ── name ──────────────────────────────────────────────────────────────
    name = front.get("name")
    if not isinstance(name, str) or name == "":
        result.fail("frontmatter has no `name`")
    else:
        if not NAME_RE.match(name):
            result.fail(f"`name: {name}` is not kebab-case (a-z, digits, single hyphens)")
        if len(name) > MAX_NAME:
            result.fail(f"`name` is {len(name)} characters, the limit is {MAX_NAME}")
        if name != path.name:
            result.fail(
                f"`name: {name}` does not match the folder `{path.name}` — "
                "the loader matches on the folder and ignores the file"
            )

    # ── description ───────────────────────────────────────────────────────
    description = front.get("description")
    if not isinstance(description, str) or description.strip() == "":
        result.fail("frontmatter has no `description` — the skill can never be matched")
    else:
        if len(description) > MAX_DESCRIPTION:
            result.fail(f"`description` is {len(description)} characters, the limit is {MAX_DESCRIPTION}")
        if not re.search(r"\buse (this|it|when)\b", description, re.IGNORECASE):
            result.warn(
                "the description does not say when to use the skill; an agent matches "
                "on this text alone, so `Use when …` with the user's own words matters"
            )
        if description.strip().lower().startswith(("a ", "an ", "the ", "helps", "this skill")):
            result.warn("the description opens with what the skill is, not when to use it")

    # ── size ──────────────────────────────────────────────────────────────
    body_lines = [line for line in body.splitlines() if line.strip() != ""]
    if len(body_lines) > MAX_BODY_LINES:
        result.fail(f"the body has {len(body_lines)} non-empty lines; move detail into references/ (limit {MAX_BODY_LINES})")
    elif len(body_lines) > COMFORTABLE_BODY_LINES:
        result.note(f"the body has {len(body_lines)} non-empty lines — fine for a procedure, worth watching")

    # ── files that should not be there ────────────────────────────────────
    for entry in sorted(path.iterdir()):
        if entry.is_dir():
            continue
        if FORBIDDEN_AT_ROOT.match(entry.name) and entry.name != skill_file.name:
            if entry.name.lower().startswith("license"):
                continue
            result.fail(f"`{entry.name}` is a human-facing file; a skill is read by an agent")
        if UNEXPECTED_BINARY.search(entry.name):
            result.warn(f"`{entry.name}` is compiled or binary and cannot be reviewed by reading it")

    # ── paths, per line so that teaching examples can be skipped ──────────
    lines = text.splitlines()
    candidates: set[str] = set()
    for index, line in enumerate(lines, 1):
        if EXAMPLE_MARKER.search(line):
            continue
        for match in ABSOLUTE_PATH.finditer(line):
            result.fail(f"line {index}: absolute path `{match.group(0)}` — use a path relative to the skill folder")
        for match in TIME_SENSITIVE.finditer(line):
            result.warn(f"line {index}: `{match.group(0)}` will age badly; read live data or drop it")
        for match in REFERENCE.finditer(line):
            candidates.add(match.group(0).rstrip(".,;:)"))
        for match in MARKDOWN_LINK.finditer(line):
            target = match.group(1).strip()
            if target.startswith(("http://", "https://", "mailto:", "#")):
                continue
            candidates.add(target)

    # ── references resolve ────────────────────────────────────────────────
    for candidate in sorted(candidates):
        if PLACEHOLDER.search(candidate):
            continue
        if not (path / candidate).exists():
            result.fail(f"referenced file does not exist: `{candidate}`")
        elif candidate.count("/") > 1:
            result.warn(f"`{candidate}` is nested more than one level deep")

    return result


def report(result: Result) -> bool:
    status = "FAIL" if result.failures else ("warn" if result.warnings else "ok  ")
    print(f"{status}  {result.path}")
    for message in result.notes:
        print(f"        note: {message}")
    for message in result.warnings:
        print(f"        warn: {message}")
    for message in result.failures:
        print(f"        FAIL: {message}")
    return not result.failures


def main() -> int:
    parser = argparse.ArgumentParser(description="Check skills against the Agent Skills format.")
    parser.add_argument("paths", nargs="+", help="skill directory, or a skills root with --recursive")
    parser.add_argument("--recursive", "-r", action="store_true", help="treat each path as a skills root")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    args = parser.parse_args()

    targets: list[Path] = []
    for raw in args.paths:
        root = Path(raw)
        if not root.is_dir():
            print(f"FAIL  {root}: not a directory")
            return 1
        if args.recursive:
            targets.extend(sorted(p for p in root.iterdir() if p.is_dir() and not p.name.startswith(".")))
        else:
            targets.append(root)

    results = [check(target) for target in targets]

    if args.json:
        print(json.dumps(
            [
                {"path": str(r.path), "failures": r.failures, "warnings": r.warnings, "notes": r.notes}
                for r in results
            ],
            indent=2,
        ))
    else:
        for result in results:
            report(result)

    failed = sum(1 for r in results if r.failures)
    warned = sum(1 for r in results if r.warnings and not r.failures)
    print()
    print(f"{len(results)} skill(s) checked: {len(results) - failed - warned} ok, {warned} with warnings, {failed} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
