"""Сравнить две отрендеренные версии одного документа — постранично.

ЗАЧЕМ. Ворота считают числа (кегль, итоги, расхождения формы), глаза говорят «вроде
нормально». Ни то, ни другое не отвечает на вопрос «правка не сломала вид». Для этого
нужна прежняя версия: сравнить страницу с страницей и увидеть, где поехало.

Идея из плагина documents Кодекса-десктопа (scripts/render_and_diff.py, лицензия
Proprietary); скрипт свой, на pymupdf.

    python render_and_diff.py старое.pdf новое.pdf --out различия
    python render_and_diff.py папка-до папка-после --out различия
    python render_and_diff.py старое.pptx новое.pptx --out различия     # отрендерит сам

Выход: строка на страницу с процентом изменившихся пикселей и вердикт. Код возврата 1,
если хоть одна страница изменилась больше порога. Рядом — картинки различий.
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

if sys.stdout is not None:
    sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")

import pymupdf  # noqa: E402

IMAGES = {".png": None, ".jpg": None, ".jpeg": None}
DOCUMENTS = {".pptx", ".docx", ".xlsx", ".ppt", ".doc", ".xls", ".odt", ".odp", ".ods"}
# Ниже этого порога разница — шум рендерера, а не правка.
DEFAULT_THRESHOLD = 0.5
SOFFICE = shutil.which("soffice") or r"C:\Program Files\LibreOffice\program\soffice.exe"


def render_document(path: Path, workdir: Path) -> Path:
    """Отдать документ LibreOffice и получить PDF. Без него сравнение невозможно."""
    if Path(SOFFICE).exists() is False and shutil.which("soffice") is None:
        raise SystemExit("LibreOffice не найден — конвертировать документ нечем")
    workdir.mkdir(parents=True, exist_ok=True)
    result = subprocess.run([SOFFICE, "--headless", "--convert-to", "pdf",
                             "--outdir", str(workdir), str(path)],
                            capture_output=True, text=True, timeout=600)
    pdf = workdir / (path.stem + ".pdf")
    if not pdf.exists():
        raise SystemExit(f"LibreOffice не сделал PDF из {path.name}: {result.stderr.strip()[:200]}")
    return pdf


def pages_of(path: Path, workdir: Path, scale: float) -> list:
    """Страницы как картинки в оттенках серого: цвет мешает видеть сдвиг, а не помогает."""
    if path.suffix.lower() in IMAGES:
        image = pymupdf.open(path) if path.suffix.lower() != ".png" else None
        if image is None:
            page = pymupdf.open()
            rect = pymupdf.Rect(0, 0, 1, 1)
            page.new_page(width=rect.width, height=rect.height)
            page[0].insert_image(rect, filename=str(path))
            return [page[0].get_pixmap(matrix=pymupdf.Matrix(scale, scale), colorspace=pymupdf.csGRAY)]
        return []
    if path.suffix.lower() in DOCUMENTS:
        path = render_document(path, workdir / (path.stem + "-render"))
    document = pymupdf.open(path)
    shots = []
    for page in document:
        pixmap = page.get_pixmap(matrix=pymupdf.Matrix(scale, scale), colorspace=pymupdf.csGRAY)
        shots.append(pixmap)
    return shots


def image_pages(folder: Path, scale: float) -> list:
    files = sorted(p for p in folder.iterdir() if p.suffix.lower() in IMAGES)
    shots = []
    for file in files:
        document = pymupdf.open()
        rect = pymupdf.Rect(0, 0, *pymupdf.Pixmap(str(file)).irect[2:])
        page = document.new_page(width=rect.width, height=rect.height)
        page.insert_image(rect, filename=str(file))
        shots.append(page.get_pixmap(matrix=pymupdf.Matrix(scale, scale), colorspace=pymupdf.csGRAY))
    return shots


def compare(before, after, out_dir: Path, page_number: int, threshold: int = 12) -> tuple[float, Path]:
    """Доля изменившихся пикселей и картинка различий.

    Пиксель считается изменившимся, если он отличается больше чем на `threshold`
    градаций серого: иначе сглаживание шрифта даёт «изменения» на пустом месте.
    """
    import numpy as np

    a = np.frombuffer(before.samples, dtype=np.uint8).reshape(before.height, before.width)
    b = np.frombuffer(after.samples, dtype=np.uint8).reshape(after.height, after.width)
    height = min(a.shape[0], b.shape[0])
    width = min(a.shape[1], b.shape[1])
    a = a[:height, :width].astype(int)
    b = b[:height, :width].astype(int)

    changed = np.abs(a - b) > threshold
    share = float(changed.mean())

    mask = np.stack([np.where(changed, 255, a // 3)] * 3, axis=-1).astype("uint8")
    mask[changed] = (220, 40, 40)
    image = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, width, height), False)
    image.set_rect(image.irect, (255, 255, 255))
    target = out_dir / f"стр-{page_number:03d}.png"
    _save_rgb(mask, target)
    return share, target


def _save_rgb(array, target: Path) -> None:
    from PIL import Image

    Image.fromarray(array).save(target)


def main() -> int:
    parser = argparse.ArgumentParser(description="Постраничное сравнение двух версий")
    parser.add_argument("before")
    parser.add_argument("after")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD,
                        help="порог в процентах, выше которого страница считается изменённой")
    parser.add_argument("--scale", type=float, default=1.5)
    args = parser.parse_args()

    before_path, after_path = Path(args.before), Path(args.after)
    for path in (before_path, after_path):
        if not path.exists():
            print(f"нет пути: {path}")
            return 1
    args.out.mkdir(parents=True, exist_ok=True)

    work = args.out / "рендер"
    if before_path.is_dir():
        first = image_pages(before_path, args.scale)
    else:
        first = pages_of(before_path, work, args.scale)
    if after_path.is_dir():
        second = image_pages(after_path, args.scale)
    else:
        second = pages_of(after_path, work, args.scale)

    if len(first) != len(second):
        print(f"страниц разное число: было {len(first)}, стало {len(second)} — "
              f"это уже изменение, сравнивать нечего")

    total = max(len(first), len(second))
    worst = 0.0
    over = 0
    print(f"страниц: {total}, порог {args.threshold:g}%")
    for index in range(total):
        if index >= len(first) or index >= len(second):
            print(f"  стр. {index + 1:<3} ЕСТЬ ТОЛЬКО В ОДНОЙ ВЕРСИИ")
            over += 1
            worst = 100.0
            continue
        share, target = compare(first[index], second[index], args.out, index + 1)
        percent = share * 100
        worst = max(worst, percent)
        verdict = "изменилась" if percent > args.threshold else "та же"
        if percent > args.threshold:
            over += 1
        print(f"  стр. {index + 1:<3} {percent:6.3f}%  {verdict:<12} {target.name}")
    if len(first) != len(second):
        print("\nразное число страниц — состав документа изменился")

    print(f"\nбольше порога: {over} страниц(ы), худшая {worst:.3f}%")
    print("изменение — не порча: инструмент показывает ГДЕ, а решает человек")
    return 1 if over else 0


if __name__ == "__main__":
    raise SystemExit(main())
