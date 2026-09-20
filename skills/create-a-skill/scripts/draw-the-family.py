#!/usr/bin/env python3
"""Render the family graph as a .drawio file, so the structure can be SEEN.

`.drawio` is XML - a file format an agent reads and writes directly, which is the third rung of
`learn-an-interface`'s ladder and well above driving an editor with the mouse. The vendor publishes the
format and an XSD to validate it:

    https://www.drawio.com/docs/reference/diagram-generation/
    https://github.com/jgraph/drawio-mcp/blob/main/shared/mxfile.xsd

THE MARK ON EACH EDGE BECOMES ITS COLOUR AND ITS LINE STYLE, which is the whole point: a reader looks at
the picture and sees at once which connections are declared and which are guessed.

    EXTRACTED  solid green    a written link that resolves - the road is signposted
    INFERRED   dashed amber   named in the text with no link - the place is named, no road drawn
    AMBIGUOUS  dotted purple  one sign, two places
    DANGLING   solid red      a link whose target is not there
    ORPHAN     red border     nothing links to it and nothing names it

    python draw-the-family.py <skills-repo> [--out _graph/family.drawio]

Reads `_graph/graph.json`, which `graph-skills.py` writes. The data and the drawing are separate on
purpose: one walk, several views, and a view can never disagree with the numbers it came from.
"""
from __future__ import annotations

import argparse
import html
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")

# The vendor's own palette, from the style reference's colour-theme table.
THEME = {
    "skill":     ("#DAE8FC", "#6C8EBF"),      # blue
    "reference": ("#FFF2CC", "#D6B656"),      # yellow
    "script":    ("#D5E8D4", "#82B366"),      # green
    "asset":     ("#E1D5E7", "#9673A6"),      # purple
    "file":      ("#F5F5F5", "#666666"),      # grey
}

EDGE = {
    # mark       colour     dashed  width
    "EXTRACTED": ("#82B366", "0", 2),
    "INFERRED":  ("#D79B00", "1", 1),
    "AMBIGUOUS": ("#9673A6", "1", 1),
    "DANGLING":  ("#B85450", "0", 2),
}

WIDTH, HEIGHT, GAP_X, GAP_Y = 240, 40, 300, 56


def esc(text: str) -> str:
    """XML-escape. The vendor's rule 9, and the one that breaks a file silently if missed."""
    return html.escape(str(text), quote=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("repo", type=Path)
    ap.add_argument("--out", default="_graph/family.drawio")
    ap.add_argument("--all", action="store_true",
                    help="draw every edge, including mentions. Default is EXTRACTED only, because "
                         "a picture with four hundred edges in it is a hairball rather than a structure")
    args = ap.parse_args()

    repo = args.repo.resolve()
    data = json.loads((repo / "_graph" / "graph.json").read_text(encoding="utf-8"))
    nodes = {n["path"]: n for n in data["nodes"]}
    invisible = set(data.get("invisible", []))
    weak = set(data.get("reachable_only_by_name", []))

    # One column per kind, so the picture reads left to right: what a skill is, what it explains, what
    # it runs.
    columns = {"skill": 0, "reference": 1, "script": 2, "asset": 3, "file": 4}
    rows: dict[int, int] = defaultdict(int)
    place: dict[str, tuple[int, int]] = {}
    for rel in sorted(nodes):
        kind = nodes[rel]["kind"]
        column = columns.get(kind, 4)
        row = rows[column]
        rows[column] += 1
        place[rel] = (60 + column * GAP_X, 100 + row * GAP_Y)

    cells: list[str] = []

    def vertex(cell_id: str, label: str, x: int, y: int, fill: str, stroke: str,
               width: int = WIDTH, height: int = HEIGHT) -> None:
        style = (f"rounded=1;whiteSpace=wrap;html=1;fillColor={fill};strokeColor={stroke};"
                 f"strokeWidth={3 if cell_id in orphan_ids else 1};fontSize=11;")
        cells.append(f'<mxCell id="{esc(cell_id)}" value="{esc(label)}" style="{style}" '
                     f'vertex="1" parent="1"><mxGeometry x="{x}" y="{y}" '
                     f'width="{width}" height="{height}" as="geometry" /></mxCell>')

    orphan_ids = {f"n{i}" for i, rel in enumerate(sorted(nodes)) if rel in invisible}
    ids = {rel: f"n{i}" for i, rel in enumerate(sorted(nodes))}

    for rel in sorted(nodes):
        node = nodes[rel]
        x, y = place[rel]
        fill, stroke = THEME.get(node["kind"], THEME["file"])
        if rel in invisible:
            stroke = "#B85450"                      # a road with no sign to it
        suffix = ""
        if rel in invisible:
            suffix = "  ⚠ no signposts"
        elif rel in weak:
            suffix = "  · named only"
        label = rel.split("skills/", 1)[-1] + suffix
        vertex(ids[rel], label, x, y, fill, stroke)

    # Every edge, coloured by how it was established. Only the declared ones by default: a picture is
    # for reading, and four hundred inferred mentions between sixty-eight boxes is a hairball. The JSON
    # keeps them all; the drawing keeps what a person can follow.
    drawn = data["edges"] if args.all else [e for e in data["edges"] if e["mark"] == "EXTRACTED"]
    for index, edge in enumerate(drawn):
        source = ids.get(edge["from"])
        target = ids.get(edge.get("to", "").split("|")[0])
        if not source or not target or source == target:
            continue
        colour, dashed, width = EDGE.get(edge["mark"], EDGE["INFERRED"])
        style = (f"endArrow=classic;html=1;strokeColor={colour};strokeWidth={width};"
                 f"dashed={dashed};rounded=1;edgeStyle=orthogonalEdgeStyle;")
        cells.append(f'<mxCell id="e{index}" style="{style}" edge="1" parent="1" '
                     f'source="{esc(source)}" target="{esc(target)}">'
                     f'<mxGeometry relative="1" as="geometry" /></mxCell>')

    # A legend, drawn as four small vertices rather than described in prose - a reader should not have
    # to be told what the colours mean in a separate document.
    legend = [("EXTRACTED - the road is signposted", EDGE["EXTRACTED"]),
              ("INFERRED - named, no road drawn", EDGE["INFERRED"]),
              ("AMBIGUOUS - one sign, two places", EDGE["AMBIGUOUS"]),
              ("DANGLING - a sign pointing at nothing", EDGE["DANGLING"])]
    for row, (text, (colour, dashed, width)) in enumerate(legend):
        style = (f"text;html=1;align=left;verticalAlign=middle;fontSize=11;fontColor={colour};"
                 f"strokeColor=none;fillColor=none;")
        cells.append(f'<mxCell id="legend{row}" value="{esc(text)}" style="{style}" '
                     f'vertex="1" parent="1"><mxGeometry x="60" y="{1400 + row * 26}" '
                     f'width="440" height="24" as="geometry" /></mxCell>')

    # The vendor's rules, followed exactly: two structural cells, no XML comments, unique ids, one
    # type flag per cell.
    #
    # AND THE FULL <mxfile> WRAPPER, because the documentation and the program disagreed. The vendor
    # says a bare <mxGraphModel> "is a valid draw.io XML fragment" and that draw.io wraps it
    # automatically - and draw.io DESKTOP 28.2.5 opened such a file as an EMPTY PAGE, with the title
    # bar showing the right filename. The wrapped form renders. EVIDENCE BEATS DOCUMENTATION, and the
    # cost of the wrapper is one line.
    model = ('<mxGraphModel dx="0" dy="0" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" '
             'arrows="1" fold="1" page="1" pageScale="1" pageWidth="1600" pageHeight="1500" '
             'math="0" shadow="0">'
             '<root><mxCell id="0" /><mxCell id="1" parent="0" />'
             + "".join(cells) +
             "</root></mxGraphModel>")
    model = ('<mxfile host="dsh" agent="draw-the-family.py">'
             '<diagram id="family" name="The family">' + model + '</diagram></mxfile>')

    out = repo / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(model, encoding="utf-8")

    # The vendor publishes a checklist; four of its fifteen items are the ones a generator gets wrong,
    # and they cost nothing to check here.
    problems = []
    if "<!--" in model:
        problems.append("XML comments are forbidden in a .drawio file")
    if '<mxCell id="0" />' not in model or '<mxCell id="1" parent="0" />' not in model:
        problems.append("the two structural cells are missing")
    for cell_id in ids.values():
        if model.count(f'id="{cell_id}"') != 1:
            problems.append(f"id {cell_id} is not unique")
    for edge in data["edges"]:
        if edge["mark"] != "DANGLING" and edge.get("to", "").split("|")[0] not in ids:
            problems.append(f"edge target missing: {edge.get('to')}")

    print(f"  nodes {len(nodes)}   edges {len(data['edges'])}   legend {len(legend)}")
    print(f"  wrote {out.relative_to(repo)}  ({len(model):,} bytes)")
    print("  open it in draw.io, or:")
    print(f"    \"C:\\Program Files\\draw.io\\draw.io.exe\" \"{out}\"")
    if problems:
        print("  PROBLEMS:")
        for one in problems[:8]:
            print(f"    - {one}")
        return 1
    print("  checklist: no comments, structural cells present, ids unique, targets exist")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
