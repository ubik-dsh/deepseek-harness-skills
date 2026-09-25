"""Проверка сравнения: одинаковые версии — ноль, изменённая страница — ловится.

    python test-render-and-diff.py
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

import pymupdf

HERE = Path(__file__).resolve().parent
SCRIPT = HERE / "render_and_diff.py"


def make_pdf(path: Path, *, moved: bool) -> None:
    """Две страницы: текст и прямоугольник. Во второй версии прямоугольник уехал."""
    document = pymupdf.open()
    for number in (1, 2):
        page = document.new_page(width=400, height=300)
        page.insert_text((40, 60), f"Страница {number}: заголовок", fontsize=16)
        page.insert_text((40, 100), "Обычный абзац, который никуда не сдвигался.", fontsize=11)
        top = 150 if not (moved and number == 2) else 200
        page.draw_rect(pymupdf.Rect(40, top, 200, top + 40), width=2)
    document.save(str(path))


def run(before: Path, after: Path, out: Path) -> tuple[int, str]:
    result = subprocess.run([sys.executable, str(SCRIPT), str(before), str(after), "--out", str(out)],
                            capture_output=True, text=True, encoding="utf-8")
    if not result.stdout.strip():
        raise SystemExit(f"инструмент молчит: {result.stderr[:400]}")
    return result.returncode, result.stdout


def main() -> int:
    work = Path(tempfile.mkdtemp(prefix="render-diff-"))
    first = work / "до.pdf"
    same = work / "то-же.pdf"
    moved = work / "после.pdf"
    make_pdf(first, moved=False)
    make_pdf(same, moved=False)
    make_pdf(moved, moved=True)

    code, text = run(first, same, work / "out-то-же")
    assert code == 0, f"одинаковые версии объявлены разными:\n{text}"
    assert "0.000%" in text or "0.00" in text, f"на одинаковых версиях не ноль:\n{text}"
    print("ok  1. две одинаковые версии — ноль изменений, код 0")

    code, text = run(first, moved, work / "out-после")
    assert code == 1, f"сдвинутая страница не поймана:\n{text}"
    assert "изменилась" in text, f"нет вердикта «изменилась»:\n{text}"
    assert "стр. 2" in text, f"не сказано, какая страница поехала:\n{text}"
    print("ok  2. сдвиг на второй странице пойман, код 1")

    lines = [line for line in text.splitlines() if line.strip().startswith("стр.")]
    assert len(lines) == 2, f"строк по страницам {len(lines)}, ждали 2"
    first_page = float(lines[0].split()[2].rstrip("%"))
    second_page = float(lines[1].split()[2].rstrip("%"))
    assert first_page < 0.5, f"первая страница не менялась, а показала {first_page}%"
    assert second_page > 1.0, f"вторая страница поехала, а показала всего {second_page}%"
    print(f"ok  3. числа разделяют страницы: первая {first_page:.3f}%, вторая {second_page:.3f}%")

    differences = sorted((work / "out-после").glob("стр-*.png"))
    assert len(differences) == 2, f"картинок различий {len(differences)}, ждали 2"
    assert differences[0].stat().st_size > 500, "картинка различий пустая"
    print("ok  4. картинки различий на месте и не пустые")

    print("\nPASS — сравнение версий проверено")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
