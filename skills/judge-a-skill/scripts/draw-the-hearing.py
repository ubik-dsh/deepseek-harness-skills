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
    cells.append('<mxCell id="defendant" value="СКИЛЛ-ПОДСУДИМЫЙ" style="rounded=0;whiteSpace=wrap;'
                 'html=1;fillColor=#DAE8FC;strokeColor=#6C8EBF;fontSize=16;fontStyle=1;" vertex="1" '
                 'parent="1"><mxGeometry x="80" y="40" width="420" height="50" as="geometry" /></mxCell>')

    previous, y = "defendant", 140
    for number in [f"Step {i}" for i in range(8)]:
        russian, role, fill, stroke = STEP_RU[number]
        english = steps.get(number, "")
        label = (f'<b>{number} — {russian}</b><br>'
                 f'<font color="#333333" style="font-size:11px">{role}</font><br>'
                 f'<font color="#888888" style="font-size:9px">{english}</font>')
        cell = f"s{number[-1]}"
        cells.append(f'<mxCell id="{cell}" value="{esc(label)}" style="rounded=1;whiteSpace=wrap;'
                     f'html=1;fillColor={fill};strokeColor={stroke};align=left;spacingLeft=10;'
                     f'fontSize=12;" vertex="1" parent="1">'
                     f'<mxGeometry x="80" y="{y}" width="540" height="76" as="geometry" /></mxCell>')
        cells.append(f'<mxCell id="a{number[-1]}" style="endArrow=classic;html=1;strokeColor=#6C8EBF;'
                     f'strokeWidth=2;rounded=0;edgeStyle=orthogonalEdgeStyle;" edge="1" parent="1" '
                     f'source="{previous}" target="{cell}"><mxGeometry relative="1" as="geometry" /></mxCell>')
        previous, y = cell, y + 96

    # Приговоры отдельной колонкой: их пять, и они выход суда, а не шаг.
    cells.append('<mxCell id="vh" value="ПЯТЬ ПРИГОВОРОВ — из них выбирает судья" style="text;html=1;'
                 'align=left;fontSize=14;fontStyle=1;strokeColor=none;fillColor=none;" vertex="1" '
                 'parent="1"><mxGeometry x="700" y="112" width="520" height="26" as="geometry" /></mxCell>')
    vy = 148
    for name in verdicts:
        russian, when, fill, stroke = VERDICT_RU.get(name, (name, "", "#F5F5F5", "#666666"))
        label = (f'<b>{russian}</b><br>'
                 f'<font style="font-size:11px">{when}</font><br>'
                 f'<font color="#888888" style="font-size:9px">{name}</font>')
        cells.append(f'<mxCell id="v{vy}" value="{esc(label)}" style="rounded=1;whiteSpace=wrap;html=1;'
                     f'fillColor={fill};strokeColor={stroke};align=left;spacingLeft=10;fontSize=12;" '
                     f'vertex="1" parent="1"><mxGeometry x="700" y="{vy}" width="520" height="70" '
                     f'as="geometry" /></mxCell>')
        vy += 84
    cells.append(f'<mxCell id="av" style="endArrow=classic;html=1;strokeColor=#6C8EBF;strokeWidth=2;'
                 f'dashed=1;edgeStyle=orthogonalEdgeStyle;" edge="1" parent="1" source="s5" '
                 f'target="v148"><mxGeometry relative="1" as="geometry" /></mxCell>')

    legend = ["ЧТО ЭТО ЗА СХЕМА",
              "Процесс суда над скиллом — judge-a-skill. Как скилл обвиняют, защищают и судят.",
              "Это НЕ схема файлов (family.drawio) и НЕ ворота регламента (gates.drawio).",
              "У каждого процесса своя схема, и они друг друга не заменяют.",
              "",
              "КАК ЧИТАТЬ",
              "Синяя рамка сверху — подсудимый. Стрелка вниз — следующий шаг суда.",
              "Красная — сторона обвинения. Зелёная — сторона защиты.",
              "Пунктир к колонке справа — «судья выбирает одно из пяти».",
              "",
              "ЧТО ГЛАВНОЕ В ЭТОМ ПРОЦЕССЕ",
              "Обвинительный лист пишется ДО чтения защиты себя — иначе доводы подгоняются под ответ.",
              "Чистый приговор — полноценный исход: если конкретного довода не уцелело, скилл оставляют.",
              "Обе стороны получают оценку, чтобы близкое решение было видно как близкое."]
    for row, text in enumerate(legend):
        bold = "1" if (text.isupper() or text.startswith("ЧТО") or text.startswith("КАК")) else "0"
        cells.append(f'<mxCell id="l{row}" value="{esc(text)}" style="text;html=1;align=left;'
                     f'verticalAlign=middle;fontSize=12;fontStyle={bold};strokeColor=none;fillColor=none;"'
                     f' vertex="1" parent="1"><mxGeometry x="80" y="{1010 + row * 26}" width="1140" '
                     f'height="24" as="geometry" /></mxCell>')

    model = ('<mxGraphModel dx="0" dy="0" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" '
             'arrows="1" fold="1" page="1" pageScale="1" pageWidth="1300" pageHeight="1400" math="0" '
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
