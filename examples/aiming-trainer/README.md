# Aiming trainer

A worked example of the practice in
[simulating-a-test.md](../../skills/create-a-skill/references/simulating-a-test.md):
a skill whose success test lives outside the machine gets a small world instead of
a sentence.

Mouse control has no command to call and no exit code. So this builds the decision
instead — a target appears, you see a picture of it, you choose a point, time
passes, and then you find out whether you were right.

```bash
python seeds.py                    # six worlds, four stages
python seeds.py --latency 5        # a slower reflex
python sim.py --sheet              # one frame per stage, for a human to look at
```

Nothing here touches your real mouse. The trainee returns a coordinate and the
world scores it, so the experiment is repeatable and does not take over the desk.

## The two halves are separate on purpose

| | |
|---|---|
| `sim.py` | draws the world, knows where the target is, and keeps score |
| `player.py` | sees only the rendered image, and knows nothing else |
| `seeds.py` | runs the same experiment over several worlds, because one is an anecdote |

`player.py` must not be able to import the answer, which is why the two files share
no state. The trainee finds the target by saturation — the background and the grid
are grey and the target is the only coloured thing — aims, and then adjusts one
number: how far ahead to aim.

## What it measured

Six independently generated worlds, 80 rounds each:

| stage | latency 1 | latency 3 | latency 5 |
|---|---|---|---|
| static | 0.946 | 0.946 | 0.946 |
| static, changing colour and shape | 0.944 | 0.944 | 0.944 |
| moving | 0.911 | 0.414 | 0.233 |
| moving, changing colour and shape | 0.908 | 0.396 | 0.208 |
| lead it settled on | 0.08 | 1.06 | 0.66 |

The trainee was never told the target's speed or the delay. It measured the gap
between where it aimed and where the target turned out to be, and moved its lead to
close it. The lead grows with the delay, which is the correct answer, reached from
evidence rather than from instruction.

The 23% at a five-tick delay is not a broken trainee. It is the honest ceiling for
anything with a reflex that slow, and a skill built on this number can say what it
is worth.

## The adversarial version: two agents, one target, a rope between them

`sim.py` measures one trainee against a world. `arena.py` makes the world fight
back. It is a fullscreen window with two agents:

| | |
|---|---|
| **Clicker** | owns the click. Scores by landing on the target. |
| **Evader** | owns the target. Scores by being somewhere else. |

Neither sees the other's decision for the round — both commit from the same
picture, which is what makes it a game rather than a demonstration. A hit pulls a
shared rope towards the clicker, a miss towards the evader, and the rope is drawn
over time as well as in the moment: one position says who is ahead this second, the
shape says whether anyone is winning, and those are different questions.

```bash
python arena.py                # fullscreen
python arena.py --windowed     # a window, for looking at
python arena.py --speed 4      # rounds per second
```

Keys: `space` pause · `←/→` speed · `w` rewrite now · `r` restart · `Esc` quit

![The arena mid-round](arena.png)

### They rewrite their own program

Every five rounds each agent writes a new version of itself. This is not a
metaphor: real files appear in `gen/`, one per agent per generation, and the next
round runs the shape that file describes.

```
gen/
  clicker_gen42.py    MODE = 'read'      SHAPES = {lead: 0.38, read: 0.37, …}
  clicker_gen43.py    MODE = 'patient'   # mode read -> patient
  evader_gen43.py     MODE = 'warp'      # speed 0.41->0.58, warp 0.25->0.45
```

Each agent keeps a decaying score **per shape**, so the rewrite is a decision
rather than a twitch: it mostly keeps the best shape it has tried and tunes its
numbers, and occasionally tries another, because a shape that never runs cannot be
scored and the search would stall on its first idea. The scores are on screen, so
you can see *why* a rewrite happened rather than only that one did.

A run to generation 43, watched on screen:

```
CLICKER  shape: patient   won 157 / lost 57    rope +0.55
   lead:0.38   read:0.37   patient:0.17*   hold:0.06      rewrite: mode read -> patient
EVADER   shape: warp      won 57 / lost 157
   warp:0.77*  jitter:0.02 flee:0.01 drift:0.00          rewrite: speed 0.41->0.58, warp 0.25->0.45
```

The clicker came from behind to lead 157 to 57, and the screen says how: it moved
off raw prediction onto a smoothed one, twice, while the evader's only shape that
scored at all was the one that occasionally teleports.

### What the evader found on its own

Given only the last crosshair it saw, it learned to sit near a wall. That is not
in its strategy anywhere; it is a consequence of the rules — the clicker's aim is
clamped to the field, so a target in a corner cannot be aimed past, and the evader
discovered the exploit by being scored.

### The honest limit

The rewrite is bounded to a set of shapes and numbers, not free-form code
generation. A language model writing arbitrary new strategy code is the obvious
next version and would drop into the same place: `Agent.rewrite` writes a file and
the next round runs it, so a call to a model there changes nothing else in the
program. What is demonstrated here is the *loop* — score, rewrite, reload, compete
— not the sophistication of what gets written.

## The hiding game: four houses, twenty clicks each

`arena_houses.py` is the same adversarial pattern with a space to hide in. Four
houses stand, each worth twenty clicks; a click on a house is taken by the house,
never by whoever is inside; the hider is invisible while sheltered and reachable
only while crossing between houses; and a house that runs out returns at least a
hundred pixels away.

```bash
python arena_houses.py            # fullscreen
python arena_houses.py --no-hide  # draw the hider inside houses too
```

![A catch mid-crossing](houses.png)

The rules are written into the hider's own generated source, so the model that
hides is literally handed the rulebook it is playing by:

```
"""Generation 33 of the Hider.

The rules it is playing by:
#   - Four houses stand, twenty clicks each.
#   - A click on a house is taken by the house, never by whoever is inside.
#   - Inside a house you cannot be seen.
#   - A house that runs out returns at least a hundred pixels away.
#   - You are visible only while travelling, and that is when a click can reach you.
#   - You may not sit in one house longer than 8 rounds; it gets too hot.
"""
```

### Six attempts to make it a game, all of them found by reading the score

| Run | Score | What was wrong |
|---|---|---|
| aim at houses | 80 – 0 | the chaser could not reach the hider at all; it never aimed at a crossing |
| add interception | 155 – 3 | the hider never *had* to move, so there were almost no crossings to intercept |
| compulsory movement | 111 – 4 | better, but seven clicks in eight still landed on open ground |
| segment interception | 110 – 5 | a crossing is a line, but the chaser was still only guessing well one time in three |
| pressure mode added | 118 – 11 | **the pressure strategy scored 0.00 and was discarded**, because the score counted catches and pressure wins nothing immediately |
| progress scored separately | **65 – 64** | a game |

The fifth row is the one worth keeping. The chaser's strategy score measured
*catches*, so the shape that grinds a house down until the hider is forced out had
no score, was never selected, and the chaser spent a hundred rounds shooting at
empty ground. **The win condition and the progress signal are different numbers**,
and scoring a strategy by the first discards every strategy whose value is delayed.

### Matches, and a slower crossing

A match lasts **three minutes**; then the round is called, the winner announced, and
a new match begins with **the same two agents**. That boundary is the point: the
strategies carry over, so a chaser that lost the first three minutes and wins the
next is the thing worth watching. The clock is on screen, and the result of the
previous match stays there.

The crossing was slowed by a third — six ticks instead of four, which was a blink
at any speed you would want to watch. What this changes is what you can *see*: the
click is resolved against the whole crossing either way, so the metric barely
moves. It is a watchability change wearing the clothes of a difficulty setting, and
saying so is cheaper than implying otherwise.

### Armour, repairs, and a match that ends in a kill

The hider wears **armour worth three clicks**. Three hits strip it; the next hit
kills, and the match stops there — a match is not a timer, it is a life.

Arriving at a house **repairs the armour, and the house pays for every point
restored**. That is the hider's entire economy, and it is a genuine trap: armour
only comes back on arrival, so repairing means crossing, and crossing is the only
time it can be hit. A hider that repairs often destroys its own cover; one that
never repairs dies on the fourth hit.

Both sides are paid, and **not for the same thing**:

| | |
|---|---|
| **Shooter** | 1 point per hit on the hare, 2 for the kill, 0.5 per destroyed house |
| **Hare** | nothing but time. A second alive is one point, so its score *is* how long it survived |

The shooter also fires **eight shots and then reloads for two seconds**, so a long
crossing is a burst with a ceiling on it rather than a guaranteed kill, and the
crossing itself is thirteen ticks — a third slower than the last version, and more
than three times slower than where it started.

That per-tick shot is what makes the armour work at all. With one click per round
the shooter needed four consecutive hits across four separate crossings, and a
measured run produced **twenty-four armour hits and no kills in two hundred and
fifty rounds**. Thirteen ticks of crossing is thirteen chances, which is what a
slower target is supposed to mean.

### Do they learn, or do they just try shapes and look?

They just tried. The first version multiplied the **template** value by a random
factor on every rewrite, so whatever had been tuned was thrown away each time and
the numbers were re-rolled from scratch. Only the shape was learned, and only as a
four-armed bandit on a decaying score.

It is now a hill climb with one candidate at a time: each generation is a trial of
the current parameters, its score is compared with the best seen, and the trial is
kept or reverted — the step size grows when a change is accepted and shrinks when
it is not. Proof, read out of the generated sources after fifty-four generations:

| | generation 1 | generation 54 |
|---|---|---|
| shooter `commit` | 0.80 | **0.98** (held at ~1.0 for thirty generations) |
| shooter `spread` | 0.15 | **0.00** |
| hare `panic` | 0.20 | **0.00** (and stayed there) |
| hare `corner` | 0.30 | **0.48** |

Twenty of the shooter's changes were kept and thirty-three reverted; twenty-eight
of the hare's were kept and twenty-five reverted. Values move, and stay moved —
which is the difference between learning and a lottery.

**What still is not learned:** the step sizes start hand-set at 0.18, the bandit
explores a shape at random 20% of the time, and the radical rewrite's choice of
shape between matches is a written rule ("if you died crossing, cross less"), not
something the agent worked out. Those are the next three things to make adaptive.

## Real reinforcement learning, and the five bugs it took

The arena's own adaptation is hill climbing: one score per generation, no value
function, no credit assignment. `rl_train.py` does the real thing — tabular
Q-learning with a per-shot reward — and runs it in parallel.

```bash
python rl_train.py --iterations 150 --workers 12 --episodes 150
python rl_train.py --show                       # the learning curve and the policy
python arena_houses.py --rl --speed 9           # drive the arena from the tables
```

The decision it learns is genuinely sequential: the shooter's magazine holds eight
shots and then it reloads for two seconds, so **whether to spend a partial burst now
or give up the crossing and reload** is a choice, and the crossing is **bowed**, so
aiming at the straight midpoint is not the best shot. Neither is told to it. It sees
one cue — which way the hare leaned as it left — and must work out what that implies.

### What it learned

The bow is `1.2 × lean` in aim-offset units. The shooter was told the lean and
nothing else. After training:

| lean | it aims at | the truth |
|---|---|---|
| -1 | **-1** | -1.2 |
| 0 | **0** | 0.0 |
| +1 | **+1** | +1.2 |

Computed exactly, the policies are worth:

| policy | accuracy |
|---|---|
| always aim at the straight midpoint | 0.473 |
| aim randomly | 0.354 |
| **what it learned** | **0.58 – 0.59** |
| the theoretical optimum | 0.603 |

Against a hare that also learns, accuracy stays flat around 0.55 — the target is
moving — but **kills rose from 752 to 1133 over 150 iterations** and the return from
60 to 93. On the arena itself, three minutes produced **19 matches, each ending in
a kill**, where the hill-climbed shooter needed 80 to 108 rounds for one.

### The five defects, because the path is the point

Every one was found by running it and reading a number. None by reading the code.

1. **The next state was random.** `nxt = state(..., random.choice(leans))` is not a
   transition, it is noise injected into the target. The unknown part has to be
   *averaged*, not sampled.
2. **The hare was rewarded for being shot.** Its punishment tested `armour > 0`,
   which is true again by the time it runs, because a kill restores the armour.
3. **Q-tables were averaged across processes.** Two workers that diverge learn
   contradictory values for the same state, and the mean of two contradictions is
   not a value function. Workers now report the *change* from the table they were
   given.
4. **A safe action became a trap.** Reloading costs a small certain amount and
   avoids the penalty for missing — and missing is what an untried aim offset looks
   like. The agent learned two of the three mappings and answered "reload" to the
   third. Optimistic initial values are the textbook fix.
5. **Q-learning was the wrong algorithm.** This is the one that mattered. The aim
   offset does not change what happens next — the next lean is random whatever was
   fired — so the bootstrapped term (`γ = 0.92`) contributed nothing but the noise
   of a value estimated from other states. The kill bonus arrives on the same step
   as the hit, so there is no credit to carry backwards. With **γ = 0** it is a
   contextual bandit, which is what the decision actually is, and it converged to
   the optimum from the first iteration.

A learning curve that oscillated between 0.35 and 0.55 for a hundred iterations
became a flat line at 0.58 the moment the algorithm matched the problem.

## Requirements

Python 3.9 or newer and Pillow. No numpy: the vision is channel arithmetic through
Pillow, deliberately, because the trainee should be able to see and nothing more.
