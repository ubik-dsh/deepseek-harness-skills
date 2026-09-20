# Russian micro-typography, and which rule is not a rule

Adopted from `Shadowru/crosspost-design-skill`'s `references/typography-ru.md`, AGPL-3.0.
**The table is borrowed; the implementation is ours**, and one rule was deliberately changed
— see the last section, which is the point of this file.

The reason typography matters at all on these platforms: they strip CSS. A tag, a class, a
font and a colour are all deleted. **Unicode survives**, so punctuation is the only layer of
presentation that reaches the reader intact.

## The nine rules

| | rule | wrong | right | mechanical? |
|---|---|---|---|---|
| 1 | quotes are «ёлочки» | `"текст"` | `«текст»` | yes |
| 2 | nested quotes are „лапки“ | `«внутри "такое"»` | `«внутри „такое“»` | yes, if the nesting is visible |
| 3 | the dash is long | `слово - слово` | `слово — слово` | yes |
| 4 | a hyphen lives inside a word | `кто — то` | `кто-то` | **no — this is a question about meaning** |
| 5 | ranges take an en dash | `5-7 дней` | `5–7 дней` | yes, **narrowly** |
| 6 | an ellipsis is one character | `...` | `…` | yes |
| 7 | no space before a mark | `слово , слово` | `слово, слово` | yes |
| 8 | a space after a mark | `слово,слово` | `слово, слово` | yes |
| 9 | one space between words | `слово␣␣слово` | `слово слово` | yes |

**Eight of the nine are mechanical. The ninth is listed as mandatory by the table it came
from, and it is not a rule.** `кто — то` is a dash where a hyphen belongs *if it is one
word*, and two words with a dash *if it is two*. No regular expression decides that. The
linter raises it as a question for the reader and **never rewrites it** — a rule that guesses
here silently changes what the sentence says.

## Rule 5 was changed, and the reason is measured

As published, the range rule is `(?<=\d)\s?-\s?(?=\d)` — any hyphen between digits becomes
an en dash. Run over a text containing these, it produces the right-hand column:

```
ГОСТ 7.32-2017       ->  ГОСТ 7.32–2017
8-800-555-35-35      ->  8-800-555-35–35
1-2-3                ->  1-2–3
-5 градусов          ->  (unchanged, no digit before)
```

**None of the first three is a range.** Two of them are identifiers a reader may have to
type into a telephone or quote in a document. The linter here uses:

```python
(?<![\d.\-])(\d{1,4})-(\d{1,4})(?![\d\-])
```

A hyphen with a **digit, a dot or another hyphen** beside it belongs to a longer token and
is left alone; a hyphen that is the whole token is a range.

Measured over 14 control traps — a standard number, a telephone number, a version chain, a
negative temperature, a markdown list marker, a CLI flag pair, a formula, a URL, a
placeholder, a time, a decimal comma — **the narrow rule changes none of them.** The
published one changes three.

## What the linter masks before it runs

Code fences, inline code, URLs, `{{placeholders}}` and HTML comments. **Typography does not
apply inside them**, and a pass that rewrites a code sample has broken a document while
reporting success.

## Non-breaking spaces, and why they are off by default

With `--nbsp`, a non-breaking space is bound after a short preposition or conjunction
(`в Москве`), before a long dash, and between a number and its unit (`10 кг`, `5 %`).

Off by default because a short post accumulates the ties faster than it accumulates
benefit, and a reader of the source sees `\u00a0` where they expected a space. Turn it on
for an article, not for a wall post.

## What the linter will not do

- **Decide rule 4.** It reports.
- **Choose between `5 %` and `5%`.** Both are defensible Russian practice; pick one for the
  document and keep it.
- **Place `ё`.** Whether `все` means *all* or `всё` means *everything* is meaning, and the
  linter never touches a letter.
- **Judge the writing.** A clean run means the punctuation is consistent with the rules. It
  says nothing about whether the article is any good.
