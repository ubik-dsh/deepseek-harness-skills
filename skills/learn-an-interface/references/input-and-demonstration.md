# Measuring the input layer, and recording a demonstration

Moved out of `SKILL.md` when the family's token budget was enforced: the skill was over the 5,000-token body the standard recommends, while passing the 500-line check that used to stand in for it.

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

## Step 4b — If a human will show you, record the demonstration

**The cheapest way to learn an interface is to watch someone who already knows it.** The bandit in
Step 6 is for when nobody does. `scripts/screenwatch.ps1` records the demonstration:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/screenwatch.ps1 -Fps 5 -Out "$env:TEMP\demo"
```

What it gives you, and why each part is there:

- **frames**, numbered, at the rate asked for. **Measured**: 5 fps holds a 200 ms interval on a
  4480x1440 desktop, and 25 frames of a 1000x700 region around the cursor come to 2.5 MB for five
  seconds. The default region is a crop around the cursor rather than the whole desktop, because a
  demonstration happens where the hand is, and a full-screen capture at that rate is hundreds of
  megabytes.
- **the cursor, drawn into the frame.** `CopyFromScreen` does not include it, so a screenshot of a
  demonstration shows everything except the thing being demonstrated. It is drawn with
  `DrawIconEx` and then ringed in black, white and magenta, because a real cursor is white on
  white about half the time.
- **`cursor.csv`** — frame, milliseconds, x, y, **buttons**. **This is the part that makes a
  demonstration learnable.** Twenty-five pictures are *watched*; twenty-five coordinates are *read*,
  and the interesting moments fall out of the numbers — where the pointer paused, and where it moved
  faster than a hand can point at anything.
  **The button column was added after a demonstration it could not answer.** An operator performed a
  drag-and-drop reorder — grab, move, release — and the trajectory showed nothing but jumps of two to
  five hundred pixels. At five frames a second **a drag is three to five samples**, and position alone
  cannot tell a drag from the pointer being waved across the screen. The question the recording was
  made to answer was unanswerable from the recording. **A log of where is not a log of what.**
- **a red border and a stamp on every frame**, so a frame from a recording can never be mistaken
  for an ordinary screenshot. That matters when the frames are the evidence.

**The cursor is ringed, not recoloured.** `SetSystemCursor` replaces the pointer for the whole
session and every application, and it is easy to leave behind. A ring is drawn into the picture,
changes nothing on the machine, and disappears with the process.

**The border window is click-through and never activates** — `WS_EX_TRANSPARENT`,
`WS_EX_TOOLWINDOW`, `WS_EX_NOACTIVATE` — so a demonstration can be given straight through it
without the overlay stealing a click or the focus.

**Ask for a demonstration before writing a bandit, and say which you did in the record.** A bandit
over six candidates costs an exploration sweep; a two-minute demonstration costs two minutes and
is given by the one participant who already knows the answer.

## Refining this skill

It is version 0.2.0 and meant to be sharpened. **What follows came from a survey of 105
repositories that ship a `SKILL.md` for interface control, each read in full and tried
here** - nine practices kept, one technique rejected on measurement, one set aside as
belonging to a different problem. The record, with the trial behind every line, is
[borrowed-practices.md](borrowed-practices.md). Two outcomes were
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
