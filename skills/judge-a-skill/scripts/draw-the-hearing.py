#!/usr/bin/env python3
"""Draw the hearing as a flow, into its own file.

`judge-a-skill` is a process: a skill is charged, argued for twice, judged from a fixed list of five
verdicts, the two cases are rated, and the whole thing is recorded. **A process is not a structure**, so
it gets its own picture and its own file - never the family's, never the gates'.

    python draw-the-hearing.py <skills-repo> [--out _graph/hearing.drawio]

The steps and the verdicts are READ OUT OF judge-a-skill/SKILL.md, so the drawing cannot drift from the
skill it draws. Same rules as the other diagrams: wrapped in <mxfile>, no comments, escaped once.
"""
from __future__ import annotations

import argparse
import html
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")

# ── LOOK. Not taste - the answers to "it reads like a book description: boxes stacked tightly, no
# air". Every number is copied from draw-a-skill-flow.py, where the operator looked at the result
# and called it beautiful.
TITLE_H = 78        # the diagram's title box: bigger than everything, because it is the entrance
STEP_H = 88         # a step, and a verdict: a title plus why, and the original name underneath
GAP = 42            # air between boxes. Below 30 the frames read as one block
TITLE_GAP = 88      # air under the title - more than GAP, so the entrance reads as an entrance
BAND_H = 34         # the column header band: it names the column without being a step
PAD_L = 20          # padding inside a frame: 10 left the text touching the border
PAD_T = 10          # top padding: 0 pressed the first line against the frame
MARGIN_X, MARGIN_Y = 90, 60     # page margins: the diagram must not start at the sheet edge

FLOW_W = 900        # the hearing, read top to bottom
VERDICT_W = 760     # the five verdicts, side by side with it
COLUMN_X = MARGIN_X + FLOW_W + GAP + 60
LEGEND_W = 900

# The vendor palette only, from jgraph/drawio-mcp/shared/style-reference.md.
BOX = "rounded=1;arcSize=10;whiteSpace=wrap;html=1;shadow=1;strokeWidth=1;"
TITLE = "rounded=1;arcSize=10;whiteSpace=wrap;html=1;shadow=1;strokeWidth=2;"
BAND = ("rounded=1;arcSize=10;whiteSpace=wrap;html=1;fillColor=#F5F5F5;strokeColor=#666666;"
        "align=left;verticalAlign=middle;spacingLeft=20;fontStyle=1;")

# Font ladder: four sizes and each means exactly one thing - the diagram title, a step's title,
# its role, and the original English heading. Not one size for everything.
F_TITLE, F_STEP, F_DETAIL, F_PATH, F_BAND = 18, 13, 11, 9, 12


def esc(text: str) -> str:
    return html.escape(str(text), quote=True)


def box(cell_id: str, label: str, x: int, y: int, w: int, h: int, fill: str, stroke: str) -> str:
    """One bordered cell with real padding. Escaped ONCE, here, on the way into the attribute."""
    return (f'<mxCell id="{esc(cell_id)}" value="{esc(label)}" style="{BOX}fillColor={fill};'
            f'strokeColor={stroke};align=left;verticalAlign=middle;spacingLeft={PAD_L};'
            f'spacingTop={PAD_T};spacingBottom={PAD_T};fontSize={F_STEP};" vertex="1" parent="1">'
            f'<mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry" /></mxCell>')


def band(cell_id: str, label: str, x: int, y: int, width: int) -> str:
    return (f'<mxCell id="{esc(cell_id)}" value="{esc(label)}" style="{BAND}fontSize={F_BAND};" '
            f'vertex="1" parent="1"><mxGeometry x="{x}" y="{y}" width="{width}" '
            f'height="{BAND_H}" as="geometry" /></mxCell>')


def arrow(cell_id: str, source: str, target: str, dashed: str = "0") -> str:
    return (f'<mxCell id="{esc(cell_id)}" style="endArrow=classic;html=1;strokeColor=#6C8EBF;'
            f'strokeWidth=2;dashed={dashed};rounded=0;edgeStyle=orthogonalEdgeStyle;exitX=0.5;'
            f'exitY=1;exitDx=0;exitDy=0;entryX=0.5;entryY=0;entryDx=0;entryDy=0;" edge="1" '
            f'parent="1" source="{esc(source)}" target="{esc(target)}">'
            f'<mxGeometry relative="1" as="geometry" /></mxCell>')

# По-русски. Порядок и содержание — из регламента суда; здесь только перевод и роли.
STEP_RU = {
    "Step 0": ("Стоит ли вообще судить", "Не созывать суд по каждому поводу", "#F5F5F5", "#666666"),
    "Step 1": ("Структурная проверка — до всякого спора",
               "Спор о содержании сломанного файла — потеря времени", "#FFE6CC", "#D79B00"),
    "Step 2": ("Обвинительный лист — ДО чтения защиты",
               "Сначала записать, что приговор обязан решить", "#FFE6CC", "#D79B00"),
    "Step 3": ("Обвинение", "Доказывает, почему скилл НЕ надо оставлять", "#F8CECC", "#B85450"),
    "Step 4": ("Защита", "Доказывает, почему скилл надо оставить", "#D5E8D4", "#82B366"),
    "Step 5": ("Судья", "Решает", "#DAE8FC", "#6C8EBF"),
    "Step 6": ("Оценка двух сторон", "Два числа из десяти, и кто победил", "#E1D5E7", "#9673A6"),
    "Step 7": ("Запись", "Где найдёт следующий: лист, обе стороны, оценка, приговор", "#E1D5E7", "#9673A6"),
}

# Приговоры по-русски, в порядке от самого мягкого к самому жёсткому.
VERDICT_RU = {
    "Acquit": ("ОПРАВДАН", "ни один конкретный довод не устоял — оставить целиком", "#D5E8D4", "#82B366"),
    "Keep with a boundary": ("ОСТАВИТЬ С ГРАНИЦЕЙ", "работает, но только при названных условиях — их и записать", "#D5E8D4", "#82B366"),
    "Fix": ("ПОЧИНИТЬ", "замысел верен, файл его предаёт — сказать, что менять", "#FFF2CC", "#D6B656"),
    "Reject the skill, take these parts": ("ОТВЕРГНУТЬ СКИЛЛ, ВЗЯТЬ ЧАСТИ", "скилл не стоит держать, а части его — стоят", "#FFE6CC", "#D79B00"),
    "Reject entirely": ("ОТВЕРГНУТЬ ЦЕЛИКОМ", "не уцелело ничего", "#F8CECC", "#B85450"),
}


def esc(text: str) -> str:
    return html.escape(str(text), quote=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("repo", type=Path)
    ap.add_argument("--out", default="_graph/hearing.drawio")
    args = ap.parse_args()
    repo = args.repo.resolve()

    source = (repo / "skills" / "judge-a-skill" / "SKILL.md").read_text(encoding="utf-8")
    steps = {m.group(1): m.group(2).strip()
             for m in re.finditer(r"##\s+(Step \d)\s+—\s+(.+?)\n", source)}
    verdicts = [m.group(1) for m in re.finditer(r"^\|\s*\*\*(.+?)\*\*\s*\|", 
                re.search(r"### The verdicts\n(.*?)(?=\n## |\n### )", source, re.S).group(1), re.M)]

    cells: list[str] = []
    # The diagram's own title box: TITLE_H and strokeWidth 2, so it reads as the entrance and not
    # as one more step.
    cells.append(f'<mxCell id="head" value="{esc("СУД НАД СКИЛЛОМ — judge-a-skill")}" '
                 f'style="{TITLE}fillColor=#DAE8FC;strokeColor=#6C8EBF;fontSize={F_TITLE};'
                 f'fontStyle=1;align=center;verticalAlign=middle;" vertex="1" parent="1">'
                 f'<mxGeometry x="{MARGIN_X}" y="{MARGIN_Y}" width="{FLOW_W}" height="{TITLE_H}" '
                 f'as="geometry" /></mxCell>')
    # The defendant, as the one thing the hearing is about. Same sentence as before, drawn as a card.
    defendant_y = MARGIN_Y + TITLE_H + TITLE_GAP
    cells.append(box("defendant", "СКИЛЛ-ПОДСУДИМЫЙ", MARGIN_X, defendant_y, FLOW_W, 56,
                     "#DAE8FC", "#6C8EBF"))
    # A COLUMN HEADER BAND per column: the reader is told which column is the process and which is
    # the outcome, instead of having to learn it from a caption.
    band_y = defendant_y + 56 + GAP
    cells.append(band("band_steps", "ВОСЕМЬ ШАГОВ СУДА — в порядке исполнения",
                      MARGIN_X, band_y, FLOW_W))
    cells.append(band("band_verdicts", "ПЯТЬ ПРИГОВОРОВ — из них выбирает судья",
                      COLUMN_X, band_y, VERDICT_W))

    y = band_y + BAND_H + GAP
    previous = "defendant"
    for number in [f"Step {i}" for i in range(8)]:
        russian, role, fill, stroke = STEP_RU[number]
        english = steps.get(number, "")
        # Four sizes doing four jobs: which step (inside the title), what it is (13), what it is for
        # (11), and the English heading (9) it was read from.
        label = (f'<b>{number} — {russian}</b><br>'
                 f'<font color="#444444" style="font-size:{F_DETAIL}px">{role}</font><br>'
                 f'<font color="#999999" style="font-size:{F_PATH}px">{english}</font>')
        cell = f"s{number[-1]}"
        cells.append(box(cell, label, MARGIN_X, y, FLOW_W, STEP_H, fill, stroke))
        cells.append(arrow(f"a{number[-1]}", previous, cell))
        previous = cell
        y += STEP_H + GAP
    flow_bottom = y - GAP

    # The verdicts are the OUTPUT of the hearing, so they get their own column, the same height per
    # box and the same air. Their vertical rhythm matches the steps', which is what makes the two
    # columns read as one picture.
    vy = band_y + BAND_H + GAP
    first_verdict = "v0"
    for index, name in enumerate(verdicts):
        russian, when, fill, stroke = VERDICT_RU.get(name, (name, "", "#F5F5F5", "#666666"))
        label = (f'<b>{russian}</b><br>'
                 f'<font color="#444444" style="font-size:{F_DETAIL}px">{when}</font><br>'
                 f'<font color="#999999" style="font-size:{F_PATH}px">{name}</font>')
        cell = f"v{index}"
        cells.append(box(cell, label, COLUMN_X, vy, VERDICT_W, STEP_H, fill, stroke))
        if index == 0:
            first_verdict = cell
        vy += STEP_H + GAP
    verdict_bottom = vy - GAP
    # «Судья выбирает одно из пяти» - the one edge between the columns.
    cells.append(f'<mxCell id="av" style="endArrow=classic;html=1;strokeColor=#6C8EBF;'
                 f'strokeWidth=2;dashed=1;edgeStyle=orthogonalEdgeStyle;" edge="1" parent="1" '
                 f'source="s5" target="{first_verdict}">'
                 f'<mxGeometry relative="1" as="geometry" /></mxCell>')

    # ЛЕГЕНДА ПАНЕЛЬЮ, А НЕ СПИСКОМ СТРОК: строки без рамки читаются как продолжение шагов.
    # HTML собирается НАСТОЯЩИМИ <b> и <br> и экранируется РОВНО ОДИН РАЗ, в box().
    legend_rows = [
        ("ЧТО ЭТО ЗА СХЕМА",
         ["Процесс суда над скиллом — judge-a-skill. Как скилл обвиняют, защищают и судят.",
          "Это НЕ схема файлов (family.drawio) и НЕ ворота регламента (gates.drawio).",
          "У каждого процесса своя схема, и они друг друга не заменяют."]),
        ("КАК ЧИТАТЬ",
         ["Синяя рамка сверху — подсудимый. Стрелка вниз — следующий шаг суда.",
          "Красная — сторона обвинения. Зелёная — сторона защиты.",
          "Пунктир к колонке справа — «судья выбирает одно из пяти»."]),
        ("ЧТО ГЛАВНОЕ В ЭТОМ ПРОЦЕССЕ",
         ["Обвинительный лист пишется ДО чтения защиты себя — иначе доводы подгоняются под ответ.",
          "Чистый приговор — полноценный исход: если конкретного довода не уцелело, скилл оставляют.",
          "Обе стороны получают оценку, чтобы близкое решение было видно как близкое."]),
    ]
    parts: list[str] = []
    for heading, lines in legend_rows:
        parts.append(f'<b>{esc(heading)}</b>')
        parts.extend(esc(line) for line in lines)
        parts.append("&nbsp;")
    legend_html = "<br>".join(parts)
    legend_h = 34 + sum(len(lines) + 1 for _, lines in legend_rows) * 22 + 16
    legend_y = max(flow_bottom, verdict_bottom) + GAP
    cells.append(f'<mxCell id="legend" value="{esc(legend_html)}" style="{BOX}'
                 f'fillColor=#FFFFFF;strokeColor=#B3B3B3;align=left;verticalAlign=top;'
                 f'spacingLeft={PAD_L};spacingTop={PAD_T};fontSize={F_DETAIL};" vertex="1" '
                 f'parent="1"><mxGeometry x="{MARGIN_X}" y="{legend_y}" width="{LEGEND_W}" '
                 f'height="{legend_h}" as="geometry" /></mxCell>')

    # The page is measured from the content, not fixed.
    page_w = COLUMN_X + VERDICT_W + MARGIN_X
    page_h = legend_y + legend_h + MARGIN_Y
    model = ('<mxGraphModel dx="0" dy="0" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" '
             'arrows="1" fold="1" page="1" pageScale="1" '
             f'pageWidth="{page_w}" pageHeight="{page_h}" math="0" '
             'shadow="0"><root><mxCell id="0" /><mxCell id="1" parent="0" />' + "".join(cells)
             + '</root></mxGraphModel>')
    model = ('<mxfile host="dsh" agent="draw-the-hearing.py"><diagram id="hearing" name="Суд">'
             + model + '</diagram></mxfile>')

    out = repo / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(model, encoding="utf-8")
    print(f"  шагов {len(steps)}   приговоров {len(verdicts)}   файл: {out.relative_to(repo)} "
          f"({len(model):,} байт)")
    if len(steps) != 8 or len(verdicts) != 5:
        print(f"  ВНИМАНИЕ: ожидалось 8 шагов и 5 приговоров, найдено {len(steps)} и {len(verdicts)}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
