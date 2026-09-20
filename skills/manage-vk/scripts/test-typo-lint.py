#!/usr/bin/env python3
"""The typography trial, kept as a regression suite.

This is the trial from _vk_trial/typo_trial.py, made permanent and pointed at the shipped
linter instead of a scratch copy. It exists because the rule it guards was measured wrong
twice before it was measured right, and because a linter that corrupts a document while
reporting success is worse than a linter that says nothing.

Two directions, and the second is the one that matters:

  * a text with one fault per mechanical rule, which the linter must repair;
  * a control text full of things that merely look like faults - a standard number, a
    telephone number, a version, a negative temperature, code, a URL, a placeholder, a
    markdown list - which the linter must leave **byte for byte** alone.

    python test-typo-lint.py
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("typo_under_test", HERE / "typo_lint.py")
typo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(typo)

PASSED: list[str] = []
FAILED: list[str] = []


def expect(label: str, condition: bool, detail: str = "") -> None:
    if condition:
        PASSED.append(label)
        print(f"  ok    {label}")
    else:
        FAILED.append(label)
        print(f"  FAIL  {label}")
        if detail:
            print(f"        {detail}")


FAULTY = """\
Он сказал "это работает" и ушёл.
Слово - слово, и ещё раз слово - слово.
Ждать 5-7 дней, потом ещё 10-12 часов.
Это было давно...
Слово , слово и снова слово , слово.
Слово,слово и ещё раз слово,слово.
Слово  слово с двойным пробелом.
Кто — то пришёл, и что — нибудь случилось.
"""

# Everything here is correct, and every line is a trap for a rule written too broadly.
CONTROL = """\
Кто-то пришёл по-русски, что-нибудь из-за угла.
ГОСТ 7.32-2017 и телефон 8-800-555-35-35.
Версия 1-2-3 сборки и температура -5 градусов.
Запустите `tool --flag --other` и `x - y` в формуле.
- пункт списка
- второй пункт
Код: `print("текст", 5-7)` — и вот правильное тире.
Ссылка https://example.com/a-b-c и {{placeholder-name}} здесь.
Время 12:30 и 50,5 процента, и это верно.
Правильные 5–7 дней, «ёлочки», „лапки“ и многоточие…
"""

TRAPS = [
    ("кто-то", "Кто-то"), ("по-русски", "по-русски"), ("что-нибудь", "что-нибудь"),
    ("из-за", "из-за"), ("ГОСТ 7.32-2017", "ГОСТ 7.32-2017"),
    ("8-800-555-35-35", "8-800-555-35-35"), ("версия 1-2-3", "1-2-3"),
    ("минус пять", "-5 градусов"), ("флаги в коде", "`tool --flag --other`"),
    ("формула в коде", "`x - y`"), ("пункт списка", "- пункт списка"),
    ("код с кавычками", '`print("текст", 5-7)`'),
    ("url", "https://example.com/a-b-c"), ("плейсхолдер", "{{placeholder-name}}"),
    ("время", "12:30"), ("десятичная дробь", "50,5"),
    ("правильный диапазон", "5–7 дней"), ("ёлочки", "«ёлочки»"), ("лапки", "„лапки“"),
]

typo.NBNS_ENABLED[0] = False


def main() -> int:
    print("  === the mechanical rules repair a faulty text")
    repaired, count = typo.fix(FAULTY)
    for label, wanted in [
        ("straight quotes become ёлочки", "«это работает»"),
        ("a spaced hyphen becomes a dash", "Слово — слово"),
        ("a numeric range becomes an en dash", "5–7 дней"),
        ("so does the second one", "10–12 часов"),
        ("an ellipsis becomes one character", "давно…"),
        ("no space before a comma", "Слово, слово"),
        ("a space after a comma", "слово, слово"),
        ("one space between words", "Слово слово"),
    ]:
        expect(label, wanted in repaired, f"not found: {wanted!r}")

    print()
    print("  === the ninth rule is reported and never fixed")
    questions = typo.find(repaired)
    names = {name for _, name, _ in questions}
    expect("the hyphen-or-dash question is raised",
           "hyphen used as a dash inside a word" in names, f"raised: {sorted(names)}")
    expect("and it was left exactly as it was",
           "Кто — то пришёл" in repaired,
           "the linter must not decide a question about meaning")

    print()
    print("  === the control text is untouched")
    guarded, changes = typo.fix(CONTROL)
    if guarded == CONTROL:
        print("  ok    byte for byte identical after every rule ran")
        PASSED.append("control untouched")
    else:
        FAILED.append("control untouched")
        print("  FAIL  the control text was changed")
        for before, after in zip(CONTROL.splitlines(), guarded.splitlines()):
            if before != after:
                print(f"        was  {before}")
                print(f"        now  {after}")
    for label, wanted in TRAPS:
        expect(f"the {label} survived", wanted in guarded, f"lost: {wanted!r}")

    print()
    print("  === --nbsp binds units and short words, and does not crash")
    #
    # This branch had never been run. It unpacked re.sub's return value into two names, which
    # raises, and the first real draft post found it. A switch nobody has executed is a switch
    # that does not work.
    typo.NBNS_ENABLED[0] = True
    try:
        # The input has to contain what each assertion looks for. The first version asserted on
        # "20 сентября" against a string with no date in it, and failed for that reason alone -
        # a test that does not contain its own subject.
        bound, bound_count = typo.fix("В Москве 18 °C, 57 % влажности, 20 сентября и 10 с.\n")
        expect("--nbsp runs at all", True, "")
        expect("a number is bound to its unit",
               "18\u00a0°C" in bound, f"got {bound!r}")
        expect("and to a percent", "57\u00a0%" in bound, f"got {bound!r}")
        expect("a short preposition is bound to its word",
               "В\u00a0Москве" in bound, f"got {bound!r}")
        expect("something was counted", bound_count > 0, f"count {bound_count}")
        # The unit list contains `с` for seconds, and without a trailing boundary it caught the
        # first letter of "сентября". A real draft produced "20\u00a0сентября".
        expect("a date is NOT mistaken for seconds",
               "20\u00a0сентября" not in bound and "20 сентября" in bound,
               f"got {bound!r}")
        expect("but a real unit still binds",
               "10\u00a0с." in bound, f"got {bound!r}")
    except Exception as trouble:                            # noqa: BLE001
        expect("--nbsp runs at all", False, f"{type(trouble).__name__}: {trouble}")
    finally:
        typo.NBNS_ENABLED[0] = False

    print()
    print(f"  {len(PASSED)} passed, {len(FAILED)} failed")
    for label in FAILED:
        print(f"    failed: {label}")
    return 1 if FAILED else 0


if __name__ == "__main__":
    raise SystemExit(main())
