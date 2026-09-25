---
name: make-a-template
description: Turn one reference document into a reusable template — a personal skill that carries the reference itself plus its MEASURED form (section order, paragraph length, where tables and code sit), and a check that fails when a new text drifts from that form. Use when asked to "make a template from this", "write the next one the same way", "keep this format", or when several documents of one kind keep coming out in different shapes. По-русски — сделай шаблон; как в прошлый раз; в той же форме; по образцу.
---

# Make a Template

One reference in, one personal skill out, and — this is the part that matters — a **check that can
fail**.

```bash
python scripts/templates.py make  --reference ФАЙЛ --name ИМЯ [--purpose "для чего"]
python scripts/templates.py check --template ИМЯ --document ГОТОВЫЙ-ФАЙЛ
python scripts/templates.py list
python scripts/test-templates.py          # проверка самого инструмента
```

## What a template is here

A folder under `~/.dsh/skills/<имя>` — personal, not part of the family repository:

```
<имя>/
  SKILL.md         как писать: для чего, порядок разделов, числа формы
  form.json        форма, ИЗМЕРЕННАЯ у образца — машиночитаемая
  reference/…      образец, сохранённый как есть
  preview.html     превью формы: где какие разделы и что внутри
```

A template exists only after `make` succeeds. A hand-written skill called a template is not one.

## Why ours checks and theirs does not

The idea is borrowed from the **Template Creator** plugin of the Codex desktop client
(`%USERPROFILE%\.cache\codex-runtimes\…\plugins\template-creator`, licence Proprietary): a reference
becomes a personal skill that later reproduces its structure, voice and layout, and the reference is
kept inside on purpose, unsanitised, because fidelity was chosen over tidiness.

**What their flow never does is verify.** A template is created and that is the end of it; nothing
tells you whether the next document actually has the same shape. Here the form is reduced to
numbers and `check` compares a finished text against them:

```
разделов: у образца 8, здесь 8
абзац: у образца ~163, здесь ~163 символов
таблицы 0/0 · код 3/3 · жирное 26/26 · ссылки 0/0
ПО ФОРМЕ: расхождений по числам нет.
```

and when it drifts:

```
НЕ ПО ФОРМЕ:
  - на месте 3 ожидался «Как проверить», а стоит «Проверка»
  - длина абзаца: у образца 120, здесь 300 (расхождение 60%)
```

**Praise without a number is not a check.** A template nobody can fail is decoration.

## What is measured, and what is not

Measured: order and level of sections, median paragraph length, and whether a section contains a
table, a list, code, a quote, or starts with a bold lead — plus totals for tables, code fences, bold
spans, links and quote lines.

**Not measured: meaning.** `check` will not tell you whether the text is any good, whether the
argument holds, or whether the facts are right. It answers one question — is this the same form —
and says so in its own output rather than letting the number stand for more than it is.

**The document title is content, not form.** `check` requires a first-level heading to exist and
reports a different title as a note, not a fault. The first version compared titles word for word
and rejected any document with a different name; the self-test caught it.

## Limits, honestly

- **Markdown only.** The measurement reads headings, paragraphs, fences, tables and lists. `.docx`,
  `.pptx`, `.xlsx` and Google links are not parsed here; for those, extract the text first or keep
  the reference as rendered HTML.
- **A form check is coarse by design.** Exact heading text is required (that is the point — the
  reader recognises the document by its sections), while counts are compared with tolerance, because
  one extra table is not a different genre.
- **`form.json` is a snapshot, not a contract.** Re-run `make --force` after editing the reference,
  otherwise the template describes an older shape than the one it carries.

## Готово, когда

**Не «сделал», а «вот это сходится»:**

- прогон идёт **в этом сообщении**, а не «я это проверял раньше»: прошлый прогон не довод;
- названо, **чем** проверено, и приведён вывод, а не пересказ вывода;
- если проверка не проходила — так и сказано, с числами, а не «почти»;
- **чего не проверял — сказано прямо.** Молчание о непроверенном читается как «проверено».

## Если заклинило

**Первая ошибка:** прочитать текст ошибки целиком, а не первую строку. **Править малое, а не
переписывать целое:** переписанное заново ломает то, что уже работало.

**Вторая попытка с тем же отказом — стоп.** Однотипный отказ не лечится третьей попыткой;
менять надо не усилие, а подход: другой инструмент, другой разрез задачи, вопрос человеку.

**И признак, что пора остановиться:** если правка делается «чтобы тест замолчал» — это уже не
починка, а подгонка. Тест, который перестал падать сам, ничего не доказал.

## Какой шаблон — спросить, а не угадывать

**Когда шаблонов больше одного, выбор делают словами, а не догадкой.** Список — `python templates.py
list`: имя, назначение, число разделов. Спросить: «делать в форме разбора технологии или в форме
отчёта?» — и назвать оба, а не подставлять первый.

**Почему это отдельный шаг.** Угаданный шаблон стоит дороже, чем вопрос: текст выходит не в той
форме, и переделывать его целиком. Взято у плагина `presentations` Кодекса-десктопа, где для этого
лежит отдельный `template-elicitation.md`.
