---
name: learn-an-interface
description: Drive a real graphical interface from an agent — a window, a ribbon, a dialog, a canvas — reaching it through the accessibility tree where one exists and learning its coordinates where none does, instead of hard-coding them. Covers the order of preference (API, CLI, file format, library, UI Automation / AX / AT-SPI, macro, and only then pixels), the input calls that actually reach a modern application, how to measure a window so clicks land, a small bandit that finds the unknown detail and remembers it, and the measured traps that make a working automator report success while doing nothing. Ships a runnable learning loop. Use when a task needs a program driven and it has no API, no command-line tool, no scriptable interface and no readable file format; when choosing between UI Automation and screenshot-and-click; when clicks land on the wrong thing or nowhere; when a keyboard or screenshot tool appears to do nothing; when a GUI step must be repeatable without a human hand.
license: MIT
compatibility: Agent Skills standard. SKILL.md is plain text. The script in scripts/ needs Python 3.8+ with Pillow, and drives Windows; the method itself is platform-neutral and the traps are documented so they can be recognised elsewhere.
metadata:
  spec: https://agentskills.io/specification
  version: 0.2.0
  status: sharpened by a survey of 105 rival skills, each read and trialled — see references/borrowed-practices.md
  measured_on: Windows 11, Paint (Microsoft Store build), two monitors at 2560x1440 and 1920x1440
  verified_against: DSH 0.1.5-rc.2
  borrowed_from: youngjunning/windows-app-automation and affaan-m/ECC (UI Automation with AutomationId selectors), BanmaXM/operate-ui-by-screenshot (an interface ladder that starts at API), alchaincyf/huashu-mac-use (the macOS side) — found by a GitHub survey of 105 repositories shipping a SKILL.md for interface control, and kept only after a live trial on Paint confirmed the tree reaches the tools and the palette by name
  sibling: design-a-reward — the reward this skill feeds is a subject of its own
---

# Learning an interface

Sometimes the only handle on a thing is a picture of a window. This skill is for
that case: how to decide whether to build it, how to see and touch a real window,
and how to **learn** the details nobody documented instead of writing coordinates
into a script and watching them go stale.

Read it in order. Step 1 is a refusal, and most of the value is there.

---

## Step 1 — Try to not do this

Driving a GUI is the last resort. The question is not "can this be automated?" —
it always can — but "is there a supported way in?" Stop at the first yes:

| ask | if yes |
|---|---|
| an API, SDK or service? | use it |
| a command-line tool? | use it |
| is it a file format you can read and write? | do that |
| a library for it? | use that |
| **does it expose an automation tree — UI Automation, AX, AT-SPI?** | **use it** |
| can the application script itself — macro, plugin, config, URL scheme? | use that |
| **nothing, and the only way in is pixels and clicks** | continue |

**The automation tree is the rung this skill was first written without, and a survey
of what already exists on GitHub is what exposed the gap.** It goes above pixels
because it is a documented, platform-versioned interface, and above macros because it
is uniform across applications. Measured on Paint:

```
Pencil   automationId='PencilTool'   supports Toggle   Off -> On, no cursor
Colors   Black, Gray, Dark red, Red, Orange, Yellow, Green, Turquoise, Indigo
Panes    only ScrollViewer - the drawing surface is NOT in the tree
```

So a palette is **a list of named colours**, not a row of pixels — an earlier session
measured that palette's pitch by scanning for it (24, not 28.6, after getting green
where yellow was wanted) when the names were there all along. And a canvas is
custom-drawn, so a stroke still needs coordinates. The boundary is clean: tools, menus,
colours, values and list rows through the tree; **drawing and dragging through
coordinates**.

Credit: the practice comes from `youngjunning/windows-app-automation` and
`affaan-m/ECC` (UI Automation with `AutomationId` selectors), `BanmaXM/operate-ui-by-screenshot`
(a ladder that starts at API rather than at screenshots) and `alchaincyf/huashu-mac-use`
for the macOS side. Full trial, code and caveats:
[references/accessibility-first.md](references/accessibility-first.md).

The order overall is about brittleness, not purity. An automator is coupled to things
nobody promised to keep: the **version** (a ribbon gets rearranged and every
coordinate silently means something else), the **theme and display scale**, the
**keyboard layout**, the **monitor count**, and **whatever window is on top**.

All five broke this work inside one afternoon. An API has none of them, and an
automation tree has almost none — it survives a move, a resize and a second monitor,
which a coordinate does not.

**Write the refusal into the skill you are building.** If the task genuinely needs
this, say which alternatives were rejected and why. That sentence separates a
considered choice from a habit, and it tells the next reader where to look when a
release breaks it.

## Step 2 — Write the success test before the automator

The test is not a formality; in a learning loop it **is the reward**, and a weak
reward does not merely fail to help — it trains the learner on the wrong target and
it converges confidently.

Name the artifact, then check a property only the right artifact has. Three ways
this went wrong, all measured:

| the weak test | what it certified |
|---|---|
| "a file exists" | a project file named `.png` — first bytes `00 00 00 20 66 74 79 70`, not `89 50 4E 47` |
| "the screen changed" | a menu opening, a highlight moving, nothing done |
| "a value came back" | an error page parsed as if it were data |

Then **run the test against the wrong thing once**, and watch it fail. A test that
has never failed is not yet a test. If the reward needs grading rather than a yes
or no, that is a subject of its own — see the sibling skill `design-a-reward`.

## Step 3 — Find the window, then ask the tree before measuring pixels

Find it by title, and take the largest match: a tooltip or a hidden owner can carry
the same words. Then, **before measuring anything**, enumerate the automation tree and
see what the program publishes. That probe takes a minute and decides the whole
approach — and on Paint it turned a measured palette into a list of named colours.

Only measure pixels for what the tree does not reach: a canvas, a dragged path, a
custom-drawn surface.

And when you do measure, **measure**, because the fastest way to lose an hour is to read
coordinates off a screenshot.

A capture shown at 1086 wide from a window of 1936 is not the window. Every click
in the first attempt landed 40% short, and the report said *"the pencil does
nothing"* rather than *"the aim is wrong"* — the wrong diagnosis, from the same
number.

The method that works:

1. capture the window;
2. crop the region of interest and **scale it up**;
3. draw a grid on the crop whose **labels are the window's own pixel numbers**;
4. read positions off the grid;
5. draw the chosen points back onto a full capture and **look at it**;
6. then click.

For a palette or a row of buttons, do not measure at all — **scan** for runs of
non-background pixels and take each run's centre. That is how the swatches were
found to be 24 apart from x 800, where estimating had put them 28.6 apart from 806
and moved every colour two places to the right.

More: [references/measuring-a-window.md](references/measuring-a-window.md).

## Step 4 — Measure the input layer too

The input calls are not interchangeable, and the failures are silent.

- **`SendInput` only.** A drag across a canvas through the legacy `mouse_event`
  changed **exactly zero pixels**; the same drag through `SendInput` left a line.
  `keybd_event` is the same trap for keys: Escape and Ctrl+S were seen, Ctrl+Z
  never was, so an undo that had visibly happened measured as not happening. The
  legacy calls still move the pointer and still open menus — which is exactly what
  makes the failure look like a logic bug.
- **Move with `ABSOLUTE | VIRTUALDESK`, then read the position back and raise if
  the pointer is not where it was asked to go.** Without `VIRTUALDESK`, an absolute
  move addresses the primary monitor and threw the cursor 942 pixels onto the other
  screen, and the click landed in a stranger's browser. Plain `SetCursorPos` is
  right about monitors and wrong about drags: no move events, so press and release
  land in one place and a stroke becomes a dot.
- **Send typed text as Unicode, or better, do not type at all.** `VkKeyScanW` answers
  with the key that produces the character *in the current keyboard layout*; on a
  Russian layout a folder path came out as `\\W/Y\/L/.` and the dialog answered "The
  file name is not valid." `KEYEVENTF_UNICODE` bypasses the layout — and where the
  automation tree offers a `ValuePattern`, `SetValue` bypasses the keyboard entirely.
- **Verify-before-press is not optional, and it is two checks, not one.** The pointer
  must have arrived **and** this window must be the one that will receive the input.
  `SendInput` goes to whatever is **focused**, not to whatever rectangle the arithmetic
  pointed at — and getting that wrong put a click into a stranger's browser window
  **twice** in this work. The fix is four lines and it names the offending window:

  ```
  refusing to click: 'Яндекс Браузер' is in front, not 'Paint' - activate the window first
  ```

  Two traps inside those four lines: **`ctypes` truncates handles** — `GetForegroundWindow`
  and `GetAncestor` return 64-bit handles and ctypes assumes `int`, so the first version
  of the guard silently passed everything until both had `restype = wintypes.HWND`; and
  **the pointer check fires first** when a window is minimised, because a minimised
  window's rectangle is the iconic placeholder, so both checks are needed.
- **Prefer a pattern to an input, and a value to a toggle.** If a control exposes
  `Toggle`, `SelectionItem`, `Value` or `Invoke`, use it — it is atomic, it cannot miss,
  and it does not care where the window is. And **set a value rather than flipping a
  state**: a state that is already set does not change when it is set again, which is
  what made a probe report "no effect" for a tool a previous run had left selected.
  Selecting an identified item also beats counting arrow keys, which is a failure this
  work has on record.

## Step 5 — Name the unknown as a small finite set of actions

You almost never need a general agent. You need one value: which row, which of four
similar buttons, what offset makes the click land. Write the candidates down.

- **small** — ten candidates converge in about ten attempts;
- **ordered by plausibility** — it costs nothing and the first sweep is shorter;
- **discrete** — a bandit over integers needs no tuning; a continuous search does.

Do not include a **safe fallback** unless you price it honestly. A "reload" action
that cost a little and avoided the penalty for missing was preferred over an
untried aim — because *missing is what an untried aim looks like* — and the agent
learned two of three mappings and answered "reload" to the third.

## Step 6 — Learn it, with a graded reward and a file

Use `scripts/learn-an-interface.py`. Copy it, replace `class Task`, keep the bandit.

```
1.0   the wanted thing happened            (a real PNG was written)
0.3   something happened, not that thing   (a file was written, as TIFF)
0.0   nothing happened
```

**Grade the reward** wherever a partial result exists. With only 1.0 and 0.0 the
learner cannot tell "nearly" from "nowhere" and spends attempts relearning what it
already knew.

Selection is UCB1 — try each action once, then prefer the best upper confidence
bound `mean + sqrt(2 * ln(total) / n)`. One formula, no learning rate,
deterministic, and exploration falls out of the same expression as exploitation.

The counts go to a JSON file beside the script. **That file is the learning.**
Losing it costs exactly one exploration sweep.

Measured, from empty memory over six candidates:

```
   iter  row  reward  best        iter  row  reward  best
      1  538     0.3    538          7  545     1.0    545
      2  545     1.0    545          8  549     1.0    545
      3  549     1.0    545          9  553     1.0    545
      4  553     1.0    545         10  545     1.0    545
      5  557     0.3    545         11  549     1.0    545
      6  560     0.3    545         12  553     1.0    545
```

Six attempts to explore, then six consecutive successes, and `--apply` afterwards
goes straight to the remembered row with no exploration at all.

## Step 7 — If the skill needs to know what kind of thing it is looking at

"Did the screen change" cannot tell a button from a drawing. "Did the change
**survive a neutral action**" can, and needs no labels:

| what | neutral action | result | so it is |
|---|---|---|---|
| a menu opened | press Escape | the pixels went back | **transient** |
| a tool was chosen | move the pointer away | the highlight stayed | **fundamental** |
| a colour was set | move the pointer away | the setting stayed | **fundamental** |
| a stroke was drawn | press Ctrl+Z | the pixels went back | **an edit** |
| the drawing surface | — | present before and after everything | **fundamental** |
| what is drawn on it | a new document | gone | **transient** |

Two traps in measuring it. **Reset between probes**: a tool that is already selected
changes nothing when clicked again, and the first version reported "no effect" for a
pencil a previous run had left selected — measuring a thing that persists means
measuring a *change* of it, so click two different swatches and see that each one
lands. And **check the world is still there** before judging an action.

## Step 8 — Prove it, and write down the cost

- Run the loop **from empty memory** and record how many attempts exploration took.
  That number is what a fresh machine pays.
- Run `--apply` and confirm it succeeds with no exploration.
- Delete the memory file and confirm the skill still works from cold.
- Run the **wrong-thing** case from step 2 and watch the test fail.
- Confirm the automator **raises** rather than clicking when the pointer misses, **when
  the target window has vanished**, and **when another window is in front**.
- **Bound the retries.** First failure: re-observe and re-resolve the target. Second:
  change the control method if the evidence points at focus, a stale element, or an
  unsupported pattern. Same failure again: **stop** and report the repeated condition.
  Our own code retried by re-running with no bound and no count of identical failures.
- **Leave a step-level trace**, off by default and switched on to reproduce a flaky
  case — a line per step, with typed text excluded unless explicitly asked for.
- **Write the display scale beside every artefact.** `GetDpiForWindow(hwnd) / 96` into
  the metadata. A capture taken without `all_screens=True` once came back as a blank
  rectangle from the second monitor and was read as "the application did not paint";
  the scale line makes that kind of postmortem obvious instead of guesswork.

Two findings that must not be averaged together:

> **"The action failed" and "there was nothing to act on" are different findings.**
> A twelve-iteration run scored zero on every attempt and the learner concluded that
> no candidate worked. The program had died partway through. Make the missing world
> raise; a missing world is not a failed action.

## Step 9 — What to write into the skill you are building

- the **gate**, as a branch the reader evaluates, with the rejected alternatives;
- the **verified success test**, and the wrong-thing run that proved it fails;
- the **learned values** — or a note that they were measured and will need
  re-measuring when the program changes;
- the **traps that bit**, in the imperative: the next person has the same two hours;
- the **cost**, so the reader knows what a cold start pays;
- one honest line that an automator is a **bet** that the pixels keep meaning what
  they meant, and how that bet can be lost.

## What this skill does not cover

- **Reward design.** What to measure, how to grade it, where the limits are, and
  the rules a reward must satisfy are a separate skill: `design-a-reward`. This one
  needs a reward and does not tell you how to choose one.
- **Non-Windows platforms.** The method transfers; the traps are documented from
  Windows measurements and the script drives Windows. The equivalent on another
  platform has its own versions of the input-layer traps.
- **Vision.** Finding a button by looking at it, rather than being told where to
  look, is a different problem. The coordinates here are measured or learned, not
  recognised.
- **Unattended scale.** One window, one task, one machine. Not a fleet.

## Refining this skill

It is version 0.2.0 and meant to be sharpened. **What follows came from a survey of 105
repositories that ship a `SKILL.md` for interface control, each read in full and tried
here** - nine practices kept, one technique rejected on measurement, one set aside as
belonging to a different problem. The record, with the trial behind every line, is
[references/borrowed-practices.md](references/borrowed-practices.md). Two outcomes were
worth more than any technique: a **defect in our own click code**, found by taking a
rival's rule seriously, and **template matching rejected with a number** - it located
the wrong button at a score of 0.889 against a 0.85 threshold, which is a confident
click on the wrong thing with a number attached that says it was right.

The parts still most likely to be wrong:

- the gate's ordering - a case where a file format existed but driving the interface
  was still right would change it;
- the bandit's action sets - every measured example was small and discrete, so nothing
  here has been tested against a large or continuous space;
- the classification table - six elements in one program is a thin sample;
- the focus guard - it was verified by bringing another window forward on purpose, and
  **not** verified against every way a window can lose focus;
- the vision fallback - rejected for reachable controls, and **not trialled on a
  surface the tree cannot see**, which is the case it is still kept for.

When a use contradicts something written here, **the use wins**: change the file,
add the measurement, and keep the counter-example.
