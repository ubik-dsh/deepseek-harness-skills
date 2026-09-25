---
name: check-a-sheet
description: Put a finished workbook through measurable gates before calling it done — formula errors, numbers stored as text, a constant hand-typed into a column of formulas, a total that disagrees with the numbers above it, duplicate keys, and merges sitting inside the data. Use before delivering an .xlsx, when a spreadsheet "looks fine" but nobody checked it, or when asked to review someone else's workbook.
---

# Check a Sheet

A workbook is a claim about arithmetic. The gates are how the claim gets tested.

```bash
python scripts/sheet_gates.py КНИГА.xlsx               # ворота, человеческим языком
python scripts/sheet_gates.py КНИГА.xlsx --json        # то же машинно
python scripts/sheet_gates.py КНИГА.xlsx --render папка  # плюс PDF для глаз
python scripts/test-sheet-gates.py                     # проверка самих ворот
```

Exit code is `1` when a hard gate trips.

## Where this comes from

The spreadsheets plugin of the Codex desktop client
(`%USERPROFILE%\.cache\codex-runtimes\…\plugins\spreadsheets`, licence Proprietary) ships two
skills: `spreadsheets` (65 KB of rules and checks) and `excel-live-control` (72 KB, driving an open
Excel through Office.js), plus domain guidance for financial models, healthcare, marketing and
research.

**Borrowed: the idea that a workbook is checked, not admired.** Not borrowed: their code, and live
Excel control — we cannot drive an open Excel and do not pretend to. Here the file is read with
`openpyxl`.

## What is gated

| ворота | что именно | уровень |
|---|---|---|
| **ошибка формулы** | `#REF!`, `#DIV/0!`, `#VALUE!`, `#NAME?`, `#N/A`, `#NUM!`, `#NULL!` | жёстко |
| **итоги** | заявленное «Итого» не сходится с суммой слагаемых над ним | жёстко |
| **объединённые** | объединение стоит внутри строк данных: рядом заполнены ячейки | жёстко |
| **число как текст** | `1 234,5` строкой — Excel такое не сложит | замечание |
| **разрыв столбца** | в столбце формул одна ячейка вписана числом руками | замечание |
| **дубликат ключа** | повтор в первом столбце таблицы | замечание |

## Honesty rules

- **openpyxl не считает формулы.** Он отдаёт либо формулу, либо последнее посчитанное значение.
  Поэтому итоги сверяются только там, где посчитанные значения в файле есть; иначе в отчёте
  прямо сказано, сколько формул без значения, — и ничего не выдумывается.
- **Как получить посчитанные значения:** прогнать книгу через LibreOffice
  (`soffice --headless --convert-to xlsx`) — он пересчитывает и кладёт значения в файл. В тесте
  это делается именно так, иначе проверять «сошлось ли» было бы не на чем.
- **Объединение — дефект не само по себе.** Жёстко ловится только объединение внутри блока данных;
  остальные печатаются замечанием со своими адресами.

## Traps already paid for

- **Проверка объединённых ячеек не могла сработать никогда.** Она искала объединение, накрывающее
  больше одной заполненной ячейки, — а в xlsx значение хранит только левая верхняя клетка
  диапазона. Признак переделан на «объединение внутри строк данных». Поймал тест.
- **Итоги проверялись по листу с формулами.** Там ячейка содержит строку `=B2*C2`, разбор числа
  возвращал «не число», и проверка молча пропускала любой неверный итог. Слагаемые теперь берутся
  с листа посчитанных значений.
- **Тест сломал сам себя:** дубликат ключа записывался в ту же ячейку, где стояло «Итого», и
  стирал надпись — проверке итогов не на чем было сработать.

## Limits

- **Смысл не проверяется.** Ворота ловят поломки, а не плохую модель.
- **Графики не проверяются** — их значения ворота не читают.
- **Живой Excel не поддерживается:** только файл. Открытая книга может содержать правки, которых
  в файле ещё нет.

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
