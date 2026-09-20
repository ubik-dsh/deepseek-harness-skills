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


def esc(text: str) -> str:
    return html.escape(str(text), quote=True)


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
    cells.append('<mxCell id="task" value="ЗАДАЧА" style="rounded=0;whiteSpace=wrap;html=1;'
                 'fillColor=#DAE8FC;strokeColor=#6C8EBF;fontSize=16;fontStyle=1;" vertex="1" parent="1">'
                 '<mxGeometry x="90" y="40" width="420" height="50" as="geometry" /></mxCell>')

    order = ["G7", "G1", "G2", "G3", "G4", "G5", "G6", "G8"]
    y = 140
    previous = "task"
    for number in order:
        russian, condition, forces, fill, stroke = MEANING[number]
        english = found.get(number, ("", ""))[0]
        label = (f'<b>{number} — {russian}</b><br>'
                 f'<font style="font-size:11px">Срабатывает: {condition}</font><br>'
                 f'<font color="#1a6b1a" style="font-size:11px">Требует: {forces}</font><br>'
                 f'<font color="#888888" style="font-size:9px">{english}</font>')
        cell = f"g{number}"
        cells.append(f'<mxCell id="{cell}" value="{esc(label)}" '
                     f'style="rounded=1;whiteSpace=wrap;html=1;fillColor={fill};strokeColor={stroke};'
                     f'align=left;spacingLeft=10;fontSize=12;" vertex="1" parent="1">'
                     f'<mxGeometry x="90" y="{y}" width="560" height="86" as="geometry" /></mxCell>')
        cells.append(f'<mxCell id="a{number}" style="endArrow=classic;html=1;strokeColor=#6C8EBF;'
                     f'strokeWidth=2;rounded=0;edgeStyle=orthogonalEdgeStyle;" edge="1" parent="1" '
                     f'source="{previous}" target="{cell}">'
                     f'<mxGeometry relative="1" as="geometry" /></mxCell>')
        previous = cell
        y += 110

    # Легенда внутри схемы: читатель не должен узнавать значения из другого файла.
    legend = ["ЧТО ЭТО ЗА СХЕМА",
              "Поток ворот регламента route-a-task: что срабатывает, когда приходит задача.",
              "Это НЕ схема файлов — та лежит в family.drawio и её эта не трогает.",
              "",
              "КАК ЧИТАТЬ",
              "Синяя рамка сверху — задача. Стрелка вниз — «после этого шага смотрим следующий».",
              "Фиолетовая — ворота, которые решают, применимо ли всё остальное.",
              "Оранжевые — обязательные при своём условии.",
              "Зелёная — про сохранность работы.",
              "",
              "ЧТО ЗНАЧИТ «ТРЕБУЕТ»",
              "Это не совет, а обязательный шаг. Пропустить его нельзя, даже если кажется лишним.",
              "Порядок — порядок чтения, а не номер: G7 стоит первым намеренно."]
    for row, text in enumerate(legend):
        bold = "1" if (text.isupper() or text.startswith("ЧТО") or text.startswith("КАК")) else "0"
        cells.append(f'<mxCell id="l{row}" value="{esc(text)}" style="text;html=1;align=left;'
                     f'verticalAlign=middle;fontSize=12;fontStyle={bold};strokeColor=none;'
                     f'fillColor=none;" vertex="1" parent="1">'
                     f'<mxGeometry x="700" y="{140 + row * 26}" width="620" height="24" '
                     f'as="geometry" /></mxCell>')

    model = ('<mxGraphModel dx="0" dy="0" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" '
             'arrows="1" fold="1" page="1" pageScale="1" pageWidth="1400" pageHeight="1200" '
             'math="0" shadow="0"><root><mxCell id="0" /><mxCell id="1" parent="0" />'
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
