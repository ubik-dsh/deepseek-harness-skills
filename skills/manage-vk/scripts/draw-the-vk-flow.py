#!/usr/bin/env python3
"""Draw what a VK community token can and cannot do, and the order a post travels in.

**The most valuable picture for this skill is the capability split**, because the expensive mistakes
here are not syntax errors - they are calls that return success and do nothing, and a wall that cannot be
read back to check.

    python draw-the-vk-flow.py <skills-repo> [--out _graph/vk.drawio]

Own file, own window: this is neither the family's structure, nor the regulation's gates, nor a hearing.
The measurements below are the ones taken in this session and recorded in references/capabilities.md.
"""
from __future__ import annotations

import argparse
import html
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")

GREEN = ("#D5E8D4", "#82B366")
RED = ("#F8CECC", "#B85450")
ORANGE = ("#FFE6CC", "#D79B00")
BLUE = ("#DAE8FC", "#6C8EBF")
PURPLE = ("#E1D5E7", "#9673A6")
GREY = ("#F5F5F5", "#666666")

# ── LOOK. Not taste - the answers to "it reads like a book description: boxes stacked tightly, no
# air". Every number is copied from draw-a-skill-flow.py, where the operator looked at the result
# and called it beautiful.
TITLE_H = 78        # the diagram's title box: bigger than everything, because it is the entrance
STEP_H = 88         # a step of the publication: a title plus why
ITEM_H = 56         # one measured capability: one line, but room to wrap onto a second
GAP = 42            # air between boxes. Below 30 the frames read as one block
TIGHT = 12          # air between siblings INSIDE one panel: well under half a box height
TITLE_GAP = 88      # air under the title - more than GAP, so the entrance reads as an entrance
BAND_H = 34         # the column header band: it names the column without being a step
PAD_L = 20          # padding inside a frame: 10 left the text touching the border
PAD_T = 10          # top padding: 0 pressed the first line against the frame
MARGIN_X, MARGIN_Y = 90, 60     # page margins: the diagram must not start at the sheet edge

ORDER_W = 460       # column 1: the order to think in
CAN_W = 760         # column 2: what the key can do
CANNOT_W = 760      # column 3: what it cannot - and this column is the important one
ORDER_X = MARGIN_X
CAN_X = ORDER_X + ORDER_W + GAP
CANNOT_X = CAN_X + CAN_W + GAP
FULL_W = CANNOT_X + CANNOT_W - MARGIN_X

# The vendor palette only, from jgraph/drawio-mcp/shared/style-reference.md.
BOX = "rounded=1;arcSize=10;whiteSpace=wrap;html=1;shadow=1;strokeWidth=1;"
TITLE = "rounded=1;arcSize=10;whiteSpace=wrap;html=1;shadow=1;strokeWidth=2;"
BAND = ("rounded=1;arcSize=10;whiteSpace=wrap;html=1;fillColor=#F5F5F5;strokeColor=#666666;"
        "align=left;verticalAlign=middle;spacingLeft=20;fontStyle=1;")

# Font ladder: four sizes and each means exactly one thing - the diagram title, a step's title,
# its explanation, and a measured item inside a panel. Not one size for everything.
F_TITLE, F_STEP, F_DETAIL, F_PATH, F_BAND = 18, 13, 11, 9, 12

# Порядок мышления - первое, что говорит скилл.
ORDER = [("ГРАНИЦЫ", "что этот ключ вообще может трогать", BLUE),
         ("ФУНКЦИИ", "чем именно, каким методом", BLUE),
         ("СМЫСЛ", "стоит ли это делать и что будет", PURPLE),
         ("ПРОСЬБЫ", "что просил оператор и что из этого вышло", PURPLE)]

STEPS = [("Step 0", "Предполётная проверка — ДО всего остального",
          "резолвит сообщество и права, ничего не меняя", ORANGE),
         ("Step 1", "Ключ живёт в окружении и больше нигде",
          "никогда не печатать, не пересылать, не коммитить", ORANGE),
         ("Step 2", "Что ключ сообщества может и чего не может — измерено",
          "смотри колонки справа", ORANGE),
         ("Step 3", "Ворота подтверждения",
          "оператор видит текст до публикации", RED),
         ("Step 4", "Опубликовать или отложить",
          "и подтвердить по post_id и глазами", GREEN)]

CAN = ["wall.post — написать на стену",
       "groups.edit — правки сообщества (молча игнорирует лишнее)",
       "wall.closeComments — закрыть комментарии",
       "groups.getById / getTokenPermissions — кто мы и что нам можно",
       "groups.getMembers / getBanned — участники и забаненные",
       "groups.getLongPollServer / setLongPollSettings — живая лента",
       "groups.addAddress / editAddress / deleteAddress — адреса",
       "вложение ДОКУМЕНТА к посту"]

CANNOT = ["ЧИТАТЬ стену: wall.get / getById / getComments — ошибка 27",
          "УДАЛИТЬ или ИСПРАВИТЬ пост: wall.delete / edit / restore — ошибка 27",
          "photos.getWallUploadServer / saveWallPhoto — ошибка 27",
          "приложить ФОТО к посту — вызов проходит, вложение пропадает",
          "groups.create / editManager / removeUser / search — нужен ключ пользователя",
          "groups.delete — такого метода НЕ СУЩЕСТВУЕТ ВООБЩЕ"]

TRAPS = ["Ошибки приходят НЕ как ошибки HTTP. VK отвечает 200, а отказ лежит в теле.",
         "err 100 — метод есть и вызывается, но аргументы не те. err 27 — метод есть, токен чужой.",
         "err 3 — такого метода нет. Это надо отправлять первым, как контроль.",
         "groups.edit возвращает 1 на ЛЮБОЙ неизвестный параметр — «принято» не значит «применено».",
         "Нет безопасной пробы записи ключом сообщества: любая запись что-то меняет."]


def esc(text: str) -> str:
    return html.escape(str(text), quote=True)


def box(cells: list[str], cell_id: str, label: str, x: int, y: int, w: int, h: int,
        colours: tuple[str, str], size: int = F_STEP) -> None:
    """One bordered cell with real padding. The HTML is escaped ONCE, here, on the way in."""
    cells.append(f'<mxCell id="{esc(cell_id)}" value="{esc(label)}" style="{BOX}'
                 f'fillColor={colours[0]};strokeColor={colours[1]};align=left;'
                 f'verticalAlign=middle;spacingLeft={PAD_L};spacingTop={PAD_T};'
                 f'spacingBottom={PAD_T};fontSize={size};" vertex="1" parent="1">'
                 f'<mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry" /></mxCell>')


def band(cells: list[str], cell_id: str, label: str, x: int, y: int, w: int) -> None:
    """A column header band: it says what the column IS, without being a node of the flow."""
    cells.append(f'<mxCell id="{esc(cell_id)}" value="{esc(label)}" style="{BAND}'
                 f'fontSize={F_BAND};" vertex="1" parent="1"><mxGeometry x="{x}" y="{y}" '
                 f'width="{w}" height="{BAND_H}" as="geometry" /></mxCell>')


def arrow(cells: list[str], cell_id: str, source: str, target: str,
          colour: str = "#6C8EBF") -> None:
    cells.append(f'<mxCell id="{esc(cell_id)}" style="endArrow=classic;html=1;strokeColor={colour};'
                 f'strokeWidth=2;rounded=0;edgeStyle=orthogonalEdgeStyle;exitX=0.5;exitY=1;exitDx=0;'
                 f'exitDy=0;entryX=0.5;entryY=0;entryDx=0;entryDy=0;" edge="1" parent="1" '
                 f'source="{esc(source)}" target="{esc(target)}">'
                 f'<mxGeometry relative="1" as="geometry" /></mxCell>')


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("repo", type=Path)
    ap.add_argument("--out", default="_graph/vk.drawio")
    args = ap.parse_args()
    repo = args.repo.resolve()

    cells: list[str] = []
    # The diagram's own title box: TITLE_H and strokeWidth 2, so it reads as the entrance and not
    # as one more card.
    cells.append(f'<mxCell id="head" value="{esc("РАБОТА С ВК — что ключ сообщества может и чего нет")}" '
                 f'style="{TITLE}fillColor=#DAE8FC;strokeColor=#6C8EBF;fontSize={F_TITLE};'
                 f'fontStyle=1;align=center;verticalAlign=middle;" vertex="1" parent="1">'
                 f'<mxGeometry x="{MARGIN_X}" y="{MARGIN_Y}" width="{FULL_W}" height="{TITLE_H}" '
                 f'as="geometry" /></mxCell>')
    # The task, as the one thing that enters the flow. Same sentence as before, drawn as a card.
    task_y = MARGIN_Y + TITLE_H + TITLE_GAP
    t = (BLUE[0], BLUE[1])
    box(cells, "in", "ЗАДАЧА В ВК", MARGIN_X, task_y, FULL_W, 56, t)
    # A COLUMN HEADER BAND per column: the reader is told what each column is. This is the fix for
    # a picture where a column of boxes has no name.
    band_y = task_y + 56 + GAP
    band(cells, "band_order", "ПОРЯДОК МЫШЛЕНИЯ — сверху вниз", ORDER_X, band_y, ORDER_W)
    band(cells, "band_can", "ЧТО ЭТОТ КЛЮЧ МОЖЕТ — измерено, не прочитано в документации",
         CAN_X, band_y, CAN_W)
    band(cells, "band_cannot", "ЧЕГО ЭТОТ КЛЮЧ НЕ МОЖЕТ — и это дороже, чем кажется",
         CANNOT_X, band_y, CANNOT_W)

    # Column 1: the order to think in, then a gap twice as large, then the publication itself.
    # The gap is the grouping - proximity says which boxes belong to which thought.
    y = band_y + BAND_H + GAP
    for i, (name, why, colours) in enumerate(ORDER):
        box(cells, f"o{i}", f"<b>{name}</b> — {why}", ORDER_X, y, ORDER_W, 56, colours)
        if i:
            arrow(cells, f"ao{i}", f"o{i - 1}", f"o{i}", colours[1])
        y += 56 + TIGHT
    order_bottom = y - TIGHT
    arrow(cells, "ao0", "in", "o0")

    y += GAP                      # GAP on top of TIGHT: the steps are a new group, not the next thought
    previous = "o3"
    arrow(cells, "as0", previous, "s0")
    for i, (number, title, why, colours) in enumerate(STEPS):
        label = (f'<b>{number} — {title}</b><br>'
                 f'<font color="#444444" style="font-size:{F_DETAIL}px">{why}</font>')
        box(cells, f"s{i}", label, ORDER_X, y, ORDER_W, STEP_H, colours)
        if i:
            arrow(cells, f"as{i}", f"s{i - 1}", f"s{i}")
        y += STEP_H + GAP
    flow_bottom = y - GAP

    # Columns 2 and 3: what the key can and cannot do. The items are siblings inside one meaning,
    # so they sit TIGHT together, and the two panels are separated by the full GAP.
    cy = band_y + BAND_H + GAP
    for i, item in enumerate(CAN):
        box(cells, f"c{i}", "+ " + item, CAN_X, cy, CAN_W, ITEM_H, GREEN, F_DETAIL)
        cy += ITEM_H + TIGHT
    can_bottom = cy - TIGHT

    ny = can_bottom + GAP         # the two panels are different meanings: the full GAP between them
    for i, item in enumerate(CANNOT):
        box(cells, f"n{i}", "− " + item, CANNOT_X, ny, CANNOT_W, ITEM_H, RED, F_DETAIL)
        ny += ITEM_H + TIGHT
    cannot_bottom = ny - TIGHT

    # ЛЕГЕНДА ПАНЕЛЬЮ, А НЕ СПИСКОМ СТРОК: строки без рамки читаются как продолжение карточек.
    # HTML собирается НАСТОЯЩИМИ <b> и <br> и экранируется РОВНО ОДИН РАЗ, в box().
    legend_rows = [
        ("ЧТО ЭТО ЗА СХЕМА",
         ["Работа с ВК: что ключ сообщества может и чего не может, и в каком порядке идёт публикация.",
          "Это НЕ структура файлов (family.drawio), НЕ ворота (gates.drawio) и НЕ суд (hearing.drawio)."]),
        ("КАК ЧИТАТЬ",
         ["Слева сверху вниз — порядок мышления и шаги публикации.",
          "Зелёная колонка — что получается. Красная — что не получается, и это важнее."]),
        ("ПОЧЕМУ КРАСНАЯ КОЛОНКА ГЛАВНАЯ",
         ["Отказы здесь приходят как успех: вызов возвращает 200 или post_id, а не происходит ничего.",
          "Стену нельзя прочитать обратно тем же ключом — проверить публикацию можно только глазами."]),
    ]
    parts: list[str] = []
    for heading, lines in legend_rows:
        parts.append(f'<b>{esc(heading)}</b>')
        parts.extend(esc(line) for line in lines)
        parts.append("&nbsp;")
    legend_html = "<br>".join(parts)
    legend_h = 34 + sum(len(lines) + 1 for _, lines in legend_rows) * 22 + 16
    legend_y = max(flow_bottom, order_bottom, cannot_bottom) + GAP
    cells.append(f'<mxCell id="legend" value="{esc(legend_html)}" style="{BOX}'
                 f'fillColor=#FFFFFF;strokeColor=#B3B3B3;align=left;verticalAlign=top;'
                 f'spacingLeft={PAD_L};spacingTop={PAD_T};fontSize={F_DETAIL};" vertex="1" '
                 f'parent="1"><mxGeometry x="{MARGIN_X}" y="{legend_y}" width="{FULL_W}" '
                 f'height="{legend_h}" as="geometry" /></mxCell>')

    # The traps are the reason the skill exists, so they get their own banded panel full width: a
    # header band above five siblings, TIGHT inside and GAP outside - the same grammar as the rest.
    traps_y = legend_y + legend_h + GAP
    band(cells, "band_traps", "ЛОВУШКИ, КОТОРЫЕ СТОЯТ ДОРОЖЕ ВСЕГО",
         MARGIN_X, traps_y, FULL_W)
    ty = traps_y + BAND_H + TIGHT
    for i, item in enumerate(TRAPS):
        box(cells, f"t{i}", item, MARGIN_X, ty, FULL_W, ITEM_H, ORANGE, F_DETAIL)
        ty += ITEM_H + TIGHT
    traps_bottom = ty - TIGHT

    # The page is measured from the content, not fixed.
    page_w = MARGIN_X + FULL_W + MARGIN_X
    page_h = traps_bottom + MARGIN_Y
    model = ('<mxGraphModel dx="0" dy="0" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" '
             'arrows="1" fold="1" page="1" pageScale="1" '
             f'pageWidth="{page_w}" pageHeight="{page_h}" math="0" '
             'shadow="0"><root><mxCell id="0" /><mxCell id="1" parent="0" />' + "".join(cells)
             + '</root></mxGraphModel>')
    model = ('<mxfile host="dsh" agent="draw-the-vk-flow.py"><diagram id="vk" name="ВК">'
             + model + '</diagram></mxfile>')

    out = repo / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(model, encoding="utf-8")
    print(f"  может {len(CAN)}   не может {len(CANNOT)}   ловушек {len(TRAPS)}   шагов {len(STEPS)}")
    print(f"  файл: {out.relative_to(repo)}  ({len(model):,} байт)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
