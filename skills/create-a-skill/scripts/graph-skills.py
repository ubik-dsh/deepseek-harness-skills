#!/usr/bin/env python3
"""The family's own graph: what points at what, and how well each edge is signposted.

A map is only useful if its signs say how they were made. Every edge here carries one of four marks,
and NONE OF THEM IS HAND-WRITTEN - each is computed from the evidence in the file:

    EXTRACTED  a written link      `[text](path.md)` whose target resolves. The author declared it.
    INFERRED   a bare mention      the target's name appears in prose with no link. Named, not linked.
    AMBIGUOUS  a mention matching more than one file. A sign pointing at two places.
    ORPHAN     no inbound EXTRACTED edge at all. A road with no sign to it.

That is the point of the labels: a reader can tell a surveyed road from a guess without trusting
anybody's memory, because the difference is the shape of the text.

    python graph-skills.py <skills-repo> [--out _graph]

The output is markdown with relative links, so opening the REPOSITORY as an Obsidian vault makes the
graph pane work with no plugin and no copying. Nothing is duplicated: the pages point at the real files.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")

LINK = re.compile(r"\[[^\]]*\]\(([^)#\s]+\.md)(?:#[^)]*)?\)")
CODE = re.compile(r"`([^`\n]+)`")
HEADING = re.compile(r"^#{2,3}\s+(.*)$", re.M)

# A sentence long enough to be a claim rather than a phrase. Used to find the same rule written twice,
# which is how a file comes to contradict itself.
CLAIM_MIN_WORDS = 12


def walk(repo: Path) -> dict[str, dict]:
    """Every node: its kind, its skill, and the text it exposes to the graph."""
    nodes: dict[str, dict] = {}
    for skill_dir in sorted(p for p in (repo / "skills").iterdir() if (p / "SKILL.md").exists()):
        name = skill_dir.name
        for path in sorted(skill_dir.rglob("*")):
            if not path.is_file() or "__pycache__" in path.parts:
                continue
            rel = path.relative_to(repo).as_posix()
            if path.name == "SKILL.md":
                kind = "skill"
            elif "references" in path.parts:
                kind = "reference"
            elif "scripts" in path.parts:
                kind = "script"
            elif "assets" in path.parts or "templates" in path.parts:
                kind = "asset"
            else:
                kind = "file"
            text = ""
            if path.suffix in {".md", ".py", ".ps1", ".mjs", ".js", ".json", ".yaml", ".yml"}:
                try:
                    text = path.read_text(encoding="utf-8", errors="replace")
                except OSError:
                    text = ""
            nodes[rel] = {"path": rel, "kind": kind, "skill": name, "name": path.name,
                          "text": text, "lines": text.count("\n") + 1 if text else 0}
    return nodes


def edges(nodes: dict[str, dict], repo: Path) -> list[dict]:
    """Every edge, with the mark that says how it was established."""
    found: list[dict] = []
    by_name: dict[str, list[str]] = defaultdict(list)
    for rel, node in nodes.items():
        by_name[node["name"]].append(rel)

    # What each node can be called. Three keys, because a file is named three ways and the first two
    # versions of this knew only one of them: the path from the repository root, the path from inside
    # its own skill (which is how a SKILL.md actually writes it - `scripts/preflight.py`), and the bare
    # name when that name is unique in the family.
    identities: dict[str, list[str]] = {}
    for rel, node in nodes.items():
        keys = [rel]
        inside = rel.split("/", 2)[-1]
        if inside != rel:
            keys.append(inside)
        if len(by_name[node["name"]]) == 1:
            keys.append(node["name"])
        identities[rel] = keys

    def by_name_key(rel: str) -> str:
        return nodes[rel]["name"]

    for rel, node in nodes.items():
        if not node["text"]:
            continue
        # MARKDOWN LINKS ARE ONLY READ IN MARKDOWN. The first version scanned every file for
        # `[text](path)` and reported eight dangling links that do not exist - they were fixtures
        # inside check-skill.py's own tests, and an example in a docstring is not a link. A tool that
        # reads code as prose invents findings.
        reads_links = node["path"].endswith(".md")
        for number, line in enumerate(node["text"].split("\n"), 1):
            if reads_links and not line.lstrip().startswith("```"):
                for target in LINK.findall(line):
                    resolved = (Path(rel).parent / target).as_posix()
                    parts: list[str] = []
                    for piece in Path(resolved).parts:
                        if piece == ".." and parts:
                            parts.pop()
                        elif piece != ".":
                            parts.append(piece)
                    candidate = "/".join(parts)
                    mark = "EXTRACTED" if candidate in nodes else "DANGLING"
                    found.append({"from": rel, "to": candidate, "mark": mark,
                                  "line": number, "evidence": line.strip()[:100]})
            # INFERRED / AMBIGUOUS: the target is NAMED here, wherever the name happens to sit.
            #
            # This was two wrong versions. The first skipped every token containing a slash, so
            # `scripts/preflight.py` - how a script is usually named - never counted, and seventeen
            # files were called orphans while their own SKILL.md named them. The second looked only
            # inside backticks, so a name in a fenced command block or in the frontmatter still did not
            # count. A mention is a mention: look for the name in the text.
            if number == 1:
                for candidate, keys in identities.items():
                    if candidate == rel:
                        continue
                    hit = next((k for k in keys if k in node["text"]), None)
                    if not hit:
                        continue
                    # A document that says `scripts/preflight.py` means its OWN, so the skill's
                    # context resolves the name - otherwise every shared relative path was ambiguous
                    # across the whole family and one wrong version reported 243 of them.
                    matches = [c for c, ks in identities.items() if c != rel and hit in ks]
                    here = [c for c in matches if nodes[c]["skill"] == node["skill"]]
                    if here:
                        matches = here
                    if "/" in hit or len(matches) <= 1:
                        found.append({"from": rel, "to": matches[0] if matches else candidate,
                                      "mark": "INFERRED", "line": 1, "evidence": hit})
                    else:
                        found.append({"from": rel, "to": "|".join(sorted(matches)),
                                      "mark": "AMBIGUOUS", "line": 1, "evidence": hit})
    return found


def reach(nodes: dict[str, dict], found: list[dict]) -> tuple[list[str], list[str]]:
    """Two different kinds of not-findable, because they are not the same problem.

    A file with no markdown link but whose NAME appears in prose is reachable by a reader who reads
    that page - a weak sign, not no sign. A file that is neither linked nor named anywhere is
    invisible, and that is the one worth shouting about.

    The first version counted only links and called twenty-eight files orphans, including every
    script in the family - each of which is named in its own SKILL.md.
    """
    linked = {e["to"] for e in found if e["mark"] == "EXTRACTED"}
    named = {e["to"] for e in found if e["mark"] in {"INFERRED", "AMBIGUOUS"}}
    weak = sorted(rel for rel, node in nodes.items()
                  if node["kind"] != "skill" and rel not in linked and rel in named)
    invisible = sorted(rel for rel, node in nodes.items()
                       if node["kind"] != "skill" and rel not in linked and rel not in named)
    return weak, invisible


def claims(nodes: dict[str, dict]) -> dict[str, list[str]]:
    """Sentences that appear in more than one place, ignoring headings and structural lines.

    Headings are excluded because the four layers of this family appear as headings in more than one
    file by design, and the first version reported that as a contradiction.
    """
    seen: dict[str, list[str]] = defaultdict(list)
    for rel, node in nodes.items():
        if node["kind"] not in {"skill", "reference"} or not node["text"]:
            continue
        for sentence in re.split(r"(?<=[.!?])\s+", node["text"]):
            if sentence.lstrip().startswith("#"):
                continue
            clean = re.sub(r"[`*_\[\]()#]", "", sentence).strip()
            clean = re.sub(r"^\d+[.)]\s*", "", clean)
            words = clean.split()
            if len(words) < CLAIM_MIN_WORDS:
                continue
            # A line that is mostly capitalised words is a structure, not a claim.
            if sum(1 for w in words if w[:1].isupper()) > len(words) / 2:
                continue
            key = " ".join(w.lower() for w in words)[:90]
            seen[key].append(f"{rel}: {clean[:120]}")
    return {k: v for k, v in seen.items() if len({c.split(":")[0] for c in v}) > 1}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("repo", type=Path)
    ap.add_argument("--out", default="_graph", help="folder to write, relative to the repository")
    args = ap.parse_args()

    repo = args.repo.resolve()
    out = repo / args.out
    nodes = walk(repo)
    found = edges(nodes, repo)
    dead = sorted({e["to"] for e in found if e["mark"] == "DANGLING"})
    weak, invisible = reach(nodes, found)
    twice = claims(nodes)

    counts = defaultdict(int)
    for edge in found:
        counts[edge["mark"]] += 1

    print(f"  nodes      {len(nodes)}")
    for mark in ("EXTRACTED", "INFERRED", "AMBIGUOUS", "DANGLING"):
        print(f"  {mark:10} {counts[mark]}")
    print(f"  reachable only by name  {len(weak)}")
    print(f"  ORPHAN (named nowhere)  {len(invisible)}")
    print(f"  claims repeated         {len(twice)}")

    (out / "skills").mkdir(parents=True, exist_ok=True)
    outgoing: dict[str, list[dict]] = defaultdict(list)
    incoming: dict[str, list[dict]] = defaultdict(list)
    for edge in found:
        outgoing[edge["from"]].append(edge)
        for one in edge["to"].split("|"):
            incoming[one].append(edge)

    def link(rel: str) -> str:
        """A relative markdown link from an output page back to the real file."""
        depth = len(Path(args.out).parts) + 1
        return "../" * depth + rel

    for skill in sorted({n["skill"] for n in nodes.values()}):
        mine = {rel: n for rel, n in nodes.items() if n["skill"] == skill}
        page = [f"# {skill}", "",
                f"{sum(1 for n in mine.values() if n['kind'] == 'reference')} reference(s), "
                f"{sum(1 for n in mine.values() if n['kind'] == 'script')} script(s).", ""]
        page.append("## What this skill points at")
        page.append("")
        for rel in sorted(mine):
            out_edges = outgoing.get(rel, [])
            if not out_edges:
                continue
            page.append(f"- [{rel}]({link(rel)})")
            for edge in out_edges[:12]:
                target = edge["to"].split("|")[0]
                page.append(f"    - `{edge['mark']}` → [{target}]({link(target)})  (line {edge['line']})")
        page.append("")
        page.append("## Who points here")
        page.append("")
        for rel in sorted(mine):
            in_edges = incoming.get(rel, [])
            if not in_edges:
                if rel != f"skills/{skill}/SKILL.md":
                    page.append(f"- [{rel}]({link(rel)}) — **ORPHAN**, nothing links to it")
                continue
            marks = sorted({e["mark"] for e in in_edges})
            page.append(f"- [{rel}]({link(rel)}) ← {', '.join(marks)} "
                        f"from {len({e['from'] for e in in_edges})} file(s)")
        page.append("")
        (out / "skills" / f"{skill}.md").write_text("\n".join(page), encoding="utf-8")

    index = ["# The family, as a graph", "",
             "**Every edge carries how it was established, and none of those marks was written by hand — "
             "each is computed from the shape of the text.**", "",
             "| mark | what it means |", "|---|---|",
             "| `EXTRACTED` | a written link that resolves. The author declared it |",
             "| `INFERRED` | a name mentioned in prose with no link. Named, not linked |",
             "| `AMBIGUOUS` | a mention that matches more than one file |",
             "| `DANGLING` | a link whose target is not there |",
             "| `ORPHAN` | nothing links to it |", "",
             f"{len(nodes)} nodes.", ""]
    index.append("## What wants attention")
    index.append("")
    if invisible:
        index.append("**Invisible — neither linked nor named anywhere.** A reader cannot find these:")
        index.append("")
        for rel in invisible:
            index.append(f"- [{rel}]({link(rel)})")
        index.append("")
    if weak:
        index.append(f"**Named but not linked — {len(weak)} file(s).** Reachable by someone who reads "
                     "the page that names them, which is a weak sign rather than no sign:")
        index.append("")
        for rel in weak:
            index.append(f"- [{rel}]({link(rel)})")
        index.append("")
    if dead:
        index.append("**Dangling — a sign pointing at nothing:**")
        index.append("")
        for rel in dead:
            index.append(f"- `{rel}`")
        index.append("")
    if twice:
        index.append(f"**Repeated verbatim — {len(twice)} — by design or by drift?** A rule written in "
                     "two places is how a file comes to contradict itself:")
        index.append("")
        for key, where in sorted(twice.items())[:20]:
            index.append(f"- {where[0][:110]}")
            for other in where[1:]:
                index.append(f"    - also in {other[:110]}")
        index.append("")
    if not (weak or invisible or dead or twice):
        index.append("Nothing. Every file is linked from somewhere, every link resolves, and no claim "
                     "appears twice.")
        index.append("")
    index.append("## By skill")
    index.append("")
    for skill in sorted({n["skill"] for n in nodes.values()}):
        index.append(f"- [{skill}](skills/{skill}.md)")
    (out / "index.md").write_text("\n".join(index), encoding="utf-8")

    machine = {"nodes": [{k: v for k, v in n.items() if k != "text"} for n in nodes.values()],
               "edges": [{k: v for k, v in e.items() if k != "evidence"} for e in found],
               "reachable_only_by_name": weak, "invisible": invisible,
               "dangling": dead, "duplicated_claims": len(twice)}
    (out / "graph.json").write_text(json.dumps(machine, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"\n  wrote {out.relative_to(repo)}/index.md, {len({n['skill'] for n in nodes.values()})} "
          f"skill page(s), graph.json")
    print(f"  open {repo} as an Obsidian vault, or read index.md directly")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
