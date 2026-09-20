#!/usr/bin/env python3
"""What fix-layout.py must and must not touch.

The two messages in here are the operator's own, typed with the layout left in Latin - they are the
reason the script exists, so they are the first regression cases rather than invented ones.

    python test-fix-layout.py
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")

spec = importlib.util.spec_from_file_location("fl", Path(__file__).parent / "fix-layout.py")
fl = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fl)

passed = failed = 0


def check(label: str, got, want) -> None:
    global passed, failed
    if got == want:
        passed += 1
        print(f"  ok    {label}")
    else:
        failed += 1
        print(f"  FAIL  {label}\n          got  {got!r}\n          want {want!r}")


# ── the mapping is a permutation of the keys, so it is exact and reversible ──────────────────────
check("latin to cyrillic, the row qwerty", fl.convert("qwerty", "ru"), "йцукен")
check("latin to cyrillic, the punctuation keys", fl.convert(";'[]", "ru"), "жэхъ")
check("cyrillic back to latin", fl.convert("йцукен", "en"), "qwerty")
check("a round trip changes nothing", fl.convert(fl.convert("привет мир", "en"), "ru"), "привет мир")
check("uppercase is preserved", fl.convert("Ghbdtn", "ru"), "Привет")
check("digits and spaces pass through", fl.convert("1 2 3", "ru"), "1 2 3")


# ── the operator's own messages, verbatim ───────────────────────────────────────────────────────
FIRST = "nfr 'nf inerf kjrfkmyfz & bkb jyf ,eltn jnrelfnj gjlrk.xfncz b nht,jdfnm ctnb &"
check("his first message converts",
      fl.convert(FIRST, "ru"),
      "так эта штука локальная & или она будет откудато подключатся и требовать сети &")
check("his second message converts",
      fl.convert("lj,fdm 'njn hfcibahjdobr r yfv d bycnhevtyns", "ru"),
      "добавь этот расшифровщик к нам в инструменты")


# ── and the four cases the DETECTOR must get right ──────────────────────────────────────────────
def decide(text: str) -> bool:
    """True when the script would change the text. Mirrors main()'s comparison."""
    russian = any(c in fl.RU_VOWELS for c in text)
    if russian:
        here, _ = fl.score(text, fl.RU_VOWELS, fl.RU_SINGLE, fl.RU_BIGRAMS)
        there, _ = fl.score(fl.convert(text, "en"), fl.EN_VOWELS, fl.EN_SINGLE, fl.EN_BIGRAMS)
    else:
        here, _ = fl.score(text, fl.EN_VOWELS, fl.EN_SINGLE, fl.EN_BIGRAMS)
        there, _ = fl.score(fl.convert(text, "ru"), fl.RU_VOWELS, fl.RU_SINGLE, fl.RU_BIGRAMS)
    return there > here


check("wrong layout, latin letters", decide(FIRST), True)
check("wrong layout, short", decide("ghbdtn"), True)
check("wrong layout, question mark", decide("rfr ltkf&"), True)

check("english is left alone", decide("The wall.post call returns a post_id."), False)
check("english prose is left alone",
      decide("Be sure that either a backup exists or you are working on a copy."), False)
check("russian is left alone",
      decide("Так эта штука локальная или она будет откуда-то подключаться?"), False)
check("russian prose is left alone",
      decide("Правило работает, если текст набран в неверной раскладке."), False)
check("a single english word is left alone", decide("attachment"), False)
check("a single russian word is left alone", decide("вложение"), False)

# A file path is the case that made the first version fail: it contains a dot inside a word.
check("a dotted identifier is not layout damage", decide("wall.post attachments=photo-241624898_456239017"), False)
check("a shell command is left alone",
      decide("python skills/manage-vk/scripts/preflight.py --env-file x.env"), False)

print(f"\n  {passed} passed, {failed} failed")
raise SystemExit(1 if failed else 0)
