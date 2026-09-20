#!/usr/bin/env python3
"""Russian micro-typography for text that will be pasted into a platform that strips CSS.

The rules are adopted from Shadowru/crosspost-design-skill's references/typography-ru.md,
AGPL-3.0 - **the table is borrowed, the code is not**: this is a reimplementation written
from the rules, which is what find-a-skill requires of anything downloaded.

It is reimplemented for one concrete reason. Their range rule is `(?<=\\d)\\s?-\\s?(?=\\d)`,
and it turns all three of these into en dashes:

    ГОСТ 7.32-2017          ->  ГОСТ 7.32–2017
    8-800-555-35-35         ->  8-800-555-35–35
    1-2-3                   ->  1-2–3

None of the three is a range. Two of them are identifiers a reader may have to type. A
linter that corrupts a document while reporting success is worse than one that is silent,
so the range rule here requires the hyphen to be the whole token: nothing numeric, dotted
or hyphenated on either side of it.

    python typo_lint.py article.md              report
    python typo_lint.py article.md --fix        rewrite in place
    python typo_lint.py article.md --nbsp       also bind short words and units

Exit 0 when clean, 1 when anything was reported, 2 on a usage error.

Eight of the nine rules are mechanical. The ninth is not, and the file says so instead of
passing it silently:

  * "Дефис только внутри слова" - `кто — то` should be `кто-то`. Whether it should is a
    question about meaning, and no regular expression answers it. It is reported as a
    question for the reader, never fixed.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# Anything between these markers is not prose and is masked before the rules run. Without
# this the linter "fixes" code samples and URLs, which is how a typography pass breaks a
# document that was correct.
MASKED = re.compile(
    r"```.*?```"                     # fenced code
    r"|`[^`]*`"                      # inline code
    r"|https?://\S+"                 # urls
    r"|\{\{[^}]*\}\}"                # placeholders
    r"|<!--.*?-->",                  # html comments
    re.S)

# Rules that rewrite. Each is (name, pattern, replacement).
FIXES: list[tuple[str, re.Pattern[str], str]] = [
    ("ellipsis", re.compile(r"\.\.\."), "…"),
    # Nested quotes first, or the outer rule below swallows them and a quotation inside a
    # quotation comes out as two « » pairs at the same level, which is wrong in Russian.
    ("nested quotes", re.compile(r"«([^»]*)\"([^\"]*)\"([^»]*)»"), r"«\1„\2“\3»"),
    ("outer quotes", re.compile(r"\"([^\"\n]+)\""), r"«\1»"),
    # The narrowed range rule. A hyphen with a digit, a dot or another hyphen beside it
    # belongs to a longer token - a standard number, a telephone number, a version - and
    # is left alone.
    ("numeric range", re.compile(r"(?<![\d.\-])(\d{1,4})-(\d{1,4})(?![\d\-])"), r"\1–\2"),
    ("spaced hyphen as a dash", re.compile(r"(?<=\w) - (?=\w)"), " — "),
    ("space before punctuation", re.compile(r"(?<=\S) +([,.;:!?])"), r"\1"),
    ("space after punctuation", re.compile(r"([,;:])(?=[^\s\d])"), r"\1 "),
    ("double space", re.compile(r"(?<=\S)  +(?=\S)"), " "),
]

# Rules that only report, because fixing them needs a decision.
REPORTS: list[tuple[str, re.Pattern[str], str]] = [
    ("an odd number of straight quotes", re.compile(r"^\s*\"[^\"\n]*$", re.M),
     "an unpaired straight quote has no mechanical repair - the closing one is missing, or "
     "it is an apostrophe, and only the reader can tell which"),
    ("hyphen used as a dash inside a word", re.compile(r"\b\w+ — \w+\b"),
     "if this is one word it needs a hyphen (`кто-то`); if it is two, the dash is right. "
     "Only the reader can say - this rule never fixes itself"),
    ("two exclamation marks, or a mixed pair", re.compile(r"!!|\?!|\!\?"),
     "one exclamation mark in an article is already a lot"),
    ("a run of capitals", re.compile(r"\b[А-ЯA-Z]{4,}\b"),
     "capitals read as shouting; use bold"),
]

# Bound to the following word so it cannot start a line alone.
NBSP = "\u00a0"
NBSP_AFTER = re.compile(r"\b(в|во|на|за|из|к|ко|с|со|о|об|от|до|по|у|и|а|но|да|не|ни|"
                        r"же|ли|бы|для|при|над|под|про|без|через|между|или|что|как|это)\s+")
NBSP_NUMBER = re.compile(r"(\d+)\s+(кг|г|м|км|см|мм|мл|л|%|руб|тыс|млн|млрд|ч|мин|с|°C|°)")


def mask(text: str) -> tuple[str, list[str]]:
    kept: list[str] = []

    def swap(match: re.Match[str]) -> str:
        kept.append(match.group(0))
        return f"\x00{len(kept) - 1}\x00"

    return MASKED.sub(swap, text), kept


def unmask(text: str, kept: list[str]) -> str:
    for index, original in enumerate(kept):
        text = text.replace(f"\x00{index}\x00", original)
    return text


def find(text: str) -> list[tuple[int, str, str]]:
    """(line number, rule, the offending text) for every report-only rule."""
    found: list[tuple[int, str, str]] = []
    for name, pattern, _ in REPORTS:
        for match in pattern.finditer(text):
            line = text.count("\n", 0, match.start()) + 1
            found.append((line, name, match.group(0)[:48]))
    return sorted(found)


def fix(text: str) -> tuple[str, int]:
    masked, kept = mask(text)
    count = 0
    for _, pattern, replacement in FIXES:
        masked, changes = pattern.subn(replacement, masked)
        count += changes
    if NBNS_ENABLED[0]:
        masked, changes = NBSP_AFTER.sub(lambda m: m.group(1) + NBSP, masked)
        count += changes
        masked, changes = NBSP_NUMBER.sub(lambda m: m.group(1) + NBSP + m.group(2), masked)
        count += changes
    return unmask(masked, kept), count


NBNS_ENABLED = [False]


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    except AttributeError:
        pass

    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("article", type=Path)
    parser.add_argument("--fix", action="store_true", help="rewrite the file in place")
    parser.add_argument("--nbsp", action="store_true",
                        help="also bind short words and units with a non-breaking space")
    args = parser.parse_args()

    if not args.article.exists():
        print(f"  no such file: {args.article}", file=sys.stderr)
        return 2

    # utf-8-sig on the way in, because that is what a Windows editor writes, and the mark
    # would otherwise reach the first rule as content.
    text = args.article.read_text(encoding="utf-8-sig", errors="replace")
    NBNS_ENABLED[0] = args.nbsp

    fixed, count = fix(text)
    questions = find(fixed)

    if args.fix and fixed != text:
        # newline="" and no BOM: the file is prose, and a byte-order mark on a document a
        # platform will paste is a stray character at the top of the article.
        args.article.write_text(fixed, encoding="utf-8", newline="")
        print(f"  rewrote {args.article}  ({count} change(s))")
    elif count:
        print(f"  {count} mechanical change(s) available - run again with --fix")

    if questions:
        print()
        print(f"  {len(questions)} thing(s) a rule will not decide for you:")
        for line, name, sample in questions:
            print(f"    line {line:5}  {name}")
            print(f"                 {sample!r}")

    print()
    if count == 0 and not questions:
        print("  clean - no rule fired and nothing was left for the reader")
        return 0
    print(f"  {count} mechanical, {len(questions)} for the reader")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
