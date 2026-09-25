"""Шаблон из образца: измерить форму, упаковать в скилл и ПРОВЕРИТЬ новый текст по нему.

ЧТО ВЗЯТО И ОТКУДА. Идея — из плагина Template Creator Кодекса-десктопа
(`%USERPROFILE%\\.cache\\codex-runtimes\\...\\plugins\\template-creator`, лицензия
Proprietary): образец превращается в личный скилл, внутри которого лежит сам
образец, а потом новые тексты делаются «в той же форме». Их правила, которые
мы повторили: ровно один образец; образец сохраняется как есть и не вычищается;
шаблон существует только после успешного запуска упаковщика; правится только
личный скилл, чужие плагины не трогаются.

ЧЕМ НАШ ЛУЧШЕ. У них шаблон создаётся и на этом всё: проверить, что новый текст
действительно похож на образец, нечем. Здесь форма ИЗМЕРЯЕТСЯ в числа
(`form.json`), а `check` сравнивает с ней готовый текст и умеет сказать «не
похоже». Хвала без числа — не проверка.

ЧТО ИМЕННО ИЗМЕРЯЕТСЯ. Не «стиль» вообще, а то, что можно пересчитать:
порядок и вид заголовков, длину абзацев, где стоят таблицы, списки и код,
сколько в тексте жирных врезок, ссылок, цитат. Это форма, а не содержание:
`check` не скажет, хорошо ли написано, — он скажет, та ли это форма.

    python templates.py make  --reference ФАЙЛ --name ИМЯ [--purpose "для чего"] [--root КАТАЛОГ]
    python templates.py check --template ИМЯ-ИЛИ-ПУТЬ --document ФАЙЛ
    python templates.py list  [--root КАТАЛОГ]
"""
from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
from datetime import date
from pathlib import Path

if sys.stdout is not None:
    sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")

HEADING = re.compile(r"^(#{1,6})\s+(.*)$")
BULLET = re.compile(r"^\s*[-*+]\s+")
NUMBERED = re.compile(r"^\s*\d+[.)]\s+")
TABLE_ROW = re.compile(r"^\s*\|")
QUOTE = re.compile(r"^\s*>")
LINK = re.compile(r"\[[^\]]+\]\([^)]+\)")
BOLD = re.compile(r"\*\*[^*]+\*\*")

DEFAULT_ROOT = Path.home() / ".dsh" / "skills"


def default_root() -> Path:
    """Личные скиллы харнесса. Шаблоны — личные, поэтому и лежат здесь, а не в семейном репозитории."""
    return DEFAULT_ROOT


def sections_of(text: str) -> list[dict]:
    """Разрезать текст по заголовкам. Всё до первого заголовка — вступление."""
    lines = text.splitlines()
    blocks: list[dict] = []
    current = {"level": 0, "title": "", "lines": []}
    in_fence = False
    for line in lines:
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
        match = None if in_fence else HEADING.match(line)
        if match:
            blocks.append(current)
            current = {"level": len(match.group(1)), "title": match.group(2).strip(), "lines": []}
        else:
            current["lines"].append(line)
    blocks.append(current)
    return [block for block in blocks if block["title"] or any(l.strip() for l in block["lines"])]


def measure_section(body: list[str]) -> dict:
    """Что видно в одном разделе, кроме самих слов."""
    real = [line for line in body if line.strip()]
    paragraphs = []
    buffer: list[str] = []
    in_fence = False
    for line in real:
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if not line.strip() or BULLET.match(line) or NUMBERED.match(line) or TABLE_ROW.match(line) or QUOTE.match(line):
            if buffer:
                paragraphs.append(" ".join(buffer))
                buffer = []
            continue
        buffer.append(line.strip())
    if buffer:
        paragraphs.append(" ".join(buffer))
    return {
        "lines": len(real),
        "paragraphs": len(paragraphs),
        "paragraph_chars_median": int(statistics.median([len(p) for p in paragraphs])) if paragraphs else 0,
        "starts_with_bold": bool(BOLD.match(real[0])) if real else False,
        "has_table": any(TABLE_ROW.match(line) for line in real),
        "has_bullets": any(BULLET.match(line) or NUMBERED.match(line) for line in real),
        "has_code": any(line.lstrip().startswith("```") for line in real),
        "has_quote": any(QUOTE.match(line) for line in real),
        "first_line": (real[0][:70] if real else ""),
    }


def measure(text: str) -> dict:
    """Полная форма документа: то, что потом можно сверить числом."""
    blocks = sections_of(text)
    body_all = text.splitlines()
    sections = []
    for block in blocks:
        entry = {"level": block["level"], "title": block["title"]}
        entry.update(measure_section(block["lines"]))
        sections.append(entry)
    real_lines = [line for line in body_all if line.strip()]
    return {
        "measured": date.today().isoformat(),
        "sections": sections,
        "section_count": len([s for s in sections if s["title"]]),
        "headings": [s["title"] for s in sections if s["title"]],
        "table_count": sum(1 for line in body_all if TABLE_ROW.match(line) and "---" not in line),
        "code_fences": len([line for line in body_all if line.lstrip().startswith("```")]) // 2,
        "bullet_lines": sum(1 for line in body_all if BULLET.match(line) or NUMBERED.match(line)),
        "bold_spans": len(BOLD.findall(text)),
        "links": len(LINK.findall(text)),
        "quote_lines": sum(1 for line in body_all if QUOTE.match(line)),
        "chars": len(text),
        "nonempty_lines": len(real_lines),
    }


def skill_md(name: str, purpose: str, reference_name: str, form: dict) -> str:
    """Скилл шаблона. Он говорит КАК писать, и не пересказывает образец словами."""
    headings = form["headings"]
    median = int(statistics.median([s["paragraph_chars_median"] for s in form["sections"]
                                    if s["paragraph_chars_median"]] or [0]))
    lines = [
        "---",
        f"name: {name}",
        f"description: Писать тексты в форме образца «{reference_name}» — {purpose}. "
        f"Использовать, когда просят новый текст такого же вида: {', '.join(headings[:4])}"
        + (" и другие разделы." if len(headings) > 4 else "."),
        "---",
        "",
        f"# Шаблон: {name}",
        "",
        f"**Для чего:** {purpose}",
        "",
        f"**Образец лежит здесь же:** `reference/{reference_name}` — читать перед работой, "
        "он сохранён как есть и не переписывается.",
        "",
        "## Форма, измеренная у образца",
        "",
        f"- разделов: **{form['section_count']}**",
        f"- абзац обычно **{median}** символов",
        f"- таблиц: {form['table_count']}, блоков кода: {form['code_fences']}, "
        f"строк списков: {form['bullet_lines']}, жирных врезок: {form['bold_spans']}, "
        f"ссылок: {form['links']}, цитат: {form['quote_lines']}",
        "",
        "Порядок разделов у образца:",
        "",
    ]
    for index, heading in enumerate(headings, 1):
        lines.append(f"{index}. {heading}")
    lines += [
        "",
        "## Как писать по этому шаблону",
        "",
        "1. Прочитать образец в `reference/` целиком — не пересказ, а сам файл.",
        "2. Держать тот же порядок и тот же вид заголовков: это не украшение, а то, "
        "по чему читатель узнаёт документ.",
        "3. Держать ту же длину абзаца. Абзац вдвое длиннее образца — уже другая форма.",
        "4. Таблицы, списки и код ставить там, где они у образца, а не где удобно.",
        "5. **Проверить результат, а не поверить себе:**",
        "",
        "```bash",
        f"python {Path(__file__).name if '__file__' in globals() else 'templates.py'} "
        f"check --template {name} --document <готовый файл>",
        "```",
        "",
        "`check` печатает расхождения по числам. **«Похоже» без чисел — это догадка.**",
        "",
    ]
    return "\n".join(lines)


def preview_html(form: dict, reference_name: str) -> str:
    """Превью формы. У них для текстового образца делается PNG — по нему формы не видно."""
    rows = []
    for section in form["sections"]:
        if not section["title"]:
            continue
        marks = []
        if section["has_table"]:
            marks.append("таблица")
        if section["has_bullets"]:
            marks.append("список")
        if section["has_code"]:
            marks.append("код")
        if section["has_quote"]:
            marks.append("цитата")
        if section["starts_with_bold"]:
            marks.append("начинается с жирного")
        rows.append(
            f"<tr><td>{'&nbsp;' * (section['level'] - 1) * 3}{section['title']}</td>"
            f"<td>{section['lines']}</td><td>{section['paragraph_chars_median']}</td>"
            f"<td>{', '.join(marks) or '—'}</td></tr>"
        )
    return f"""<!doctype html>
<html lang="ru"><head><meta charset="utf-8">
<title>Форма образца {reference_name}</title>
<style>
 body{{font:14px/1.5 system-ui,sans-serif;margin:2rem;background:light-dark(#fff,#181818);color:light-dark(#111,#eee)}}
 table{{border-collapse:collapse;width:100%}} th,td{{border-bottom:1px solid #8884;padding:6px 10px;text-align:left}}
 th{{font-weight:600}} h1{{font-size:1.3rem}}
</style></head><body>
<h1>Форма образца «{reference_name}»</h1>
<p>Разделов: {form['section_count']} · таблиц: {form['table_count']} · блоков кода: {form['code_fences']} ·
жирных врезок: {form['bold_spans']} · ссылок: {form['links']}</p>
<table><thead><tr><th>раздел</th><th>строк</th><th>символов в абзаце</th><th>что внутри</th></tr></thead>
<tbody>{''.join(rows)}</tbody></table>
</body></html>
"""


def cmd_make(args) -> int:
    reference = Path(args.reference).resolve()
    if not reference.is_file():
        print(f"образца нет: {reference}")
        return 1
    text = reference.read_text(encoding="utf-8", errors="replace")
    form = measure(text)
    if form["section_count"] < 2:
        print(f"в образце {form['section_count']} раздел(ов) — формы не видно, нужно хотя бы два")
        return 1

    root = Path(args.root).resolve() if args.root else default_root()
    target = root / args.name
    if target.exists() and not args.force:
        print(f"шаблон уже есть: {target} — возьмите другое имя или --force")
        return 1
    (target / "reference").mkdir(parents=True, exist_ok=True)
    (target / "reference" / reference.name).write_bytes(reference.read_bytes())
    (target / "form.json").write_text(json.dumps(form, ensure_ascii=False, indent=2), encoding="utf-8")
    (target / "SKILL.md").write_text(
        skill_md(args.name, args.purpose or f"тексты вида «{reference.stem}»", reference.name, form),
        encoding="utf-8")
    (target / "preview.html").write_text(preview_html(form, reference.name), encoding="utf-8")

    index = root / "templates.json"
    entries = []
    if index.exists():
        try:
            entries = json.loads(index.read_text(encoding="utf-8"))
        except Exception:
            entries = []
    entries = [e for e in entries if e.get("name") != args.name]
    entries.append({
        "name": args.name,
        "purpose": args.purpose or f"тексты вида «{reference.stem}»",
        "reference": reference.name,
        "sections": form["section_count"],
        "created": date.today().isoformat(),
    })
    index.write_text(json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"шаблон собран: {target}")
    print(f"  разделов у образца: {form['section_count']}, абзац ~"
          f"{int(statistics.median([s['paragraph_chars_median'] for s in form['sections'] if s['paragraph_chars_median']] or [0]))} символов")
    print(f"  образец сохранён как есть: reference/{reference.name}")
    print(f"  превью формы: {target / 'preview.html'}")
    print(f"  список шаблонов: {index}")
    return 0


def find_template(name_or_path: str, root: Path) -> Path | None:
    candidate = Path(name_or_path)
    if candidate.is_dir() and (candidate / "form.json").is_file():
        return candidate
    direct = root / name_or_path
    return direct if (direct / "form.json").is_file() else None


def cmd_check(args) -> int:
    root = Path(args.root).resolve() if args.root else default_root()
    template = find_template(args.template, root)
    if template is None:
        print(f"шаблона «{args.template}» нет в {root}")
        return 1
    document = Path(args.document).resolve()
    if not document.is_file():
        print(f"документа нет: {document}")
        return 1

    form = json.loads((template / "form.json").read_text(encoding="utf-8"))
    now = measure(document.read_text(encoding="utf-8", errors="replace"))

    problems: list[str] = []
    notes: list[str] = []

    # ЗАГОЛОВОК ДОКУМЕНТА — НЕ ФОРМА, А СОДЕРЖАНИЕ. Первый заход сравнивал его
    # слова наравне с разделами, и текст с другим названием объявлялся «не по форме».
    # Форму держат разделы (уровень 2 и ниже); от заголовка требуется только то,
    # что он есть и что он первого уровня.
    want_title = next((s["title"] for s in form["sections"] if s["level"] == 1 and s["title"]), None)
    got_title = next((s["title"] for s in now["sections"] if s["level"] == 1 and s["title"]), None)
    if want_title is not None and got_title is None:
        problems.append(f"нет заголовка документа первого уровня (у образца он был: «{want_title}»)")
    elif want_title is not None:
        notes.append(f"заголовок свой: «{got_title}» вместо «{want_title}» — это содержание, не форма")

    want = [s["title"] for s in form["sections"] if s["level"] >= 2 and s["title"]]
    got = [s["title"] for s in now["sections"] if s["level"] >= 2 and s["title"]]
    for index, heading in enumerate(want):
        if index >= len(got):
            problems.append(f"нет раздела «{heading}» (он {index + 1}-й у образца)")
        elif got[index] != heading:
            problems.append(f"на месте {index + 1} ожидался «{heading}», а стоит «{got[index]}»")
    for extra in got[len(want):]:
        notes.append(f"лишний раздел в конце: «{extra}»")

    def near(label, a, b, tolerance=0.5):
        if b == 0 and a == 0:
            return
        base = max(a, b, 1)
        delta = abs(a - b) / base
        if delta > tolerance:
            problems.append(f"{label}: у образца {a}, здесь {b} (расхождение {delta:.0%})")

    near("таблиц", form["table_count"], now["table_count"])
    near("блоков кода", form["code_fences"], now["code_fences"])
    near("жирных врезок", form["bold_spans"], now["bold_spans"], 0.8)
    near("ссылок", form["links"], now["links"], 0.8)

    want_median = int(statistics.median([s["paragraph_chars_median"] for s in form["sections"]
                                         if s["paragraph_chars_median"]] or [0]))
    got_median = int(statistics.median([s["paragraph_chars_median"] for s in now["sections"]
                                        if s["paragraph_chars_median"]] or [0]))
    near("длина абзаца", want_median, got_median, 0.6)

    print(f"шаблон: {template.name} · документ: {document.name}")
    print(f"разделов: у образца {form['section_count']}, здесь {now['section_count']}")
    print(f"абзац: у образца ~{want_median}, здесь ~{got_median} символов")
    print(f"таблицы {form['table_count']}/{now['table_count']} · код {form['code_fences']}/{now['code_fences']} "
          f"· жирное {form['bold_spans']}/{now['bold_spans']} · ссылки {form['links']}/{now['links']}")
    for note in notes:
        print(f"  замечание: {note}")
    if problems:
        print("\nНЕ ПО ФОРМЕ:")
        for problem in problems:
            print(f"  - {problem}")
        print("\n(это проверка ФОРМЫ, а не содержания: она не скажет, хорошо ли написано)")
        return 1
    print("\nПО ФОРМЕ: расхождений по числам нет.")
    print("(проверка формы, а не содержания: смысл ею не проверяется)")
    return 0


def cmd_list(args) -> int:
    root = Path(args.root).resolve() if args.root else default_root()
    index = root / "templates.json"
    if not index.exists():
        print(f"шаблонов нет ({index})")
        return 1
    for entry in json.loads(index.read_text(encoding="utf-8")):
        print(f"{entry['name']:<28} {entry.get('sections', '?'):>2} разделов  "
              f"{entry.get('created', '')}  {entry.get('purpose', '')}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Шаблоны из образца: собрать и проверить")
    sub = parser.add_subparsers(dest="command", required=True)

    make = sub.add_parser("make")
    make.add_argument("--reference", required=True)
    make.add_argument("--name", required=True)
    make.add_argument("--purpose", default=None)
    make.add_argument("--root", default=None)
    make.add_argument("--force", action="store_true")
    make.set_defaults(handler=cmd_make)

    check = sub.add_parser("check")
    check.add_argument("--template", required=True)
    check.add_argument("--document", required=True)
    check.add_argument("--root", default=None)
    check.set_defaults(handler=cmd_check)

    listing = sub.add_parser("list")
    listing.add_argument("--root", default=None)
    listing.set_defaults(handler=cmd_list)

    args = parser.parse_args()
    return args.handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
