---
name: design-a-reward
description: Design the reward signal for anything that learns — reinforcement learning, a bandit, hill climbing, an evolutionary search, a scoring function, a grader. Covers what to measure, how to grade it when a yes-or-no is too coarse, how to find the limits and the step sizes, the rules a reward must satisfy, and an ordered checklist for a learning curve that will not rise. Ships a probing harness that scores degenerate and adversarial policies against your reward, so a reward that can be won without doing the task is caught before it trains anything. Use when building or debugging any learner; when a score, fitness function or grader is being designed; when a curve is flat, oscillating or rising then falling; when an agent learned something other than what was wanted; when choosing between binary and graded feedback, or between a bandit and a full sequential method.
license: MIT
compatibility: Agent Skills standard. SKILL.md is plain text. The script in scripts/ needs Python 3.8+, standard library only, and is a template to copy rather than a tool to install.
metadata:
  spec: https://agentskills.io/specification
  version: 0.1.0
  status: first formulation, to be sharpened by use
  measured_on: tabular Q-learning and UCB1 bandits, 150 parallel iterations, and a two-agent arena
  verified_against: this harness 0.1.5-rc.2
  sibling: learn-an-interface — where the reward is a verified property of a real window
---

# Designing a reward

Everything a learner becomes, it becomes from the number you give it. The algorithm
is the easy half; five separate defects in one project were all in the reward and in
what the reward was attached to, and each one produced a confident wrong answer.

This skill is the procedure and the rules. It applies to reinforcement learning, to a
bandit, to a hill climb, to a fitness function, to any grader an agent is optimised
against.

---

## Step 1 — Write the claim down as a sentence, then try to beat it

A reward is a claim: *"more of this number means more of what I want."* Write that
sentence in the skill or the code before writing the function.

> Aiming at the bow of the crossing scores more than aiming at the straight midpoint.

Then **try to falsify it**, by hand, before the learner ever runs:

- what is the **cheapest** way to get a high number? Not the intended way — the
  cheapest way.
- what does **doing nothing** score?
- what does **doing the maximum of everything** score?
- what scores well **without the task being done at all**?

`scripts/probe-reward.py` runs exactly this: your reward against a set of degenerate
and adversarial policies. Run it first. A reward that a lazy policy wins will train a
lazy agent, and it will do so smoothly and convincingly.

## Step 2 — Check the reward can fail

Same doctrine as any success test, and here it is not a formality: **the reward is
the success test**, and a weak reward does not merely fail to help — it trains the
policy on the wrong target and converges confidently.

Measured: *"did the file get saved?"* passed. The file was named `picture.png`. Its
first bytes were `00 00 00 20 66 74 79 70` — a project file wearing an image's
extension. A reward that asked whether a file existed certified it every time.

**Run the reward against the wrong thing once, and watch it return a low score.** A
reward that has never been seen to fail is not yet a reward.

## Step 3 — Make sure every branch actually fires

The most embarrassing class of defect: a term that can never be reached.

Measured: a hare was punished for dying. The punishment tested `armour > 0` — and a
kill **restores the armour**, so by the time the test ran the condition was true
again. The hare was rewarded for being shot, for the whole run, and its behaviour was
consistent with that.

For every term in the reward, ask: **what sequence of events reaches this line?**
Then put a counter on it and confirm the count is not zero. An unreached branch is
worse than a missing one, because it looks like a considered design.

## Step 4 — Grade it, unless a yes-or-no is genuinely all there is

A binary reward discards information that cost real attempts to obtain.

```
1.0   the wanted thing happened            (a real PNG was written)
0.3   something happened, not that thing   (a file was written, as TIFF)
0.0   nothing happened
```

With only 1.0 and 0.0 a learner cannot tell "nearly" from "nowhere", and it spends
attempts relearning what it already knew — or, worse, it cannot find the gradient
that would lead it out.

Grade **only where the grades are meaningful**. Three levels that correspond to three
genuinely different states of the world; not ten invented to look precise. If you
cannot say what the world looks like at 0.6, do not have a 0.6.

## Step 5 — Find the limits by measuring what the learner achieves

Bounds are parameters, and a bound that is hit is a message.

Measured: a hare's `panic` parameter was optimised down to **exactly 0.00** and stayed
there for fifty generations. That reads as "it learned that panicking is useless". It
is weaker than that: the optimisation pushed a number into the wall of its own range.
The real finding is *"panic is harmful within the range it was given"*, and it also
says the parameterisation may be wrong — maybe panic should be able to go negative, or
maybe it was never a useful axis.

So, for each parameter or action:

1. **sample the achieved values** at the end of a run — not the reward, the inputs;
2. anything pinned at a bound is a **boundary solution**: report it as such, and ask
   whether the range was the mistake;
3. anything that never moves is a **dead axis**: the reward does not depend on it, or
   the step is too small to escape;
4. record the **range actually visited**, which tells you the useful span better than
   the configured one ever did.

More: [references/bounds-and-steps.md](references/bounds-and-steps.md).

## Step 6 — Choose the step from the reward's shape, not from taste

- **Discrete action set** — a bandit. Ten candidates converge in about ten attempts.
  This is the right answer far more often than it is chosen.
- **Continuous parameters** — a hill climb with an adaptive step: multiply by ~1.25 on
  acceptance, ~0.8 on rejection. Crude, and it worked.
- **A reward that arrives long after the decision** — only then do you need credit
  assignment and a discount.
- **A reward that arrives on the same step as the action, and where the action does
  not change what happens next** — this is a **bandit**, and treating it as a
  sequential problem is the defect in step 7.

Measured, and it is the single largest fix in the project: an aim offset was learned
with Q-learning at `gamma = 0.92`, on the general principle that bootstrapping is
what makes Q-learning Q-learning. But the next lean of the crossing is drawn at
random whatever was fired — the action did not change what came next — so the
bootstrapped term contributed nothing but the noise of a value estimated from nine
other states. The curve oscillated between 0.35 and 0.55 for a hundred iterations.
With **`gamma = 0`** it is a contextual bandit, which is what the decision was, and it
converged to the optimum from the first iteration.

**Match the algorithm to the reward's structure.** A moving learning curve is
sometimes not a tuning problem at all.

## Step 7 — Do not let a safe action dominate

If the action set contains a fallback — wait, reload, do nothing, ask for help — price
it honestly or the learner will hide in it.

Measured: reloading cost a small certain amount and avoided the penalty for missing.
But **missing is exactly what an untried aim looks like**, and the good aim had to be
discovered. The agent learned two of the three aim mappings and answered "reload" to
the third. Optimistic initial values are the textbook fix: assume an untried action is
good, so trying it is what reduces the estimate.

## Step 8 — If two learners compete, stop expecting a monotone curve

When each agent's reward depends on the other's policy, the problem is
**non-stationary by construction**: the hare improving makes the shooter's accuracy
fall, and a flat or falling curve proves nothing either way.

Measured: over 150 iterations against a hare that was also learning, accuracy stayed
flat near 0.55 while kills rose from 752 to 1133. Both were true.

To tell learning from co-adaptation, **freeze one side** and measure again. Against a
frozen opponent the same learner went 0.473 to 0.59 and stayed. That control is the
only thing that made the result readable.

Two more rules for adversarial scoring, both learned the hard way:

- **score the two sides on different events.** Paying both for the same event
  discarded the strategy whose payoff was delayed, and it looked like a balance
  problem for several iterations.
- **separate the win condition from the progress signal.** The thing that ends the
  match and the thing that says "getting warmer" are not the same number, and using
  one for both is what hides progress in a slow strategy.

## Step 9 — When the curve will not rise, check in this order

Cheapest and most likely first. Every item on this list was an actual defect in one
project, and every one was found by running rather than by reading.

1. **Is the reward being computed at all?** Count how many times each branch fires.
2. **Is the world still there?** A twelve-attempt run scored zero on everything and
   the learner concluded no candidate worked — the program had died. A missing world
   is not a failed action; make it raise.
3. **Is the state a real transition?** Bootstrapping off `random.choice(...)` of the
   possible next states is not a transition, it is noise in the target. Unknown parts
   are **averaged**, not sampled.
4. **Is the algorithm matched to the reward's structure?** See step 6.
5. **Is a safe action eating the exploration?** See step 7.
6. **Is the reward's scale right?** A kill bonus of +5 beside hits of +1 makes the
   kill dominate every other consideration; a bonus of +0.01 makes it invisible.
7. **Is the measurement noisy?** Compute the standard error before believing a
   wobble: at 120 episodes and ~29 000 samples the standard error was ±0.3%, so a
   swing from 0.35 to 0.55 was real change, not noise. Publishing the noise floor is
   what makes a curve readable.
8. **Are you averaging things that must not be averaged?** Two workers that diverge
   learn contradictory values for the same state, and the mean of two contradictions
   is not a value function. Average the **change** from a shared starting point, not
   the finished values.

Full detail and the code shapes: [references/diagnosing-a-flat-curve.md](references/diagnosing-a-flat-curve.md).

## Step 10 — Write the reward down as a contract

In the skill or the file that holds the reward:

- the **claim**, in one sentence, with the probe that tries to beat it;
- every **term**, its unit, its scale, and **what sequence of events reaches it**;
- the **noise floor** of the measurement;
- the **limits** you imposed, and which of them the learner actually hit;
- the **algorithm** and why it matches the reward's structure;
- the **counter-example**: a run where the reward scored the wrong thing highly.

## What this skill does not cover

- **Where the reward comes from.** If it has to be read off a real interface, that is
  the sibling skill `learn-an-interface`.
- **Exploration strategies beyond UCB1 and epsilon-greedy**, and anything requiring a
  neural network. The rules transfer; the code here does not.
- **Reward models learned from human preference.** Same rules apply to the result, and
  nothing here has been measured against the process.
- **Safe exploration and constrained RL.** Named because a reward with hard limits is
  a different problem from a reward with a big penalty.

## Refining this skill

Version 0.1.0. The parts most likely to be wrong:

- the **checklist order** — it is ordered by what bit, in one project, and a
  different project would reorder it;
- **grading levels** — one measured example with three levels is a thin basis for the
  advice;
- **step sizes** — 1.25 and 0.8 worked once and are recorded as an observation, not a
  recommendation.

When a use contradicts something here, the use wins: change the file, keep the
counter-example.
