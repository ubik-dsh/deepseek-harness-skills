#!/usr/bin/env python3
"""Check a skill against the mechanical rules of the Agent Skills format.

Written because the failures this catches are cheap to find and expensive to
discover later, once the skill is trusted: a name that does not match its folder
violates the standard, a stale relative path breaks the one time it is needed,
an absolute path works on exactly one machine.

Standard library only, so it runs anywhere Python does.

    python check-skill.py <skill-directory>
    python check-skill.py <skills-root> --recursive

Exit code 0 when nothing failed, 1 when something did. Warnings never fail the
run: a judgement call is reported as a judgement call.

Every rule here has a regression test in test-check-skill.py, because the first
version of this file had seven defects that only an adversarial reviewer found,
and two of them made it blind to the very thing it was written to catch.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
MAX_NAME = 64
MAX_DESCRIPTION = 1024
MAX_BODY_LINES = 500
COMFORTABLE_BODY_LINES = 100
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv"}
# Folders that hold a skill's own material. A single `.md` inside one of these is
# a document belonging to a skill, not a skill of its own.
RESOURCE_DIRS = {"references", "reference", "scripts", "assets", "examples", "docs", "templates", "data"}

# A file an agent has no reason to open. The stem is matched, with or without a
# suffix, because the first version of this pattern was anchored to a bare word:
# `^(readme|changelog|...)$` never matches `README.md`, so the checker was blind
# to the three files its own anti-patterns page names verbatim.
FORBIDDEN_STEM = re.compile(
    r"^(readme|changelog|changes|installation|contributing|"
    r"history|notes|todo|roadmap|authors|credits|getting[-_]started)"
    r"([._-][a-z0-9._-]*)?$",
    re.IGNORECASE,
)
LICENCE_STEM = re.compile(r"^licen[cs]e", re.IGNORECASE)

# Inside a resource folder, `notes.md` and `history.md` are ordinary documents
# that the skill is supposed to have. Only names that belong to a human reader -
# a readme, a changelog - are wrong anywhere in the tree.
FORBIDDEN_ANYWHERE = re.compile(
    r"^(readme|changelog|changes|contributing|getting[-_]started)([._-][a-z0-9._-]*)?$",
    re.IGNORECASE,
)

# `(?<![A-Za-z0-9])` is load-bearing: without it "subscripts/superscripts"
# matches `scripts/superscripts`, and the checker reports a broken link in a
# skill that has none. A word boundary is the difference between a finding and
# noise.
REFERENCE = re.compile(r"(?<![A-Za-z0-9])(?:references|scripts|assets)/[A-Za-z0-9._/-]+")
MARKDOWN_LINK = re.compile(r"\[[^\]]*\]\(([^)#\s]+)")
PLACEHOLDER = re.compile(r"(<[^>]*>|\$\{?[A-Za-z_]|\{\{|%s|\{name\})")

ABSOLUTE_PATH = re.compile(r"(?:[A-Za-z]:\\|/home/|/Users/|/root/|/var/|/etc/)")

TIME_SENSITIVE = re.compile(
    r"\b(as of (q[1-4]|20\d\d)|in (january|february|march|april|may|june|july|"
    r"august|september|october|november|december) 20\d\d|currently (as of|the)|"
    r"latest version is|at the time of writing)\b",
    re.IGNORECASE,
)

UNEXPECTED_BINARY = re.compile(r"\.(pyc|pyo|exe|dll|so|dylib|class|jar|bin)$", re.IGNORECASE)

# Text that marks a line as teaching by counter-example: `references/x.md`, never
# `references/a/b/c.md`, or "As of Q4 2024" rots.
NEGATION = re.compile(r"\b(never|avoid|don't|do not|not |instead|rots?|bad|wrong|anti-?pattern|counter-?example)\b", re.IGNORECASE)

# A quoted span is where an example lives. The first version of this file kept a
# line-level skip instead, which silently discarded real absolute paths on any
# line that happened to contain the word "not". Suppression is now narrow in two
# directions at once: the match must be inside backticks AND the line must read
# as a counter-example. Anything else is reported.
QUOTED = re.compile(r"`[^`]*`")


def quoted_ranges(line: str) -> list[tuple[int, int]]:
    return [(m.start(), m.end()) for m in QUOTED.finditer(line)]


def inside(index: int, ranges: list[tuple[int, int]]) -> bool:
    return any(start <= index < end for start, end in ranges)


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


def locate_skill_file(path: Path, allow_flat: bool = True) -> tuple[Path | None, bool]:
    """Return the file to check and whether it is the flat single-file form.

    A flat skill is one `.md` file dropped into a skills root. During a
    recursive walk the same shape appears inside a skill's own resource folders -
    `references/` holding a single document - so flat detection is restricted to
    directories that are not themselves resource folders, and the caller can turn
    it off entirely.
    """
    skill_file = path / "SKILL.md"
    if skill_file.is_file():
        return skill_file, False
    if not allow_flat or path.name.lower() in RESOURCE_DIRS:
        return None, False
    entries = list(path.iterdir())
    if any(entry.is_dir() for entry in entries):
        return None, False
    flat = sorted(p for p in path.glob("*.md") if p.name != "SKILL.md")
    if len(flat) == 1 and len(entries) == 1:
        return flat[0], True
    return None, False


def check(path: Path) -> Result:
    result = Result(path)
    skill_file, is_flat = locate_skill_file(path)

    if skill_file is None:
        result.fail("no SKILL.md (and no single flat .md file) in the folder")
        return result

    raw = skill_file.read_bytes()
    had_bom = raw.startswith(b"\xef\xbb\xbf")
    # utf-8-sig, not utf-8: a byte-order mark is what Windows editors write by
    # default, and reading it as content makes the checker blame the frontmatter
    # delimiters for a defect that is one byte long.
    text = raw.decode("utf-8-sig", errors="replace")

    if had_bom:
        result.warn(
            f"{skill_file.name} starts with a UTF-8 byte-order mark. Some harnesses "
            "read the frontmatter only when --- is the file's first character, so "
            "save it without the mark"
        )

    front, body = split_frontmatter(text)
    if not front:
        result.fail("no YAML frontmatter delimited by --- at the top of the file")
        return result

    # ── name ──────────────────────────────────────────────────────────────
    # The standard requires the name to match its directory. DSH does not
    # enforce it - it registers the frontmatter name and never compares the two -
    # so a mismatch works in DSH and breaks in a harness that does enforce it.
    # That is a portability defect, which is what the message says.
    expected = skill_file.stem if is_flat else path.name
    label = "file name" if is_flat else "folder"
    name = front.get("name")
    if not isinstance(name, str) or name == "":
        result.fail("frontmatter has no `name`")
    else:
        if not NAME_RE.match(name):
            result.fail(f"`name: {name}` is not kebab-case (a-z, digits, single hyphens)")
        if len(name) > MAX_NAME:
            result.fail(f"`name` is {len(name)} characters, the limit is {MAX_NAME}")
        if name != expected:
            result.fail(
                f"`name: {name}` does not match the {label} `{expected}`. The standard "
                "requires the two to be identical; DSH accepts a mismatch, other "
                "harnesses may not"
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
    # The standard recommends keeping SKILL.md under 500 lines; it is not a hard
    # limit and DSH caps nothing. The number here is the recommendation, and the
    # lower figure is only a prompt to think about splitting.
    body_lines = [line for line in body.splitlines() if line.strip() != ""]
    if len(body_lines) > MAX_BODY_LINES:
        result.fail(
            f"the body has {len(body_lines)} non-empty lines. The standard recommends "
            f"staying under {MAX_BODY_LINES}; move detail into references/"
        )
    elif len(body_lines) > COMFORTABLE_BODY_LINES:
        result.note(f"the body has {len(body_lines)} non-empty lines — fine for a procedure, worth watching")

    # ── files that should not be there ────────────────────────────────────
    # Walked, not just listed: a README dropped into references/ is the same
    # anti-pattern as one at the root. A script called install.sh is not.
    for entry in sorted(path.rglob("*")):
        if any(part in SKIP_DIRS for part in entry.parts) or entry.is_dir() or entry.name == skill_file.name:
            continue
        if LICENCE_STEM.match(entry.stem):
            continue
        where = entry.relative_to(path).as_posix()
        nested = "/" in where
        pattern = FORBIDDEN_ANYWHERE if nested else FORBIDDEN_STEM
        if pattern.match(entry.stem):
            result.fail(f"`{where}` is a human-facing file; a skill is read by an agent")
        elif entry.suffix.lower() == ".txt" and not nested:
            result.fail(f"`{where}` is a human-facing file; a skill is read by an agent")
        if UNEXPECTED_BINARY.search(entry.name):
            result.warn(f"`{where}` is compiled or binary and cannot be reviewed by reading it")

    # ── paths, per line so that quoted counter-examples can be skipped ────
    candidates: set[str] = set()
    for index, line in enumerate(text.splitlines(), 1):
        ranges = quoted_ranges(line)
        example = NEGATION.search(line) is not None
        for match in ABSOLUTE_PATH.finditer(line):
            if example and inside(match.start(), ranges):
                continue
            result.fail(f"line {index}: absolute path `{match.group(0)}` — use a path relative to the skill folder")
        for match in TIME_SENSITIVE.finditer(line):
            if example and inside(match.start(), ranges):
                continue
            result.warn(f"line {index}: `{match.group(0)}` will age badly; read live data or drop it")
        for match in REFERENCE.finditer(line):
            if example and inside(match.start(), ranges):
                continue
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


def collect_targets(root: Path) -> list[Path]:
    """Find skill folders and flat skill files anywhere under a root.

    The first version listed only the root's immediate subdirectories and skipped
    any whose name began with a dot - which is exactly where several harnesses,
    including DSH, keep their skills. Pointed at such a repository it printed
    "0 skill(s) checked" and exited 0: a gate that covered nothing and said so
    only if you read the count.
    """
    targets: list[Path] = []
    # The root is evaluated as well as everything under it. `rglob` yields
    # descendants only, so a root that *is* a flat skill directory was invisible
    # and the walk reported that it had found nothing.
    candidates = [root, *sorted(root.rglob("*"))]
    for path in candidates:
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if not path.is_dir():
            continue
        # Flat detection stays on during the walk. The resource-folder guard in
        # locate_skill_file is what prevents a lone document inside references/
        # from being read as a skill; turning flat detection off here instead
        # made the walk blind to a root that holds nothing but flat skills.
        skill_file, _ = locate_skill_file(path)
        if skill_file is not None:
            targets.append(path)
    return targets


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
    parser.add_argument("--recursive", "-r", action="store_true", help="search each path for skills, at any depth")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    args = parser.parse_args()

    targets: list[Path] = []
    for raw in args.paths:
        root = Path(raw)
        if not root.is_dir():
            print(f"FAIL  {root}: not a directory")
            return 1
        if args.recursive:
            targets.extend(collect_targets(root))
        else:
            targets.append(root)

    if args.recursive and not targets:
        print(f"FAIL  no skill found under {args.paths[0]} — check the --recursive root")
        return 1

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
