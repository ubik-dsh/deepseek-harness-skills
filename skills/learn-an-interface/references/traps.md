# The traps, all of them measured

Each one was found by running something and reading a number. None by reading the
code. They are in the imperative on purpose: every one of them cost between twenty
minutes and two hours, and the next reader has the same two hours to lose.

---

## Input

### Use `SendInput`. The legacy calls do not reach a modern application.

Measured on Paint: a drag across the canvas through **`mouse_event` changed exactly
zero pixels**. The identical drag through `SendInput` left a line. `keybd_event` is
the same trap for keys — Escape and Ctrl+S were seen, **`Ctrl+Z` never was**, so an
undo that had visibly happened (the stroke was gone from the canvas) was measured as
not having happened at all, and the classification reported "the stroke persists"
for something that had already been undone.

What makes this expensive is that the old calls **still work for some things**.
They move the pointer, they open menus, they press Escape. So the failure looks like
a logic bug in your own code, and you go looking there.

```
SendInput        mouse and keys, both, always
mouse_event      no
keybd_event      no
```

### An absolute move without `VIRTUALDESK` goes to the wrong monitor

`mouse_event` with `MOUSEEVENTF_ABSOLUTE` addresses the **primary monitor** unless
`MOUSEEVENTF_VIRTUALDESK` is also set. On a two-monitor desktop it threw the cursor
942 pixels back onto the other screen — and the click that followed landed in
somebody else's browser window. That is a real window, on a real desktop, belonging
to a real person.

### `SetCursorPos` alone gives a drag no move events

It is correct about monitors, and it fixed the clicking. But it does not generate
the move events an application needs to see a **drag**: press and release land in the
same place, so a drawing program records a dot, and a one-pixel dot on white is below
any sensible threshold. The stroke was drawn correctly and measured as nothing.

`SendInput` with `MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE | MOUSEEVENTF_VIRTUALDESK`
is right about both. Normalise to the virtual desktop:

```python
nx = int((screen_x - virtual_left) * 65535 / (virtual_width - 1))
ny = int((screen_y - virtual_top) * 65535 / (virtual_height - 1))
```

### Verify the pointer arrived, before pressing anything

```python
user32.SetCursorPos(...)          # or SendInput
user32.GetCursorPos(byref(landed))
if abs(landed.x - screen_x) > 2 or abs(landed.y - screen_y) > 2:
    raise RuntimeError("pointer did not arrive - refusing to click")
```

Four lines. They convert "I clicked an unknown place on a live desktop" into a
stopped run with a message. On a desktop that belongs to someone, this is not
optional.

### Typing goes through the keyboard layout

`VkKeyScanW` answers with the key that produces the character **in the current
layout**. On a Russian layout, typing a folder path with backslashes produced
`\\W/Y\/L/.` and the dialog answered *"The file name is not valid."*

Send each character as a scan code with `KEYEVENTF_UNICODE` and the layout stops
mattering:

```python
send_key(0, scan=ord(ch), flags=KEYEVENTF_UNICODE)          # press
send_key(0, up=True, scan=ord(ch), flags=KEYEVENTF_UNICODE) # release
```

### Slow the drag down

A stroke sent in one frame is a stroke most programs record as a single point.
Around 30 ms per point, and a pause of ~100 ms after the button goes down. Fast
enough to look like a person, slow enough that the path is seen as a path.

---

## The world around your window

### A modal prompt blocks everything and reports nothing

One attempt saved a file with the wrong extension. The next attempt hit an
**overwrite prompt**, and every subsequent attempt was blocked by that prompt while
the log said *"nothing was written"*. Six consecutive attempts were spent learning
nothing, and the obvious reading — "no candidate works" — was wrong.

Before each attempt, **dismiss anything modal**. After each attempt, check whether a
dialog is still standing.

### Dismiss by matching titles loosely

A prompt titled `Confirm Save As` is not the `Save as` dialog, and matching exactly
will find neither. Match case-insensitively on a few words, and press Escape rather
than choosing a button — Escape cancels, which writes nothing.

### "The action failed" and "there was nothing to act on" are different findings

A twelve-iteration run scored **zero on every attempt**, and the learner concluded
that no candidate in the list worked. Paint had died partway through the run; the
harness was gone, not the candidate. Averaging those two together teaches the wrong
lesson with full confidence.

Verify the target exists **before** judging the action, and **raise** when it does
not. Never record a zero for an attempt that never happened.

### The program can die between attempts

Related to the above, and it happened for no visible reason. Check the window still
exists at the start of every iteration; if it does not, relaunch or stop — but do not
keep recording.

---

## Drawing and choosing

### Shapes are drawn from corner to corner

A tool that inscribes its shape in the drag rectangle draws **nothing** when the drag
is a straight line along one edge. A roof triangle was dragged along its own base —
same `y` at both ends — so it was a triangle of zero height.

The costly part is what came next: the fill that was supposed to go inside it landed
on bare canvas and **flooded the entire page** one colour. The visible symptom was
"the whole picture is red", which points at the fill, not at the missing triangle.

Give every shape a drag with both width and height.

### Fills need a point genuinely inside, and the bucket is not where you think

The bucket was clicked at `(285, 127)` — the **gap between the pencil and the
eraser** — for several runs. Every house came out as an empty outline, and the
conclusion drawn was "the shape tools draw outlines only". They do; but the bucket
was never clicked at all. Measured, it is at `(309, 92)`.

Scan the toolbar for the icon rather than estimating it, exactly as for a palette.

And the fill point matters: a click that lands on the outline, or outside the shape,
floods the whole canvas. Compute an interior point from the geometry — for a
triangle, the centre of mass, not the centre of the bounding box.

### A state that is already set does not change when it is set again

The classification probe clicked a tool that a **previous run had left selected**,
saw no change, and reported "no effect" for something that works perfectly. The same
happened to a colour swatch.

Reset before probing, or probe a **change** rather than a state — click two different
colours and check that each click lands, instead of clicking one and asking whether
the screen moved.

---

## Measurement

### Read coordinates from the window, never from a scaled screenshot

A capture shown at 1086 wide from a window of 1936 wide: every click 40% short, and
the diagnosis "the pencil does nothing" instead of "the aim is wrong". See
[measuring-a-window.md](measuring-a-window.md).

### A capture can be of the wrong monitor

`ImageGrab.grab` without `all_screens=True` captures the primary monitor only. A
window on the second screen came back as a blank white rectangle, and the first
conclusion was that the application had not painted.

### The dark-pixel scan needs the right row

Scanning for icon positions at `y = 90` found **one** run where there were seven
icons. The icons are thin outlines; at that row most of them have no dark pixels.
Scan several rows, or scan a band, and compare.

---

## The habit underneath all of them

Every trap here produced a **plausible wrong diagnosis** — including the decision to
measure something that had a name.

| the number said | the truth was |
|---|---|
| "the pencil does nothing" | the click was 40% short |
| "the tools draw outlines only" | the bucket was never clicked |
| "no candidate in the list works" | the program had died |
| "the stroke persists" | the undo happened and was not seen |
| "the application did not paint" | the capture was of the other monitor |
| "the whole page is red" | a triangle of zero height |
| "yellow is green" | the palette pitch was 24, not 28.6 |
| the palette pitch had to be measured | **the palette is a list of named colours** — the names were in the automation tree the whole time |

That last row is the one to sit with. Every other entry is a measurement done badly;
that one is **a measurement that did not need doing at all**, and it cost more time
than any of the others. Before measuring pixels, ask the program what it has:
[accessibility-first.md](accessibility-first.md).

So when a measurement says something surprising, the first hypothesis is not the
program and not the logic. **It is the measurement.** Draw the points on a picture
and look at them; count the colours; print the raw number instead of a verdict;
capture before and after and diff them.

That is not caution, it is arithmetic. Seven out of seven.
