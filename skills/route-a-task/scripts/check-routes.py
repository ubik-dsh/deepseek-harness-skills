"""Сверка: каждый ли скилл семьи умеет маршрутизироваться.

Зачем. Таблица `ROUTES` в `route.py` правится руками. Добавили скилл и забыли вписать —
карта врёт: агент идёт на дело, спрашивает маршрут, а скилла там нет, и работа делается
руками. Это не догадка: ровно так и вышло — четыре скилла, сделанных за один вечер, в
маршрутах отсутствовали.

Проверяется не «упомянут ли скилл вообще», а **есть ли маршрут, который на него ведёт**:
имя скилла в поле `tool` хотя бы одного маршрута.

Скиллы, которые зовутся только по имени и в маршрутах им не место, перечислены явно —
с причиной. Список исключений виден и проверяется: он в файле `route-exceptions.json`.

    python check-routes.py [--json]
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

if sys.stdout is not None:
    sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")

HERE = Path(__file__).resolve().parent
SKILL_DIR = HERE.parent
FAMILY = SKILL_DIR.parent
EXCEPTIONS = FAMILY / "route-a-task" / "route-exceptions.json"
ROUTE_PY = HERE / "route.py"


def load_routes() -> list[dict]:
    spec = importlib.util.spec_from_file_location("route_table", ROUTE_PY)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return list(module.ROUTES)


def family_skills() -> list[str]:
    return sorted(path.parent.name for path in FAMILY.glob("*/SKILL.md"))


def missing(skills: list[str], routes: list[dict], exceptions: dict[str, str]) -> list[str]:
    routed = {route.get("tool") for route in routes}
    return [name for name in skills if name not in routed and name not in exceptions]


def main() -> int:
    parser = argparse.ArgumentParser(description="Сверка маршрутов со списком скиллов")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    routes = load_routes()
    skills = family_skills()
    exceptions = {}
    if EXCEPTIONS.is_file():
        exceptions = {k: v for k, v in json.loads(EXCEPTIONS.read_text(encoding="utf-8")).items()
                      if not k.startswith("_")}
    gaps = missing(skills, routes, exceptions)

    result = {
        "skills": len(skills),
        "routes": len(routes),
        "routed": sorted({route.get("tool") for route in routes}),
        "exceptions": exceptions,
        "missing": gaps,
    }
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"скиллов в семье: {len(skills)}, маршрутов: {len(routes)}, "
              f"исключений: {len(exceptions)}")
        if gaps:
            print(f"\nБЕЗ МАРШРУТА ({len(gaps)}) — карта на них не укажет:")
            for name in gaps:
                print(f"  - {name}")
            print("\nЛибо добавьте маршрут в route.py, либо впишите скилл в "
                  "route-exceptions.json с причиной, почему он зовётся только по имени.")
            return 1
        print("у каждого скилла есть маршрут или объяснённое исключение")
    return 0 if not gaps else 1


if __name__ == "__main__":
    raise SystemExit(main())
