"""Проверка ФОРМЫ отчёта о рецензии: находка без места — не находка.

Зачем проверять форму отчёта, а не код: смысл рецензии машинно не оценить, а вот
её обязательный минимум — можно. Находка без уровня, без места (файл:строка) и без
проверяемого утверждения бесполезна: её нельзя ни проверить, ни починить. Отчёт
«находок нет» без списка проверенного — это «не смотрел».

    python check-review.py ОТЧЁТ.md [--json]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

if sys.stdout is not None:
    sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")

SEVERITY = ("критично", "важно", "мелко")
# «путь:строка» — папки, точки, дефисы, кириллица, любые расширения
LOCATION = re.compile(r"[\w./\\\u0400-\u04FF-]+\.\w+:\d+|[\w./\\\u0400-\u04FF-]+:\d+")
CHECKED = re.compile(r"^\s*(?:##\s*)?(что проверялось|проверено|checked)\b", re.IGNORECASE)
NONE_FOUND = re.compile(r"находок нет|находок не найдено|no findings", re.IGNORECASE)
FINDING = re.compile(r"^\s*[-*]\s*\[(критично|важно|мелко)\]\s*(.*)$", re.IGNORECASE)
# Утверждение должно быть проверяемым: назван прогон, вывод или команда.
# ПЕРВАЯ ВЕРСИЯ считала доводом любую цифру (`\d`), и находка «README.md:12 —
# стиль не тот» проходила как доказанная: номер строки выглядел доказательством.
# Поймал тест.
EVIDENCE = re.compile(r"проверил|проверено|прогон|запустил|вывод|тест|ворота|команда|"
                      r"открыл|сравнил|посчитал", re.IGNORECASE)


def collect(lines: list[str]) -> list[dict]:
    """Собрать находки. Многострочные тоже: довод часто стоит на второй строке.

    Первая версия смотрела только на строку с находкой и потому браковала верный
    отчёт, где «проверил прогоном» написано ниже. Поймал тест.
    """
    findings = []
    current = None
    for number, line in enumerate(lines, start=1):
        match = FINDING.match(line)
        if match:
            if current is not None:
                findings.append(current)
            current = {"line": number, "severity": match.group(1).lower(),
                       "text": match.group(2).strip(), "body": match.group(2).strip()}
            continue
        if current is None:
            continue
        if line.strip() == "" or line.lstrip().startswith(("#", "-", "*")):
            findings.append(current)
            current = None
            continue
        current["body"] += " " + line.strip()
    if current is not None:
        findings.append(current)
    return findings


def check(text: str) -> dict:
    lines = text.splitlines()
    checked_section = any(CHECKED.match(line) for line in lines)
    raw = collect(lines)
    problems = []
    findings = []

    for entry in raw:
        place = LOCATION.search(entry["body"])
        findings.append({"line": entry["line"], "severity": entry["severity"],
                         "text": entry["text"][:110],
                         "where": place.group(0) if place else None})
        if place is None:
            problems.append(f"строка {entry['line']}: находка «{entry['severity']}» без места — "
                            f"укажите файл:строка, иначе её негде смотреть")
        # Прогон требуется там, где утверждение о ПОВЕДЕНИИ. Для опечатки в «мелко»
        # требовать прогон — выдумка: чинится взглядом.
        if entry["severity"] in ("критично", "важно") and not EVIDENCE.search(entry["body"]):
            problems.append(f"строка {entry['line']}: находка «{entry['severity']}» о поведении "
                            f"без проверяемого утверждения — скажите, чем это видно")

    none_found = any(NONE_FOUND.search(line) for line in lines)
    if not findings and not none_found:
        problems.append("нет ни находок, ни прямого «находок нет» — непонятно, что вышло")
    if (not findings or none_found) and not checked_section:
        problems.append("не сказано, ЧТО проверялось: «находок нет» без списка проверенного "
                        "означает «не смотрел»")

    return {
        "findings": findings,
        "counts": {level: sum(1 for f in findings if f["severity"] == level) for level in SEVERITY},
        "checked_section": checked_section,
        "none_found": none_found,
        "problems": problems,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Форма отчёта о рецензии")
    parser.add_argument("report", type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    if not args.report.is_file():
        print(f"отчёта нет: {args.report}")
        return 1
    report = check(args.report.read_text(encoding="utf-8", errors="replace"))

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        counts = report["counts"]
        print(f"находок: {len(report['findings'])} "
              f"(критично {counts['критично']}, важно {counts['важно']}, мелко {counts['мелко']})")
        if report["none_found"]:
            print("отчёт говорит: находок нет")
        if report["problems"]:
            print("\nОТЧЁТ НЕ ГОДИТСЯ:")
            for problem in report["problems"]:
                print(f"  - {problem}")
            return 1
        print("форма отчёта в порядке")
    return 0 if not report["problems"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
