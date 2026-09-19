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
