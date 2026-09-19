# The rules of a reward

Eleven invariants. Each one is followed by the measured failure that put it here, in
the form it actually took, because a rule with its scar is remembered and a rule
without one is decoration.

A reward is a claim that *more of this number means more of what I want*. These are
the ways that claim turns out to be false.

---

## R1 — It must be checkable, and it must have been seen to fail

The reward is the success test. If the test can pass while the goal fails, the learner
converges on the wrong thing — smoothly, confidently, and with a rising curve.

**Failure:** a grader asked *"does the output file exist?"*. It passes for a Paint
project file named `picture.png` whose first bytes are `00 00 00 20 66 74 79 70`
rather than `89 50 4E 47`. Every attempt scored full marks and none of them produced an
image.

**Practice:** name the artifact, then check a property only the right artifact has.
Run the check against the wrong thing once and watch the number stay low.

## R2 — It must not be satisfiable without the task

Before anything trains, find the **cheapest** way to score highly — not the intended
way, the cheapest way.

**Failure, in an earlier form of the same work:** the score for both sides was computed
from the same event. The strategy whose payoff arrived later was scored as strictly
worse than one that collected points immediately, and it was bred out within a few
iterations. It had been the correct strategy.

**Practice:** `scripts/probe-reward.py`. Score `do_nothing`, `always_max`, `random`,
`exploit` and the intended policy. If any of the first four beats the intended one, the
reward is wrong and no amount of training will fix it.

## R3 — Every branch must be reachable

For each term: **what sequence of events reaches this line?** Put a counter on it.

**Failure:** a hare was punished for dying. The punishment ran after the armour had
been **restored by the kill**, so its condition (`armour > 0`) was true again by the
time it was tested. The hare was rewarded for being shot, for the whole run.

**Practice:** count every branch. A zero count is a design error, not a tuning
problem. An unreached branch is worse than a missing one because it looks deliberate.

## R4 — The time step must match when the reward arrives

- arrives **on the same step** as the action → no discounting needed;
- arrives **later** → credit assignment, and only then a discount;
- arrives **once per episode** → an episode-level method, or a shaped signal.

**Failure:** an aim offset was learned with `gamma = 0.92` because bootstrapping is
what makes Q-learning Q-learning. The next state was drawn at random regardless of the
action, so the bootstrapped term was the noise of a value estimated from other states.
A hundred iterations oscillated between 0.35 and 0.55. At `gamma = 0` — a contextual
bandit, which the decision actually was — it converged to the optimum from the first
iteration.

**Practice:** ask whether the action changes the next state. If it does not, do not
bootstrap.

## R5 — No safe action may dominate

If the action set holds a fallback — wait, reload, do nothing, decline — it must be
priced for what it costs, or the learner will live in it.

**Failure:** reloading cost a small certain amount and avoided the miss penalty.
Missing is exactly what an **untried** aim looks like, so the safe action beat the
exploration it needed. Two of three mappings were learned; the third was answered
"reload" forever.

**Practice:** price the fallback by the opportunity it consumes, or initialise
optimistically so untried actions look attractive.

## R6 — The units must be comparable

Terms in different units summed without a thought will be dominated by whichever has
the biggest numbers.

**Failure:** a kill bonus of `+5` beside per-hit rewards of `+1` meant that only the
kill mattered; a deviation of a few hits was invisible next to it. The same reward with
the bonus at `+0.01` made the kill irrelevant.

**Practice:** write each term's unit and typical magnitude. If one term is more than
about ten times another, say so on purpose.

## R7 — A bound that is hit is a message

**Failure:** a `panic` parameter was driven to exactly `0.00` and stayed there for fifty
generations. That looks like a lesson — "panicking is useless" — and is weaker: the
optimiser pushed a number into the wall of its range. The honest statement is *"panic
is harmful within the range it was given"*, plus the suspicion that the range or the
axis was wrong.

**Practice:** sample the achieved **inputs**, not the reward. Anything pinned at a
limit is a boundary solution — report it as one. Anything that never moves is a dead
axis.

## R8 — Grade it where grades exist

Binary feedback throws away information that cost attempts to obtain.

**Failure, avoided:** a save-format search used `1.0` for a PNG, **`0.3` for a file
written in the wrong format** and `0.0` for nothing. The `0.3` is what stopped the
learner concluding that TIFF was the answer — a purely binary reward would have called
TIFF a total failure, identical to no file at all.

**Practice:** three to five levels, each corresponding to a genuinely different state
of the world. If you cannot describe the world at 0.6, do not have a 0.6.

## R9 — The noise floor must be known

A wobble in a curve is only a finding if it is larger than the measurement error.

**Failure, avoided:** before believing a swing from 0.35 to 0.55, the standard error
was computed: 120 episodes at roughly 29 000 samples gave **±0.3%**. The swing was
therefore real change in the policy, not sampling noise — which redirected the search
from "the measurement is noisy" to "the algorithm is wrong", where the answer was.

**Practice:** compute it. With independent trials, `sqrt(p(1-p)/n)`. Publish it beside
the curve. An unqualified curve is not evidence.

## R10 — Never average things that must not be averaged

**Failure:** parallel workers each finished their own Q-table and the main process
averaged the tables. Two workers that start together and diverge learn
**contradictory values for the same state**, and the mean of two contradictions is not
a value function. Measured against a frozen opponent — so that nothing but the learner
was moving — the averaged version went 0.45, 0.44, 0.54, 0.51, 0.42: noise wearing a
learning curve.

**Practice:** have each worker report the **change** from the shared table it was
given, and add the mean change to the shared table. The thing being averaged is then a
direction, not a value.

## R11 — Separate the win condition from the progress signal

The thing that ends an episode and the thing that says "getting warmer" are different
numbers, and using one for both hides progress.

**Failure:** a two-agent arena was scored on the win condition. A strategy whose payoff
was delayed looked strictly worse at every measurement, was bred out, and the contest
that had been 111–4 collapsed to 65–64 — the balance was restored by removing the
strategy that was winning.

**Practice:** the win condition decides when to stop. The progress signal decides what
to prefer. A moving average over recent events, not a running total, is usually the
right shape for the second one.

---

## Applying them

`scripts/probe-reward.py` covers R1, R2 and R8 mechanically: it scores a set of probe
policies against your reward. R3, R4, R6, R7, R9 and R10 are instrumentation —
counters, unit tables, error bars, input histograms — and have to be built into the
learner rather than tested from outside.

The three that cost the most in practice were **R1**, **R2** and **R4**. The one that
was hardest to see was **R3**, because a branch that never fires looks exactly like a
branch that is working.
