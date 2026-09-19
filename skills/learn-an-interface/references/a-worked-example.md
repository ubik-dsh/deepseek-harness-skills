# A worked example: the task that needed no learning

The most useful outcome of this skill is not a trained policy. It is **discovering
that none is needed**, and the only way to run the procedure properly is to be willing
to reach that answer.

This is the whole method applied to a second program, from the gate to a graded result,
and the honest headline is that the ladder stopped two rungs above the pixels.

---

## The task

Compute `8573 + 44071` in Windows Calculator. The answer — **52644** — is known in
advance, deliberately, so that the automator can be **graded** rather than admired.

## Step 1, the gate: this is a demonstration, not a need

The first thing the gate says is *do not build an automator for a sum that needs
none*. That verdict is recorded and then set aside for one reason and one only: the
value here is in **evaluating the method**, not in the arithmetic. A task whose answer
is already known is the only kind that can grade an automator at all.

Being explicit about that matters. A skill that quietly ignores its own gate the moment
a demonstration is convenient is a skill whose gate means nothing.

## Step 2, the success test, written before anything else

> The display reads **52644** after the equals key is pressed.

And read back **through the automation tree**, not from a screenshot — because a
screenshot proves only that something was drawn, which is the weak test this skill
exists to warn about. A display value read through the API is a property only the right
result has.

## Step 3, ask the tree before measuring a single pixel

The probe found **73 descendants: 50 Buttons, 7 Groups, 7 Texts**.

Every control had a name **and** a stable identifier:

```
num7Button   num3Button   plusButton    num4Button
num0Button   num1Button   equalButton   clearButton
Display is 0        <-- the display itself, readable
```

Fifty named buttons including the entire number pad and every operator, and the display
exposed as text.

## The verdict the probe produced

**There is nothing to learn and no coordinate to remember.**

- no bandit is needed — the actions are not unknown, they are *named*;
- no coordinate is needed — `Invoke()` does not care where the button is;
- no screenshot is needed — the result is read from the same tree that drove it;
- nothing is coupled to the window position, the display scale, the theme, or the
  number of monitors.

## Step 6, drive it and grade it

```powershell
$element = Find-Id $calc 'num8Button'
$invoke = $null
if ($element.TryGetCurrentPattern(
        [System.Windows.Automation.InvokePattern]::Pattern, [ref]$invoke)) {
    $invoke.Invoke()
}
```

Eleven invocations and a read-back:

```
display before: '0'
  clearButton   -> '0'
  num8Button    -> '8'
  num5Button    -> '85'
  num7Button    -> '857'
  num3Button    -> '8 573'
  plusButton    -> '8 573'
  num4Button    -> '4'
  ...
  equalButton   -> '52 644'

parsed 52644 = expected 52644
RESULT: CORRECT
```

Exit code 0. No cursor, no coordinate, no screenshot, no memory file.

## What this is worth

The comparison is the point. Built the way the Paint automator was built — measure the
button positions, run a bandit over the pixel offsets, keep the counts in a file — this
would have been **roughly ten times the code, coupled to the window position and the
display scale, and not one bit more correct**.

The rung of the ladder did the work, and it was reached because the probe happened
**before** the measuring.

## What it does not show

- **It does not exercise the learning loop at all.** The bandit was not needed and was
  not used, so this example says nothing about whether the learner works. That evidence
  is elsewhere: six exploratory attempts over the rows of a file-type list, then no
  further misses, and a later run that goes straight to the remembered value.
- **It is a first-party modern application.** Calculator publishes an unusually
  complete tree. The probe is cheap precisely so that a program which publishes almost
  nothing is discovered in a minute rather than an hour — and *that* is the case the
  learning loop exists for.
- **`Invoke` was not verified against a disabled or hidden control.** Every button here
  was live. A greyed-out control may accept the pattern and do nothing, which is a
  failure mode this example did not touch.

## The lesson, in one line

**Probe before you measure.** The cheapest step in the method turned out to be the one
that removed most of the work — and it is only cheap if it happens first.

---

# Second example: the hybrid, which is what most real tasks are

Calculator was the pure case - the tree had everything and no coordinate was needed.
Drawing a picture in Paint is the **mixed** case, and most tasks land here: the tree
supplies the controls, and coordinates remain for the one thing the tree cannot
describe.

## What the tree supplied, with no measurement at all

| | how |
|---|---|
| tools and shapes | `press("Oval")`, `press("Rounded rectangle")` - **by name**, through `TogglePattern` |
| all 20 colours | named, with rectangles: **pitch 24 from x 800** |
| the canvas bounds | `ScrollViewer`, 1920x821, **read from the tree** |

The colour row is the part worth dwelling on. An earlier session recovered that pitch
by **scanning pixels for it**, after asking for yellow and being given green. The same
number came straight from the program, and matched the hand measurement exactly.

## What remained coordinates

**Only where in the picture each thing goes.** That is a decision about the drawing,
not a measurement of the program - which is exactly the boundary this skill predicts.

## What the tree could not do

- **`Shape fill` pressed, and offered no selectable options.** The fill mode had to be
  done with the bucket, which is what a person does too.
- **The colour swatches have no selection pattern.** They are clicked - but aimed at a
  rectangle **the tree reported**, re-read every run, rather than at a number measured
  off a screenshot once.

## Two defects found while doing it

**The fill order matters.** The wheels came out as white circles with black lids: the
fill point had landed inside the car body's region, so the bucket flooded only the cap
of each wheel. Drawing the wheels **first** and the body over them gives a whole circle
and hides the half that should be hidden. A flood fill cares about what has already
been drawn, so ordering is part of correctness and not only of appearance.

**The pattern is not guessable from the control type.** `press("Pencil")` failed with
"no pattern" - Paint's ribbon buttons answer to **`Toggle`**, not to `Invoke`, and the
first trial of this work had *already* demonstrated that without it being noticed. The
helper now tries Invoke, then Toggle, then SelectionItem.

## And the learning paid for itself

The save went to the **row the bandit learned in an earlier session**, first try, and
produced a real PNG with no search:

```
saving (first candidate row 553)
row 553: first bytes 89 50 4e 47 0d 0a 1a 0a -> PNG
```

That is the whole point of keeping the counts in a file. Six exploratory attempts once,
and every run afterwards begins at the answer.
