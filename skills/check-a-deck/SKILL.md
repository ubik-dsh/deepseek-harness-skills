---
name: check-a-deck
description: Put a finished presentation through measurable gates before calling it done — shapes off the slide, text that runs into other text, font sizes below a floor, leftover placeholders, slides carrying too many words, and table totals that do not match the numbers above them. Use before delivering a .pptx, when a deck "looks fine" but nobody checked it, or when asked to review someone else's slides.
---

# Check a Deck

A finished deck is a claim. The gates are how the claim gets tested.

```bash
python scripts/deck_gates.py КОЛОДА.pptx                 # ворота, человеческим языком
python scripts/deck_gates.py КОЛОДА.pptx --json          # то же машинно
python scripts/deck_gates.py КОЛОДА.pptx --render папка  # плюс PDF для глаз
python scripts/test-deck-gates.py                        # проверка самих ворот
```

Exit code is `1` when a hard gate trips, so it can stand in a chain.

## Where this comes from

The presentations plugin of the Codex desktop client
(`%USERPROFILE%\.cache\codex-runtimes\…\plugins\presentations`, licence Proprietary) is built around
**gates, not slide-building**: `native_table_arithmetic_gate.py`, `native_quantitative_chart_gate.py`,
`native_chart_title_gate.py`, `inspect_presentation_layout_geometry.py` (102 KB),
`inspect_presentation_package_integrity.py`, `template_source_fidelity_gate.py`. The deck is not
finished until the gates pass.

**The idea is borrowed; the code is ours.** Python plus `python-pptx`, no dependency on their
package, no copying of their scripts.

## What is gated

| ворота | что именно | уровень |
|---|---|---|
| **пакет** | колода открывается, слайды есть, размер слайда задан | жёстко |
| **за краем** | фигура вышла за границу слайда больше чем на 0,1″ | жёстко |
| **шрифт** | размер ниже порога (`--min-font`, по умолчанию 12 пт) | жёстко |
| **заглушка** | в тексте осталось `TODO`, `FIXME`, `lorem ipsum`, `заполнить` | жёстко |
| **числа** | сумма слагаемых в столбце не сходится с заявленным «Итого» | жёстко |
| **много слов** | слайд несёт больше `--max-words` слов (по умолчанию 60) | замечание |
| **налезают** | два текстовых блока перекрываются больше чем на четверть меньшего | замечание (оценка) |
| **заметки** | слайд без заметок | замечание |

## Honesty rules this tool follows

- **Сказано, что оценка, а не измерение.** «Налезают» считается по площади и потому помечено
  оценкой: перенос строк и реальные границы текста так не измерить.
- **Наследованный кегль не выдумывается.** `python-pptx` отдаёт `None` для размера, взятого из
  макета. Такие прогоны считаются отдельной строкой (`runs_without_size`), а не подставляются
  «на глаз».
- **Разнобой кеглей в верхней четверти — не дефект.** Заголовок и подзаголовок разного размера
  это норма; строка печатается как сведение, а не как приговор.
- **Зазор 0,1″ на вылет** оставлен намеренно: тени и выноски выходят за край законно.

## Traps already paid for

- **`slide.number` не существует** в `python-pptx` — номер берётся из `enumerate(deck.slides, 1)`.
- **Одно имя на две вещи.** Внутри разбора таблиц параметр «номер слайда» и функция разбора числа
  назывались одинаково (`number`); функция затирала номер, и отчёт падал на сериализации в JSON.
- **«Хотя бы два слагаемых» прячет ошибку.** С этим условием таблица из одной строки с неверным
  «Итого» проходила ворота. Теперь столбец считается числовым, если **все** его непустые клетки —
  числа, и одного слагаемого достаточно. Поймал тест, а не глаза.

## Limits

- **Смысл и красота не проверяются.** Ворота ловят поломки, а не плохой вкус.
- **Графики не проверяются.** У них для этого отдельные ворота с разбором данных диаграмм; здесь
  читаются текст и таблицы — значения внутри диаграмм не сверяются.
- **Рендер требует LibreOffice** и делается для глаз, а не для ворот: числа берутся из файла.

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
