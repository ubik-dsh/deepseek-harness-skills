"""Управление чужим окном Windows: список, дерево доступности, снимок, нажатия.

ЧТО ЗДЕСЬ ВЗЯТО И ОТКУДА. Три приёма подсмотрены у плагина Computer Use из
Кодекса-десктопа (пакет `computer-use`, файл `docs/api.md`, лицензия Proprietary,
рядом с приложением в `%USERPROFILE%\\.codex\\.tmp\\bundled-marketplaces\\openai-bundled`):

1. КАЖДОЕ ДЕЙСТВИЕ ПРИВЯЗАНО К ОКНУ, и оно само поднимает свою цель. У них
   `click({window, x, y})`, и «input methods activate their target window
   automatically». У нас раньше был `SetForegroundWindow` снаружи, и ввод
   уходил в чужое окно — в браузере он попадал в адресную строку.
2. `set_value(element_index, value)` — ЗАМЕНА ЗНАЧЕНИЯ через доступность, а не
   набор текста. Это то, что не получилось у нас в диалоге Кодекса: щелчок
   уходил, `SendInput` доходил, а текст не появлялся.
3. СНИМОК ОКНА, А НЕ ЭКРАНА. У них `Windows.Graphics.Capture` и скриншот
   «works even when windows are occluded». У нас был снимок прямоугольника
   экрана, поэтому перекрытое окно в кадр не попадало.

Наш инструмент — не их пакет: их движок запускается только внутри их рантайма
(`failed to launch codex app-server: program not found`), а лицензия закрытая.
Здесь то же самое сделано на `uiautomation` и нашем Python.

ЧЕСТНО О ГРАНИЦАХ. У окон Chromium и Electron (Кодекс, наш чат в браузере)
дерево доступности ПУСТОЕ, пока приложение не увидит клиента UIA: обход находит
десяток панелей и один документ без детей. Инструмент это показывает сам, а не
делает вид, что дерево есть. Для таких окон остаются координаты и снимок —
и снимок здесь работает, даже если окно перекрыто.

    python computer.py windows [--title ЧАСТЬ] [--json]
    python computer.py tree    --title ЧАСТЬ [--depth 12] [--limit 40]
    python computer.py shot    --title ЧАСТЬ --out файл.png
    python computer.py click   --title ЧАСТЬ (--name ИМЯ | --x N --y N)
    python computer.py setval  --title ЧАСТЬ --name ИМЯ --value ТЕКСТ
    python computer.py typetext --title ЧАСТЬ --text ТЕКСТ
    python computer.py key     --title ЧАСТЬ --keys "Control_L+a"
    python computer.py probe   --title ЧАСТЬ
"""
from __future__ import annotations

import argparse
import json
import sys
import time

if sys.stdout is not None:
    sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")

import uiautomation as auto  # noqa: E402

auto.SetGlobalSearchTimeout(4)

# Признак «дерево отдаётся» — не число узлов. У маленькой формы WinForms их всего
# десять, и это живое дерево; у Chromium их девятнадцать, и это пустышка из
# контейнеров. Поэтому смотрим, есть ли в дереве элемент, с которым можно
# работать: поле, кнопка, список, флажок.
CONTAINER_TYPES = {
    "PaneControl", "GroupControl", "DocumentControl", "WindowControl",
    "StatusBarControl", "TitleBarControl", "ToolBarControl", "CustomControl",
}


def tree_is_alive(nodes: list[dict]) -> bool:
    return any(node["type"] not in CONTAINER_TYPES and node["name"] for node in nodes)


def find_window(title_fragment: str, pid: int | None = None):
    """Окно по части заголовка или по pid. Возвращает None, если не нашлось."""
    for window in auto.GetRootControl().GetChildren():
        try:
            if pid is not None and window.ProcessId != pid:
                continue
            if pid is None and title_fragment.lower() not in (window.Name or "").lower():
                continue
            if not window.Name:
                continue
            return window
        except Exception:
            continue
    return None


def rect_of(control) -> tuple[int, int, int, int]:
    box = control.BoundingRectangle
    return (box.left, box.top, box.right, box.bottom)


def walk(control, max_depth: int, budget: int = 4000):
    """Обход дерева. Возвращает (узлы, счётчик ошибок).

    Узел — словарь, а не объект: объект живёт до конца обхода, а нам нужен
    снимок дерева, по которому потом можно искать.
    """
    nodes: list[dict] = []
    errors: list[str] = []
    stack = [(control, 0)]
    while stack and len(nodes) < budget:
        node, depth = stack.pop()
        try:
            kind = node.ControlTypeName
            name = node.Name or ""
        except Exception as error:
            errors.append(f"{type(error).__name__}: {error}")
            continue
        value = None
        value_readonly = None
        try:
            pattern = node.GetValuePattern()
            value = pattern.Value or ""
            value_readonly = bool(pattern.IsReadOnly)
        except Exception:
            pass
        entry = {
            "depth": depth,
            "type": kind,
            "name": name,
            "value": value,
            "readonly": value_readonly,
            "rect": rect_of(node),
            "control": node,
        }
        nodes.append(entry)
        if depth >= max_depth:
            continue
        try:
            for child in node.GetChildren():
                stack.append((child, depth + 1))
        except Exception as error:
            errors.append(f"GetChildren {type(error).__name__}: {error}")
    return nodes, errors


def describe(nodes: list[dict], limit: int) -> str:
    lines = []
    for entry in nodes[:limit]:
        pad = "  " * min(entry["depth"], 8)
        line = f"{pad}{entry['type']:<20} «{entry['name'][:50]}»"
        if entry["value"]:
            line += f" = «{entry['value'][:34]}»"
            if entry["readonly"]:
                line += " [только чтение]"
        lines.append(line)
    return "\n".join(lines)


def activate(window) -> str:
    """Поднять окно. Возвращает строку о том, что вышло, — для отчёта."""
    try:
        window.SetActive()
    except Exception:
        pass
    try:
        window.SetFocus()
    except Exception:
        pass
    # Их правило: действие само поднимает цель. Здесь проверяем результат, а не вызов:
    # после подъёма окно должно быть тем, которое мы просили.
    time.sleep(0.25)
    actual = auto.GetForegroundControl()
    for _ in range(2):
        if actual.ProcessId == window.ProcessId:
            return "окно впереди"
        try:
            window.SetActive()
        except Exception:
            pass
        time.sleep(0.35)
        actual = auto.GetForegroundControl()
    return f"поднять не удалось: впереди pid={actual.ProcessId}"


def find_element(window, nodes: list[dict], name: str, kinds: tuple[str, ...] = ()):
    """Элемент по имени. Приоритет — тот, у которого есть значение: его и меняют."""
    candidates = [n for n in nodes if name.lower() in n["name"].lower()]
    if kinds:
        typed = [n for n in candidates if n["type"] in kinds]
        if typed:
            candidates = typed
    if not candidates:
        return None
    with_value = [n for n in candidates if n["value"] is not None and not n["readonly"]]
    return (with_value or candidates)[0]


def cmd_windows(args) -> int:
    rows = []
    for window in auto.GetRootControl().GetChildren():
        try:
            if not window.Name:
                continue
            left, top, right, bottom = rect_of(window)
            rows.append({
                "pid": window.ProcessId,
                "class": window.ClassName,
                "title": window.Name,
                "width": right - left,
                "height": bottom - top,
                "rect": [left, top, right, bottom],
            })
        except Exception:
            continue
    if args.title:
        rows = [r for r in rows if args.title.lower() in r["title"].lower()]
    if args.json:
        print(json.dumps(rows, ensure_ascii=False, indent=2))
        return 0
    if not rows:
        print("окон не нашлось")
        return 1
    for row in rows:
        print(f"pid={row['pid']:<7} {row['width']}x{row['height']:<6} "
              f"{row['class'][:26]:<28} «{row['title'][:60]}»")
    return 0


def cmd_tree(args) -> int:
    window = find_window(args.title, args.pid)
    if window is None:
        print(f"окно «{args.title}» не найдено")
        return 1
    nodes, errors = walk(window, args.depth)
    print(f"окно «{window.Name}» pid={window.ProcessId}: узлов {len(nodes)}")
    print(describe(nodes, args.limit))
    if not tree_is_alive(nodes):
        print("\nВНИМАНИЕ: в дереве нет ни одного элемента, с которым можно работать, — "
              "приложение не отдаёт доступность (так ведут себя Chromium и Electron). "
              "Ищите по координатам и снимку, а не по именам элементов.")
    if errors:
        print(f"ошибок обхода: {len(errors)}; первая: {errors[0][:90]}")
    return 0


def cmd_shot(args) -> int:
    window = find_window(args.title, args.pid)
    if window is None:
        print(f"окно «{args.title}» не найдено")
        return 1
    left, top, right, bottom = rect_of(window)
    try:
        window.CaptureToImage(args.out)
    except Exception as error:
        print(f"снимок не вышел: {type(error).__name__} {error}")
        return 1
    import os
    size = os.path.getsize(args.out)
    print(f"снимок окна «{window.Name}» -> {args.out} ({size} байт, "
          f"{right - left}x{bottom - top})")
    print("это снимок ОКНА, а не экрана: перекрытие другим окном ему не мешает")
    return 0


def cmd_click(args) -> int:
    window = find_window(args.title, args.pid)
    if window is None:
        print(f"окно «{args.title}» не найдено")
        return 1
    state = activate(window)
    if args.name:
        nodes, _ = walk(window, args.depth)
        element = find_element(window, nodes, args.name)
        if element is None:
            print(f"элемент «{args.name}» в дереве не найден; {state}")
            return 1
        element["control"].Click()
        print(f"нажал «{element['name'][:40]}» ({element['type']}), {state}")
        return 0
    if args.x is None or args.y is None:
        print("нужно либо --name, либо --x и --y")
        return 1
    left, top, _, _ = rect_of(window)
    window.Click(args.x + left, args.y + top)
    print(f"нажал в точке окна ({args.x},{args.y}), {state}")
    return 0


def cmd_setval(args) -> int:
    window = find_window(args.title, args.pid)
    if window is None:
        print(f"окно «{args.title}» не найдено")
        return 1
    nodes, _ = walk(window, args.depth)
    element = find_element(window, nodes, args.name)
    if element is None:
        print(f"элемент «{args.name}» не найден — дерево пустое или имя другое")
        return 1
    if element["value"] is None:
        print(f"у «{element['name'][:40]}» нет ValuePattern: замену значения "
              f"сделать нечем, придётся кликать и печатать")
        return 1
    if element["readonly"]:
        print(f"«{element['name'][:40]}» только для чтения")
        return 1
    activate(window)
    element["control"].GetValuePattern().SetValue(args.value)
    time.sleep(0.2)
    check = element["control"].GetValuePattern().Value or ""
    ok = args.value in check
    print(("значение заменено" if ok else "значение НЕ подтвердилось")
          + f": «{check[:40]}»")
    return 0 if ok else 1


def cmd_typetext(args) -> int:
    window = find_window(args.title, args.pid)
    if window is None:
        print(f"окно «{args.title}» не найдено")
        return 1
    state = activate(window)
    auto.SendKeys(args.text, waitTime=0.01)
    print(f"напечатал {len(args.text)} символов в окно «{window.Name}», {state}")
    return 0


def cmd_key(args) -> int:
    window = find_window(args.title, args.pid)
    if window is None:
        print(f"окно «{args.title}» не найдено")
        return 1
    state = activate(window)
    auto.SendKeys("{" + args.keys + "}", waitTime=0.02)
    print(f"нажал {args.keys} в окне «{window.Name}», {state}")
    return 0


def cmd_probe(args) -> int:
    """Проверка перед действием: есть ли окно, живое ли дерево, отвечает ли окно."""
    problems = []
    window = find_window(args.title, args.pid)
    if window is None:
        print(f"ПРОВАЛ: окна «{args.title}» нет")
        return 1
    print(f"окно: «{window.Name}» pid={window.ProcessId} class={window.ClassName}")
    if not window.IsEnabled:
        problems.append("окно не отвечает (IsEnabled = False)")
    nodes, errors = walk(window, 6, budget=600)
    print(f"узлов дерева: {len(nodes)}")
    if not tree_is_alive(nodes):
        problems.append("дерево доступности не отдаётся — только координаты и снимок")
    if errors:
        problems.append(f"ошибок обхода: {len(errors)}")
    if problems:
        print("замечания:")
        for problem in problems:
            print(f"  - {problem}")
    else:
        print("дерево живое, искать элементы по именам можно")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Управление окном Windows")
    sub = parser.add_subparsers(dest="command", required=True)

    def add(name, handler, needs_title=True):
        item = sub.add_parser(name)
        if needs_title:
            item.add_argument("--title", required=True, help="часть заголовка окна")
            item.add_argument("--pid", type=int, default=None)
        item.set_defaults(handler=handler)
        return item

    listing = sub.add_parser("windows")
    listing.add_argument("--title", default=None)
    listing.add_argument("--json", action="store_true")
    listing.set_defaults(handler=cmd_windows)

    tree = add("tree", cmd_tree)
    tree.add_argument("--depth", type=int, default=12)
    tree.add_argument("--limit", type=int, default=40)

    shot = add("shot", cmd_shot)
    shot.add_argument("--out", required=True)

    click = add("click", cmd_click)
    click.add_argument("--name", default=None)
    click.add_argument("--x", type=int, default=None)
    click.add_argument("--y", type=int, default=None)
    click.add_argument("--depth", type=int, default=12)

    setval = add("setval", cmd_setval)
    setval.add_argument("--name", required=True)
    setval.add_argument("--value", required=True)
    setval.add_argument("--depth", type=int, default=12)

    typetext = add("typetext", cmd_typetext)
    typetext.add_argument("--text", required=True)

    key = add("key", cmd_key)
    key.add_argument("--keys", required=True)

    probe = add("probe", cmd_probe)

    args = parser.parse_args()
    return args.handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
