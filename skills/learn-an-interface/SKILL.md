---
name: learn-an-interface
description: Drive a real graphical interface from an agent — a window, a ribbon, a dialog, a canvas — reaching it through the accessibility tree where one exists and learning its coordinates where none does, instead of hard-coding them. Covers the order of preference (API, CLI, file format, library, UI Automation / AX / AT-SPI, macro, and only then pixels), the input calls that actually reach a modern application, how to measure a window so clicks land, a small bandit that finds the unknown detail and remembers it, and the measured traps that make a working automator report success while doing nothing. Ships a runnable learning loop. Use when a task needs a program driven and it has no API, no command-line tool, no scriptable interface and no readable file format; when choosing between UI Automation and screenshot-and-click; when clicks land on the wrong thing or nowhere; when a keyboard or screenshot tool appears to do nothing; when a GUI step must be repeatable without a human hand.
license: MIT
compatibility: Agent Skills standard. SKILL.md is plain text. The script in scripts/ needs Python 3.8+ with Pillow, and drives Windows; the method itself is platform-neutral and the traps are documented so they can be recognised elsewhere.
metadata:
  spec: https://github.com/agentskills/agentskills/blob/main/docs/specification.mdx
  version: 0.2.0
  status: sharpened by a survey of 105 rival skills, each read and trialled — see references/borrowed-practices.md
  measured_on: Windows 11, Paint (Microsoft Store build), two monitors at 2560x1440 and 1920x1440
  verified_against: this harness 0.1.5-rc.2
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

### Open a page in a new tab, never in the one that is in front

**A navigation helper was written the obvious way — `Ctrl+L`, type the address, `Enter` — and `Ctrl+L`
acts on the tab that happens to be active.** The active tab was the harness's own chat page in the
same browser, so the address bar filled with a VK URL and **the conversation the operator was holding
was replaced by a community page.** Nothing was lost, and it was still the agent destroying the
operator's window in order to look at something.

```
Ctrl+T      a new tab, before anything is typed
Ctrl+L      the address bar in it
type, Enter
```

`Ctrl+T` costs one keystroke and cannot overwrite anything. **Reusing the active tab should be an
explicit choice, not the path of least resistance.**

**Why it is easy to get wrong:** the agent talks to the operator *through* a page in the very browser
it is driving, so the most important tab in the session is also the one most likely to be in front and
most likely to be mistaken for a scratch pad. From the inside it is just another tab that looks
unused.

**The general form: a window, a tab or a clipboard the agent did not open belongs to the operator, and
using it in place is an action on their work rather than on the agent's.** The same sentence already
covers the clipboard, and it now covers the active tab. **The failure is invisible from the agent's
side** — the page loads, the task proceeds, and the only person who sees the damage is the one whose
chat disappeared.

### How input is calibrated and measured

**Calibrating a mouse, the two numbering schemes, and the traps in launching a GUI to do it are in [references/calibrating-input.md](references/calibrating-input.md).** Read it before writing anything that has to tell a click from a drag, or that starts a window for a human to interact with.


### An empty reading among a unanimous majority is a miss, not a datum

**When thirteen of fourteen readings come back and the fourteenth does not, suspect the reading, not
the world.** A list whose every row yields a value does not have one row that has no value; it has one
row the pointer missed.

Measured the hard way. Fourteen sidebar rows were mapped by hovering each one and reading the
browser's status bar. **Two came back odd** — one empty, one duplicating the row above — and **both
were written into the skill as findings** before anyone checked them. The rows were 38 px apart, the
pointer was up to 22 px out, and the two findings were a gap between rows and the row above it. The
panel had fourteen distinct addresses all along.

**The shape of the error is what makes it dangerous.** An exception is exactly what a reader
remembers, so a false exception does more damage than a missing reading — and it is
indistinguishable from a true one until somebody measures again. The file cannot reveal it; only an
outside reader can, and in this case the operator did.

So the rule is not "be careful": **an anomaly against a unanimous majority is a measurement failure
until it is re-measured, and re-measuring is not optional.** The clearest form of it came from that
operator, and it is worth keeping in his words:

> *if nine out of ten have it, the tenth is probably "not found" rather than "not there".*

**A silent empty result is the failure mode to design against**, because it looks like an answer. An
error would have been caught; a blank is read as *"the row is not a link"* and written down.

### Two triggers, and neither one replaces the other

The quantitative rule above and *"a surprising finding is a reason to re-measure"* cover different
ground, and it was a mistake to treat the second as the vaguer version of the first. **The first
fires without judgement but needs a majority to compare against. The second fires on a single reading
where no majority exists, and pays for that reach by needing the reader to notice surprise at all.**
Neither subsumes the other, and both belong here.

| the situation | what fires |
|---|---|
| many readings, one odd, the rest agree | **an anomaly against a unanimous majority is a miss** — no judgement needed |
| **one** reading, and it is surprising | **a surprising result is a reason to re-measure, not a sentence to publish** |
| **no majority, and nothing looks surprising** | **neither fires** — and this is the dangerous row |

**The third row is not hypothetical.** `wall.post` returned the same `post_id` twice, identically,
once with a picture attached and once without, and the attachment was dropped in silence. There was
no majority to be odd against and nothing surprising in the reply — **one reading, looking exactly as
it should.** Nothing in either trigger reaches it; only *verify the effect, never the reply* does.
That is why the two rules here are a pair and not a hierarchy, and why neither is a substitute for
looking at the result.


A worked run of the whole method on a second program, where the answer turned out to be
**"there is nothing to learn"**, is in
[a-worked-example.md](references/a-worked-example.md). It is worth reading before
building anything: the probe removed most of the work, and it only does that if it
happens first.

**Measuring the input layer, and recording a demonstration, are in [references/input-and-demonstration.md](references/input-and-demonstration.md).** Read it before writing anything that sends input or asks a human to show you how.

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
