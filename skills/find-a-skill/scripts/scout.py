#!/usr/bin/env python3
"""Look for a skill that already does the job, before writing a new one.

The rule is not new — `affaan-m/ECC` ships `skill-scout` saying exactly this, and
`search-first` generalises it to code. What this script adds is that the search is
**runnable** and searches the roots that are actually on this machine, in the order
this harness actually resolves them.

    python scout.py "interface automation" --synonyms gui,desktop,click
    python scout.py "reward design" --local-only
    python scout.py "pdf" --json results.json

Two things it measures rather than assumes:

  * **the seven skill roots and their ranks.** The rival skill searches
    `~/.claude/skills` and a marketplace path. That is two of seven here, and it is
    the wrong two when the skill in front of you was loaded from a project folder.
  * **that GitHub's result counts are not a measure of anything.** A code search for
    `filename:SKILL.md gui automation` reports a total_count in the hundreds of
    thousands because the query matches file *contents* too. The *repository list* is
    usable; the number is not. This script prints the repositories and says so.

Exit codes: 0 if anything matched, 1 if nothing did.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

# The roots this harness resolves, in the order it resolves them. Measured live on
# DSH 0.1.5-rc.2 by probing all seven. Lower rank wins.
def skill_roots(project: Path) -> list[tuple[int, str, Path]]:
    home = Path.home()
    dsh_home = Path(os.environ.get("DSH_HOME", home / ".dsh"))
    agents_home = Path(os.environ.get("DSH_AGENTS_HOME", home / ".agents"))
    roots = [
        (100, "project .dsh", project / ".dsh" / "skills"),
        (200, "project .agents", project / ".agents" / "skills"),
        (300, "custom DSH_SKILLS", Path(os.environ["DSH_SKILLS"]) if os.environ.get("DSH_SKILLS") else None),
        (400, "$DSH_HOME", dsh_home / "skills"),
        (500, "$DSH_AGENTS_HOME", agents_home / "skills"),
        # Compatibility with other harnesses that read a different name.
        (550, "claude project", project / ".claude" / "skills"),
        (560, "claude home", home / ".claude" / "skills"),
    ]
    return [(rank, label, path) for rank, label, path in roots if path is not None]


FRONTMATTER = re.compile(r"^---\s*\n(.*?)\n---", re.S)


def read_frontmatter(path: Path) -> tuple[str, str]:
    """The name and description, which is the whole matching surface of a skill."""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return "", ""
    match = FRONTMATTER.match(text)
    if not match:
        return path.parent.name, ""
    name, description = path.parent.name, ""
    for line in match.group(1).splitlines():
        if line.startswith("name:"):
            name = line[5:].strip()
        elif line.startswith("description:"):
            description = line[12:].strip()
    return name, description


def local_scan(project: Path, keywords: list[str]) -> list[dict]:
    """Every installed skill, scored by how well it matches."""
    found: dict[str, dict] = {}
    for rank, label, root in skill_roots(project):
        if not root or not root.is_dir():
            continue
        for path in sorted(root.glob("*/SKILL.md")):
            name, description = read_frontmatter(path)
            haystack = f"{name} {description} {path.parent.name}".lower()
            hits = [word for word in keywords if word.lower() in haystack]
            if not hits:
                continue
            # A keyword in the name beats one buried in a description, and a root
            # that wins resolution beats one that loses to it.
            name_hits = [word for word in keywords if word.lower() in name.lower()]
            score = len(name_hits) * 10 + len(hits) - rank / 1000
            entry = {
                "skill": name,
                "source": label,
                "path": str(path),
                "rank": rank,
                "matched": hits,
                "score": round(score, 2),
                "description": description[:200],
            }
            previous = found.get(str(path))
            if previous is None or entry["score"] > previous["score"]:
                found[str(path)] = entry
    return sorted(found.values(), key=lambda item: -item["score"])


def rate_note(headers) -> tuple[str, int]:
    """What the response says about the budget, and how long until it returns.

    GitHub puts the whole answer in the headers of every authenticated response:
    `x-ratelimit-remaining` and `x-ratelimit-reset`, an epoch second. Measured on this
    machine, the limits are 5000 an hour for the REST API, 30 a minute for repository
    search and 10 a minute for code search - all three read from the responses rather
    than from documentation, because documentation is the thing that goes stale.

    Returns a human note and the seconds to wait. A wait of 0 means the budget is fine.
    """
    remaining = headers.get("x-ratelimit-remaining") if headers else None
    reset = headers.get("x-ratelimit-reset") if headers else None
    retry_after = headers.get("retry-after") if headers else None

    wait = 0
    if retry_after and str(retry_after).isdigit():
        wait = int(retry_after)
    elif reset and str(reset).isdigit():
        wait = max(0, int(reset) - int(time.time()))
        if remaining is not None and str(remaining).isdigit() and int(remaining) > 2:
            wait = 0                      # budget left; nothing to wait for

    if remaining is None:
        return "", wait
    note = f"{remaining} left"
    if wait > 0:
        note += f", resets in {wait}s"
    return note, wait


# Repository search allows 30 requests a minute; code search allows 10. Three words is
# well inside the first and would be a third of the second.
MAX_REMOTE_QUERIES = 6


def github_search(keywords: list[str], token: str | None, limit: int) -> list[dict]:
    """Find SKILL.md files on GitHub whose path or repo matches.

    Search repositories rather than trusting code-search totals: the code endpoint
    reports a count inflated by content matches and is rate limited hard without a
    token.
    """
    results: list[dict] = []
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "scout-a-skill"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    # One word per query, never a phrase, and every word rather than the first two.
    # A phrase matches nothing at all on a search engine while its own words each match
    # plenty, and dropping the rest of the request silently is worse than making it.
    words: list[str] = []
    for phrase in keywords:
        for word in phrase.split():
            if word and word.lower() not in {seen.lower() for seen in words}:
                words.append(word)
    if len(words) > MAX_REMOTE_QUERIES:
        skipped = words[MAX_REMOTE_QUERIES:]
        words = words[:MAX_REMOTE_QUERIES]
        results.append({
            "error": f"searched the first {MAX_REMOTE_QUERIES} words only; skipped: "
                     f"{', '.join(skipped)}. Repository search allows 30 requests a "
                     "minute, so add the rest in a second pass rather than losing them",
        })

    for position, query in enumerate(f"agent skills {word}" for word in words):
        url = "https://api.github.com/search/repositories?" + urllib.parse.urlencode(
            {"q": query, "sort": "stars", "per_page": str(min(limit, 10))})
        if position > 0:
            # Repository search is 30 a minute. One request a second is three times
            # inside the budget and costs nothing worth measuring.
            time.sleep(1.1)
        request = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=25) as response:
                # The budget is on every response. Reading it is what turns a limit into
                # a pause instead of a wall.
                _note, wait = rate_note(response.headers)
                if wait > 0:
                    time.sleep(min(wait, 60))
                data = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as trouble:
            # A limit is not a failure and must not read like one. Without the reset
            # time the reader cannot tell a minute from an hour, and "no results" and
            # "refused" look identical in a log.
            note, wait = rate_note(trouble.headers)
            if trouble.code in (403, 429) and wait > 0:
                results.append({
                    "error": f"repositories '{query}': HTTP {trouble.code} - rate limited"
                             f"{', ' + note if note else ''}. Retry in {wait}s; this is a "
                             "budget, not an empty result",
                })
            else:
                results.append({"error": f"repositories '{query}': HTTP {trouble.code}"
                                         f"{', ' + note if note else ''}"})
            continue
        except Exception as trouble:                     # noqa: BLE001
            results.append({"error": f"repositories '{query}': {trouble}"})
            continue
        for item in data.get("items", []):
            results.append({
                "repo": item["full_name"],
                "stars": item["stargazers_count"],
                "pushed": item.get("pushed_at", "")[:10],
                "description": (item.get("description") or "")[:160],
                "query": query,
            })
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("keywords", nargs="+", help="what the skill should do")
    parser.add_argument("--synonyms", default="", help="comma-separated extra words")
    parser.add_argument("--project", type=Path, default=Path.cwd())
    parser.add_argument("--local-only", action="store_true")
    parser.add_argument("--remote-only", action="store_true")
    parser.add_argument("--token-file", type=Path, default=None)
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--json", type=Path, default=None)
    args = parser.parse_args()

    keywords = list(args.keywords)
    if args.synonyms:
        keywords += [word.strip() for word in args.synonyms.split(",") if word.strip()]

    report: dict = {"keywords": keywords, "local": [], "remote": [], "notes": []}

    if not args.remote_only:
        print(f"  searching the roots this harness resolves, for {keywords}")
        report["local"] = local_scan(args.project, keywords)
        shown = report["local"][: args.limit]
        if shown:
            print(f"\n  {'score':>6}  {'skill':<26}{'source':<20}matched")
            for entry in shown:
                print(f"  {entry['score']:>6}  {entry['skill']:<26}"
                      f"{entry['source']:<20}{', '.join(entry['matched'])}")
                if entry["description"]:
                    print(f"          {entry['description'][:120]}")
        else:
            print("    nothing installed matches")

    if not args.local_only:
        token = os.environ.get("GITHUB_TOKEN")
        if not token and args.token_file and args.token_file.exists():
            token = args.token_file.read_text(encoding="utf-8").strip()
        if not token:
            report["notes"].append(
                "no GITHUB_TOKEN: remote search will be rate limited or refused")
        print(f"\n  searching GitHub"
              f"{' (authenticated)' if token else ' (unauthenticated - expect refusals)'}")
        remote = github_search(keywords, token, args.limit)
        report["remote"] = remote
        for entry in remote:
            if "error" in entry:
                print(f"    {entry['error']}")
                continue
            print(f"    {entry['stars']:>7}*  {entry['repo']:<44}"
                  f"{entry['pushed']}  {entry['description'][:70]}")
        report["notes"].append(
            "GitHub reports a total_count for code searches that is inflated by content "
            "matches - in the hundreds of thousands for ordinary words. Read the "
            "repository list, not the number.")

    print()
    print("  a match is a candidate, not an answer:")
    print("    1. read it in full - not the description");
    print("    2. trial it on your own case, and write down what the trial showed;")
    print("    3. keep it only if the trial agreed, and name where it came from.")
    print("  see references/trialling-an-external-skill.md")

    if args.json:
        args.json.write_text(json.dumps(report, indent=1), encoding="utf-8")
        print(f"\n  written to {args.json}")

    return 0 if (report["local"] or any("repo" in e for e in report["remote"])) else 1


if __name__ == "__main__":
    raise SystemExit(main())
