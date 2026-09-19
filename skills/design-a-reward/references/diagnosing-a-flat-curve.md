# A curve that will not rise

An ordered checklist. Ordered by what actually bit, cheapest and most likely first,
with the code shape of each defect so it can be recognised rather than reasoned about.

All five training defects in one project are on this list, and **every one was found by
running something and printing a number**. None by reading the code, and none by
adjusting hyper-parameters — four rounds of tuning produced nothing, and the fifth
finding was not a tuning problem at all.

---

## 0. Before anything: what does the curve actually look like

Three shapes, three different diagnoses. Get this right first.

| shape | most likely |
|---|---|
| flat at a low value | the reward is not reaching the learner, or the learner is stuck on a safe action |
| flat at a **good** value | it converged. Check the ceiling by hand — maybe it is right |
| oscillating in a band | the target is non-stationary, the step is too large, or the algorithm does not match the structure |
| rising then falling | two learners competing, or the reward has a short-term term that dominates an eventual one |

**Compute the noise floor before believing any of it.** `sqrt(p(1-p)/n)` for a
proportion. Measured: 120 episodes, ~29 000 samples, ±0.3%. A swing from 0.35 to 0.55
was therefore real change in the policy — which ruled out "the measurement is noisy"
and pointed at the algorithm, where the answer was.

An oscillation that is larger than the noise floor is a **policy** oscillation. That is
a very different sentence from "the metric is noisy".

---

## 1. Is the reward being computed at all?

Put a counter on **every branch** of the reward function, and print the counts.

**The defect this catches:** a hare was punished for dying, and the punishment tested
`armour > 0` *after* a kill had restored the armour. The branch never fired once in a
whole run. The hare was rewarded for being shot.

```python
COUNTS = collections.Counter()

def reward(...):
    if killed_now:
        COUNTS["kill"] += 1
        return -10.0
    COUNTS["alive"] += 1
    return 1.0
```

A zero count is a design error. Do not tune around it.

## 2. Is the world still there?

**The defect this catches:** twelve attempts scored zero, and the learner concluded that
no candidate in its action set worked. The program it was driving had died partway
through. Nothing was wrong with the reward or the search — the environment was gone.

Distinguish the two verdicts explicitly, and make the missing world **raise** rather
than return a low reward:

```python
if Window.find("Paint", timeout=1) is None:
    raise RuntimeError("the target vanished - the run is void, not unsuccessful")
```

Averaging "the action failed" with "there was nothing to act on" teaches the wrong
lesson with full confidence.

## 3. Is the state a real transition?

This is the most common way a correct-looking Q-learning implementation is wrong.

**The defect this catches:**

```python
# wrong: not a transition, noise injected into the target
nxt = state(armour, shots, random.choice((-1, 0, 1)))
target = reward + gamma * max(Q[nxt].values())
```

`random.choice` of the possible next states is not what happens next. The unknown part
of the successor must be **averaged** out of the target:

```python
# right: the unknown is averaged, the known is exact
def expected_next_value(table, armour, shots, actions):
    return sum(
        max(table.get(state(armour, shots, lean), {}).values(), default=0.0)
        for lean in (-1, 0, 1)
    ) / 3
```

The first version moved the return from 69.6 to 64.8 over a hundred iterations, which
is to say nowhere.

## 4. Does the algorithm match the reward's structure?

Ask: **does the action change what happens next?**

- if **no** → it is a contextual bandit. Use no discount, and the estimate is a running
  average of the reward earned in that state.
- if **yes** → a sequential method, and a discount means something.

**The defect this catches:** an aim offset was learned with `gamma = 0.92`. The next
state was drawn at random whatever was fired, so the bootstrapped term contributed the
noise of nine other states and nothing else. The curve oscillated between 0.35 and 0.55
for a hundred iterations. At `gamma = 0` it converged from the **first** iteration:

```
gamma 0.92    0.484  0.547  0.503  0.447  0.444  0.498  0.500  0.473  0.557  0.354
gamma 0.00    0.594  0.569  0.577  0.588  0.567  0.595  0.570  0.577  0.586  0.591
```

A learning curve that oscillates is sometimes not a tuning problem at all.

## 5. Is a safe action eating the exploration?

**The defect this catches:** the action set contained "reload" at a small certain cost.
Missing is what an **untried** aim looks like, so reloading beat the exploration that
would have found the good aim. Two of three mappings were learned; the third was
answered "reload".

Symptoms: one action takes the large majority of pulls, and the states where it is
chosen are exactly the states where exploration was needed.

Fixes: price the fallback for the opportunity it consumes; or initialise untried
actions optimistically so that trying them is what reduces the estimate.

## 6. Is the scale right?

Write each term's unit and typical magnitude, side by side.

**The defect this catches:** a kill bonus of `+5` against per-hit rewards of `+1`. Only
the kill could affect the ordering; a difference of three hits was invisible. The same
reward with the bonus at `+0.01` made the kill irrelevant and the hits everything.

If one term is more than about ten times another, be able to say why.

## 7. Are you averaging something that must not be averaged?

**The defect this catches:** parallel workers each finished a Q-table and the main
process averaged them. Workers that start together and diverge learn **contradictory
values for the same state**. Measured against a frozen opponent — so that only the
learner was moving — the averaged version read 0.45, 0.44, 0.54, 0.51, 0.42, 0.61:
noise in the shape of a learning curve.

Average the **change** from a shared table, not the finished values:

```python
delta  = {s: {a: v - base[s].get(a, 0.0) for a, v in row.items()} for s, row in learned.items()}
merged = base[s][a] + mean(delta_i[s][a] for i in deltas)
```

## 8. Are two learners moving at once?

If each agent's reward depends on the other's policy, the problem is **non-stationary by
construction** and a flat curve proves nothing.

Measured: over 150 iterations against a hare that was also learning, accuracy stayed
flat near 0.55, while kills rose from **752 to 1133** and the return from 60 to 93. Both
are true, and only one of them is visible in accuracy.

**The control that makes it readable: freeze one side.** Against a frozen opponent the
same learner went from 0.473 to 0.59 and stayed there. Without that run, the honest
conclusion would have been "it does not learn", which was wrong.

Always run a frozen-opponent control before concluding anything about a two-learner
system.

## 9. Is the action space shaped in a way the reward cannot overcome?

Two shapes that defeat a correct learner:

- **too large.** A hundred discrete actions explored once each is a hundred attempts
  before any learning starts. Cut to ten.
- **fragmented states.** A state of `(armour 0-3) x (magazine 0-2) x (lean -1..1)` is 27
  cells. If the reward depends only on `lean`, the other 18 cells are noise splitting
  the data nine ways. Ask which parts of the state the **optimal action** depends on.

## 10. Then, and only then, tune

Only after 1–9 come back clean:

- the **learning rate**: too high makes it oscillate, too low makes it look flat;
- **exploration**: too little and it locks into the first thing that worked, too much
  and it never settles;
- the **step size** for a hill climb: roughly ×1.25 on acceptance, ×0.8 on rejection;
- the **number of iterations** — kills were still rising at iteration 150.

Record what each change did, and if a tuning change "fixed" it, go back and check 1–9
again. In this project, four rounds of tuning fixed nothing, and the fifth finding —
that the algorithm did not match the reward's structure — fixed all of it at once.

---

## The shape of the answer

Ordering the list by what bit also orders it by likelihood, and the top three are all
**instrumentation**, not theory. Counting the branches, checking the world, and
printing the raw transition instead of a verdict are each a few lines, and each one
found a defect that survived hours of reasoning.

So when a curve is flat, the first move is not a hypothesis. It is a counter.
