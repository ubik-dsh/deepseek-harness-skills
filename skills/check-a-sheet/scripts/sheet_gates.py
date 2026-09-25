"""Ворота для таблицы: измеримые проверки книги .xlsx.

ОТКУДА ИДЕЯ. У плагина spreadsheets Кодекса-десктопа
(`%USERPROFILE%\\.cache\\codex-runtimes\\...\\plugins\\spreadsheets`, лицензия
Proprietary) два скилла: `spreadsheets` (65 КБ правил и поверок) и
`excel-live-control` (72 КБ, водит открытый Excel через Office.js). Там же —
руководства по областям: финансовые модели, медицина, маркетинг, наука.

Наше — то же по смыслу, но проверяемое и без их кода: `openpyxl`, никаких
зависимостей сверх обычного Python. Водить открытый Excel мы не умеем и не
делаем вид: здесь читается файл.

ЧТО ЛОВЯТ ВОРОТА

    ошибки формул     #REF!, #DIV/0!, #VALUE!, #NAME?, #N/A, #NUM!, #NULL!
    число как текст   «1 234,5» строкой — Excel такое не складывает
    разрыв столбца    в столбце формул одна ячейка вбита числом руками
    итоги             «Итого» не сходится с суммой слагаемых над ним
    дубликаты ключей  повтор в первом столбце таблицы
    объединённые      объединённые ячейки поверх данных
    без результата    формула есть, а посчитанного значения в файле нет

ЧЕГО НЕ ДЕЛАЕТ. Не считает сами формулы: openpyxl читает либо формулу, либо
последнее посчитанное значение, но не вычисляет. Поэтому «итоги» сверяются
только там, где рядом с формулой есть посчитанное значение, — иначе честно
говорится «посчитать нечем».

    python sheet_gates.py КНИГА.xlsx [--json] [--render папка]
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

if sys.stdout is not None:
    sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")

import openpyxl  # noqa: E402

ERRORS = ("#REF!", "#DIV/0!", "#VALUE!", "#NAME?", "#N/A", "#NUM!", "#NULL!", "#GETTING_DATA")
TOTAL_WORD = re.compile(r"^(итого|всего|total|sum)\b", re.IGNORECASE)
# Число, записанное текстом: пробелы как разделители разрядов, запятая вместо точки.
NUMERIC_TEXT = re.compile(r"^-?\d{1,3}(?:[ \u00a0]\d{3})+(?:[.,]\d+)?$|^-?\d+,\d+$")


def as_number(value):
    """Число из ячейки: числа как есть, строки — только если это точно число."""
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    if isinstance(value, str):
        cleaned = value.strip().replace("\u00a0", "").replace(" ", "").replace(",", ".")
        cleaned = cleaned.replace("%", "")
        try:
            return float(cleaned)
        except ValueError:
            return None
    return None


def gate(book_path: Path) -> dict:
    formulas = openpyxl.load_workbook(book_path, data_only=False)
    values = openpyxl.load_workbook(book_path, data_only=True)
    findings: list[dict] = []
    warnings: list[dict] = []
    formulas_without_value = 0
    formula_cells = 0

    for name in formulas.sheetnames:
        sheet = formulas[name]
        cached = values[name]
        merged = [str(rng) for rng in sheet.merged_cells.ranges]

        # Объединённые ячейки.
        # ПЕРВАЯ ВЕРСИЯ ЭТОЙ ПРОВЕРКИ НЕ МОГЛА СРАБОТАТЬ НИКОГДА: она искала
        # объединение, накрывающее больше одной заполненной ячейки, а в xlsx
        # значение хранит только левая верхняя клетка диапазона. Поймал тест.
        # Честный признак другой: объединение внутри блока данных — когда в тех же
        # строках, но вне объединённых столбцов, есть заполненные ячейки.
        for rng in sheet.merged_cells.ranges:
            filled_outside = 0
            for row_index in range(rng.min_row, rng.max_row + 1):
                for col_index in range(1, sheet.max_column + 1):
                    if rng.min_col <= col_index <= rng.max_col:
                        continue
                    if sheet.cell(row=row_index, column=col_index).value not in (None, ""):
                        filled_outside += 1
            size = rng.size["columns"] * rng.size["rows"]
            if filled_outside and size > 1:
                findings.append({"kind": "объединённые", "sheet": name, "where": str(rng),
                                 "text": f"объединение {rng} стоит внутри строк данных: "
                                         f"рядом с ним заполнено {filled_outside} ячеек; "
                                         f"сортировка и формулы такую сетку не любят"})

        for row in sheet.iter_rows():
            for cell in row:
                value = cell.value
                if isinstance(value, str) and value.startswith("="):
                    formula_cells += 1
                    seen = cached[cell.coordinate].value
                    if seen is None or (isinstance(seen, str) and seen in ERRORS):
                        formulas_without_value += 1
                    if isinstance(seen, str) and seen in ERRORS:
                        findings.append({"kind": "ошибка формулы", "sheet": name,
                                         "where": cell.coordinate,
                                         "text": f"{value[:40]} → {seen}"})
                    continue
                if isinstance(value, str):
                    if value.strip() in ERRORS:
                        findings.append({"kind": "ошибка формулы", "sheet": name,
                                         "where": cell.coordinate, "text": value.strip()})
                    elif NUMERIC_TEXT.match(value.strip()):
                        warnings.append({"kind": "число как текст", "sheet": name,
                                         "where": cell.coordinate,
                                         "text": f"«{value.strip()}» — Excel такое не сложит"})
                    continue

        # разрыв в столбце формул: столбец, где формул много, а одна ячейка — константа
        for column in sheet.iter_cols():
            cells = [c for c in column if c.value not in (None, "")]
            if len(cells) < 4:
                continue
            flags = [isinstance(c.value, str) and c.value.startswith("=") for c in cells]
            if sum(flags) >= 3 and not all(flags) and any(not f for f in flags):
                soft = [c.coordinate for c, f in zip(cells, flags) if not f]
                warnings.append({"kind": "разрыв столбца", "sheet": name,
                                 "where": ",".join(soft[:4]),
                                 "text": f"столбец {cells[0].column_letter}: формул {sum(flags)}, "
                                         f"констант {len(soft)} — похоже, одну ячейку вписали руками"})

        # итоги: строка «Итого» против суммы слагаемых над ней
        for row in sheet.iter_rows():
            for cell in row:
                if not isinstance(cell.value, str) or not TOTAL_WORD.match(cell.value.strip()):
                    continue
                for column in range(cell.column + 1, sheet.max_column + 1):
                    stated = as_number(cached.cell(row=cell.row, column=column).value)
                    # Слагаемые берём из листа с ПОСЧИТАННЫМИ значениями: на листе
                    # с формулами ячейка содержит строку «=B2*C2», и первая версия
                    # считала её не числом, а пустотой — проверка молча пропускала
                    # любой неверный итог. Поймал тест.
                    addends = [cached.cell(row=above, column=column).value
                               for above in range(1, cell.row)]
                    numbers = [as_number(v) for v in addends if v not in (None, "")]
                    if stated is None or len(numbers) < 1 or any(n is None for n in numbers):
                        continue
                    total = round(sum(numbers), 6)
                    if abs(total - stated) > 0.01:
                        findings.append({
                            "kind": "итоги", "sheet": name, "where": cell.coordinate,
                            "text": f"столбец {sheet.cell(row=1, column=column).column_letter}: "
                                    f"заявлено {stated:g}, сумма слагаемых {total:g}",
                        })

        # дубликаты в первом столбце: признак таблицы — заполнено много строк
        first = [sheet.cell(row=r, column=1).value for r in range(2, sheet.max_row + 1)]
        keys = [str(v).strip() for v in first if v not in (None, "")]
        seen_keys: dict[str, int] = {}
        for key in keys:
            seen_keys[key] = seen_keys.get(key, 0) + 1
        for key, count in seen_keys.items():
            if count > 1:
                warnings.append({"kind": "дубликат ключа", "sheet": name, "where": "столбец A",
                                 "text": f"«{key[:30]}» встречается {count} раз"})

        if merged:
            warnings.append({"kind": "объединённые ячейки", "sheet": name, "where": ",".join(merged[:3]),
                             "text": f"объединений на листе: {len(merged)}"})

    return {
        "file": str(book_path),
        "sheets": formulas.sheetnames,
        "formula_cells": formula_cells,
        "formulas_without_value": formulas_without_value,
        "findings": findings,
        "warnings": warnings,
    }


def render(path: Path, outdir: Path) -> str:
    soffice = shutil.which("soffice") or r"C:\Program Files\LibreOffice\program\soffice.exe"
    if not Path(soffice).exists():
        return "LibreOffice не найден — рендер пропущен"
    outdir.mkdir(parents=True, exist_ok=True)
    result = subprocess.run([soffice, "--headless", "--convert-to", "pdf",
                             "--outdir", str(outdir), str(path)],
                            capture_output=True, text=True, timeout=300)
    if result.returncode != 0:
        return f"LibreOffice отказался: {result.stderr.strip()[:120]}"
    pdf = outdir / (path.stem + ".pdf")
    return f"PDF для просмотра: {pdf}" if pdf.exists() else "PDF не появился"


def main() -> int:
    parser = argparse.ArgumentParser(description="Ворота для .xlsx")
    parser.add_argument("book", type=Path)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--render", type=Path, default=None)
    args = parser.parse_args()

    if not args.book.is_file():
        print(f"книги нет: {args.book}")
        return 1
    try:
        report = gate(args.book)
    except Exception as error:
        print(f"книга не открылась: {type(error).__name__} {error}")
        return 1

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"книга: {args.book.name}")
        print(f"листов: {len(report['sheets'])} — {', '.join(report['sheets'][:5])}")
        print(f"ячеек с формулами: {report['formula_cells']}")
        if report["formulas_without_value"]:
            print(f"формул без посчитанного значения в файле: {report['formulas_without_value']} "
                  f"(openpyxl их не считает — итоги по ним не сверяются)")
        if report["findings"]:
            print(f"\nНЕ ПРОХОДИТ ({len(report['findings'])}):")
            for item in report["findings"]:
                print(f"  {item['sheet']:<14} {item['where']:<10} {item['kind']:<15} {item['text']}")
        else:
            print("\nжёсткие ворота пройдены")
        if report["warnings"]:
            print(f"\nзамечания ({len(report['warnings'])}):")
            for item in report["warnings"][:12]:
                print(f"  {item['sheet']:<14} {item['where']:<10} {item['kind']:<18} {item['text']}")
    if args.render:
        print(render(args.book, args.render))
    return 1 if report["findings"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
