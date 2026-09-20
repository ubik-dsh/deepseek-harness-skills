# Calibrating input, and measuring what a mouse actually sends

Moved out of SKILL.md when it passed the family's 500-line limit — which is the rule working on this skill rather than on somebody else's.

## Reading a recording: three tools, and the reason they ship here

**A description of a method with no tool beside it makes every reader build the tool.** This reference
described how to find a change in a recording and how to look at one, and shipped neither — so an
independent agent given a 1635-frame recording **rebuilt the analysis four times over** (`scan`,
`motion`, `stamps`, `titles`), spending most of an hour arriving where a script would have put it in
one command. **`create-a-skill` says it plainly — anything deterministic belongs in `scripts/`, because
a script gives the same answer twice and costs fewer tokens than regenerated code — and this file broke
its own family's rule.**

| script | what it answers |
|---|---|
| `scripts/read_demo.py <folder>` | **where the hand paused** — the trajectory as numbers, pauses and jumps, before any picture is opened |
| `scripts/find_shift.py <folder> --box X,Y,W,H` | **where the interface moved** — the frames where a screen region changed, largest first |
| `scripts/stack_column.py <folder> --box …` | **what it looks like** — the same screen column from many frames, side by side, with a reference line |

**`read_demo.py` comes first, always.** Twenty-five pictures are *watched*; twenty-five coordinates are
*read*, and the pauses fall out of the numbers. It is the cheapest step and it removes most of the work.

**`find_shift.py` needs `cursor.csv`, and that is the point.** The frames are cropped around the pointer,
so a fixed box means a different part of the screen in every frame; the script maps each one back before
comparing. **Its first version did not, and reported that a region was byte-identical for three minutes
while a page was being driven** — the zeroes were the only clue.

**`stack_column.py` is how a shift is actually seen** rather than inferred: the same screen column from
ten frames minutes apart, with a red line at one fixed screen y. The line crossing the same words in
every column is the answer in one look.


## The recorder writes three things, and the third is the one that shows a drag

`scripts/screenwatch.ps1` produces **frames**, `cursor.csv` and `mouse.csv`, all on one clock:

```
cursor.csv   frame,ms,x,y,buttons          five a second, with the button state
mouse.csv    ms,event,x,y,injected,detail  every event the system delivers
```

**`mouse.csv` comes from a low-level hook (`WH_MOUSE_LL`), not from polling**, because five samples a
second cannot show a drag: it is three to five samples and a click can fall entirely between two of
them. Measured on a real drag against VK's reorder dialog:

```
3662,L-down,700,399,1,
3910,move,733,424,1,          twelve steps, a straight line
...
4345,move,1099,699,1,
4611,L-up,1099,699,1,         held 949 ms across 399 px
```

**Moves are logged only while a button is down.** A low-level hook sees hundreds of moves a second and
logging them all buries the events that matter; a move with the button held *is* the drag.

**A hook needs a message loop on the thread that installed it.** The first standalone version installed
it and sat in a `while` loop with `Start-Sleep` — which is not a pump — so it recorded **nothing**,
reported success and raised no error. In the recorder it works because `Application.Run` is already
there.

## `injected` — because a global hook sees the operator's hand too

**An agent driving a mouse and an operator using one produce the same events, and a global hook catches
both.** A recorded drag looked like it was oscillating between two paths: it was two hands in one log,
and nothing in the file said which was which.

`MSLLHOOKSTRUCT.flags` carries **`LLMHF_INJECTED`**, the system's own statement that an event was
synthesised. The column is that bit, and it is what keeps the agent's input out of the operator's
demonstration and the operator's out of the agent's test. **Without it, a recording of the agent's own
drag cannot be told from a recording of somebody else's.**

## `scripts/drag.ps1` — a drag a browser actually accepts

```
powershell -File scripts/drag.ps1 -FromX 700 -FromY 400 -ToX 1100 -ToY 700 -Steps 20 [-NoRelease]
```

Four things it does that a naive drag does not, each from a measured failure:

- **`SendInput` only.** A drag through the legacy `mouse_event` changed exactly zero pixels.
- **`ABSOLUTE | VIRTUALDESK`, with a move event per step.** Plain `SetCursorPos` is right about monitors
  and wrong about drags: no move events, so press and release land in one place.
- **Intermediates, not a jump.** A browser decides a drag has begun from movement past its threshold,
  and one 400-px jump is read as a click that teleported.
- **`-NoRelease` holds the button down**, which is the only way to look at step 5 of the logic — *check
  the target SHOWS it will accept.* Against VK's menu dialog, holding showed the row greyed and lifted
  with its label drawn twice: a ghost and the dragged copy.

**And release the button whatever happens.** A run that stops while holding leaves the operator's mouse
pressed; the first attempt here did exactly that and needed a separate call to put it up.

## What a working drag looks like, end to end

Against VK's `Порядок в меню`, 2026-09-20, on a menu ordered `вукер`, `псваиртва`:

```
1  find the source by name          вукер, the first row
2  find the target                  the second row's position
3  press its handle                 (1099, 735)
4  move in steps                    twenty, with the button down
5  CHECK IT SHOWS IT WILL ACCEPT    grey lifted row, label drawn twice   <- looked at, while holding
6  release
7  verify                           the page reads псваиртва, вукер - and it persisted after Сохранить
```

**Step 5 is what makes it verified rather than hoped for; step 7 is what makes it a result rather than a
gesture.**

### Record the LOGIC of an interaction, not the coordinates of one

**A calibration log is a record of instances. A skill needs the rule.** The operator made this
distinction after watching a drag land at `754,235` in a log: the number proves the gesture happened and
is worthless as knowledge, **because where to drop depends on the situation.**

What belongs in a skill is the shape:

```
1  find the SOURCE            by name, by row, by what it says - not by a pixel
2  find the TARGET            the same way
3  press the source's handle
4  move in STEPS, not one jump
5  check the target SHOWS it will accept   a highlight, an insertion line, a lifted row
6  release
7  verify the result          the order changed, the object is where it was put
```

**Step 5 is the one that gets skipped and the one that makes a drag reliable.** A drop target is
identified by its **state**, not by its coordinates: in VK's menu reorder the row you drop onto is the
one whose position the dragged row will take, and it says so before the release. **Reading that state is
what turns a guessed coordinate into a verified action.**

**So the coordinates in this family's files are a starting point and never the method.** Where they are
written down they carry a warning to re-measure, and the warning is not a formality: the same page moved
a row by 18 px between two sessions, and a whole map of fourteen rows was recorded wrong from guessed
positions.

### A coordinate read off a magnified crop is not a screen coordinate

**The crop is scaled, and the model is shown a scaled copy of the scaled crop.** So a number read from
the picture in front of you passes through two factors before it means anything, and both are easy to
forget:

```
the crop was magnified by N        so a distance in the picture is N times a screen distance
the harness downscales the image   so the preview may be a third size again
```

**An independent agent lost roughly half a session to this**: its first `Сохранить` click landed
**123 px** off, from a coordinate read off a magnified crop. **Measure in the raw capture**, and compute
the mapping explicitly — `absolute = origin + magnified / N` — rather than reading a position by eye.
**Or do not measure at all**: find the control by its own pixels, or ask the page for its geometry.

**And a dialog is animated.** A coordinate taken in the first moment after it opens is stale: the panel
was still moving and the number describes a frame that no longer exists. **Wait for it to settle** —
about four seconds was enough here — before measuring anything inside it.

**Both of these are the same mistake as a remembered coordinate**: a number that was true of a
different picture.

**The distinction has a use in the other direction too: a calibration SHOULD record instances.** Pixels,
timings and both endpoints are exactly how a numbering scheme gets established — `754,235` is why the
drag could be told from a stray click. **Instances to measure with; rules to write down.**

### Calibrate the mouse with a game, not with a log

**A log says what the system received. It cannot say whether what arrived is what the hand did.** So
give the operator a window with a known gesture per step and a tick when it lands: `scripts/mouse_game.py`
is one, and it is the tool that produced the table below.

```
python scripts/mouse_game.py --out game.csv --lang ru
```

Nine steps: left-click a cube, double-click it, right-click, middle-click, both side buttons, the wheel
each way, and a drag from the left half of the window into the right. The whole checklist is visible,
the title bar names the next step, and every raw event is written to the log — **including the ones the
game does not need, because the point is to find out what the mouse actually sends.**

**It settled a question no documentation could**, because there are two numbering schemes and they
disagree. Measured on one Windows 11 machine, with the Win32 hook and tkinter watching the same hand:

| gesture | Win32 hook (`mousewatch.ps1`) | tkinter (`mouse_game.py`) |
|---|---|---|
| left | `L-down` / `L-up` | `Button-1` |
| **right** | `R-down` / `R-up` | **`Button-3`** |
| **middle** | `M-down` / `M-up` | **`Button-2`** |
| side, back | `X-down X1(back)` | **`Button-4`** |
| side, forward | `X-down X2(forward)` | **`Button-5`** |
| wheel away | `wheel +1` | `delta=+120` |
| wheel toward | `wheel -1` | `delta=-120` |
| double click | two press pairs | two `Button-1` within ~130 ms |
| drag | `L-down` … `L-up` | `Button-1` … `B1-release` |

**The two schemes are not interchangeable and neither is guessable from the other.** A double click was
123 ms between release and the next press; a drag was 302 ms across 572 px, with both endpoints.

**And tkinter binds only `Button-1`..`Button-5` on this build** — the game records `BOUND
buttons=1|2|3|4|5` at startup. The first version awaited the side buttons as `Button-8` and `Button-9`,
which is the numbering some platforms use and which tkinter here **refuses to bind at all**: the game
sat at six of nine, ticking nothing, while the operator pressed exactly the right buttons. **It looked
like the window closing. It was the window not listening.**

### A GUI an agent starts must raise itself

**A window opened by an agent appears BEHIND whatever is in front**, because nothing gave it focus. The
calibration game was launched from a background job and came up underneath the browser: the operator saw
nothing and the run could not start. `-topmost`, `lift()` and `focus_force()` at startup, and
`SetWindowPos` afterwards if it still parks off-screen.

**And launch it as a managed background job, not as a shell job inside a command that then exits.**
PowerShell kills the jobs it owns when their parent goes away: the first launch used `Start-Job` inside
a command that returned immediately, and the game died a few seconds later — which reads exactly like a
crash after the first click.
