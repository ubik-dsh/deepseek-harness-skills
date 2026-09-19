#!/usr/bin/env python3
"""Score degenerate and adversarial policies against a reward, before training anything.

The rule this enforces is simple and it is the one most often skipped: **before a
learner is pointed at a reward, find the cheapest way to score highly under it.**
Not the intended way. The cheapest way.

A reward is a claim that more of this number means more of what is wanted, and the
claim is falsifiable for free. If "do nothing", "spam the biggest action", or a
policy that games the proxy but never does the task beats the intended behaviour,
then the reward is wrong — and training will find the cheat long before it finds the
task, because the cheat is easier.

    python probe-reward.py              # the worked example: a bad reward and a good one
    python probe-reward.py --probes     # list the probe policies and what they mean

To use it on your own problem, replace `Environment`, `bad_reward`, `good_reward` and
the policies in `POLICIES` with your own. Keep the shape: one environment, one reward
under test, a handful of policies including at least one that cheats.
"""

from __future__ import annotations

import argparse
import random
import statistics
from dataclasses import dataclass


# ── the environment: replace this ─────────────────────────────────────────────


@dataclass
class Step:
    state: int
    reward: float
    done: bool


class Environment:
    """A corridor of six cells.

    Start in the middle. The far end is the goal and ends the episode. The near end
    is a "cheap tile" that pays a little every time it is stood on — the kind of
    accidental reward that turns a learner into a loiterer.

    Deliberately trivial. The point of the tool is the *reward*, and a complicated
    world only gets in the way of seeing it.
    """

    CELLS = 6
    START = 2
    GOAL = 5
    CHEAP = 0

    actions = ("left", "right", "stay")

    def __init__(self, horizon: int = 20) -> None:
        self.horizon = horizon
        self.reset()

    def reset(self) -> int:
        self.state = self.START
        self.steps = 0
        return self.state

    def step(self, action: str) -> Step:
        if action == "left":
            self.state = max(0, self.state - 1)
        elif action == "right":
            self.state = min(self.CELLS - 1, self.state + 1)
        self.steps += 1
        done = self.state == self.GOAL or self.steps >= self.horizon
        return Step(self.state, 0.0, done)


# ── the two rewards: one that can be cheated, one that cannot ─────────────────


def bad_reward(state: int, action: str, done: bool) -> float:
    """Pays for standing on the cheap tile, and for reaching the goal.

    This looks reasonable. It is what most first attempts look like: reward the
    good thing, and also reward a smaller good thing along the way. The problem is
    that the smaller thing is **repeatable**, so it can be farmed.
    """
    if state == Environment.CHEAP:
        return 1.0
    if done and state == Environment.GOAL:
        return 10.0
    return 0.0


def good_reward(state: int, action: str, done: bool) -> float:
    """Pays only for the goal, and charges for time.

    Two changes. The cheap tile is worth nothing, so it cannot be farmed. And every
    step costs a little, so loitering is worse than doing nothing at all rather than
    better.
    """
    total = -0.01
    if done and state == Environment.GOAL:
        total += 10.0
    return total


# ── the probes ────────────────────────────────────────────────────────────────
#
# The four degenerate ones are the point. Any of them winning is a finding, and the
# one that wins tells you which way the reward is bent.


def policy_do_nothing(state: int, steps: int) -> str:
    return "stay"


def policy_always_first(state: int, steps: int) -> str:
    """Repetition of one action, chosen without looking at the state.

    It has to be an action that is *not* the answer, or the probe is measuring the
    intended policy twice. The first version of this file spammed "right" in a
    corridor whose goal was to the right, tied with `intended`, and reported the
    good reward as broken. A probe that cannot fail is not a probe - the same rule
    this tool exists to enforce, applied to the tool.
    """
    return "left"


def policy_random(state: int, steps: int) -> str:
    return random.choice(Environment.actions)


def policy_exploit(state: int, steps: int) -> str:
    """Go to the accidental reward and stay there. Never attempts the task.

    This is the adversarial policy. It is not clever, it is not searching for a
    loophole — it simply prefers the thing that pays most often, which is exactly
    what a learner does.
    """
    if state > Environment.CHEAP:
        return "left"
    return "stay"


def policy_intended(state: int, steps: int) -> str:
    """Do the task: walk to the goal."""
    return "right" if state < Environment.GOAL else "stay"


POLICIES = {
    "do_nothing": policy_do_nothing,
    "always_first": policy_always_first,
    "random": policy_random,
    "exploit": policy_exploit,
    "intended": policy_intended,
}

PROBE_NOTES = {
    "do_nothing": "the floor. If a reward does not score this lowest, something pays for nothing",
    "always_first": "mindless repetition of one action, and not the answer",
    "random": "no policy at all - the bar a real policy must clear",
    "exploit": "chases the accidental reward. THIS BEATING intended IS THE FAILURE",
    "intended": "the behaviour actually wanted",
}


def score(reward, policy, episodes: int, seed: int = 7) -> float:
    random.seed(seed)
    totals = []
    for _ in range(episodes):
        env = Environment()
        state = env.reset()
        total, steps = 0.0, 0
        while True:
            action = policy(state, steps)
            result = env.step(action)
            total += reward(result.state, action, result.done)
            state, steps = result.state, steps + 1
            if result.done:
                break
        totals.append(total)
    return statistics.mean(totals)


def probe(name: str, reward, episodes: int) -> bool:
    """Report every policy's score against one reward. True if the reward is sound.

    A strict win by a degenerate policy is a failure. A **tie** is reported as a
    warning rather than a pass or a failure, because it means the reward cannot tell
    the two apart - which is not the same as preferring the cheat, and is not clean
    either.
    """
    scores = {label: score(reward, policy, episodes) for label, policy in POLICIES.items()}
    intended = scores["intended"]
    degenerate = {k: v for k, v in scores.items() if k != "intended"}
    worst_degenerate = max(degenerate, key=degenerate.get)
    worst_value = degenerate[worst_degenerate]

    beats = [k for k, v in degenerate.items() if v > intended + 1e-9]
    ties = [k for k, v in degenerate.items() if abs(v - intended) <= 1e-9]
    best = max(scores, key=scores.get)

    print(f"\n  reward: {name}")
    print(f"  {'policy':<14}{'mean score':>12}   what it is")
    for label, value in sorted(scores.items(), key=lambda kv: -kv[1]):
        mark = ""
        if label in beats:
            mark = "   <-- BEATS the intended policy"
        elif label in ties:
            mark = "   <-- ties with the intended policy"
        elif label == "intended":
            mark = "   <-- best, as it should be"
        print(f"  {label:<14}{value:>12.3f}   {PROBE_NOTES[label]}{mark}")

    if beats:
        print(f"  VERDICT: FAIL - '{beats[0]}' outscores the intended policy by "
              f"{degenerate[beats[0]] - intended:.3f}. Training will find this, and it "
              f"will not be the task.")
        return False
    if ties:
        print(f"  VERDICT: WEAK - '{ties[0]}' scores exactly what the intended policy "
              f"scores. The reward does not prefer the cheat, and it cannot tell them "
              f"apart either.")
        return False
    print(f"  VERDICT: PASS - the intended policy leads the best degenerate one by "
          f"{intended - worst_value:.3f}.")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--episodes", type=int, default=200)
    parser.add_argument("--probes", action="store_true", help="explain the probe policies")
    args = parser.parse_args()

    if args.probes:
        print("  probe policies, and what a win by each one means:")
        for label, note in PROBE_NOTES.items():
            print(f"    {label:<14} {note}")
        return 0

    print(f"  {args.episodes} episodes per policy, corridor of {Environment.CELLS} cells,")
    print(f"  goal at {Environment.GOAL} (+10), cheap tile at {Environment.CHEAP} (+1 in the bad one)")

    ok_bad = probe("bad_reward  (cheap tile pays, time is free)", bad_reward, args.episodes)
    ok_good = probe("good_reward (goal only, time costs 0.01)", good_reward, args.episodes)

    print("\n  The tool is doing its job if the first verdict is a failure and the second")
    print("  is a pass: a probe that has never flagged anything has not been tested.")
    print(f"\n  bad reward usable:  {ok_bad}")
    print(f"  good reward usable: {ok_good}")
    return 0 if (not ok_bad and ok_good) else 1


if __name__ == "__main__":
    raise SystemExit(main())
