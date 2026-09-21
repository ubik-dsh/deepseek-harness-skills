#!/usr/bin/env python3
"""Draw any skill's steps as a flow, in Russian, into its own .drawio file.

Sibling of `graph-skills.py` and `draw-the-family.py`, but for ONE skill instead of the whole family. The
steps are read out of that skill's SKILL.md, so the picture cannot drift from the skill it draws - only
the Russian glosses are kept beside this script, because a diagram is for a person.

    python draw-a-skill-flow.py <repo> <skill> [--out _graph/<skill>.drawio]

Glosses live in `skill-glosses.ru.json` next to this file:

    {
      "manage-windows": {
        "title": "Работа с Windows из агента",
        "sections": {"Step 0 — read before you touch": ["Прочитать до того, как трогать", "почему это первое"]}
      }
    }

A heading with no gloss is drawn in English with a marker, so a missing translation is VISIBLE rather
than silently passed over.

The output is a NEW file every time and never touches another diagram: each skill has its own picture and
its own window.
"""
from __future__ import annotations

import argparse
import html
import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")

BLUE, GREEN, ORANGE, RED, PURPLE, GREY = (
    ("#DAE8FC", "#6C8EBF"), ("#D5E8D4", "#82B366"), ("#FFE6CC", "#D79B00"),
    ("#F8CECC", "#B85450"), ("#E1D5E7", "#9673A6"), ("#F5F5F5", "#666666"))

LEVEL_COLOURS = [BLUE, ORANGE, PURPLE, GREEN, GREY]

# ── ВИД. Числа не на глаз: каждое отвечает на жалобу «как описание книги».
#
# Правило, из которого выведено остальное: РАЗМЕР И ОТСТУП ГОВОРЯТ О РОЛИ. Одинаковая высота у всех
# рамок убирает иерархию, и взгляду не за что зацепиться - страница читается одним абзацем.
TITLE_H = 78        # заголовок схемы: крупнее всех, потому что он и есть вход
STEP_H = 88         # шаг: заголовок + зачем + исходная строка
GAP = 42            # воздух между шагами. Меньше 30 - рамки читаются как один блок
BOX_W = 640         # ширина колонки шагов
PAD_L = 20          # отступ слева внутри рамки: 10 заставляло текст липнуть к границе
PAD_T = 10          # отступ сверху, иначе первая строка прижата к рамке
MARGIN_X, MARGIN_Y = 90, 60     # поля страницы: схема не должна начинаться у края листа

# Тень даёт объём и отделяет рамку от листа. arcSize подобран так, чтобы скругление читалось, но не
# спорило с прямоугольной сеткой колонок.
BOX = "rounded=1;arcSize=10;whiteSpace=wrap;html=1;shadow=1;strokeWidth=1;"
TITLE = "rounded=1;arcSize=10;whiteSpace=wrap;html=1;shadow=1;strokeWidth=2;"

# Иерархия шрифта: четыре размера, и каждый значит ровно одно.
F_TITLE, F_STEP, F_DETAIL, F_PATH = 18, 13, 11, 9


def esc(text: str) -> str:
    return html.escape(str(text), quote=True)


def sections_of(text: str) -> list[tuple[str, str]]:
    """Every `##` heading and the first sentence under it. `###` belongs to its parent."""
    out: list[tuple[str, str]] = []
    for match in re.finditer(r"^##\s+(.+?)\n(.*?)(?=^##\s|\Z)", text, re.S | re.M):
        heading = match.group(1).strip()
        if heading.startswith("What this skill does not cover") or heading.startswith("Refining"):
            continue
        body = re.sub(r"[`*#>]", "", match.group(2)).strip()
        first = re.split(r"(?<=\.)\s", body)[0][:150] if body else ""
        out.append((heading, first))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("repo", type=Path)
    ap.add_argument("skill")
    ap.add_argument("--out", default="")
    args = ap.parse_args()
    repo = args.repo.resolve()
    skill = args.skill
    out_rel = args.out or f"_graph/{skill}.drawio"

    source_path = repo / "skills" / skill / "SKILL.md"
    if not source_path.exists():
        print(f"  нет такого скилла: {source_path}")
        return 2
    source = source_path.read_text(encoding="utf-8")

    gloss_path = Path(__file__).resolve().parent / "skill-glosses.ru.json"
    all_gloss = json.loads(gloss_path.read_text(encoding="utf-8")) if gloss_path.exists() else {}
    gloss = all_gloss.get(skill, {})
    title_ru = gloss.get("title", skill)
    sections_ru: dict[str, list[str]] = gloss.get("sections", {})

    sections = sections_of(source)
    if not sections:
        print(f"  в {skill}/SKILL.md не нашлось разделов ## ")
        return 1

    cells: list[str] = []
    cells.append(f'<mxCell id="head" value="{esc(title_ru)}" style="{TITLE}'
                 f'fillColor=#DAE8FC;strokeColor=#6C8EBF;fontSize={F_TITLE};fontStyle=1;'
                 f'align=center;verticalAlign=middle;" vertex="1" parent="1">'
                 f'<mxGeometry x="{MARGIN_X}" y="{MARGIN_Y}" width="{BOX_W}" height="{TITLE_H}" '
                 f'as="geometry" /></mxCell>')

    y, previous, untranslated = MARGIN_Y + TITLE_H + GAP, "head", []
    for index, (heading, first) in enumerate(sections):
        translated = sections_ru.get(heading)
        if translated:
            russian, why = translated[0], (translated[1] if len(translated) > 1 else "")
        else:
            russian, why = heading, first
            untranslated.append(heading)
        label = (f'<b>{russian}</b><br>'
                 f'<font color="#444444" style="font-size:{F_DETAIL}px">{why}</font><br>'
                 f'<font color="#999999" style="font-size:{F_PATH}px">{heading}</font>')
        colour = LEVEL_COLOURS[min(index, len(LEVEL_COLOURS) - 1)]
        cells.append(f'<mxCell id="s{index}" value="{esc(label)}" style="{BOX}'
                     f'fillColor={colour[0]};strokeColor={colour[1]};align=left;verticalAlign=middle;'
                     f'spacingLeft={PAD_L};spacingTop={PAD_T};spacingBottom={PAD_T};'
                     f'fontSize={F_STEP};" vertex="1" parent="1">'
                     f'<mxGeometry x="{MARGIN_X}" y="{y}" width="{BOX_W}" height="{STEP_H}" '
                     f'as="geometry" /></mxCell>')
        cells.append(f'<mxCell id="a{index}" style="endArrow=classic;html=1;strokeColor=#6C8EBF;'
                     f'strokeWidth=2;rounded=0;edgeStyle=orthogonalEdgeStyle;exitX=0.5;exitY=1;'
                     f'exitDx=0;exitDy=0;entryX=0.5;entryY=0;entryDx=0;entryDy=0;" edge="1" parent="1" '
                     f'source="{previous}" target="s{index}">'
                     f'<mxGeometry relative="1" as="geometry" /></mxCell>')
        previous, y = f"s{index}", y + STEP_H + GAP

    # ЛЕГЕНДА ПАНЕЛЬЮ, А НЕ СПИСКОМ СТРОК. Строки без рамки читаются как продолжение схемы и глазом
    # не отделяются от шагов; панель с заголовком и полями говорит: это справка, а не часть потока.
    legend_rows = [("ЧТО ЭТО ЗА СХЕМА",
                    [f"Порядок работы скилла {skill}: шаги в том порядке, в каком их надо делать.",
                     "Это НЕ структура файлов (family.drawio) и НЕ ворота регламента (gates.drawio)."]),
                   ("ЦВЕТ РАМОК — ЧЕРЕДОВАНИЕ, А НЕ ЗНАЧЕНИЕ",
                    ["Пять цветов идут по кругу по номеру шага. Они не значат ничего: ни важности,",
                     "ни очереди, ни типа. Это полосатость — чтобы глаз не терял строку в длинном",
                     "списке, как в таблице с чередующимися строками.",
                     "Если у шагов появится настоящий признак — обязательный, опасный, ворота —",
                     "цвет надо будет отдать ЕМУ, а не номеру. Пока такого признака нет."]),
                   ("КАК ЧИТАТЬ",
                    ["Синяя рамка сверху — сам скилл. Стрелка вниз — следующий шаг.",
                     "Заголовок по-русски, под ним зачем этот шаг, внизу мелко — исходный заголовок."]),
                   ("О ЧЁМ ЭТОТ СКИЛЛ", [gloss.get("what", "")])]
    parts = []
    for heading, lines in legend_rows:
        parts.append(f'<b>{esc(heading)}</b>')
        parts.extend(esc(line) for line in lines if line)
        parts.append("&nbsp;")
    legend_html = "<br>".join(parts)
    legend_h = 34 + sum(len(lines) + 1 for _, lines in legend_rows) * 22 + 16
    cells.append(f'<mxCell id="legend" value="{esc(legend_html)}" style="{BOX}'
                 f'fillColor=#FFFFFF;strokeColor=#B3B3B3;align=left;verticalAlign=top;'
                 f'spacingLeft={PAD_L};spacingTop={PAD_T};fontSize={F_DETAIL};" vertex="1" parent="1">'
                 f'<mxGeometry x="{MARGIN_X + BOX_W + GAP + 60}" y="{MARGIN_Y}" width="660" '
                 f'height="{legend_h}" as="geometry" /></mxCell>')

    page_h = max(y, MARGIN_Y + legend_h) + MARGIN_Y
    page_w = MARGIN_X + BOX_W + GAP + 60 + 660 + MARGIN_X
    model = ('<mxGraphModel dx="0" dy="0" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" '
             f'arrows="1" fold="1" page="1" pageScale="1" pageWidth="{page_w}" pageHeight="{page_h}" '
             'math="0" shadow="0"><root><mxCell id="0" /><mxCell id="1" parent="0" />' + "".join(cells)
             + '</root></mxGraphModel>')
    model = (f'<mxfile host="dsh" agent="draw-a-skill-flow.py"><diagram id="{esc(skill)}" '
             f'name="{esc(title_ru)}">{model}</diagram></mxfile>')

    out = repo / out_rel
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(model, encoding="utf-8")
    print(f"  {skill}: шагов {len(sections)}   {out.relative_to(repo)}  ({len(model):,} байт)")
    if untranslated:
        print(f"  БЕЗ ПЕРЕВОДА ({len(untranslated)}): {untranslated[:3]}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
