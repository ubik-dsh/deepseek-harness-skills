"""Проверка проверяльщика: отчёт с изъяном обязан падать, без изъяна — проходить.

    python test-check-review.py
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPT = HERE / "check-review.py"

GOOD = """# Рецензия изменения

## Что проверялось

- diff коммита 7d00db4 целиком
- прогон node tools/dev/test-style-switch.mjs

- [критично] packages/style-switch/lib/index.js:214 — секция не снимается при
  выключении; проверил прогоном теста, он это ловит.
- [важно] lamp-style.py:318 — mode_index определён после кнопки, которая его читает.
  Проверил прогоном: запуск падает с AttributeError, вывод в логе.
- [мелко] README.ru.md:12 — опечатка, на работу не влияет.
"""

NONE = """# Рецензия изменения

## Что проверялось

- все 18 файлов пакета
- прогон ворот deck_gates.py

Находок нет.
"""

NO_PLACE = """# Рецензия

## Что проверялось

- diff

- [важно] тут что-то не так с обработкой ошибок, проверено прогоном
"""

NO_EVIDENCE = """# Рецензия

## Что проверялось

- diff

- [важно] README.md:12 — стиль не тот
"""

EMPTY = """# Рецензия

Всё хорошо.
"""


def run(text: str) -> tuple[int, dict]:
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / "report.md"
        path.write_text(text, encoding="utf-8")
        result = subprocess.run([sys.executable, str(SCRIPT), str(path), "--json"],
                                capture_output=True, text=True, encoding="utf-8")
        if not result.stdout.strip():
            raise SystemExit(f"проверяльщик молчит: {result.stderr[:300]}")
        return result.returncode, json.loads(result.stdout)


def main() -> int:
    code, report = run(GOOD)
    assert code == 0, f"годный отчёт забракован: {report['problems']}"
    assert len(report["findings"]) == 3, f"находок насчитано {len(report['findings'])}, ждали 3"
    assert report["counts"] == {"критично": 1, "важно": 1, "мелко": 1}, report["counts"]
    assert report["findings"][0]["where"].endswith("index.js:214"), report["findings"][0]
    print("ok  1. годный отчёт проходит; находки разложены по уровням")

    code, report = run(NONE)
    assert code == 0, f"«находок нет» со списком проверенного забраковано: {report['problems']}"
    assert report["none_found"] and not report["findings"]
    print("ok  2. «находок нет» со списком проверенного — законный ответ")

    code, report = run(NO_PLACE)
    assert code == 1 and any("без места" in p for p in report["problems"]), report["problems"]
    print("ok  3. находка без места забракована")

    code, report = run(NO_EVIDENCE)
    assert code == 1 and any("проверяем" in p for p in report["problems"]), report["problems"]
    print("ok  4. находка без проверяемого утверждения забракована")

    code, report = run(EMPTY)
    assert code == 1 and len(report["problems"]) >= 2, report["problems"]
    print("ok  5. «всё хорошо» без списка и без находок забраковано дважды")

    print("\nPASS — проверяльщик отчётов проверен")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
