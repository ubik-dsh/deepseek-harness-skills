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

## Requirements

Python 3.9 or newer and Pillow. No numpy: the vision is channel arithmetic through
Pillow, deliberately, because the trainee should be able to see and nothing more.
