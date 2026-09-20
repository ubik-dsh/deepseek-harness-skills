#!/usr/bin/env python3
"""Text typed in the wrong keyboard layout, detected and converted.

An operator on a Russian layout who forgets to switch produces Latin-looking text that is not any
language: `nfr 'nf inerf kjrfkmyfz` is «так эта штука локальная». A reader who knows the mapping
understands it at once; an agent that does not will treat it as a foreign phrase, guess, or ask. This
decodes it and says WHY it thinks the layout is wrong, so the reader can disagree.

    python fix-layout.py "nfr 'nf inerf kjrfkmyfz"      detect and convert if it looks wrong
    python fix-layout.py --to-ru "ghbdtn"               force one direction
    python fix-layout.py --to-en "Привет"               the other
    python fix-layout.py --file message.txt             a file
    cat message.txt | python fix-layout.py -            standard input

Exit 0 when the text was converted, 1 when it was left alone. That makes it usable in a pipe.
"""
from __future__ import annotations

import argparse
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")

# The physical keys, in order, on both layouts. A key does not move, so this is a permutation and not
# a translation - which is why it is exact and reversible.
EN = "qwertyuiop[]asdfghjkl;'zxcvbnm,./QWERTYUIOP{}ASDFGHJKL:\"ZXCVBNM<>?"
RU = "йцукенгшщзхъфывапролджэячсмитьбю.ЙЦУКЕНГШЩЗХЪФЫВАПРОЛДЖЭЯЧСМИТЬБЮ,"

TO_RU = str.maketrans(EN, RU)
TO_EN = str.maketrans(RU, EN)

# Letters that carry no sound of their own at the start of a Russian word, and the single-letter words
# each language really uses. A Latin word of one letter that is not "a" or "I" is a strong signal.
RU_SINGLE = set("викос у")
EN_SINGLE = {"a", "i", "A", "I"}
RU_VOWELS = set("аеёиоуыэюяАЕЁИОУЫЭЮЯ")
EN_VOWELS = set("aeiouyAEIOUY")

# Punctuation that a Russian letter can BE. When one of these sits inside a run of Latin letters, the
# Latin is almost certainly Russian underneath: English does not put a comma between two letters.
INSIDE_PUNCT = ",.;'[]`"


# The two most common letter pairs of each language, as a small stand-in for a language model.
#
# THE FIRST VERSION OF THIS FILE SCORED WITH HEURISTICS - vowel ratio, consonant runs, odd one-letter
# words, punctuation inside a word - AND IT VOTED WRONG ON A REAL CASE. Given an English sentence it
# preferred the Cyrillic nonsense the conversion produced, because "wall.post" contains a dot and the
# dot carried a penalty. A pile of weak signals adds up to a confident wrong answer.
#
# Adjacent letter pairs do not: every real word is mostly made of common pairs, and gibberish is not,
# in any layout. This is a language model with sixty parameters and it separates the cases cleanly.
RU_BIGRAMS = set("""
ст но то на ен ов ни ра во ко пр по ро ос го ер ре ом ли ат ьн ой ел ка та ет ла ого
ло ал ит ль ва те ел ьс ос ка ни ет ре ли он ан ос ом ел ит ьн ый ом ую ие ий ого его
""".split())
EN_BIGRAMS = set("""
th he in er an re on at en nd ti es or te of ed is it al ar st to nt ng se ha as ou io
le ve co me de hi ri ro ic ne ea ra ce li ch ll be ma si om ur ca el ta la ns di fo ho
""".split())


def bigram_score(text: str, table: set[str]) -> tuple[float, int]:
    """What fraction of the letter pairs are pairs this language actually uses."""
    letters = "".join(c.lower() for c in text if c.isalpha())
    pairs = [letters[i:i + 2] for i in range(len(letters) - 1)]
    if not pairs:
        return 0.0, 0
    hits = sum(1 for pair in pairs if pair in table)
    return hits / len(pairs), len(pairs)


def consonant_run(word: str, vowels: set[str]) -> int:
    """The longest run of letters with no vowel in it."""
    longest = current = 0
    for ch in word:
        if ch.isalpha() and ch not in vowels:
            current += 1
            longest = max(longest, current)
        else:
            current = 0
    return longest


def score(text: str, vowels: set[str], single: set[str], table: set[str]) -> tuple[float, list[str]]:
    """How much this text looks like a real language, and what the evidence was.

    The letter pairs carry most of the weight; the rest are reported so a reader can see the reasoning
    and disagree with it.
    """
    reasons: list[str] = []
    share, pair_count = bigram_score(text, table)
    points = share * 100.0
    reasons.append(f"{share:.0%} of {pair_count} letter pairs are common in this language")

    words = [w for w in text.split() if w]
    letters = [c for c in text if c.isalpha()]
    if letters:
        ratio = sum(1 for c in letters if c in vowels) / len(letters)
        if ratio < 0.25:
            points -= 6
            reasons.append(f"only {ratio:.0%} vowels")
        elif 0.38 <= ratio <= 0.55:
            points += 3
            reasons.append(f"{ratio:.0%} vowels, which is normal")

    worst = max([consonant_run(w, vowels) for w in words] or [0])
    if worst >= 5:
        points -= 5
        reasons.append(f"a run of {worst} consonants with no vowel")

    odd = [w for w in words if len(w) == 1 and w.isalpha() and w not in single]
    if odd:
        points -= 4 * len(odd)
        reasons.append(f"one-letter word(s) this language does not have: {' '.join(sorted(set(odd)))}")

    return points, reasons


def convert(text: str, direction: str) -> str:
    return text.translate(TO_RU if direction == "ru" else TO_EN)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("text", nargs="?", help="the text, or - for standard input")
    ap.add_argument("--file", help="read the text from a file instead")
    ap.add_argument("--to-ru", action="store_true", help="convert as if typed on a Latin layout")
    ap.add_argument("--to-en", action="store_true", help="convert as if typed on a Cyrillic layout")
    ap.add_argument("--quiet", action="store_true", help="print the conversion only")
    args = ap.parse_args()

    if args.file:
        text = open(args.file, encoding="utf-8").read()
    elif args.text == "-" or (args.text is None and not sys.stdin.isatty()):
        text = sys.stdin.read()
    elif args.text:
        text = args.text
    else:
        ap.print_help()
        return 1
    text = text.rstrip("\n")

    if args.to_ru or args.to_en:
        out = convert(text, "ru" if args.to_ru else "en")
        print(out if args.quiet else f"  converted ({'latin -> cyrillic' if args.to_ru else 'cyrillic -> latin'}):\n    {out}")
        return 0

    # No direction given: score the text as it stands and as the other layout would have it.
    looks_russian = any(c in RU_VOWELS for c in text)
    if looks_russian:
        as_is_points, as_is_reasons = score(text, RU_VOWELS, RU_SINGLE, RU_BIGRAMS)
        other, other_v, other_s, other_b = convert(text, "en"), EN_VOWELS, EN_SINGLE, EN_BIGRAMS
    else:
        as_is_points, as_is_reasons = score(text, EN_VOWELS, EN_SINGLE, EN_BIGRAMS)
        other, other_v, other_s, other_b = convert(text, "ru"), RU_VOWELS, RU_SINGLE, RU_BIGRAMS
    other_points, other_reasons = score(other, other_v, other_s, other_b)

    if not args.quiet:
        print(f"  as typed    score {as_is_points:+3}   {text[:70]}")
        for reason in as_is_reasons:
            print(f"                - {reason}")
        print(f"  converted   score {other_points:+3}   {other[:70]}")
        for reason in other_reasons:
            print(f"                - {reason}")
        print()

    if other_points > as_is_points:
        print(other if args.quiet else f"  WRONG LAYOUT -> {other}")
        return 0
    print(text if args.quiet else f"  left alone  -> {text}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
