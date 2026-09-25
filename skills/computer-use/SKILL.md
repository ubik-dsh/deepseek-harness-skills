---
name: computer-use
description: Drive another Windows application's window from an agent — list windows, read the accessibility tree, replace a field's value, click by element or coordinate, and capture the window even when it is covered. Use when a task means operating someone else's UI (a desktop app, a chat window, a form) rather than a file or a CLI, and when a screenshot of the screen would show the wrong thing because the target is behind another window. По-русски — нажми в чужой программе; открой окно; покажи в проводнике; сними окно, даже если перекрыто.
---

# Computer Use

Operating another program's window: find it, read what is in it, change a field, press a button,
and prove the result. The toolkit is `scripts/computer.py`.

```bash
python scripts/computer.py windows [--title ЧАСТЬ]        # какие окна есть
python scripts/computer.py probe   --title ЧАСТЬ          # можно ли вообще работать
python scripts/computer.py tree    --title ЧАСТЬ          # дерево доступности
python scripts/computer.py shot    --title ЧАСТЬ --out файл.png
python scripts/computer.py setval  --title ЧАСТЬ --name ИМЯ --value ТЕКСТ
python scripts/computer.py click   --title ЧАСТЬ (--name ИМЯ | --x N --y N)
python scripts/computer.py typetext --title ЧАСТЬ --text ТЕКСТ
python scripts/computer.py key     --title ЧАСТЬ --keys "Control_L+a"
```

## Where the three ideas come from

Borrowed from the Computer Use plugin that ships with the Codex desktop client
(`%USERPROFILE%\.codex\.tmp\bundled-marketplaces\openai-bundled\plugins\computer-use`,
file `docs/api.md`; the engine itself is `@oai/sky`, licence Proprietary). **Their engine cannot be
taken:** the package loads, exposes all fourteen methods, and then fails with
`failed to launch codex app-server: program not found` — it only lives inside their runtime. So the
ideas are reimplemented here on `uiautomation`, and the source is named rather than hidden.

| Their idea | What was wrong without it |
|---|---|
| **Every action carries its target window, and the input method activates it itself** | We called `SetForegroundWindow` from outside and returned success without checking; in a browser the text went to the address bar |
| **`set_value(element_index, value)` — replace a value through accessibility, not by typing** | Click landed, `SendInput` landed, and the typed text never appeared in the dialog |
| **Screenshot of the window, not of the screen** | Our screenshot was a rectangle of the screen, so a covered window was simply absent from the frame |

## The order that works

1. **`windows`** — find the target and note its pid and class.
2. **`probe`** — say honestly whether the accessibility tree exists. A window whose tree is a stub
   can only be driven by coordinates and checked by screenshot.
3. **`tree`** — if the tree is alive, work by element name; that survives layout changes.
4. **`setval`** before `typetext`: replacing a value cannot land in the wrong field, and typing can.
5. **Act, then read the value back or capture the window.** An action that was not verified is a
   guess. `setval` prints the value it read back; `click` prints whether the window came forward.

## What actually happens on this machine — measured

| Application | Accessibility tree | How to work with it |
|---|---|---|
| **WinForms / native apps** | **alive**: `EditControl «field» = «empty»`, `ButtonControl «press»` | by element name; `setval` works |
| **Chromium and Electron** (Codex desktop, the browser) | **stub**: 8–19 nodes, all panes, one `DocumentControl` with no children | coordinates + window screenshot |

Chromium publishes its tree only after it notices a UI Automation client, and a plain walk does not
wake it. Do not read the stub as "the app is empty": `tree_is_alive()` in the script counts
*workable* elements, not nodes, precisely because a ten-node WinForms form is alive and a
nineteen-node Chromium window is not.

## Verified end to end

Against a throwaway WinForms form, with another window in the foreground:

```
setval --name field --value "привет из DSH"   → значение заменено: «привет из DSH»
click  --name press                           → нажал «press», окно впереди
the target's own handler wrote the file       → привет из DSH
shot   (foreground was another app)           → the form's own pixels, value visible
```

## Traps

- **`IsValuePatternAvailable` does not exist on every control type** (`PaneControl` raises
  `AttributeError`). Ask for the pattern inside `try`, as the script does — a swallowed exception
  there reads as "no fields found", which is a lie about the application.
- **A node count is not a liveness test.** Ten nodes can be a real form; nineteen can be an empty
  shell. Count workable elements instead.
- **`--name` matches a substring.** Several elements can match; the script prefers one with an
  editable value, and otherwise says what it picked.
- **`SetActive()` returning without raising is not success.** Read the foreground window afterwards,
  which is what `activate()` does.
- The toolkit never closes, deletes, or submits anything by itself; every action is one explicit
  command, so a wrong step is visible before it becomes a wrong result.
