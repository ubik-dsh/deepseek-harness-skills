# What was taken from other skills, and what was rejected

A survey of GitHub found **105 repositories shipping a `SKILL.md` for interface
control** — the practice is not new and this skill is not the first. So the useful
question is not "does this exist" but "does someone do it better, and does their way
survive a trial on our case".

This is the record. Every entry was read in full, tried on Paint, and kept or rejected
on the measurement, not on the reputation of the repository it came from.

Two things came out of it that are worth more than everything else: **a real defect in
our own click code**, and **a popular technique that failed its trial**.

---

## Kept

### The automation tree, above pixels — the gap in our own gate

**From:** `youngjunning/windows-app-automation`, `affaan-m/ECC` (`windows-desktop-e2e`),
`BanmaXM/operate-ui-by-screenshot`, `alchaincyf/huashu-mac-use`.

Our gate went API → CLI → file format → library → macro → pixels, and skipped the one
interface that sits between a library and a macro. **Trial on Paint:** `Pencil` found by
`automationId='PencilTool'` and toggled `Off → On` with no cursor; the palette turned
out to be a list of named colours (`Yellow`, `Red`, `Green`, …) that an earlier session
had spent a long time measuring by scanning pixels for its pitch.

Full trial: [accessibility-first.md](accessibility-first.md).

### The locator ladder

**From:** `affaan-m/ECC`.

```
AutomationId  >  Name (text)  >  ClassName + index  >  XPath
  (stable)        (readable)      (fragile)           (last resort)
```

**Trial:** confirmed — `PencilTool` and `EraserTool` were found by identifier, while
`Save as` and `Fill with color` were **not** found by their names. Identifiers first,
names second, and enumerate rather than assume.

### Verify the target window is in front before pressing — **this was a defect in our code**

**From:** `youngjunning/windows-app-automation` — *"bring the target window forward and
set focus explicitly"*, under the diagnosis *"typing goes to the wrong place"*.

Our `click()` moved the pointer, checked that the pointer arrived, and then pressed.
It never checked that the window under the pointer was the one that would **receive**
the input — and `SendInput` goes to whatever is **focused**, not to whatever rectangle
the arithmetic pointed at.

**Trial, and this is the incident:** a run moved the Paint window and clicked a learned
coordinate without activating first. The foreground switched to the user's browser.
The click had gone into somebody else's window — the **second** time in this work that
an unverified click reached a window nobody intended.

The fix is four lines, and the guard now names the window it is protecting:

```
REFUSED: refusing to click: 'Яндекс Браузер' is in front, not 'Paint' - activate the window first
```

Two implementations traps inside those four lines, both worth recording:

- **`ctypes` truncates handles.** `GetForegroundWindow` and `GetAncestor` return
  64-bit handles and ctypes assumes `int` for an unprototyped return. A truncated
  handle never compares equal to a real one, so the first version of the guard
  **passed everything silently**. `restype = wintypes.HWND` for both.
- **There are two guards and the pointer one fires first.** With the window
  *minimised* its rectangle becomes the iconic placeholder (`-31734, -31901`), so the
  pointer check refuses before the focus check ever runs. Both are needed; the order
  is not a design choice.

### Patterns instead of visual input

**From:** `youngjunning/windows-app-automation` — *"prefer `SetValue` over visual
typing"*.

**Trial:** `TogglePattern.Toggle()` changed Paint's tool state with no cursor and no
typing at all. The same logic covers text: a `ValuePattern.SetValue` cannot go through
the keyboard layout, which is the trap that made a folder path come out as `\\W/Y\/L/.`.

### Idempotence: set a value rather than flip a state

**From:** `youngjunning/windows-app-automation` — *"prefer `set to value` over `toggle`,
opening a known route over repeated `Back`, and selecting an identified item over
arrow-key counts"*.

**Trial, already on the record:** our classification probe reported "no effect" for a
tool that a previous run had left selected, and for a colour swatch that was already
the current colour. **A state that is already set does not change when it is set
again.** This rule names the cause and the fix: set a value, and measure the value, not
the delta.

It also explains a failure from the same session — a search that pressed the down arrow
eight times to select a row in a list. Counting keystrokes is exactly what this rule
says not to do, and it did not work.

### Bounded retry

**From:** `youngjunning/windows-app-automation`:

> 1. first failure: re-observe and re-resolve the target;
> 2. second failure: change the control method if evidence suggests focus, stale
>    element, or unsupported pattern;
> 3. same failure again: stop and report the repeated condition.

**Kept as a rule.** Our code retried by guessing and re-running, with no bound and no
record of how many times the same thing had failed.

### Evidence chosen before the action

**From:** `youngjunning/windows-app-automation` — a table pairing each *requested
result* with *strong evidence* for it: a setting change is proved by reopening the
setting, a save by application confirmation **plus** a file read-back and size.

Ours says "write the success test first" and gives the three ways a weak test fails.
Theirs is stronger because it pairs the result with the evidence rather than leaving
the choice open, and it carries the rule that **non-visual claims need non-visual
evidence** — a file, a log, a process state, not a screenshot.

### A step-level trace, off by default

**From:** `affaan-m/ECC`.

A JSONL line per step, enabled by an environment variable, with a second variable to
include typed text (and an explicit warning not to use it on credentials). We wrote
screenshots and no structured trace, so a failure could be looked at but not grepped.

### Record the display scale beside every artefact

**From:** `affaan-m/ECC` — write `GetDpiForWindow(hwnd) / 96` into the artefact
metadata, so a postmortem is obvious instead of guesswork.

Cheap, and this work has an adjacent scar: a capture taken without `all_screens=True`
came back as a blank rectangle from the second monitor and was read as "the application
did not paint".

### The annotated match overlay — ours, confirmed independently

**From:** `affaan-m/ECC`'s `debug_match`, which draws the best-match rectangle and its
score back onto the screen, green for pass and red for fail.

This is the same habit this skill's measurement method is built on — **draw the chosen
points onto a capture and look at it** — arrived at independently, and theirs adds the
score and the pass/fail colour. Theirs is better; the colour is taken.

---

## Rejected, with the trial

### Template matching as the pixel fallback

**From:** `affaan-m/ECC` — `cv2.matchTemplate` with a confidence threshold (0.85),
warned in the same document as fragile against display scaling, theme changes and
occlusion.

This was the most tempting idea in the survey, because it *recognises* the target where
we *remember* where it was. So it was trialled properly: cut the Pencil button out of a
capture, then find it again.

```
in the same window           found at (266, 99)    score 1.000
on the full desktop          found at (2818, 91)   score 1.000   (absolute, two monitors)
after moving the window      found at (306, 139)   score 0.889   <-- the ERASER
```

**It found the wrong control with a score above the threshold.** The Pencil's
neighbouring button matched at 0.889 against a 0.85 bar — a **false positive inside the
confidence margin**, and the failure mode is the worst one available: a confident click
on the wrong thing, with a number attached that says it was right.

The move that caused it was worth 260 pixels horizontally and 90 vertically. Nothing
exotic.

And the follow-up is the part that decides it: **our stored coordinate is
window-relative and re-resolved against the window rectangle on every click**, so it
survived the same move with no template at all. Tested: after the move, clicking the
learned coordinate selected the tool, confirmed through the automation tree — once the
missing focus check was fixed.

So the technique was rejected for the role it was proposed for. It is not deleted from
the world: it remains the right answer for a surface where the tree is silent **and**
the target cannot be expressed as a window-relative position — a full-screen game, an
image inside a document, a control that moves within its own window. The warning is
recorded with it: **check the margin, not just the threshold**, and draw the match back
onto the screen before trusting it.

### The "notes after learning a workflow" loop

**From:** `BanmaXM/operate-ui-by-screenshot` — its maintenance reference, on how to
update the skill after a new UI workflow is learned.

Kept as a *habit* — record what was learned — and rejected as the mechanism, because it
is a human writing prose after the fact. Ours is a bandit with counts in a file and a
verified reward: six exploratory attempts and then no further misses, and a later run
that goes straight to the remembered value. The note is the weaker version of the same
intention.

### Sandboxing and workspace isolation tiers

**From:** `affaan-m/ECC` and `majiayu000/claude-skill-registry` — filesystem isolation,
Windows Job Objects, Windows Sandbox, and a strong emphasis on containment and
security for computer-use agents.

**Not taken here, and deliberately.** Both are right *for their problem*: unattended
agents running untrusted flows on machines that matter. This skill is written for a
task an agent drives on its own desktop with a human present, and the safety that
matters at that scale is different in kind — **verify before you press, refuse to click
into the wrong window, put the cursor back**. Adding a container layer would be
answering a question this skill is not asking.

Recorded rather than dismissed, because the moment this skill is used unattended on a
machine that is not the agent's own, that material becomes the starting point.

---

## The shape of the result

Of the practices tried: **nine kept, one rejected on a false-positive measurement, one
kept as a weaker version of what we already had, one set aside as belonging to a
different problem.**

The two most valuable outcomes were not techniques to add. One was a **defect found in
our own code** by taking a rival's rule seriously — and the defect was a click reaching
a stranger's window, which no amount of feature-adding would have found. The other was
**a technique rejected with a number**, which is the only kind of rejection that stays
rejected.
