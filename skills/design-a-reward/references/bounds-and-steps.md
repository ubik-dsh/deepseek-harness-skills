# Limits and steps

How to decide what range a parameter may take, how finely it may move, and how to tell
when a limit is telling you something. These are the two settings that decide whether a
search can find anything at all, and both are usually chosen by guessing.

---

## Part 1 — Limits

### A limit is a claim about the world, not a convenience

Every bound you write says *"the useful value lies in here"*. If that claim is false,
the search will find the wall and stop, and the result will look like a lesson.

**Measured.** A hiding agent had a `panic` parameter with the range `[0, 1]`. The
optimiser drove it to **exactly 0.00** and left it there for fifty generations. The
obvious reading is *"it learned that panicking is useless"*.

The honest reading is weaker, and more useful:

> panic is harmful **at or above zero**, within the range it was given.

A value pinned against a bound is a **boundary solution**, and a boundary solution is a
question about the parameterisation. Three things it can mean, in order of likelihood:

1. **the range is wrong** — the optimum is outside it, and the search is pressed against
   the edge trying to get there;
2. **the axis is wrong** — the quantity does not matter at all, and the optimiser parked
   it somewhere arbitrary (the wall is just the nearest stable place);
3. **the parameterisation is wrong** — `panic` bounded at zero cannot express
   *actively avoiding* a thing, which may be what the world wanted.

### How to find the limits rather than guess them

1. **Run once with a wide range** and record the range the learner actually visits.
   That span is better evidence than any reasoned guess.
2. **Look at the achieved inputs**, not the reward. Print a histogram of every parameter
   at the end of a run. This is the single most informative diagnostic in this
   document, and it takes six lines.
3. **A value at a bound gets reported as a bound.** Not as a finding about the world.
4. **A value that never moves is a dead axis.** Either the reward does not depend on it
   (make a term that does, or delete it), or the step is too small to escape the
   starting point.
5. **A value that visits its whole range** is either genuinely unconstrained, or the
   step is so large the search is sampling noise. Check whether the reward changes
   across that span.

```python
# after a run, this is worth more than the reward curve
for name, values in achieved.items():
    low, high = min(values), max(values)
    at_wall = sum(1 for v in values if v in (low, high)) / len(values)
    print(f"{name:16} visited [{low:.3f}, {high:.3f}]  at a wall {at_wall:.0%}")
```

A parameter at a wall 100% of the time is pinned. At a wall 40% of the time it is
bouncing. At a wall 0% of the time it is free — and if its range is much wider than what
it visited, the range is too wide and the steps are being wasted.

### Limits on actions

The same question for a discrete action set: is the action that should win actually
**available**?

**Measured.** An aim-offset search offered offsets of `-2, -1, 0, 1, 2`. The true bows
for three situations were `0.0`, `1.0`, `2.0`. All three were reachable. Had the widest
bow been `2.8` with the same action set, the best achievable would have been `2` — a
permanent ceiling caused by a bound, which no amount of learning removes.

**Practice:** for each state, check the optimal action is inside the action set. If it
is not, the ceiling is the bound and the curve is flat for a reason that has nothing to
do with learning.

---

## Part 2 — Steps

### Match the step to how the reward responds

| the reward's response | the step |
|---|---|
| a value changes smoothly as the parameter moves | a small step, or a gradient method |
| the value is unchanged until a **threshold** is crossed | a step at least as large as the distance to the threshold |
| the value is a **choice between discrete outcomes** | a discrete action set, not a step at all |

**Measured, and it is the most expensive mistaken step in the project.** A test for
whether an aircraft was moving looked at the jump in position between two frames. The
first versions used a **fixed or relative jump threshold**, and the measured accuracy
was 50% — a coin toss. The reason: **a jump is a discontinuity, not a speed.** For a
fast-moving target the per-frame displacement is large for every frame, so a threshold
on displacement fires on every frame; for a slow one it never fires. The fix was to
look for the *change* in displacement, and accuracy went to 0.95 static and 0.91 for a
moving target.

The step was the wrong shape for the signal, and no tuning of its size could have
helped.

### Step sizes for a hill climb

Measured and workable, offered as an observation rather than a rule:

```
accept  -> step *= 1.25
reject  -> step *= 0.8
start   -> about 15% of the parameter's range
propose -> value + gauss(0, step)
```

Two properties make this behave:

- **the step remembers.** Growing on success and shrinking on failure lets the search
  travel a long way early and settle finely late, without a schedule;
- **it proposes from the current value, not the template.** The first version multiplied
  the *initial* value by a random factor every rewrite, so nothing accumulated: after
  fifty generations the parameters looked exactly as random as the first. Only the
  choice of strategy was being learned, and weakly. Proposing from the **current** value
  is the difference between a search and a series of unrelated samples.

**Check this explicitly.** Read the generated parameters at generation 1 and at
generation N. If they are statistically indistinguishable, the search is not
accumulating, whatever the score says.

### Step sizes for a discrete action set

There is no step; there is a **count**.

- **ten candidates** converge in about ten attempts, which is the practical ceiling for
  anything costing a real interaction;
- **around twenty** is the most that has been seen to converge in a reasonable budget;
- **a hundred** costs a hundred attempts before learning starts.

Derive the candidates from the measurement rather than the imagination. In the measured
case, rows of a menu were known to be about eight pixels apart, so candidates were
placed eight apart around the estimate — six of them covering the plausible region.

### Exploration vs exploitation, without a second knob

`epsilon` is a knob. UCB1 is not:

```
score = mean reward + sqrt(2 * ln(total pulls) / pulls of this action)
```

Try everything once, then prefer the best bound. The square-root term **is** the
exploration, and it shrinks by itself as samples accumulate. Deterministic, no schedule
to tune, and the reasoning for a choice can be read off the numbers afterwards.

Use `epsilon` when the action space is large or continuous and UCB1's "try everything
once" is unaffordable — and then epsilon must **decay**, or the policy never settles.

---

## Part 3 — What to write down

- the **configured range** of every parameter and every action;
- the **achieved range**, measured after the run;
- which parameters were **at a wall**, and the percentage of samples;
- the **step rule** and its two factors;
- for a discrete set, **why those candidates and how many**;
- the check that the **optimal action is reachable** in every state.

And the sentence that makes it readable: *"this parameter was pinned at its upper bound
for the whole run"* is a different finding from *"this parameter converged"*, and only
one of them is a statement about the world.
