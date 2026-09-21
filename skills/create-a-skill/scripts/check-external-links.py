#!/usr/bin/env python3
"""Check the EXTERNAL links in a repository, which the relative-link checker does not.

`test-links.mjs` resolves relative paths and anchors and says PASS on a repository carrying a dead URL,
because a URL pointing at somebody else's server is not a path it can resolve. That gap let
`https://agentskills.io/specification` sit in twelve files - the standard this whole family cites - until
the operator tried to open it and found nothing there.

A dead external link is worse than a dead internal one: an internal one is a typo, and an external one is
a claim about the world that has stopped being true.

    python check-external-links.py <repo> [--only-host agentskills.io] [--timeout 20]

Exit 0 when every link answers, 1 when some do not, 2 when the repository has no external links at all.

DELIBERATELY NOT PART OF check-skill.py. It needs the network, it is slow, and a check that cannot run on
a plane is a check that gets disabled. Run it before publishing, not before every edit.
"""
from __future__ import annotations

import argparse
import re
import sys
import urllib.error
import urllib.request
from collections import defaultdict
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")

URL = re.compile(r"https?://[^\s)\]\"'<>]+")
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", "_graph"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("repo", type=Path)
    ap.add_argument("--only-host", default="", help="check just this host")
    ap.add_argument("--timeout", type=int, default=20)
    args = ap.parse_args()
    repo = args.repo.resolve()

    found: dict[str, list[str]] = defaultdict(list)
    for path in sorted(repo.rglob("*.md")):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for url in URL.findall(text):
            url = url.rstrip(".,;:")
            if args.only_host and args.only_host not in url:
                continue
            found[url].append(path.relative_to(repo).as_posix())

    if not found:
        print("  внешних ссылок не найдено")
        return 2

    print(f"  проверяю {len(found)} внешних ссылок\n")
    dead, alive = [], 0
    for url in sorted(found):
        request = urllib.request.Request(url, method="HEAD",
                                         headers={"User-Agent": "dsh-link-check/1"})
        status = ""
        try:
            with urllib.request.urlopen(request, timeout=args.timeout) as answer:
                status = f"HTTP {answer.status}"
                alive += 1
        except urllib.error.HTTPError as trouble:
            # A REFUSAL IS NOT A DEATH. 403 and 405 mean the server dislikes HEAD, and 418 and 429 mean
            # it recognised a robot and turned it away - VK answers 418 to every automated request. The
            # first version of this file called all of those dead and reported seven live VK links as
            # broken, which is the same mistake as a checker that passes a dead link: reading a status
            # code as an answer to a question it was never asked.
            if trouble.code in (403, 405, 418, 429):
                status = f"HTTP {trouble.code} (сервер жив, робота не пускает)"
                alive += 1
            else:
                status = f"HTTP {trouble.code}"
        except Exception as trouble:                      # noqa: BLE001
            status = type(trouble).__name__
        if status.startswith("HTTP 2") or "робота не пускает" in status:
            print(f"    ok    {status:34} {url[:70]}")
        else:
            dead.append((url, status, found[url]))
            print(f"    МЁРТВА {status:33} {url[:70]}")

    if dead:
        print(f"\n  МЁРТВЫХ ССЫЛОК: {len(dead)}")
        for url, status, where in dead:
            print(f"    {url}")
            print(f"      {status}; встречается в {len(where)}: {', '.join(where[:4])}")
        return 1
    print(f"\n  все {alive} ссылок отвечают")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
