"""Проверка шаблонного инструмента: он должен уметь ПРОВАЛИТЬ неподходящий текст.

Смысл теста не в том, что «собралось», а в том, что проверка различает:
текст по форме проходит, текст с пропавшим разделом — нет, текст с вдвое
длинными абзацами — нет. Инструмент, который всегда говорит «по форме»,
бесполезен.

    python test-templates.py
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPT = HERE / "templates.py"

REFERENCE = """# Разбор: пример

**Короткая врезка в начале.**

## Что стоит на машине

Первый абзац образца. Он короткий и объясняет ровно одну мысль.

- пункт первый
- пункт второй

## Как проверить

Второй раздел. Тоже короткий абзац, чтобы форма была видна.

```bash
echo проверка
```

## Чего не вышло

Третий раздел с честной оговоркой.
"""

# тот же порядок заголовков и тот же вид тела — форма та же, слова другие
GOOD = """# Разбор: другой предмет

**Другая короткая врезка.**

## Что стоит на машине

Здесь другие слова, но такая же короткая мысль в абзаце.

- другой пункт
- и ещё один

## Как проверить

Другая проверка, такая же короткая.

```bash
echo другой
```

## Чего не вышло

Другая честная оговорка.
"""

BAD_HEADING = GOOD.replace("## Чего не вышло", "## Итоги")

BAD_LENGTH = """# Разбор: длинные абзацы

**Врезка.**

## Что стоит на машине

""" + ("Это очень длинный абзац, который повторяется, чтобы медиана длины вылезла за допуск. " * 8) + """

## Как проверить

""" + ("И здесь то же самое, длинно и нудно, потому что форма абзаца не та. " * 8) + """

## Чего не вышло

""" + ("Заключение тоже растянуто сверх всякой меры и потому не по форме. " * 8)


def run(*args: str, cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(SCRIPT), *args], cwd=cwd,
                          capture_output=True, text=True, encoding="utf-8")


def main() -> int:
    work = Path(tempfile.mkdtemp(prefix="templates-test-"))
    try:
        reference = work / "reference.md"
        reference.write_text(REFERENCE, encoding="utf-8")
        root = work / "skills"

        made = run("make", "--reference", str(reference), "--name", "proba",
                   "--purpose", "проба", "--root", str(root), cwd=work)
        assert made.returncode == 0, made.stderr
        assert (root / "proba" / "form.json").is_file(), "форма не сохранена"
        assert (root / "proba" / "reference" / "reference.md").is_file(), "образец не сохранён"
        assert (root / "templates.json").is_file(), "список шаблонов не заведён"
        form = json.loads((root / "proba" / "form.json").read_text(encoding="utf-8"))
        # заголовок документа считается первым разделом: он тоже часть формы
        assert form["section_count"] == 4, f"разделов насчитано {form['section_count']}, ждали 4"
        print("ok  1. шаблон собран: форма, образец, превью, список")

        same = work / "same.md"
        same.write_text(REFERENCE, encoding="utf-8")
        result = run("check", "--template", "proba", "--document", str(same), "--root", str(root), cwd=work)
        assert result.returncode == 0, f"сам образец не прошёл проверку:\n{result.stdout}"
        print("ok  2. образец проходит проверку по самому себе")

        good = work / "good.md"
        good.write_text(GOOD, encoding="utf-8")
        result = run("check", "--template", "proba", "--document", str(good), "--root", str(root), cwd=work)
        assert result.returncode == 0, f"текст по форме не прошёл:\n{result.stdout}"
        print("ok  3. другой текст в той же форме проходит")

        bad = work / "bad-heading.md"
        bad.write_text(BAD_HEADING, encoding="utf-8")
        result = run("check", "--template", "proba", "--document", str(bad), "--root", str(root), cwd=work)
        assert result.returncode == 1, "пропавший раздел не был замечен"
        assert "Чего не вышло" in result.stdout, "в отчёте нет имени пропавшего раздела"
        print("ok  4. подменённый раздел — проверка провалена")

        longer = work / "bad-length.md"
        longer.write_text(BAD_LENGTH, encoding="utf-8")
        result = run("check", "--template", "proba", "--document", str(longer), "--root", str(root), cwd=work)
        assert result.returncode == 1, "вдвое длинные абзацы не были замечены"
        assert "длина абзаца" in result.stdout, "в отчёте нет строки про длину абзаца"
        print("ok  5. абзацы вдвое длиннее — проверка провалена")

        missing = run("check", "--template", "нет-такого", "--document", str(good),
                      "--root", str(root), cwd=work)
        assert missing.returncode == 1 and "нет в" in missing.stdout
        print("ok  6. несуществующий шаблон — отказ, а не пустой успех")

        print("\nPASS — шаблонный инструмент проверен")
        return 0
    finally:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
