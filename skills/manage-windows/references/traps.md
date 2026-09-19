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
| a path ending in a backslash, inside a string | drop it, or double it вЂ” a trailing backslash escapes the closing quote |
| assuming `\` | `Join-Path`, or accept both and normalise |
| a command over 8191 characters | a script file |

The trailing-backslash trap is worth naming: `"C:\dir\"` is not a string ending in a
backslash, it is an unterminated string, and the error points somewhere else.

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
virtual-desktop move, the layout-dependent typing, and the scripts written into the working
tree.
