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
    cells.append(f'<mxCell id="head" value="{esc(title_ru)}" style="rounded=0;whiteSpace=wrap;html=1;'
                 f'fillColor=#DAE8FC;strokeColor=#6C8EBF;fontSize=16;fontStyle=1;" vertex="1" '
                 f'parent="1"><mxGeometry x="70" y="30" width="560" height="48" as="geometry" /></mxCell>')

    y, previous, untranslated = 110, "head", []
    for index, (heading, first) in enumerate(sections):
        translated = sections_ru.get(heading)
        if translated:
            russian, why = translated[0], (translated[1] if len(translated) > 1 else "")
        else:
            russian, why = heading, first
            untranslated.append(heading)
        label = (f'<b>{russian}</b><br>'
                 f'<font color="#444444" style="font-size:11px">{why}</font><br>'
                 f'<font color="#999999" style="font-size:9px">{heading}</font>')
        colour = LEVEL_COLOURS[min(index, len(LEVEL_COLOURS) - 1)]
        cells.append(f'<mxCell id="s{index}" value="{esc(label)}" style="rounded=1;whiteSpace=wrap;'
                     f'html=1;fillColor={colour[0]};strokeColor={colour[1]};align=left;spacingLeft=10;'
                     f'fontSize=12;" vertex="1" parent="1">'
                     f'<mxGeometry x="70" y="{y}" width="560" height="72" as="geometry" /></mxCell>')
        cells.append(f'<mxCell id="a{index}" style="endArrow=classic;html=1;strokeColor=#6C8EBF;'
                     f'strokeWidth=2;rounded=0;edgeStyle=orthogonalEdgeStyle;" edge="1" parent="1" '
                     f'source="{previous}" target="s{index}">'
                     f'<mxGeometry relative="1" as="geometry" /></mxCell>')
        previous, y = f"s{index}", y + 92

    legend = [f"ЧТО ЭТО ЗА СХЕМА",
              f"Порядок работы скилла {skill}: шаги в том порядке, в каком их надо делать.",
              "Это НЕ структура файлов (family.drawio) и НЕ ворота регламента (gates.drawio).",
              "",
              "КАК ЧИТАТЬ",
              "Синяя рамка сверху — сам скилл. Стрелка вниз — следующий шаг.",
              "Заголовок по-русски, под ним зачем этот шаг, внизу мелко — исходный заголовок из файла.",
              "",
              "О ЧЁМ ЭТОТ СКИЛЛ",
              gloss.get("what", "")]
    for row, text in enumerate(legend):
        bold = "1" if (text.isupper() or text.startswith("ЧТО") or text.startswith("КАК")
                       or text.startswith("О ЧЁМ")) else "0"
        # row is in the Y COORDINATE. Without it every line lands at the same spot and the legend draws
        # as one black smudge - which is what the operator saw and reported. The other three diagrams
        # had it right, so the bug looked like a rendering problem rather than a missing variable.
        cells.append(f'<mxCell id="l{row}" value="{esc(text)}" style="text;html=1;align=left;'
                     f'verticalAlign=middle;fontSize=12;fontStyle={bold};strokeColor=none;fillColor=none;"'
                     f' vertex="1" parent="1"><mxGeometry x="700" y="{110 + row * 30}" width="640" '
                     f'height="26" as="geometry" /></mxCell>')

    model = ('<mxGraphModel dx="0" dy="0" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" '
             'arrows="1" fold="1" page="1" pageScale="1" pageWidth="1400" pageHeight="1400" math="0" '
             'shadow="0"><root><mxCell id="0" /><mxCell id="1" parent="0" />' + "".join(cells)
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
