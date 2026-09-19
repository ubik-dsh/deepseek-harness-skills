"""Real reinforcement learning for the houses game: tabular Q-learning, in parallel.

Where this differs from the arena's own adaptation, and why it is worth the work:

    hill climbing (what the arena does)   RL (what this does)
    ------------------------------------  ------------------------------------
    one score per *generation*            one reward per *shot and per step*
    no credit assignment                   the kill's bonus propagates backwards
                                          through the armour states that led to it
    no value function                      Q(state, action) is the value function
    a change is kept or reverted           every action is scored, not just the
                                           last change

The shooter's problem is genuinely sequential. Its magazine holds eight shots and
then it reloads for two seconds, so it has to decide *whether to spend a partial
burst now or skip the crossing and reload* - and the crossing path is bowed, so
aiming straight at the midpoint is not the best action. Both of those are learned
here, neither is told.

    python rl_train.py --iterations 100 --workers 8
    python rl_train.py --show            # learning curves from the saved tables

Training runs on a compact model of the arena rather than on the arena's own
window: the same states, the same rewards, the same rules, no drawing. That is a
real limitation and it is stated rather than hidden - what transfers is the policy,
which the arena then runs for real.
"""

from __future__ import annotations

import argparse
import json
import multiprocessing as mp
import random
import statistics
from pathlib import Path

ARMOR_MAX = 3
MAGAZINE = 8
SHOTS_PER_CROSSING = 4   # a crossing is a window, not the whole magazine
CROSS_TICKS = 13
EPISODE_ROUNDS = 120

# What the shooter is told, and what is actually true. It sees which way the hare
# leaned as it left - a sign, one of three - and the crossing really does bow that
# way, but by an amount it has to learn and with noise it cannot remove.
#
# The first attempt at this made the bow a fixed function of the distance, which
# the agent simply memorised: thirty-eight kills per episode and nothing left to
# decide. The state has to carry information the action can use and the answer must
# not be exact, or there is no problem.
LEAN_EFFECT = 1.2        # how far the path bows in the direction of the lean
BOW_NOISE = 0.6          # spread of that bow, invisible to the shooter
SHOT_NOISE = 1.0         # spread of a single shot around where it was aimed
HIT_WINDOW = 1.0         # how close a shot must land to count

# The shooter chooses one of five aim offsets, or refuses the crossing entirely to
# reload. The reload action is what makes this a sequential problem rather than a
# bandit: taking it costs a whole crossing and buys a full magazine.
OFFSETS = (-2, -1, 0, 1, 2)
ACTIONS = (*OFFSETS, "reload")

HARE_ACTIONS = ("stay", "near", "far")

ALPHA = 0.18
# Zero, and that is a correction rather than a setting. The first version used
# 0.92 on the general principle that bootstrapping is what makes Q-learning
# Q-learning - and it was wrong for this problem. The aim offset does not change
# what happens next: the next lean is drawn at random whatever was fired, so the
# only thing the bootstrapped term contributed was the noise of a value estimated
# from nine other states. The kill bonus arrives on the same step as the hit that
# caused it, so there is no credit to carry backwards.
#
# With gamma at zero this is a contextual bandit over the lean, which is what the
# decision actually is - and the estimate is a plain running average of the reward
# each offset has earned in each situation.
GAMMA = 0.0
EPSILON_START = 0.35
EPSILON_END = 0.04

# What an action is assumed to be worth before it has ever been tried.
#
# This is the fix for a real trap the first version fell into. Every value started
# at zero, so the *safe* action looked as good as any: reloading costs a small
# certain amount and avoids the penalty for missing, which made it preferable to
# shooting badly - and shooting badly is what an untried aim offset looks like. The
# agent learned two of the three lean-to-aim mappings and answered "reload" to the
# third instead of exploring the offset that would have been better than both.
#
# Optimistic initial values are the textbook answer: an action nobody has tried is
# assumed to be good, so trying it is what reduces the estimate, and exploration
# stops being something epsilon has to force.
OPTIMISTIC = 1.0


def row_for(table: dict[str, dict[str, float]], state: str, actions) -> dict[str, float]:
    return table.setdefault(state, {str(a): OPTIMISTIC for a in actions})


def mag_bucket(shots: int) -> int:
    if shots <= 0:
        return 0
    return 1 if shots <= 4 else 2


def hp_bucket(hp: int) -> int:
    return 0 if hp <= 6 else (1 if hp <= 13 else 2)


def shooter_state(armour: int, shots: int, lean: int) -> str:
    return f"{armour}|{mag_bucket(shots)}|{lean}"


def hare_state(armour: int, stay: int, best_hp: int) -> str:
    return f"{armour}|{min(stay, 2)}|{hp_bucket(best_hp)}"


def pick(table: dict[str, dict[str, float]], state: str, actions, epsilon: float) -> str:
    """Return an action, always as the string the table is keyed by.

    The first version returned an int when exploring and a string when exploiting,
    because the table keys are strings and `random.choice` is not. That worked until
    an action was used as a number, which is the one thing the shooter's aim does.
    One type, one place it is converted.
    """
    if random.random() < epsilon or state not in table:
        return str(random.choice(actions))
    row = table[state]
    best = max(row.values())
    return random.choice([a for a, v in row.items() if v == best])


def q_update(table: dict[str, dict[str, float]], state: str, action, reward: float,
             v_next: float, actions, alpha: float = ALPHA, gamma: float = GAMMA) -> None:
    """The whole of tabular Q-learning, in five lines.

    The value of the action just taken moves towards the reward received plus the
    discounted value of what comes next. That second term is what the arena's hill
    climbing has no equivalent of: it is how the bonus for a kill reaches the
    decision, four hits earlier, to spend a shot on a stripped target.

    `v_next` is passed in rather than a next state, and that is the correction that
    mattered. The first version bootstrapped off `random.choice` of the possible
    next states, which is not a transition at all - it is noise injected into the
    target, and a hundred iterations of it moved the return from 69.6 to 64.8, which
    is to say nowhere. The unknown part of the next state has to be *averaged*, not
    sampled.
    """
    row = row_for(table, state, actions)
    target = reward + gamma * v_next
    row[str(action)] += alpha * (target - row[str(action)])


def expected_next_value(table: dict[str, dict[str, float]], armour: int, shots: int, actions) -> float:
    """What the next step is worth, averaging over the one thing it cannot know.

    The armour and the magazine are decided by the action; the lean of the next
    crossing is not. So the value of the successor is the mean over the three leans
    of the best action available in each. This is the whole fix above.
    """
    values = []
    for lean in (-1, 0, 1):
        state = shooter_state(armour, shots, lean)
        row = table.get(state)
        values.append(max(row.values()) if row else OPTIMISTIC)
    return sum(values) / len(values)


def play_episode(q_shooter: dict, q_hare: dict, epsilon: float, record: list,
                 freeze_hare: bool = False) -> dict:
    """One match, abstractly. Returns what happened."""
    houses = [20, 20, 20, 20]
    house_index = 0
    armour = ARMOR_MAX
    shots = MAGAZINE
    stay = 0
    crossing = False
    kills = 0
    hits = 0
    wasted = 0
    survived = 0
    shooter_return = 0.0

    for _ in range(EPISODE_ROUNDS):
        # ── the hare decides ──────────────────────────────────────────────
        best_hp = max(houses)
        hs = hare_state(armour, stay, best_hp)
        # A frozen hare is the control: it answers whether the shooter is learning,
        # separately from whether the shooter is keeping up. Against a hare that
        # adapts too, the accuracy is a moving target by construction and a flat
        # curve proves nothing either way.
        ha = random.choice(HARE_ACTIONS) if freeze_hare else pick(q_hare, hs, HARE_ACTIONS, epsilon)
        if armour < ARMOR_MAX and random.random() < 0.3 + 0.5 * (1 - armour / ARMOR_MAX):
            ha = "far" if random.random() < 0.5 else "near"
        if stay >= 8:
            ha = "near"

        if ha == "stay":
            stay += 1
            crossing = False
        else:
            # Somewhere to go, and the house pays for the repairs on arrival.
            options = [i for i in range(4) if i != house_index]
            target = max(options, key=lambda i: houses[i]) if ha == "far" else random.choice(options)
            cost = ARMOR_MAX - armour
            if cost > 0 and houses[target] > 0:
                paid = min(cost, houses[target])
                houses[target] -= paid
                armour += paid
            if houses[target] <= 0:
                houses[target] = 20
            house_index = target
            stay = 0
            crossing = True

        # ── the shooter decides ───────────────────────────────────────────
        # The lean is what it can see; the bow is what is true.
        lean = random.choice((-1, 0, 1))
        true_bow = LEAN_EFFECT * lean + random.gauss(0, BOW_NOISE)
        ss = shooter_state(armour, shots, lean)
        sa = pick(q_shooter, ss, ACTIONS, epsilon)
        reward = 0.0
        killed_now = False

        if crossing:
            if sa == "reload":
                shots = MAGAZINE
                reward = -0.02                      # a crossing given up
            else:
                offset = int(sa)
                fired = min(shots, SHOTS_PER_CROSSING)
                shots -= fired
                landed = 0
                for _ in range(fired):
                    if abs(offset - true_bow + random.gauss(0, SHOT_NOISE)) < HIT_WINDOW:
                        landed += 1
                hits += landed
                wasted += fired - landed
                reward = landed * 1.0 - (fired - landed) * 0.05
                armour = max(0, armour - landed)
                if armour == 0 and landed > 0:
                    # Stripped, and the extra hit kills. The bonus is what the
                    # discounting carries back to the armour states before it.
                    kills += 1
                    killed_now = True
                    reward += 5.0
                    armour = ARMOR_MAX
            if shots <= 0:
                shots = MAGAZINE                    # reloading finishes next round
        else:
            if shots < MAGAZINE and random.random() < 0.5:
                shots = MAGAZINE
            reward = -0.01

        survived += 1
        shooter_return += reward
        if record is not None:
            record.append(reward)
        # The real successor: armour and magazine are decided by the action, and the
        # only unknown is averaged rather than sampled.
        v_next = expected_next_value(q_shooter, armour, shots, ACTIONS)
        q_update(q_shooter, ss, sa, reward, v_next, ACTIONS)
        # The hare is paid in time and punished for dying. `killed_now` is what makes
        # that punishment fire at all: the first version tested `armour > 0`, which is
        # true again by then because a kill restores the armour, so the hare was
        # rewarded for being shot and never learned to avoid it.
        hare_reward = -10.0 if killed_now else 1.0
        if not freeze_hare:
            q_update(q_hare, hs, ha, hare_reward, 0.0, HARE_ACTIONS)

    return {
        "shots": hits + wasted,
        "hits": hits,
        "kills": kills,
        "survived": survived,
        "return": round(shooter_return, 2),
    }


def worker(job: tuple) -> tuple:
    """One parallel learner. Returns how far it moved, not where it ended up.

    This is the correction that mattered. The first version returned its finished
    tables and the main process averaged them, which is how neural network weights
    are pooled and is wrong here: two workers that start together and diverge learn
    *contradictory* values for the same state, and the mean of two contradictions is
    not a value function. Measured against a frozen opponent - so that nothing but
    the shooter was moving - the averaged version went 0.45, 0.44, 0.54, 0.51, 0.42,
    which is noise wearing a learning curve.

    A worker now reports the difference from the table it was given, and the main
    process adds the mean of those differences to the shared tables. Same parallel
    structure, and the thing being averaged is a change.
    """
    q_shooter, q_hare, episodes, seed, freeze = job
    base_shooter = json.loads(json.dumps(q_shooter))
    base_hare = json.loads(json.dumps(q_hare))
    random.seed(seed)
    totals = []
    for _ in range(episodes):
        totals.append(play_episode(q_shooter, q_hare,
                                   random.uniform(EPSILON_END, EPSILON_START), None, freeze))
    return delta(base_shooter, q_shooter), delta(base_hare, q_hare), totals


def delta(base: dict, learned: dict) -> dict:
    out: dict[str, dict[str, float]] = {}
    for state, row in learned.items():
        was = base.get(state, {})
        change = {a: v - was.get(a, 0.0) for a, v in row.items() if abs(v - was.get(a, 0.0)) > 1e-12}
        if change:
            out[state] = change
    return out


def apply_delta(base: dict, deltas: list[dict]) -> dict:
    """Add the mean change from every worker to the shared tables."""
    totals: dict[str, dict[str, float]] = {}
    counts: dict[str, dict[str, int]] = {}
    for change in deltas:
        for state, row in change.items():
            target = totals.setdefault(state, {})
            seen = counts.setdefault(state, {})
            for action, value in row.items():
                target[action] = target.get(action, 0.0) + value
                seen[action] = seen.get(action, 0) + 1
    for state, row in totals.items():
        merged = base.setdefault(state, {})
        for action, value in row.items():
            merged[action] = merged.get(action, 0.0) + value / counts[state][action]
    return base


def evaluate(q_shooter: dict, q_hare: dict, episodes: int = 120, freeze_hare: bool = False) -> dict:
    """Play greedily, with no exploration, so the curve shows the policy and not luck."""
    stats = [play_episode(q_shooter, q_hare, 0.0, None, freeze_hare) for _ in range(episodes)]
    hits = sum(s["hits"] for s in stats)
    shots = sum(s["shots"] for s in stats) or 1
    return {
        "hits": hits,
        "shots": shots,
        "accuracy": round(hits / shots, 4),
        "kills": sum(s["kills"] for s in stats),
        "return": round(statistics.mean(s["return"] for s in stats), 2),
    }


def train(iterations: int, workers: int, episodes: int, out: Path, freeze_hare: bool = False,
          alpha: float = ALPHA) -> None:
    global ALPHA
    ALPHA = alpha
    q_shooter: dict = {}
    q_hare: dict = {}
    history = []

    label = "vs a frozen hare" if freeze_hare else "vs a hare that also learns"
    print(f"{'iter':>5}{'accuracy':>10}{'kills':>8}{'return':>9}   (greedy, {label}, alpha {alpha})")
    for iteration in range(1, iterations + 1):
        jobs = [(json.loads(json.dumps(q_shooter)), json.loads(json.dumps(q_hare)), episodes,
                 1000 + iteration * 97 + w, freeze_hare) for w in range(workers)]
        with mp.Pool(workers) as pool:
            results = pool.map(worker, jobs)
        q_shooter = apply_delta(q_shooter, [r[0] for r in results])
        if not freeze_hare:
            q_hare = apply_delta(q_hare, [r[1] for r in results])
        greedy = evaluate(q_shooter, q_hare, freeze_hare=freeze_hare)
        greedy["iteration"] = iteration
        greedy["states"] = len(q_shooter)
        history.append(greedy)
        if iteration % 10 == 0 or iteration == 1:
            print(f"{iteration:>5}{greedy['accuracy']:>10.3f}{greedy['kills']:>8}{greedy['return']:>9.2f}")

    out.mkdir(parents=True, exist_ok=True)
    (out / "shooter_q.json").write_text(json.dumps(q_shooter, indent=1), encoding="utf-8")
    (out / "hare_q.json").write_text(json.dumps(q_hare, indent=1), encoding="utf-8")
    (out / "history.json").write_text(json.dumps(history, indent=1), encoding="utf-8")
    print(f"\nwritten to {out}")


def show(out: Path) -> None:
    history = json.loads((out / "history.json").read_text(encoding="utf-8"))
    print(f"{'iter':>5}{'accuracy':>10}{'kills':>7}{'return':>10}")
    for row in history[:: max(1, len(history) // 12)]:
        print(f"{row['iteration']:>5}{row['accuracy']:>10.3f}{row['kills']:>7}{row['return']:>10.2f}")

    q = json.loads((out / "shooter_q.json").read_text(encoding="utf-8"))
    print("\nwhat the shooter learned, by armour left and magazine state:")
    print(f"{'state':<10}{'best action':>14}{'value':>9}")
    for state in sorted(q, key=lambda s: (s.split('|')[0], s.split('|')[1], s.split('|')[2]))[:14]:
        row = q[state]
        best = max(row.items(), key=lambda kv: kv[1])
        print(f"{state:<10}{best[0]:>14}{best[1]:>9.2f}")

    paths = {"lean -1": -LEAN_EFFECT, "lean 0": 0.0, "lean +1": LEAN_EFFECT}
    print("\nthe bow it was never told about:", paths)
    for lean in (-1, 0, 1):
        picks = [max(q[s].items(), key=lambda kv: kv[1])[0]
                 for s in q if s.endswith(f"|{lean}") and s.split("|")[0] == "3"]
        if picks:
            print(f"  lean {lean:+d}: preferred aim {max(set(picks), key=picks.count)}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Q-learning for the houses game.")
    parser.add_argument("--iterations", type=int, default=100)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--episodes", type=int, default=400, help="episodes per worker per iteration")
    parser.add_argument("--out", type=Path, default=Path(__file__).with_name("rl"))
    parser.add_argument("--show", action="store_true")
    parser.add_argument("--freeze-hare", action="store_true",
                        help="hold the hare random, to see whether the shooter learns at all")
    parser.add_argument("--alpha", type=float, default=ALPHA, help="learning rate")
    args = parser.parse_args()

    if args.show:
        show(args.out)
    else:
        train(args.iterations, args.workers, args.episodes, args.out, args.freeze_hare, args.alpha)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
