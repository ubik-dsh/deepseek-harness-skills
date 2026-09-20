# Calibrating input, and measuring what a mouse actually sends

Moved out of SKILL.md when it passed the family's 500-line limit — which is the rule working on this skill rather than on somebody else's.

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
