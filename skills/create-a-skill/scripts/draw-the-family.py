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

# ── LOOK. These are not taste, they are the answers to a complaint: "it reads like a book
# description - boxes stacked tightly, no air". The rule under all of them is that SIZE AND
# PADDING SAY WHAT A THING IS (see ../draw-a-diagram/references/making-it-look-right.md). One
# height for every frame erases the hierarchy and the page reads as a single paragraph, so the
# numbers below are copied from draw-a-skill-flow.py, where the operator looked at the result
# and called it beautiful.
TITLE_H = 78        # the diagram's own title box: bigger than everything, because it is the entrance
STEP_H = 88         # a node: its name, what it is, and the path underneath
CELL_H = 62         # a node with a name but no description - the case the air is for
ROW_H = 74          # row pitch in a column: the tallest cell plus GAP
GAP = 42            # air between boxes. Below 30 the frames read as one block
BAND_H = 34         # the column header band: it says what the column IS, without being a node
TITLE_GAP = 48      # air under the title. A gap of 30 is not "almost the same"
PAD_L = 20          # padding inside a frame: 10 left the text touching the border
PAD_T = 10          # top padding: 0 pressed the first line against the frame
MARGIN_X, MARGIN_Y = 90, 60     # page margins: the diagram must not start at the sheet edge

# The vendor palette only, from jgraph/drawio-mcp/shared/style-reference.md.
BOX = "rounded=1;arcSize=10;whiteSpace=wrap;html=1;shadow=1;strokeWidth=1;"
TITLE = "rounded=1;arcSize=10;whiteSpace=wrap;html=1;shadow=1;strokeWidth=2;"
BAND = ("rounded=1;arcSize=10;whiteSpace=wrap;html=1;fillColor=#F5F5F5;strokeColor=#666666;"
        "align=left;verticalAlign=middle;spacingLeft=20;fontStyle=1;")

# Font ladder: four sizes and each means exactly one thing. Never one size for everything -
# that was the thing that made the page read as a single paragraph.
F_TITLE, F_STEP, F_DETAIL, F_PATH, F_BAND = 18, 13, 11, 9, 12

# One width class per column, because breaking a uniform width is the first fix for the flat
# band: a path needs more room than a file name, and giving both the same width wastes the page.
COL_WIDTH = {"skill": 420, "reference": 660, "script": 520, "asset": 420, "file": 520}


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

    # Русские подписи из словаря рядом со скриптом. Он лежит отдельно и правится руками: описание
    # файла — знание о семье, а не часть рисовальщика, и держать его в коде значит хоронить.
    glossary_path = Path(__file__).resolve().parent / "family-glossary.json"
    glossary = json.loads(glossary_path.read_text(encoding="utf-8")) if glossary_path.exists() else {}

    columns = {"skill": 0, "reference": 1, "script": 2, "asset": 3, "file": 4}
    present = sorted({columns.get(nodes[rel]["kind"], 4) for rel in nodes})
    if not present:                       # a graph with no nodes: place nothing, but do not crash
        present = [0]
    x_of = {column: MARGIN_X + sum(COL_WIDTH[k] + GAP for k in present[:present.index(column)])
            for column in present}
    rows: dict[int, int] = defaultdict(int)
    place: dict[str, tuple[int, int]] = {}
    for rel in sorted(nodes):
        kind = nodes[rel]["kind"]
        column = columns.get(kind, 4)
        row = rows[column]
        rows[column] += 1
        # Header band first, then the nodes: the pitch is ROW_H so the tallest cell keeps its GAP.
        place[rel] = (x_of[column], MARGIN_Y + TITLE_H + TITLE_GAP + BAND_H + GAP + row * ROW_H)

    cells: list[str] = []

    def vertex(cell_id: str, label: str, x: int, y: int, fill: str, stroke: str,
               width: int = COL_WIDTH["skill"], height: int = CELL_H) -> None:
        # Text inside a box is left and middle, with the padding named in the style. Without
        # spacingTop the first line is pressed against the frame; without spacingLeft it touches
        # the border. Both were true of the first version of this picture.
        style = (f"{BOX}fillColor={fill};strokeColor={stroke};"
                 f"strokeWidth={3 if cell_id in orphan_ids else 1};fontSize={F_STEP};"
                 f"align=left;verticalAlign=middle;spacingLeft={PAD_L};spacingTop={PAD_T};"
                 f"spacingBottom={PAD_T};")
        cells.append(f'<mxCell id="{esc(cell_id)}" value="{esc(label)}" style="{style}" '
                     f'vertex="1" parent="1"><mxGeometry x="{x}" y="{y}" '
                     f'width="{width}" height="{height}" as="geometry" /></mxCell>')

    # A COLUMN HEADER BAND, so the reader knows what each column is without a caption somewhere
    # else. A band, not seven separate nodes: it belongs to the column, not to the flow.
    def band(cell_id: str, label: str, x: int, width: int) -> None:
        style = f"{BAND}fontSize={F_BAND};"
        cells.append(f'<mxCell id="{esc(cell_id)}" value="{esc(label)}" style="{style}" '
                     f'vertex="1" parent="1"><mxGeometry x="{x}" '
                     f'y="{MARGIN_Y + TITLE_H + TITLE_GAP}" width="{width}" height="{BAND_H}" '
                     f'as="geometry" /></mxCell>')

    orphan_ids = {f"n{i}" for i, rel in enumerate(sorted(nodes)) if rel in invisible}
    ids = {rel: f"n{i}" for i, rel in enumerate(sorted(nodes))}

    # The header bands, one per column that actually has nodes in it.
    for column in present:
        kind = next(k for k, c in columns.items() if c == column)
        band(f"band{column}", f"{BAND_TITLE[kind]}  ·  {rows[column]}", x_of[column],
             COL_WIDTH[kind])

    for rel in sorted(nodes):
        node = nodes[rel]
        x, y = place[rel]
        kind = node["kind"]
        fill, stroke = THEME.get(kind, THEME["file"])
        if rel in invisible:
            stroke = "#B85450"                      # a road with no sign to it
        short = rel.split("skills/", 1)[-1]
        # Русское описание сверху, путь мелким шрифтом под ним: читателю нужен смысл, а путь нужен,
        # чтобы файл можно было найти. Русское имя — заголовок строки (F_STEP), путь — строка
        # источника (F_PATH): два разных размера, потому что это две разные вещи.
        russian = glossary.get(rel, "")
        # HTML собирается НАСТОЯЩИМИ скобками и экранируется ровно один раз, в vertex(). Первая
        # версия писала &lt;b&gt; здесь и потом экранировала ещё раз - draw.io получил &amp;lt;b&amp;gt;
        # и нарисовал разметку текстом. Двойное экранирование не падает, оно просто портит вид.
        if russian:
            label = (f'<b>{russian}</b><br>'
                     f'<font color="#666666" style="font-size:{F_PATH}px">{short}</font>')
        else:
            label = f'<b>{short}</b>'
        if rel in invisible:
            label += f'<br><font color="#B85450" style="font-size:{F_PATH}px">⚠ нигде не назван</font>'
        elif rel in weak:
            label += (f'<br><font color="#D79B00" style="font-size:{F_PATH}px">'
                      f'· назван, но не связан</font>')
        # Height answers to the TEXT: a node with a description is a rich card, one without is a leaf.
        vertex(ids[rel], label, x, y, fill, stroke, width=COL_WIDTH.get(kind, COL_WIDTH["file"]),
               height=STEP_H if russian else CELL_H)

    # Every edge, coloured by how it was established.
    #
    # TWO KINDS OF INFERRED, AND ONLY ONE OF THEM IS A GUESS. When a SKILL.md names a file inside its
    # OWN skill - its own script, in backticks - the author declared that relationship as surely as a
    # markdown link does; they wrote the name instead of the link. When one skill names a file in
    # ANOTHER skill, that is a mention and nothing more.
    #
    # The first version filtered to EXTRACTED only, and the script column came out with ZERO arrows
    # pointing at it. The scripts looked orphaned and they are not - their own SKILL.md names them on
    # its first screen. A filter that removes real edges along with the noise is a blindfold.
    def keep(edge: dict) -> bool:
        if args.all or edge["mark"] == "EXTRACTED":
            return True
        if edge["mark"] in {"INFERRED", "AMBIGUOUS"}:
            source = nodes.get(edge["from"], {})
            target = nodes.get(edge.get("to", "").split("|")[0], {})
            # Only the SKILL.md naming its own files. A mention inside a reference is a weaker thing
            # than the skill declaring what belongs to it, and drawing both put 366 edges on the page.
            return (bool(source) and source.get("skill") == target.get("skill")
                    and source.get("name") == "SKILL.md")
        return False

    drawn = [e for e in data["edges"] if keep(e)]
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

    # ЛЕГЕНДА, нарисованная в самой схеме. Читатель не должен узнавать, что значат цвета, из другого
    # файла - схема без легенды это картинка, а не карта. Рисуется списком текстовых ячеек.
    legend_title = ["ЧТО ЗНАЧИТ ЦВЕТ РАМКИ",
                    "синяя — скилл", "жёлтая — справочник", "зелёная — скрипт",
                    "фиолетовая — вложение", "серая — прочий файл",
                    "",
                    "ЧТО ЗНАЧИТ ОБВОДКА",
                    "тонкая — обычная", "красная толстая — файл НИГДЕ не назван",
                    "",
                    "ЧТО ЗНАЧИТ СТРЕЛКА",
                    "сплошная зелёная — EXTRACTED: ссылка написана  (щит стоит)",
                    "пунктир янтарный — INFERRED: имя есть, ссылки нет  (место названо, дороги нет)",
                    "точками фиолетовая — AMBIGUOUS: имя подходит к двум файлам  (щит на два места)",
                    "сплошная красная — DANGLING: ссылка в никуда  (щит в пустоту)",
                    "",
                    "ЧТО ЗДЕСЬ ВООБЩЕ",
                    "Схема связей внутри семьи навыков: 9 скиллов, их справочники и скрипты.",
                    "Стрелка означает «этот файл ссылается на тот»."]
    for row, text in enumerate(legend_title):
        bold = "1" if text.isupper() or text.startswith("ЧТО") else "0"
        style = ("text;html=1;align=left;verticalAlign=middle;fontSize=12;"
                 f"fontStyle={bold};strokeColor=none;fillColor=none;")
        cells.append(f'<mxCell id="legend{row}" value="{esc(text)}" style="{style}" '
                     f'vertex="1" parent="1"><mxGeometry x="60" y="{3450 + row * 24}" '
                     f'width="700" height="22" as="geometry" /></mxCell>')

    # The vendor's rules, followed exactly: two structural cells, no XML comments, unique ids, one
    # type flag per cell.
    #
    # AND THE FULL <mxfile> WRAPPER, because the documentation and the program disagreed. The vendor
    # says a bare <mxGraphModel> "is a valid draw.io XML fragment" and that draw.io wraps it
    # automatically - and draw.io DESKTOP 28.2.5 opened such a file as an EMPTY PAGE, with the title
    # bar showing the right filename. The wrapped form renders. EVIDENCE BEATS DOCUMENTATION, and the
    # cost of the wrapper is one line.
    model = ('<mxGraphModel dx="0" dy="0" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" '
             'arrows="1" fold="1" page="1" pageScale="1" pageWidth="2200" pageHeight="3400" '
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

    print(f"  nodes {len(nodes)}   edges {len(drawn)} drawn of {len(data['edges'])}   "
          f"legend {len(legend_title)} lines")
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
