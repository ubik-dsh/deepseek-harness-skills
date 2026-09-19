# When the test is outside the machine, build one

Some skills cannot be verified, because their success test happens in a place the
agent has no access to: a hand on a mouse, a cable in a socket, a person's
reaction. The temptation is to write the skill anyway, with a success test made of
words — *"the user is comfortable with the mouse"* — and that is a skill nobody can
ever finish or fail.

**The fix is not a better adjective. It is a simulator.**

## The principle

If the real test is physical, build a small world that has the same shape as the
real one and can be scored. Not a mock of the hardware — a model of the *decision*
the skill is about. For aiming, that is: there is a target, you see a picture of
it, you choose a point, time passes, and then you find out whether you were right.

The agent then has something it never had before: **a number**. And a number can
be repeated, compared and improved, which is the whole difference between a skill
and a wish.

## What the world needs to have

| Ingredient | Why | What happens without it |
|---|---|---|
| **A picture, not the coordinates** | The agent must perceive, or the exercise tests nothing | The player reads the answer key and the simulation is a formality |
| **A reaction delay** | Real agents act on stale information | Measured: with no delay the trainee scored **100% at every stage** and learned nothing, because a target moving six pixels cannot escape a fourteen-pixel hit radius |
| **Feedback after every attempt** | Learning needs a signal | Guessing in the dark |
| **Increasing difficulty** | A flat task measures one ability | You cannot tell perception from prediction |
| **A world that is not the trainee's** | The trainee must not be able to cheat by inspecting it | The number means nothing |

## The measured proof

A trainer was built for aiming — the example this practice came from — with four
stages: a static target; a static target that changes colour and shape; a moving
target; and a moving target that changes colour and shape. The trainee saw only
the rendered image, found the target by saturation, chose a point, and adjusted
one number: how far ahead to aim. Run over six independently generated worlds, 80
rounds each:

| stage | latency 1 | latency 3 | latency 5 |
|---|---|---|---|
| static | 0.946 | 0.946 | 0.946 |
| static, changing | 0.944 | 0.944 | 0.944 |
| moving | **0.911** | **0.414** | **0.233** |
| moving, changing | **0.908** | **0.396** | **0.208** |
| lead it settled on | 0.08 | **1.06** | 0.66 |

Three things are worth reading out of that table.

**The trainee learned the thing that mattered, and was not told it.** It was never
given the target's speed or the delay. It measured the gap between where it had
aimed and where the target turned out to be, and moved its lead towards closing it.
The lead it settled on grows with the delay, which is the correct answer, arrived
at from evidence.

**Difficulty had to be real.** With no reaction delay every number was 1.000 and
the exercise proved nothing at all. The delay is not a detail of the simulation;
it *is* the simulation. A simulated world that is easier than the real one teaches
the wrong lesson with the same confidence.

**The ceiling is the finding, not a failure.** 23% at a five-tick delay is not a
broken trainee, it is the honest answer to "how well can anything do this with a
reaction this slow". A skill built on this number can now say what it is worth.

## How to build one

1. **Name the decision.** Not the hardware — the choice the skill is about. Aiming
   is a choice; "using a mouse" is not.
2. **Write the world and the trainee as separate files.** They must not share
   state. If the trainee can import the world, it will, and the measurement is
   over.
3. **Score every attempt, and keep the history.** Accuracy alone hides everything;
   the change from the first third to the last third is what separates learning
   from luck.
4. **Run several worlds.** One seed is an anecdote. The table above is six, and
   the spread is reported rather than the best.
5. **Put the delay in early.** It is the first thing to add and the easiest to
   forget, because the version without it looks like a success.
6. **Write down what the simulation does not model.** The trainer here has no
   muscles, no fatigue, no mis-click and no screen scaling. It measures perception
   and prediction; it does not measure a hand.

## Six wrong versions before one right one

Recorded because the number is only believable if the path to it is.

1. **No reaction delay.** Every stage scored 100%. Nothing was measured.
2. **One bit of feedback** — hit or miss — nudging the lead in a fixed direction.
   It diverged, scoring 9% with the lead pinned to its ceiling, because a miss has
   many causes and only one of them is "not enough lead".
3. **Correcting by the measured speed.** The trainee does not observe the speed: it
   observes displacement between two frames, and that already includes the delay,
   so the correction was several times too large. 2%.
4. **A fixed threshold for "this is a teleport, not motion".** Chosen from the
   world's top speed and wrong, because a moving target displaces 24 to 36 pixels
   per frame once the delay is in the interval. Every observation read as a jump,
   and the learner was reset on every turn.
5. **The same threshold relative to the average displacement.** A static target has
   no average, so half its respawns read as motion and the score fell to 50%.
6. **Teaching the average over the first few frames.** It learned a respawn.

What finally worked was not a better threshold but a different question: a jump is
not a speed, it is a **discontinuity**. Real motion changes smoothly and a teleport
does not, so comparing this frame's displacement with the last one needs no
calibration, no warm-up and no knowledge of the world.

**None of the six was found by thinking.** Every one was found by running the thing
and reading the number, which is the same lesson as everywhere else in this skill.

## Three things the arena taught that the trainer could not

The trainer checks one trainee against a world. The arena puts two agents against
each other — one owns the click, one owns the target — and three lessons came out
of it that a single trainee cannot produce.

### Put something adversarial against your rule, or you will not see its seams

The evader was given the last crosshair it saw and nothing else. It learned to sit
near a wall. **That strategy is written nowhere in it.** It is a consequence of the
rules: the clicker's aim is clamped to the field, so a target in a corner cannot be
aimed past, and the evader found the exploit because it was scored for finding it.

Every rule has a seam where it clamps, truncates or refuses, and something will
live there. A tester who follows the rules never finds it; an opponent who is
rewarded for breaking them finds it immediately. If you want to know where your
specification is weak, do not review it — **put something against it that wins by
exploiting it.**

### A learner that forgets its past selves is twitching

The first version of the rewrite chose a new shape at random each generation. It
looked like evolution and was a random walk: an agent that changes shape and never
remembers which shape worked cannot improve, only move. Adding a decaying score per
shape — kept across generations, shown on screen — turned the rewrite into a
decision, and made the reason for it visible: *mode read -> patient*.

Self-modification needs a memory of the outcomes of past selves. Without it the
output is motion.

### Measure what you can, not what you want to know

All six failures of the trainee were one mistake in six costumes: treating an
observation as a measurement of the thing that mattered.

| Wanted to know | Actually observed | Consequence |
|---|---|---|
| the target's speed | displacement between two frames, which includes the delay | correction four times too large |
| how wrong the lead was | hit or miss | diverged, because a miss has many causes |
| whether this was a teleport | how fast it moved | every frame of a moving target read as a jump |
| what "usual" means for a static target | the first few frames | learned a respawn |

Each fix was the same move: **stop reaching for the quantity you want and find one
you can actually measure that closes the same gap.** The working controller measures
the distance between where it aimed and where the target turned out to be — which
needs no knowledge of speed or delay — and drives that to zero.

This is the same discipline as *no completion claim without fresh evidence*, one
level down. There it is about what you tell the user. Here it is about what your
code is allowed to believe.
