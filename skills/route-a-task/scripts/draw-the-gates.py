#!/usr/bin/env python3
"""Draw the regulation's gates as a flow, into its own file, without touching any other diagram.

The family graph shows STRUCTURE - which file references which. **The gates are a PROCESS: what fires
when a task arrives, and what each one forces.** Those are different questions and they belong in
different pictures, which is why this writes `gates.drawio` and never opens the family's file.

    python draw-the-gates.py <skills-repo> [--out _graph/gates.drawio]

The gates are read out of route-a-task/SKILL.md, so this cannot drift from the regulation it draws; the
Russian glosses are the only thing kept here, because a diagram is for a person even when an agent wrote
it. Same rules as the family diagram: wrapped in <mxfile>, no comments, escaped once.
"""
from __future__ import annotations

import argparse
import html
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")

# Что означает каждый номер по-русски, и что он требует. Порядок здесь - порядок чтения, а не номер:
# G7 идёт первым, потому что решает, применимо ли остальное.
MEANING = {
    "G7": ("Наблюдать можно только с разрешения оператора",
           "перед всем остальным", "решает, применимо ли остальное вообще", "#E1D5E7", "#9673A6"),
    "G1": ("Чужой контент сканируется до использования",
           "любой чужой файл, скилл, репозиторий", "сначала скан, потом чтение", "#FFE6CC", "#D79B00"),
    "G2": ("Искать, прежде чем писать",
           "перед тем как писать скилл или инструмент", "сначала поиск, потом авторство", "#FFE6CC", "#D79B00"),
    "G3": ("Прочитать машину до изменения",
           "перед диагностикой или починкой", "сначала чтение, потом запись", "#FFE6CC", "#D79B00"),
    "G4": ("Независимый агент читает скилл до того, как его назовут готовым",
           "перед публикацией или принятием скилла", "сначала чужой прогон, потом готово", "#FFE6CC", "#D79B00"),
    "G5": ("Выбор инструмента — решение с записью",
           "когда инструмент ещё не выбран", "сначала запись выбора и причины", "#FFE6CC", "#D79B00"),
    "G6": ("Тихо неверный результат проверяет тот, кто его не делал",
           "когда результат может ошибиться незаметно", "сначала независимая проверка", "#FFE6CC", "#D79B00"),
    "G8": ("Сделай потерю переживаемой до записи",
           "перед правкой того, что больно потерять", "сначала копия или коммит", "#D5E8D4", "#82B366"),
}


# ── LOOK. Not taste - the answers to "it reads like a book description: boxes stacked tightly,
# no air". Every number is copied from draw-a-skill-flow.py, where the operator looked at the
# result and called it beautiful.
TITLE_H = 78        # the diagram's title box: bigger than everything, because it is the entrance
STEP_H = 88         # a gate: number plus what it forces, and the English heading underneath
GAP = 42            # air between boxes. Below 30 the frames read as one block
TITLE_GAP = 88      # air under the title - more than GAP, so the entrance reads as an entrance
BAND_H = 34         # the column header band: it names the column without being a step
PAD_L = 20          # padding inside a frame: 10 left the text touching the border
PAD_T = 10          # top padding: 0 pressed the first line against the frame
MARGIN_X, MARGIN_Y = 90, 60     # page margins: the diagram must not start at the sheet edge

BOX_W = 900         # one column of gates, and the legend is exactly as wide as it
LEGEND_W = 740
LEGEND_X = MARGIN_X + BOX_W + GAP + 60

# The vendor palette only, from jgraph/drawio-mcp/shared/style-reference.md.
BOX = "rounded=1;arcSize=10;whiteSpace=wrap;html=1;shadow=1;strokeWidth=1;"
TITLE = "rounded=1;arcSize=10;whiteSpace=wrap;html=1;shadow=1;strokeWidth=2;"
BAND = ("rounded=1;arcSize=10;whiteSpace=wrap;html=1;fillColor=#F5F5F5;strokeColor=#666666;"
        "align=left;verticalAlign=middle;spacingLeft=20;fontStyle=1;")

# Font ladder: four sizes and each means exactly one thing - the diagram title, a gate's title,
# what it forces, and the English heading it was read from. Not one size for everything.
F_TITLE, F_STEP, F_DETAIL, F_PATH, F_BAND = 18, 13, 11, 9, 12


def esc(text: str) -> str:
    return html.escape(str(text), quote=True)


def box(cell_id: str, label: str, x: int, y: int, w: int, h: int, fill: str, stroke: str) -> str:
    """One bordered cell with real padding. Escaped ONCE, here, on the way into the attribute."""
    return (f'<mxCell id="{esc(cell_id)}" value="{esc(label)}" style="{BOX}fillColor={fill};'
            f'strokeColor={stroke};align=left;verticalAlign=middle;spacingLeft={PAD_L};'
            f'spacingTop={PAD_T};spacingBottom={PAD_T};fontSize={F_STEP};" vertex="1" parent="1">'
            f'<mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry" /></mxCell>')


def arrow(cell_id: str, source: str, target: str) -> str:
    return (f'<mxCell id="{esc(cell_id)}" style="endArrow=classic;html=1;strokeColor=#6C8EBF;'
            f'strokeWidth=2;rounded=0;edgeStyle=orthogonalEdgeStyle;exitX=0.5;exitY=1;exitDx=0;'
            f'exitDy=0;entryX=0.5;entryY=0;entryDx=0;entryDy=0;" edge="1" parent="1" '
            f'source="{esc(source)}" target="{esc(target)}">'
            f'<mxGeometry relative="1" as="geometry" /></mxCell>')


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("repo", type=Path)
    ap.add_argument("--out", default="_graph/gates.drawio")
    args = ap.parse_args()
    repo = args.repo.resolve()

    source = (repo / "skills" / "route-a-task" / "SKILL.md").read_text(encoding="utf-8")
    found = {}
    for match in re.finditer(r"### (G\d) — (.+?)\n\n(.*?)(?=\n### |\n## |\Z)", source, re.S):
        number, title = match.group(1), match.group(2).strip()
        body = re.sub(r"[`*]", "", match.group(3))
        found[number] = (title, re.split(r"(?<=\.)\s", body.strip())[0][:150])

    cells: list[str] = []
    # The diagram's own title box: TITLE_H and strokeWidth 2, so it reads as the entrance and not
    # as one more gate in the flow.
    cells.append(f'<mxCell id="head" value="{esc("ВОРОТА РЕГЛАМЕНТА route-a-task")}" '
                 f'style="{TITLE}fillColor=#DAE8FC;strokeColor=#6C8EBF;fontSize={F_TITLE};'
                 f'fontStyle=1;align=center;verticalAlign=middle;" vertex="1" parent="1">'
                 f'<mxGeometry x="{MARGIN_X}" y="{MARGIN_Y}" width="{BOX_W}" height="{TITLE_H}" '
                 f'as="geometry" /></mxCell>')
    # The task, as the one thing that enters the flow. It is the same sentence as before ("ЗАДАЧА"),
    # drawn as a rounded card so the flow does not start with a shape nobody else uses.
    task_y = MARGIN_Y + TITLE_H + TITLE_GAP
    cells.append(box("task", "ЗАДАЧА", MARGIN_X, task_y, BOX_W, 56, "#DAE8FC", "#6C8EBF"))
    # A COLUMN HEADER BAND, so the reader is told what the column is: eight gates in reading order.
    cells.append(f'<mxCell id="band" value="{esc("ВОСЕМЬ ВОРОТ — в порядке ЧТЕНИЯ, а не номеров")}" '
                 f'style="{BAND}fontSize={F_BAND};" vertex="1" parent="1">'
                 f'<mxGeometry x="{MARGIN_X}" y="{task_y + 56 + GAP}" width="{BOX_W}" '
                 f'height="{BAND_H}" as="geometry" /></mxCell>')

    order = ["G7", "G1", "G2", "G3", "G4", "G5", "G6", "G8"]
    y = task_y + 56 + GAP + BAND_H + GAP
    previous = "task"
    for number in order:
        russian, condition, forces, fill, stroke = MEANING[number]
        english = found.get(number, ("", ""))[0]
        # Four sizes doing four jobs: the gate's name (13), what fires it (11), what it forces (11,
        # green because it is the obligation), and the English heading (9) it was read from.
        label = (f'<b>{number} — {russian}</b><br>'
                 f'<font color="#444444" style="font-size:{F_DETAIL}px">Срабатывает: {condition}'
                 f'</font><br>'
                 f'<font color="#1a6b1a" style="font-size:{F_DETAIL}px">Требует: {forces}</font><br>'
                 f'<font color="#999999" style="font-size:{F_PATH}px">{english}</font>')
        cells.append(box(f"g{number}", label, MARGIN_X, y, BOX_W, STEP_H, fill, stroke))
        cells.append(arrow(f"a{number}", previous, f"g{number}"))
        previous = f"g{number}"
        y += STEP_H + GAP
    flow_bottom = y - GAP

    # ЛЕГЕНДА ПАНЕЛЬЮ, А НЕ СПИСКОМ СТРОК. Строки без рамки читаются как продолжение потока и
    # глазом не отделяются от ворот; панель с заголовком и полями говорит: это справка.
    # HTML собирается НАСТОЯЩИМИ <b> и <br> и экранируется РОВНО ОДИН РАЗ, в box().
    legend_rows = [
        ("ЧТО ЭТО ЗА СХЕМА",
         ["Поток ворот регламента route-a-task: что срабатывает, когда приходит задача.",
          "Это НЕ схема файлов — та лежит в family.drawio и её эта не трогает."]),
        ("КАК ЧИТАТЬ",
         ["Синяя рамка сверху — задача. Стрелка вниз — «после этого шага смотрим следующий».",
          "Фиолетовая — ворота, которые решают, применимо ли всё остальное.",
          "Оранжевые — обязательные при своём условии.",
          "Зелёная — про сохранность работы."]),
        ("ЧТО ЗНАЧИТ «ТРЕБУЕТ»",
         ["Это не совет, а обязательный шаг. Пропустить его нельзя, даже если кажется лишним.",
          "Порядок — порядок чтения, а не номер: G7 стоит первым намеренно."]),
    ]
    parts: list[str] = []
    for heading, lines in legend_rows:
        parts.append(f'<b>{esc(heading)}</b>')
        parts.extend(esc(line) for line in lines)
        parts.append("&nbsp;")
    legend_html = "<br>".join(parts)
    legend_h = 34 + sum(len(lines) + 1 for _, lines in legend_rows) * 22 + 16
    cells.append(f'<mxCell id="legend" value="{esc(legend_html)}" style="{BOX}'
                 f'fillColor=#FFFFFF;strokeColor=#B3B3B3;align=left;verticalAlign=top;'
                 f'spacingLeft={PAD_L};spacingTop={PAD_T};fontSize={F_DETAIL};" vertex="1" '
                 f'parent="1"><mxGeometry x="{LEGEND_X}" y="{task_y}" width="{LEGEND_W}" '
                 f'height="{legend_h}" as="geometry" /></mxCell>')

    # The page is measured from the content, not fixed: a fixed height either crops the diagram or
    # leaves a dead half-page under it.
    page_h = max(flow_bottom, task_y + legend_h) + MARGIN_Y
    page_w = LEGEND_X + LEGEND_W + MARGIN_X
    model = ('<mxGraphModel dx="0" dy="0" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" '
             'arrows="1" fold="1" page="1" pageScale="1" '
             f'pageWidth="{page_w}" pageHeight="{page_h}" math="0" shadow="0">'
             '<root><mxCell id="0" /><mxCell id="1" parent="0" />'
             + "".join(cells) + '</root></mxGraphModel>')
    model = ('<mxfile host="dsh" agent="draw-the-gates.py"><diagram id="gates" name="Ворота">'
             + model + '</diagram></mxfile>')

    out = repo / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(model, encoding="utf-8")
    print(f"  ворот нарисовано: {len(order)}   файл: {out.relative_to(repo)}  ({len(model):,} байт)")
    missing = [g for g in order if g not in found]
    if missing:
        print(f"  ВНИМАНИЕ: в регламенте не найдены {missing}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
