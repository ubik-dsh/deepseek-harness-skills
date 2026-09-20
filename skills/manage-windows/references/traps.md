# Traps

Behaviours that surprise on Windows, each with the form that fails and the form that works.
Most of them fail **without a message**: the command exits 0, the output is valid, and the data
is wrong. That is why they are worth writing down — a loud failure teaches itself.

Sources are named at the end. The ones marked **[ours]** were paid for in this repository.

---

## JSON

| Fails | Works |
|---|---|
| `ConvertTo-Json $obj` | `ConvertTo-Json $obj -Depth 10` |

**Silent and lossy.** Past depth 2 the cmdlet stops descending, returns well-formed JSON, and
exits 0. The nested part is simply gone. There is no way to notice from the output, because the
output is valid — it is just not the object you had.

This is the most expensive entry in this file, because nothing about it looks like a failure.

## Parentheses and operators

| Fails | Works |
|---|---|
| `if (Test-Path "a" -or Test-Path "b")` | `if ((Test-Path "a") -or (Test-Path "b"))` |
| `if (Get-Item $x -and $y -eq 5)` | `if ((Get-Item $x) -and ($y -eq 5))` |

An unparenthesised cmdlet call swallows what follows as its own parameter, so the condition is
not the condition you wrote. PowerShell does not complain; it evaluates something else.

## Null before property

| Fails | Works |
|---|---|
| `$array.Count -gt 0` | `$array -and $array.Count -gt 0` |
| `$text.Length` | `if ($text) { $text.Length }` |

`$null.Count` and `$null.Length` differ by version and by strict mode. Guarding is the only form
that holds everywhere.

## Strings

| Fails | Works |
|---|---|
| `"Value: $($obj.prop.sub.nested)"` | `$v = $obj.prop.sub.nested; "Value: $v"` |

Nested expressions inside interpolation are legal and fragile: the parser's idea of where the
expression ends is not always the reader's. Assign first.

## Text and encoding

**A bare `powershell.exe` is 5.1, and 5.1 writes a byte-order mark.** Any file it writes begins
with three invisible bytes, and any reader matching from the start of the file — a regex
anchored with `^`, a frontmatter parser, a line-by-line comparison — will miss. **[ours]** A
parser in this repository required a file to begin with `---`; a BOM in front made it read the
file as empty and write nothing, silently, while reporting success.

| Fails | Works |
|---|---|
| `Get-Content -Raw f \| Set-Content f` on 5.1 | use a UTF-8-aware tool, and verify |
| parsing a file with `^` | strip a leading `\uFEFF` first |
| assuming 7 because the machine has it | `$PSVersionTable.PSVersion.Major` |

**Do not write non-ASCII from 5.1.** Emit ASCII and translate at the edge, or use 7. Emoji in
output is the usual way this bites: the console mangles them and the log becomes unreadable at
exactly the moment it matters.

```powershell
$PSVersionTable.PSVersion.Major          # 5 or 7, and the rules differ
[System.Text.Encoding]::UTF8             # what you think you are writing
```

| Purpose | Not this on 5.1 | This |
|---|---|---|
| Success | ✅ | `[OK]` |
| Error | ❌ | `[X]` |
| Warning | ⚠️ | `[WARN]` |
| Info | ℹ️ | `[i]` |

The same rule for `cmd`: **`chcp 65001` breaks `set /p`.** The encoding workaround is worse than
the problem, which is the reason to prefer PowerShell rather than to patch the batch file.

## Launching

| Fails | Works |
|---|---|
| `powershell -Command "& 'script.ps1'"` | `powershell.exe -NoProfile -ExecutionPolicy Bypass -File "script.ps1"` |
| `Start-Process ... -Wait` for a GUI app that never exits | return immediately and poll for the window |
| `-Password "..."` as an argument | an authenticated session, or a prompt |

**A password on a command line is readable by other processes on the machine.** It is also
written to the process table, which is the kind of thing log collectors keep.

`-NoProfile` because a profile can change behaviour or print into your output;
`-ExecutionPolicy Bypass` for this invocation only; `-File` so quoting and encoding cannot
rewrite the arguments.

## Elevation

```powershell
([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()
  ).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
```

Check it rather than assuming. **And do not elevate the agent to avoid a prompt** — an
administrator agent can do anything on the machine and has no way to ask about it. A per-user
setting, a narrower operation, or one command the user runs themselves is almost always
available.

## Input

| Fails where it matters | Works |
|---|---|
| `mouse_event` | `SendInput` |
| `SetCursorPos` alone, before a drag | a move event with `MOUSEEVENTF_MOVE`, then press |
| a move without `MOUSEEVENTF_VIRTUALDESK` | normalised virtual-desktop coordinates |
| `VkKeyScanW` for text | `KEYEVENTF_UNICODE` |
| sending without focusing | focus, confirm, then send |

`mouse_event` and `keybd_event` work in Notepad and do nothing in a XAML or WinUI application —
which is the worst kind of failure, because the approach looks validated. **[ours]**

`VkKeyScanW` maps a character through the **current keyboard layout**, so on a Russian layout it
returns nothing usable for Latin text. `KEYEVENTF_UNICODE` bypasses the layout entirely. **[ours]**

Without `MOUSEEVENTF_VIRTUALDESK`, absolute coordinates are interpreted against the primary
monitor. On a multi-monitor machine the click lands on a different screen than the one intended.
**[ours]**

## Files

| Fails | Works |
|---|---|
| a generated script in the working tree | a scratch directory the tool owns |
| a temp file beside the source | `%TEMP%` |
| editing the registry for a documented setting | the documented setting |

A task script written into the working tree becomes an untracked file in someone's repository.
This repository has done it repeatedly. **[ours]**

## Command line and paths

| Fails | Works |
|---|---|
| a path with spaces, unquoted | quoted, always |
| a path ending in a backslash, inside a string | drop it, or double it — a trailing backslash escapes the closing quote |
| assuming `\` | `Join-Path`, or accept both and normalise |
| a command over 8191 characters | a script file |

The trailing-backslash trap is worth naming: `"C:\dir\"` is not a string ending in a
backslash, it is an unterminated string, and the error points somewhere else.

## Window state

| Fails | Works |
|---|---|
| `ShowWindow($h, 9)` to "make sure it is visible" | `if (IsIconic($h)) { ShowWindow($h, 9) }` |
| assuming a restored window is where it was | re-measure after any geometry change |

**`SW_RESTORE` (9) un-maximises a maximised window.** It does not mean "make it usable"; it means
"put it back to its restored size", and for a window that is already maximised that is a
**change**. Calling it unconditionally shrank a full-screen browser to 968x524 and moved every
control the click coordinates had been measured against — the coordinates were still right and
the window was not, which is the failure this skill exists to prevent, arriving through the
preparation step rather than the press.

The three states are separate and each needs its own call: `IsIconic` → `SW_RESTORE`, `IsZoomed`
→ already fine, neither → already fine. And a call that changes geometry is **an action on
someone's desktop**: measure the rectangle before and after, and put it back. **[ours]**

## Assembling an input struct in PowerShell

| Fails | Works |
|---|---|
| `$i = New-Object Win+INPUT; $i.mi.dx = 100` | build the struct inside a C# helper method |
| trusting `SendInput`'s return value | reading the cursor position back |

**`SendInput` reports success while sending nothing.** PowerShell does not reliably write a field
of a nested value-type field on a boxed struct: `$input.mi.dx = …` left `dx` at zero, the event
went out with no movement, and `SendInput` returned **1**. The cursor never moved.

This is the most expensive shape of bug in this file — a call that succeeds and does nothing —
and the only defence is the one the skill already demands: **read the state back**.
`GetCursorPos` after the move, `WindowFromPoint` at the point before the press. A check that
compares the reply to an expectation catches it; believing the reply does not. **[ours]**

## One process, several windows

| Fails | Works |
|---|---|
| `--pid` alone to mean "this window" | the window **handle**, or pid plus a verified title |
| `MainWindowHandle` as "the window of the process" | enumerating the process's top-level windows |

**A pid is not a window.** Two Yandex Browser windows — the VK settings page and this harness —
had the **same pid, 7092**, because one browser process owns both. `MainWindowHandle` named only
one of them, so pid identity would have "verified" the wrong window while passing every check.

The preflight's fifth check says *"by process id **or handle**"*; it implements the pid. On a
machine where one process owns several windows that is a gap between the prose and the code, and
it was found by needing the handle. **[ours]**

## A script's step order

| Fails | Works |
|---|---|
| an action block written above the `Add-Type` that defines its type | every action after the code it calls |
| assuming a failed statement stops the script | `$ErrorActionPreference`, or ordering that cannot fail |

**A script whose steps are in the wrong order does not stop at the step that failed.** Two action
blocks were written above the `Add-Type` that defined the class they called: they raised
`Unable to find type [Typer]`, and the script **carried on to the next block anyway** and pressed
Enter twice into a field nothing had been typed into. PowerShell reported both failures and ran
everything else.

The damage was small and the shape is not: a step that fails silently leaves the steps after it
running on a state that was never prepared. Order the actions after their dependencies, and make
the following step depend on the one before it — the fixed version types only when there is a
string to type.

## `$Home` is taken

| Fails | Works |
|---|---|
| `param([switch]$Home)` | `param([switch]$ToStart)` |
| `$Host`, `$Input`, `$Args`, `$Error`, `$Matches` as parameter names | anything else |

**PowerShell's automatic variables cannot be parameter names.** `-Home` fails at binding time with
*"Cannot overwrite variable Home because it is read-only or constant"*, and **the script body never
runs at all** — while the click that preceded it and the keystrokes that followed it both did. The
first attempt at adding a line to a text field left a click and two newlines applied with no text
between them, which split a word in the middle of a sentence.

The failure is loud and the consequence is quiet, which is the combination worth remembering. **[ours]**

## Reading a control out of a screenshot

| Fails | Works |
|---|---|
| a colour threshold to classify ticked against empty | an ASCII map of the pixels, read directly |
| eyeballing a crop to a coordinate | a bounding box computed from the drawn border |

A threshold classifier reported nearly every row of a settings list as *ticked* while the image
plainly showed one tick. It was measuring antialiased glyph edges in the label column, not the
boxes. **A classifier that disagrees with the picture is one to stop using** — printing the
pixels as a character map gave the box, its state and its centre in one look, because a drawn
border is a shape and a threshold is a guess. **[ours]**

---

## Where these came from

**`raphaol/powershell-windows-best-skill`** (as `powershell-windows-master`) — the JSON,
parentheses, null, string-interpolation, ASCII and launching entries, and the script header
template. Judged at 5 for the prosecutor against 6 for the defence: the first of twelve
hearings where the defence won, and the reason was that its opening is a trap list rather than
advice, and it needs nothing from another harness.

**`browser-use/windows-harness`** — one call per decision point, the foreground-first input
ladder with named fallbacks, and writing generated scripts to the tool's own directory rather
than the working tree.

**`Lucien-1127/strata-skill`** (as `windows-automation`) — the `chcp 65001` trap, the exact
PowerShell invocation with the reason for each flag, and the shortcut COM lines.

**`mturac/everything-openai-codex`** (as `windows-desktop-e2e`) — the accessibility-tree rung,
now held by `learn-an-interface`.

**[ours]** — found by doing it: the BOM defect, the input calls that reach nothing, the
virtual-desktop move, the layout-dependent typing, the scripts written into the working
tree, and — from one click on a VK settings page — `SW_RESTORE` shrinking the window it was
meant to prepare, a hand-assembled input struct that `SendInput` accepted and ignored, a pid
that two windows shared, and a colour threshold that classified label glyphs as ticked boxes.
