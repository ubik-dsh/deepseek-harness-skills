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
        colours: tuple[str, str], size: int = 12) -> None:
    cells.append(f'<mxCell id="{cell_id}" value="{esc(label)}" style="rounded=1;whiteSpace=wrap;'
                 f'html=1;fillColor={colours[0]};strokeColor={colours[1]};align=left;spacingLeft=10;'
                 f'fontSize={size};" vertex="1" parent="1">'
                 f'<mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry" /></mxCell>')


def arrow(cells: list[str], cell_id: str, source: str, target: str, colour: str = "#6C8EBF") -> None:
    cells.append(f'<mxCell id="{cell_id}" style="endArrow=classic;html=1;strokeColor={colour};'
                 f'strokeWidth=2;rounded=0;edgeStyle=orthogonalEdgeStyle;" edge="1" parent="1" '
                 f'source="{source}" target="{target}"><mxGeometry relative="1" as="geometry" /></mxCell>')


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("repo", type=Path)
    ap.add_argument("--out", default="_graph/vk.drawio")
    args = ap.parse_args()
    repo = args.repo.resolve()

    cells: list[str] = []
    cells.append('<mxCell id="in" value="ЗАДАЧА В ВК" style="rounded=0;whiteSpace=wrap;html=1;'
                 'fillColor=#DAE8FC;strokeColor=#6C8EBF;fontSize=16;fontStyle=1;" vertex="1" parent="1">'
                 '<mxGeometry x="80" y="30" width="380" height="46" as="geometry" /></mxCell>')

    # Порядок мышления.
    for i, (name, why, colours) in enumerate(ORDER):
        box(cells, f"o{i}", f"<b>{name}</b> — {why}", 80, 100 + i * 46, 380, 40, colours, 11)
        if i:
            arrow(cells, f"ao{i}", f"o{i-1}", f"o{i}", colours[1])
    arrow(cells, "ao0", "in", "o0")

    y = 300
    previous = "o3"
    arrow(cells, "as0", previous, "s0")
    for i, (number, title, why, colours) in enumerate(STEPS):
        label = (f'<b>{number} — {title}</b><br>'
                 f'<font color="#444444" style="font-size:11px">{why}</font>')
        box(cells, f"s{i}", label, 80, y, 380, 56, colours)
        if i:
            arrow(cells, f"as{i}", f"s{i-1}", f"s{i}")
        y += 74

    # Главное: что можно и что нельзя.
    box(cells, "ch", "<b>ЧТО ЭТОТ КЛЮЧ МОЖЕТ</b> — измерено, не прочитано в документации",
        540, 100, 470, 30, GREEN, 13)
    cy = 142
    for i, item in enumerate(CAN):
        box(cells, f"c{i}", "+ " + item, 540, cy, 470, 38, GREEN, 11)
        cy += 46
    box(cells, "nh", "<b>ЧЕГО ЭТОТ КЛЮЧ НЕ МОЖЕТ</b> — и это дороже, чем кажется",
        540, cy + 20, 470, 30, RED, 13)
    ny = cy + 62
    for i, item in enumerate(CANNOT):
        box(cells, f"n{i}", "− " + item, 540, ny, 470, 44, RED, 11)
        ny += 52

    ty = max(ny, y) + 40
    box(cells, "th", "<b>ЛОВУШКИ, КОТОРЫЕ СТОЯТ ДОРОЖЕ ВСЕГО</b>", 80, ty, 930, 30, ORANGE, 13)
    for i, item in enumerate(TRAPS):
        box(cells, f"t{i}", item, 80, ty + 42 + i * 40, 930, 34, ORANGE, 11)

    legend = ["ЧТО ЭТО ЗА СХЕМА",
              "Работа с ВК: что ключ сообщества может и чего не может, и в каком порядке идёт публикация.",
              "Это НЕ структура файлов (family.drawio), НЕ ворота (gates.drawio) и НЕ суд (hearing.drawio).",
              "",
              "КАК ЧИТАТЬ",
              "Слева сверху вниз — порядок мышления и шаги публикации.",
              "Зелёная колонка — что получается. Красная — что не получается, и это важнее.",
              "",
              "ПОЧЕМУ КРАСНАЯ КОЛОНКА ГЛАВНАЯ",
              "Отказы здесь приходят как успех: вызов возвращает 200 или post_id, а не происходит ничего.",
              "Стену нельзя прочитать обратно тем же ключом — проверить публикацию можно только глазами."]
    for row, text in enumerate(legend):
        bold = "1" if (text.isupper() or text.startswith("ЧТО") or text.startswith("КАК")
                       or text.startswith("ПОЧЕМУ")) else "0"
        cells.append(f'<mxCell id="l{row}" value="{esc(text)}" style="text;html=1;align=left;'
                     f'verticalAlign=middle;fontSize=12;fontStyle={bold};strokeColor=none;fillColor=none;"'
                     f' vertex="1" parent="1"><mxGeometry x="80" y="{ty + 280 + row * 26}" width="1140" '
                     f'height="24" as="geometry" /></mxCell>')

    model = ('<mxGraphModel dx="0" dy="0" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" '
             'arrows="1" fold="1" page="1" pageScale="1" pageWidth="1100" pageHeight="1600" math="0" '
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
