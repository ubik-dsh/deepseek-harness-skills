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
from urllib.parse import unquote

NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
MAX_NAME = 64
MAX_DESCRIPTION = 1024
MAX_BODY_LINES = 500
COMFORTABLE_BODY_LINES = 100
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv"}
# `__pycache__` is skipped when looking for skills, but not when looking for
# binaries: a compiled file inside a skill is exactly what a reader should be
# told about, and this checker's author committed one while shipping a rule
# against them.
BINARY_SCAN_SKIP = {".git", "node_modules", ".venv", "venv"}
MAX_SCAN_BYTES = 2 * 1024 * 1024
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

# No spaces in the class, deliberately. Allowing them made the pattern swallow
# whole command lines - `scripts/accept_changes.py in.docx out.docx` was reported
# as a missing file. A path containing a literal space is handled at resolution
# time instead, by trying the whole quoted span as a fallback.
REFERENCE = re.compile(r"(?<![A-Za-z0-9])(?:references|scripts|assets)/[A-Za-z0-9._%/-]+")
MARKDOWN_LINK = re.compile(r"\[[^\]]*\]\(([^)#\s]+)")
PLACEHOLDER = re.compile(r"(<[^>]*>|\$\{?[A-Za-z_]|\{\{|%s|\{name\})")

# `(?<![A-Za-z0-9])` guards the drive letter for the same reason it guards the
# reference paths: without it the `e:\` inside `file:\/\/documents` reads as an
# absolute Windows path, and a JavaScript URI example is reported as a portability
# defect. A drive letter starts a token or it is not a drive letter.
# The rule catches paths that only resolve where they were written: a user's home
# directory, a specific mount, a drive letter, a network share. Standard system
# locations are deliberately absent - `/tmp`, `/usr` and `/bin` mean the same
# thing on every Unix and flagging them produced noise in other people's skills.
# `//server/share` is also absent because it is indistinguishable from the `//`
# in `https://` and matched every URL in every document.
ABSOLUTE_PATH = re.compile(
    r"(?<![A-Za-z0-9])(?:[A-Za-z]:\\|/home/|/Users/|/root/|/mnt/|/srv/|/opt/"
    r"|\\\\[A-Za-z0-9._-]+\\)"
)

TIME_SENSITIVE = re.compile(
    r"\b(as of (q[1-4]|20\d\d)|in (january|february|march|april|may|june|july|"
    r"august|september|october|november|december) 20\d\d|currently (as of|the)|"
    r"latest version is|at the time of writing)\b",
    re.IGNORECASE,
)

UNEXPECTED_BINARY = re.compile(r"\.(pyc|pyo|exe|dll|so|dylib|class|jar|bin)$", re.IGNORECASE)

# A heading that admits the limit of the skill. Any of these phrasings counts.
# The optional word in the middle is not decoration: this file's own heading reads
# "What this skill does not cover", and the first version of the pattern missed it.
COVERAGE_SECTION = re.compile(
    r"^#{1,4}\s*.*(what this(?:\s+\w+){0,2}\s+(does not|doesn't) cover|not covered"
    r"|out of scope|limitations|what this is not|not tested|uncovered|known gaps)",
    re.IGNORECASE | re.MULTILINE,
)

# Text that marks a line as teaching by counter-example: `references/x.md`, never
# `references/a/b/c.md`, or "As of Q4 2024" rots.
NEGATION = re.compile(r"\b(never|avoid|don't|do not|not |instead|rots?|bad|wrong|anti-?pattern|counter-?example)\b", re.IGNORECASE)

# A quoted or bracketed path is where an example lives. Suppression is narrow in
# two directions at once: the match must be inside backticks or angle brackets
# AND the line must read as a counter-example. Anything else is reported.
#
# Bare prose is deliberately not collected as a reference. "Better scripts/tools
# that produced better output?" is a sentence, and reading it as a claim about a
# file made the checker cry wolf on somebody else's skill. Angle brackets are
# included because `<references/absent.md>` is how a real reference is often
# written, and leaving those out made the checker blind in the other direction.
QUOTED = re.compile(r"`[^`]*`|<[^<>\s]*[/\\][^<>\s]*>")


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


def _yaml_reader():
    """The YAML reader, if this machine has one.

    The question these rules answer is "does the frontmatter come back as a plain
    mapping", and the only authority on that is a parser. This checker used to refuse to
    ask one, on the reasoning that the parser is the thing being mistrusted — which is
    backwards, and produced two rules that were wrong in opposite directions: it rejected
    a double-quoted value containing a colon, and it rejected a plain value wrapped onto
    the next line, both of which YAML reads perfectly.

    Measured against the `yaml` package DSH itself bundles, over 18 constructs, PyYAML
    agreed with it on **every one** — wrapping, folded scalars, `allowed-tools:` and
    `tags:` sequences, nested `metadata:`, quoted and unquoted colons, an unterminated
    quote, and the compact-mapping error that actually blocks registration. So where a
    parser exists it is the answer, and the text rules below are the fallback for a
    machine without one.
    """
    try:
        import yaml
        return yaml.safe_load
    except ImportError:
        return None


def frontmatter_value_faults(text: str) -> tuple[list[tuple[int, str]], bool]:
    """What a YAML reader will object to in the frontmatter, and whether one was asked.

    Returns `(faults, parsed)`. When `parsed` is False the reader was missing and the
    faults come from text rules, which know only the constructs someone already met — so
    a clean result there is weaker than a clean result from a parse, and the caller says
    so rather than letting the two read alike.

    The real fault, measured and identical in both of its shapes, is **a nested mapping in
    a compact position**: a colon in an unquoted value (`description: a thing: b`), or an
    indented `key: value` under a value that already has one. A wrapped plain scalar is
    not a fault, and neither is an indented `- item`. DSH parses the frontmatter and
    silently declines to register a skill whose parse fails, so the file is invisible and
    nothing is reported.

    History, because both versions were wrong in ways worth not repeating: the first
    reported every nested key as a continuation, since keys under `metadata:` are indented
    too. The second fixed that and then reported the continuation of a plain scalar and
    every YAML list as faults — a checker that tells an author to mangle a correct file is
    worse than one that misses a broken one, because the author believes it.
    """
    lines = text.split("\n")
    if not lines or lines[0].rstrip("\r") != "---":
        return [], True

    closing = None
    for index in range(1, len(lines)):
        if lines[index].rstrip("\r") == "---":
            closing = index
            break
    if closing is None:
        return [], True

    block = "\n".join(line.rstrip("\r") for line in lines[1:closing])

    reader = _yaml_reader()
    if reader is not None:
        try:
            reader(block)
        except Exception as trouble:                    # noqa: BLE001 - any parse failure
            mark = getattr(trouble, "problem_mark", None)
            problem = getattr(trouble, "problem", None) or str(trouble).splitlines()[0]
            where = mark.line + 2 if mark is not None else 1
            return ([(
                where,
                f"a YAML reader rejects this frontmatter - {problem}. DSH parses the "
                "frontmatter and declines to register a skill it cannot read, reporting "
                "nothing, so this file is invisible until it is fixed. The usual cause is "
                "a colon in an unquoted value: wrap the whole value in quotes, or use a "
                "dash",
            )], True)
        return [], True

    faults: list[tuple[int, str]] = []
    key_re = re.compile(r"^(\s*)([A-Za-z_][A-Za-z0-9_-]*):(.*)$")
    block_markers = ("|", ">", "|-", ">-", "|+", ">+")
    in_block = False
    # True while the key just read is a top-level key that already carries a scalar. An
    # indented key under one of those is the compact-mapping error; an indented key under
    # a key with no value (`metadata:`) is an ordinary nested mapping.
    scalar_open = False

    for index in range(1, closing):
        line = lines[index].rstrip("\r")
        stripped = line.strip()
        if stripped == "" or stripped.startswith("#"):
            continue
        indent = len(line) - len(line.lstrip(" \t"))

        if in_block:
            if indent > 0:
                continue
            in_block = False

        match = key_re.match(line)
        if match is None:
            if indent > 0:
                # An indented line that is not `key: value` is either a sequence item, a
                # wrapped plain scalar, or prose. YAML folds all three, so none is a
                # fault — unless it carries a colon, which opens the compact mapping
                # again. Measured: `description: x` followed by `  more: prose` errors,
                # followed by `  more prose` does not.
                if not stripped.startswith("-") and ": " in line:
                    faults.append((
                        index + 1,
                        f"`{stripped[:38]}` continues a value and carries a colon, which "
                        "a YAML reader takes as a nested mapping. Keep every frontmatter "
                        "value on one line; prose belongs in the body",
                    ))
            else:
                faults.append((index + 1, f"no colon - `{stripped[:38]}` is not a key"))
            continue

        value = match.group(3).strip()
        if indent > 0 and scalar_open:
            # The other shape of the same fault, and the reason this rule exists at all.
            # `metadata:` with keys under it is fine, because that key has no value;
            # `description: something` with a key under it is a compact mapping and the
            # reader refuses the whole document. Measured both ways.
            faults.append((
                index + 1,
                f"`{match.group(2)}` is indented under a value that already has one, "
                "which a YAML reader takes as a nested mapping. Keep every frontmatter "
                "value on one line; prose belongs in the body",
            ))
            scalar_open = False
            continue

        if value in block_markers:
            in_block = True
            scalar_open = False
            continue

        # A quoted scalar is a string whatever is inside it. Checked before the masking
        # below, because the masking knows about backticks and angle brackets and knows
        # nothing about the quotes that decide this question.
        if is_quoted_scalar(value):
            scalar_open = indent == 0
            continue

        masked = value
        for begin, finish in reversed(quoted_ranges(value)):
            masked = masked[:begin] + " " * (finish - begin) + masked[finish:]
        if ": " in masked:
            faults.append((
                index + 1,
                f"`{match.group(2)}` contains a colon in an unquoted value. A YAML "
                "reader takes it as a nested mapping and DSH then declines to register "
                "the skill, reporting nothing. Wrap the whole value in quotes, or use a "
                "dash",
            ))
        scalar_open = indent == 0 and value != ""

    return faults, False


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

    # ── frontmatter values that a reader will not treat as values ─────────
    # Found by a fresh agent, after every other check here had passed: a colon inside a
    # value. DSH reads the frontmatter with a YAML parser and silently declines to
    # register a skill whose mapping does not come back whole. The file looks fine, the
    # name matches, and `skill <name>` answers "unknown or no longer available".
    #
    # The parser is asked first now, and this comment used to argue the opposite — that
    # asking the parser whether it understood the file answers nothing, because the parser
    # is what is being mistrusted. That reasoning is backwards and it cost two rules that
    # rejected valid YAML: a quoted value containing a colon, and a plain value wrapped
    # onto the next line. A parser is not a suspect here; it is the only witness.
    faults, parsed = frontmatter_value_faults(text)
    if not parsed:
        result.note(
            "the YAML reader is not installed here, so the frontmatter was checked with "
            "text rules instead of by parsing it. A clean result is weaker than a parse: "
            "the rules know only the constructs someone has already met"
        )
    for line_number, complaint in faults:
        result.fail(f"frontmatter line {line_number}: {complaint}")

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
    # limit and DSH caps nothing. Total lines, not non-empty ones: counting only
    # the lines with content let a 605-line file pass a 500-line rule.
    total_lines = len(body.splitlines())
    non_empty = [line for line in body.splitlines() if line.strip() != ""]
    if total_lines > MAX_BODY_LINES:
        result.fail(
            f"the body is {total_lines} lines. The standard recommends staying under "
            f"{MAX_BODY_LINES}; move detail into references/"
        )
    elif len(non_empty) > COMFORTABLE_BODY_LINES:
        result.note(f"the body has {len(non_empty)} non-empty lines — fine for a procedure, worth watching")

    # ── a stated limit ────────────────────────────────────────────────────
    # Silence about the edges is read as covering them, which makes it a claim.
    # Borrowed from the vendor skill's early-stop disclosure; see
    # references/borrowed-practices.md.
    if not COVERAGE_SECTION.search(body):
        result.warn(
            "the body does not say what the skill does not cover. Name the inputs it "
            "was not tried on and the cases it skips, or a reader will assume there "
            "are none"
        )

    # ── files that should not be there, and binaries ──────────────────────
    # Walked, not just listed: a README dropped into references/ is the same
    # anti-pattern as one at the root. A script called install.sh is not.
    documents: list[Path] = []
    for entry in sorted(path.rglob("*")):
        if entry.is_dir() or entry.name == skill_file.name:
            continue
        if any(part in BINARY_SCAN_SKIP for part in entry.parts):
            continue
        where = entry.relative_to(path).as_posix()
        if UNEXPECTED_BINARY.search(entry.name):
            result.warn(f"`{where}` is compiled or binary and cannot be reviewed by reading it")
        if any(part in SKIP_DIRS for part in entry.parts):
            continue
        if LICENCE_STEM.match(entry.stem):
            continue
        nested = "/" in where
        pattern = FORBIDDEN_ANYWHERE if nested else FORBIDDEN_STEM
        if pattern.match(entry.stem):
            result.fail(f"`{where}` is a human-facing file; a skill is read by an agent")
        elif entry.suffix.lower() == ".txt" and not nested:
            result.fail(f"`{where}` is a human-facing file; a skill is read by an agent")
        if entry.suffix.lower() == ".md" and entry.stat().st_size <= MAX_SCAN_BYTES:
            documents.append(entry)

    # ── the same rules, applied to everything the agent will read ─────────
    # The first version read SKILL.md and stopped. A dated fact or an absolute
    # path in references/ was invisible, which made the checker's scope narrower
    # than its own rule: the material in references/ is loaded by the agent just
    # as the body is.
    for document in [skill_file, *sorted(set(documents))]:
        if document != skill_file and document.resolve() == skill_file.resolve():
            continue
        where = document.relative_to(path).as_posix()
        try:
            body_text = document.read_bytes().decode("utf-8-sig", errors="replace")
        except OSError:
            continue
        candidates: set[str] = set()
        spans: set[str] = set()
        for index, line in enumerate(body_text.splitlines(), 1):
            ranges = quoted_ranges(line)
            example = NEGATION.search(line) is not None
            for start, end in ranges:
                spans.add(line[start:end].strip("`<>").strip().rstrip(".,;:)"))
            for match in ABSOLUTE_PATH.finditer(line):
                if example and inside(match.start(), ranges):
                    continue
                result.fail(f"{where}:{index}: absolute path `{match.group(0)}` — use a path relative to the skill folder")
            for match in TIME_SENSITIVE.finditer(line):
                if example and inside(match.start(), ranges):
                    continue
                result.warn(f"{where}:{index}: `{match.group(0)}` will age badly; read live data or drop it")
            for match in REFERENCE.finditer(line):
                if example and inside(match.start(), ranges):
                    continue
                # Only a quoted, bracketed or linked path is a claim about a
                # file. Prose that happens to contain `scripts/tools` is a
                # sentence, and treating it as a reference made the checker
                # report a broken link in a skill that had none.
                if inside(match.start(), ranges):
                    candidates.add(match.group(0).rstrip(".,;:)"))
            for match in MARKDOWN_LINK.finditer(line):
                target = match.group(1).strip()
                if target.startswith(("http://", "https://", "mailto:", "#")):
                    continue
                candidates.add(target)

        # Links inside a document resolve against that document's own folder.
        base = document.parent
        for candidate in sorted(candidates):
            if PLACEHOLDER.search(candidate):
                continue
            if resolves(base, path, candidate):
                if candidate.count("/") > 1:
                    result.warn(f"{where}: `{candidate}` is nested more than one level deep")
                continue
            # The pattern stops at a space, so `references/my doc.md` arrives here
            # as `references/my`. Before reporting it, try any quoted span on the
            # page that begins with it: if the longer form exists, the path is
            # real and only the splitting was wrong.
            if any(span.startswith(candidate) and resolves(base, path, span) for span in spans):
                continue
            result.fail(f"{where}: referenced file does not exist: `{candidate}`")

    return result


def resolves(base: Path, root: Path, candidate: str) -> bool:
    """Does a path mentioned in the text point at something real?

    Prose names a script without its extension (`scripts/check_fields` for
    `check_fields.py`) and names folders as readily as files. Failing those as
    broken links makes the checker cry wolf, so a match is accepted when the
    path exists, exists with a common suffix, or exists as a directory.
    """
    for target in (base / candidate, root / candidate):
        if target.exists():
            return True
        for suffix in (".py", ".sh", ".mjs", ".js", ".md", ".json", ".yaml", ".yml", ".txt"):
            if target.with_suffix(suffix).exists():
                return True
    # A markdown link target is URL-encoded; a file on disk is not. `my%20doc.md`
    # in the text has to be matched against the `my doc.md` that exists.
    decoded = unquote(candidate)
    if decoded != candidate:
        for target in (base / decoded, root / decoded):
            if target.exists():
                return True
    return False


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
