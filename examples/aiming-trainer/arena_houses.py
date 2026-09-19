"""The arena with houses: four shelters, each with twenty clicks of life.

The rules the hiding model is given, in its own generated source:

  * there are four houses, and every one of them stands for twenty clicks;
  * a click that lands on a house is taken by the house, not by whoever is inside;
  * while you are inside a house you are not visible to the chaser;
  * when a house runs out it vanishes and comes back somewhere else, at least a
    hundred pixels from where it stood;
  * you are visible exactly while you are between houses, and that is when a click
    can reach you.

So the hiding model has one job - be inside a house when the click lands, and be
somewhere else when your house is about to run out - and the chaser has the harder
one, because most of the time it cannot see what it is trying to hit.

    python arena_houses.py                # fullscreen
    python arena_houses.py --windowed
    python arena_houses.py --no-hide      # draw the evader inside houses too

Keys:  space pause · ←/→ speed · w rewrite now · r restart · h toggle hiding · Esc quit
"""

from __future__ import annotations

import argparse
import json
import math
import random
import textwrap
import time
from dataclasses import dataclass, field
from pathlib import Path

import tkinter as tk

GEN = Path(__file__).with_name("gen-houses")

HOUSE_COUNT = 4
HOUSE_W = 118
HOUSE_H = 86
HOUSE_HP = 20
MIN_RESPAWN_DISTANCE = 100.0
MAX_STAY = 8             # rounds in one house before it is too hot to keep
CROSS_TICKS = 13         # was 4, then 6, then 9, now a third slower again
SHOTS_PER_MAGAZINE = 8   # then the shooter is reloading
RELOAD_SECONDS = 2.0
ARMOR_MAX = 3            # clicks to strip the armour, then one more to kill
MATCH_SECONDS = 600.0    # a safety net; a match is supposed to end with a kill

# The crossing is a curve, not a straight line, and the bow is what a trained
# shooter can correct for and an untrained one cannot. OFFSET_PX is what one unit
# of the learned aim offset is worth in pixels; LEAN_EFFECT is how far the path
# really bows, in the same units. The two are deliberately close, so the policy the
# reinforcement learner found transfers as the aim it learned to make.
LEAN_EFFECT = 1.2
OFFSET_PX = 14.0
RL_DIR = Path(__file__).with_name("rl")

# The shooter is paid for damage and for the kill; the hare is paid for time, and
# time is the only thing it is paid for. A second of life is one point, which makes
# the two totals comparable without pretending they measure the same thing.
POINTS_HIT = 1.0
POINTS_KILL = 2.0
POINTS_HOUSE = 0.5
POINTS_PER_SECOND_ALIVE = 1.0

LATENCY = 3
ROUNDS_PER_GENERATION = 5
EVADER_RADIUS = 9
RULES = (
    "Four houses stand, twenty clicks each.",
    "A click on a house is taken by the house, never by whoever is inside.",
    "Inside a house you cannot be seen.",
    "A house that runs out returns at least a hundred pixels away.",
    "You are visible only while travelling, and that is when a click can reach you.",
    f"You may not sit in one house longer than {MAX_STAY} rounds; it gets too hot.",
    f"You wear armour worth {ARMOR_MAX} clicks. When it is gone, the next click kills you.",
    "Reaching a house repairs your armour, and the house pays for every point restored.",
    f"The shooter fires {SHOTS_PER_MAGAZINE} shots, then reloads for {RELOAD_SECONDS:.0f} seconds.",
    "Your score is the time you stay alive. Nothing else is worth anything to you.",
)


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def mag_bucket(shots: int) -> int:
    if shots <= 0:
        return 0
    return 1 if shots <= 4 else 2


def hp_bucket(hp: int) -> int:
    return 0 if hp <= 6 else (1 if hp <= 13 else 2)


class RlPolicy:
    """The trained tables, and the two questions the arena asks of them.

    Loaded rather than learned here: the learning happened in rl_train.py, on a
    compact model of this game, over a hundred iterations across twelve processes.
    What arrives is a policy - a mapping from what each agent can see to what it
    should do - and the arena simply obeys it.
    """

    def __init__(self, directory: Path) -> None:
        self.shooter = json.loads((directory / "shooter_q.json").read_text(encoding="utf-8"))
        self.hare = json.loads((directory / "hare_q.json").read_text(encoding="utf-8"))

    @staticmethod
    def _best(row: dict[str, float], default: str) -> str:
        if not row:
            return default
        top = max(row.values())
        return random.choice([a for a, v in row.items() if v == top])

    def shooter_action(self, armour: int, shots: int, lean: int) -> str:
        """One of the five aim offsets, in units of OFFSET_PX, or 'reload'."""
        return self._best(self.shooter.get(f"{armour}|{mag_bucket(shots)}|{lean}", {}), "0")

    def hare_action(self, armour: int, stay: int, best_hp: int) -> str:
        """'stay', 'near' or 'far'."""
        return self._best(self.hare.get(f"{armour}|{min(stay, 2)}|{hp_bucket(best_hp)}", {}), "near")


@dataclass
class House:
    x: float
    y: float
    hp: int = HOUSE_HP
    flash: int = 0
    born: int = 0

    @property
    def left(self) -> float:
        return self.x - HOUSE_W / 2

    @property
    def top(self) -> float:
        return self.y - HOUSE_H / 2

    @property
    def right(self) -> float:
        return self.x + HOUSE_W / 2

    @property
    def bottom(self) -> float:
        return self.y + HOUSE_H / 2

    def contains(self, px: float, py: float) -> bool:
        return self.left <= px <= self.right and self.top <= py <= self.bottom


@dataclass
class Agent:
    """Same shape as the other arena: a strategy with a memory of its own shapes."""

    name: str
    modes: dict[str, dict[str, float]]
    mode: str
    rules: tuple[str, ...] = ()
    params: dict[str, float] = field(default_factory=dict)
    scores: dict[str, float] = field(default_factory=lambda: {})
    wins: int = 0
    losses: int = 0
    generation: int = 1
    last_note: str = "born"
    points: float = 0.0
    battle: dict[str, float] = field(default_factory=dict)

    # ── learning state ────────────────────────────────────────────────────
    # The first version of this arena had none of this. Every rewrite multiplied
    # the *template* value by a random factor, so whatever had been tuned was
    # thrown away each time and the parameters were re-rolled from scratch. That is
    # not learning, it is a lottery with a memory for the shape only. Now a change
    # is proposed, tried, and kept only if the score it produced was better, with
    # the step size growing when it works and shrinking when it does not.
    best_params: dict[str, float] = field(default_factory=dict)
    best_score: float = -1.0
    on_trial: dict[str, float] | None = None
    step: dict[str, float] = field(default_factory=dict)
    gen_wins: float = 0.0
    gen_total: float = 0.0
    accepted: int = 0
    rejected: int = 0

    def __post_init__(self) -> None:
        if not self.params:
            self.params = dict(self.modes[self.mode])
        self.best_params = dict(self.params)
        if not self.scores:
            self.scores = {name: 0.0 for name in self.modes}
        if not self.step:
            self.step = {key: 0.18 for key in self.params}

    def score(self, won: bool) -> None:
        if won:
            self.wins += 1
            self.gen_wins += 1
        else:
            self.losses += 1
        self.gen_total += 1
        self.scores[self.mode] = self.scores[self.mode] * 0.7 + (1.0 if won else 0.0) * 0.3

    def rewrite(self, radical: bool = False) -> str:
        """Keep what worked, revert what did not, and propose one change.

        This is a hill climb with one candidate at a time. The generation just
        played was a trial of the parameters currently in `params`; its score is
        compared with the best seen so far, and the trial is accepted or thrown
        away accordingly. The step size follows the simplest rule there is - grow it
        when a change is accepted, shrink it when one is rejected - so the search
        settles instead of oscillating, and can escape again if it stops improving.

        The shape is a separate decision, and a coarser one: a four-armed bandit over
        the modes, scored by a decaying average, plus the battle statistics on a
        radical rewrite. Numbers tune a strategy; only a different shape can fix a
        strategy whose shape is wrong.
        """
        self.generation += 1
        previous_mode, previous_params = self.mode, dict(self.params)

        # 1. Judge the trial that just finished.
        verdict = "first"
        if self.gen_total > 0:
            trial_score = self.gen_wins / self.gen_total
            if trial_score > self.best_score:
                self.best_params = dict(self.params)
                self.best_score = trial_score
                self.accepted += 1
                self.step = {k: min(0.45, v * 1.25) for k, v in self.step.items()}
                verdict = f"kept {trial_score:.2f}"
            else:
                self.params = dict(self.best_params)
                self.rejected += 1
                self.step = {k: max(0.02, v * 0.8) for k, v in self.step.items()}
                verdict = f"reverted from {trial_score:.2f}"

        # 2. Choose a shape: mostly the best so far, sometimes another.
        if radical and self.battle:
            wanted = self.preferred_mode()
            if wanted is not None:
                self.mode = wanted
            else:
                self.mode = max(self.scores.items(), key=lambda kv: kv[1])[0]
        else:
            best = max(self.scores.items(), key=lambda kv: kv[1])
            self.mode = best[0] if random.random() < 0.8 else random.choice(list(self.modes))

        # 3. If the shape changed, the numbers belonged to the old shape.
        if self.mode != previous_mode:
            self.params = dict(self.modes[self.mode])
            self.best_params = dict(self.params)
            self.best_score = -1.0
            self.step = {key: 0.18 for key in self.params}

        # 4. Propose one change to the numbers, from where they are now - not from
        # the template, which is what made the earlier version a re-roll.
        self.params = {
            key: _clamp(value + random.gauss(0, self.step.get(key, 0.18)), 0.0, 1.0)
            for key, value in self.params.items()
        }
        self.gen_wins = 0.0
        self.gen_total = 0.0

        changed = [f"{k} {previous_params.get(k, 0):.2f}->{v:.2f}"
                   for k, v in self.params.items()
                   if abs(previous_params.get(k, 0) - v) > 0.02]
        if self.mode != previous_mode:
            note = f"mode {previous_mode} -> {self.mode}"
        else:
            note = ", ".join(changed) if changed else "no change worth making"
        self.last_note = f"{verdict}; {note}"
        self.write_source()
        return self.last_note

    def preferred_mode(self) -> str | None:
        """A shape suggested by the match that just ended.

        This is the whole reason a radical rewrite is worth having. Tuning numbers
        cannot fix a strategy whose shape is wrong, and the running score cannot say
        what went wrong - but the battle can. The hider's statistics know whether it
        died in the open or was cornered; the chaser's know whether its clicks were
        finding anything at all.
        """
        b = self.battle
        if self.name == "Chaser":
            if b.get("wasted", 0) > max(1.0, b.get("useful", 0)):
                return "siege"              # too many clicks landing on nothing
            if b.get("kills", 0) >= 1:
                return None                 # it worked; keep the shape and tune it
            return "intercept"
        if self.name == "Hider":
            if b.get("died_crossing", 0) >= 1 or b.get("hits_taken", 0) >= 2:
                return "leave-late"         # being caught in the open; stay put longer
            if b.get("repairs", 0) >= 2:
                return "leave-early"        # repairing saved it; do it sooner
            return None
        return None

    def battle_summary(self) -> str:
        # Short on purpose: the rewrite note is drawn beside the other agent's lines
        # and a full battle dump runs straight through them.
        items = sorted(self.battle.items())[:3]
        return " ".join(f"{k}={v:.0f}" for k, v in items)

    def write_source(self) -> Path:
        GEN.mkdir(exist_ok=True)
        path = GEN / f"{self.name.lower()}_gen{self.generation:02d}.py"
        rules = "\n".join(f"#   - {line}" for line in self.rules) if self.rules else "#   (no rulebook for this role)"
        body = (
            f'"""Generation {self.generation} of the {self.name}.\n\n'
            f"The rules it is playing by:\n{rules}\n\n"
            f"Written by the arena after {ROUNDS_PER_GENERATION} rounds of experience.\n"
            f"Change from the previous generation: {self.last_note}\n"
            f"Score so far - {self.wins} won, {self.losses} lost\n"
            f'"""\n\n'
            f"MODE = {self.mode!r}\n\n"
            f"PARAMS = {{\n"
            + "".join(f"    {k!r}: {v:.3f},\n" for k, v in self.params.items())
            + "}\n\n"
            f"SHAPES = {{\n"
            + "".join(f"    {k!r}: {v:.3f},\n" for k, v in self.scores.items())
            + "}\n"
        )
        path.write_text(body, encoding="utf-8")
        return path


def make_clicker() -> Agent:
    return Agent(
        name="Chaser",
        mode="intercept",
        rules=(
            "The hider is invisible inside a house and visible between them.",
            "You can only reach it in the open, which means the crossing.",
        ),
        modes={
            # Pressure the house it is sitting in, and switch to the crossing only
            # when that house is nearly down and the hider is about to run. Doing
            # one or the other is what the earlier versions did: aiming only at
            # crossings wasted seven clicks in eight on empty ground and never broke
            # a single house, and aiming only at houses never touched the hider.
            "siege": {"commit": 0.9, "spread": 0.10, "break": 0.7},
            # Aim where it must pass: halfway between the house it was last seen in
            # and the one it is most likely to run to.
            "intercept": {"commit": 0.8, "spread": 0.15, "break": 0.6},
            # Break the house it is hiding in until it has to run, then wait on the
            # likely crossing.
            "camp": {"commit": 0.6, "spread": 0.10, "break": 1.0},
            # Everything at once, for when the belief is wrong.
            "spread": {"commit": 0.1, "spread": 0.9, "break": 0.2},
        },
    )


def make_evader() -> Agent:
    return Agent(
        name="Hider",
        mode="leave-late",
        rules=RULES,
        modes={
            # Stay until the house is nearly gone, then run.
            "leave-late": {"patience": 0.75, "panic": 0.2, "corner": 0.3},
            # Run at the first click on the house.
            "leave-early": {"patience": 0.1, "panic": 0.9, "corner": 0.3},
            # Move often, on a timer, whether or not anything is happening.
            "restless": {"patience": 0.4, "panic": 0.4, "corner": 0.6},
            # Prefer the house furthest from the last click.
            "far": {"patience": 0.6, "panic": 0.5, "corner": 0.9},
        },
    )


class World:
    def __init__(self, width: float, height: float) -> None:
        self.width = width
        self.height = height
        self.reset()

    def reset(self) -> None:
        self.houses: list[House] = []
        for _ in range(HOUSE_COUNT):
            self.houses.append(House(*self.free_spot()))
        self.house_index = 0            # which house the hider is in
        self.travelling = False
        self.from_house = 0
        self.to_house = 0
        self.progress = 1.0
        self.x, self.y = self.houses[0].x, self.houses[0].y
        self.stay = 0                   # rounds spent in the current house
        self.lean = 0                   # which way this crossing bows
        self.last_seen_house: int | None = 0    # the chaser's belief
        self.last_click: tuple[float, float] | None = None
        self.rope = 0.0
        self.rope_history: list[float] = []
        self.rounds: list[dict[str, object]] = []
        self.round_number = 0
        self.destroyed = 0
        self.match_number = 1
        self.match_catches = 0
        self.match_rope_history: list[float] = []
        self.last_match: str = ""
        self.armor = ARMOR_MAX
        self.killed = False
        self.armor_damage = 0
        self.repairs = 0
        self.died_crossing = False
        self.wasted = 0
        self.useful = 0

    def free_spot(self, avoid: House | None = None) -> tuple[float, float]:
        """A house position that respects the hundred-pixel rule."""
        margin_x, margin_y = HOUSE_W / 2 + 8, HOUSE_H / 2 + 8
        for _ in range(200):
            x = random.uniform(margin_x, max(margin_x + 1, self.width - margin_x))
            y = random.uniform(margin_y, max(margin_y + 1, self.height - margin_y))
            if avoid is not None and math.hypot(x - avoid.x, y - avoid.y) < MIN_RESPAWN_DISTANCE:
                continue
            if any(math.hypot(x - h.x, y - h.y) < HOUSE_W * 0.9 for h in self.houses if h is not avoid):
                continue
            return x, y
        return self.width / 2, self.height / 2

    def visible(self) -> bool:
        return self.travelling

    def path_point(self, t: float) -> tuple[float, float]:
        """A point along the crossing, which is a curve rather than a line.

        A quadratic Bezier from the house it left to the house it is heading for,
        with the control point pushed sideways by the lean. A straight line here
        would leave a trained aimer nothing to correct, and the learner's whole
        finding - that a crossing bows and by how much - would be unusable.
        """
        start = self.houses[self.from_house]
        end = self.houses[self.to_house]
        mid_x = (start.x + end.x) / 2
        mid_y = (start.y + end.y) / 2
        dx, dy = end.x - start.x, end.y - start.y
        length = math.hypot(dx, dy) or 1.0
        # Perpendicular to the line, pushed by the lean.
        bow = LEAN_EFFECT * OFFSET_PX * self.lean
        ctrl_x = mid_x - dy / length * bow
        ctrl_y = mid_y + dx / length * bow
        inv = 1 - t
        return (
            inv * inv * start.x + 2 * inv * t * ctrl_x + t * t * end.x,
            inv * inv * start.y + 2 * inv * t * ctrl_y + t * t * end.y,
        )

    def middle(self) -> tuple[float, float]:
        """The straight-line midpoint - where an aimer who knows nothing would shoot."""
        start = self.houses[self.from_house]
        end = self.houses[self.to_house]
        return ((start.x + end.x) / 2, (start.y + end.y) / 2)

    def perpendicular(self) -> tuple[float, float]:
        start = self.houses[self.from_house]
        end = self.houses[self.to_house]
        dx, dy = end.x - start.x, end.y - start.y
        length = math.hypot(dx, dy) or 1.0
        return (-dy / length, dx / length)


class Arena:
    def __init__(self, root: tk.Tk, windowed: bool, speed: float, hide: bool,
                 policy: RlPolicy | None = None) -> None:
        self.root = root
        self.speed = speed
        self.hide = hide
        self.policy = policy
        self.paused = False

        if not windowed:
            root.attributes("-fullscreen", True)
        else:
            root.geometry("1280x860")
        root.configure(bg="#0e1116")
        self.canvas = tk.Canvas(root, bg="#0e1116", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        root.bind("<Escape>", lambda _e: root.destroy())
        root.bind("<space>", self.toggle_pause)
        root.bind("<Left>", lambda _e: self.change_speed(-0.5))
        root.bind("<Right>", lambda _e: self.change_speed(0.5))
        root.bind("r", lambda _e: self.restart())
        root.bind("w", lambda _e: self.force_rewrite())
        root.bind("h", self.toggle_hide)

        self.chaser = make_clicker()
        self.hider = make_evader()
        # Where the hider has gone when it left each house. The chaser sees every
        # arrival, so this is knowledge it legitimately has, and without it the
        # chaser guesses the same way forever and the score sits at 175 to 5.
        self.transitions: dict[tuple[int, int], int] = {}
        self.chaser.write_source()
        self.hider.write_source()

        self.width = 0.0
        self.height = 0.0
        self.world: World | None = None
        self.phase = "move"
        self.phase_tick = 0
        self.pending: dict[str, object] = {}
        self.flash = ""
        self.flash_left = 0
        self.rewrite_banner = 0
        self.match_banner = 0
        self.match_started = time.monotonic()
        self.shots_fired = 0
        self.reload_until = 0.0
        self.canvas.bind("<Configure>", self.on_resize)
        self.tick()

    # ── the match clock ───────────────────────────────────────────────────
    def match_seconds_left(self) -> float:
        return max(0.0, MATCH_SECONDS - (time.monotonic() - self.match_started))

    def end_match(self, killed: bool = False) -> None:
        """Close the match, hand both agents the battle, and let them rewrite.

        The boundary is not about the score. It is the moment the two agents are
        allowed to change shape - not nudge numbers, which they do every five rounds,
        but read what actually happened and become something else. A hider whose
        statistics say it died in the open should stop crossing so much; a chaser
        whose clicks mostly landed on nothing should stop shooting at nothing.
        Numbers cannot express either of those, which is why this exists.
        """
        world = self.world
        assert world is not None
        world.armor = 0 if killed else world.armor

        if killed:
            headline = f"hider KILLED in {world.round_number} rounds"
        else:
            headline = f"time up after {world.round_number} rounds"
        world.last_match = (
            f"match {world.match_number}: {headline} — "
            f"shooter {self.chaser.points:.1f} / hare {self.hider.points:.0f}s alive"
        )

        # The battle, in the terms each role can act on.
        self.chaser.battle = {
            "rounds": world.round_number,
            "useful": world.useful,
            "wasted": world.wasted,
            "armour": world.armor_damage,
            "kills": 1 if killed else 0,
        }
        self.hider.battle = {
            "rounds": world.round_number,
            "hits": world.armor_damage,
            "repairs": world.repairs,
            "crossings": world.destroyed,
            "died": 1 if killed else 0,
        }
        self.chaser.rewrite(radical=True)
        self.hider.rewrite(radical=True)
        self.rewrite_banner = 70
        self.match_banner = 110

        world.match_number += 1
        world.match_catches = 0
        world.match_rope_history.append(world.rope)
        world.rope = 0.0
        world.rope_history.clear()
        world.rounds.clear()
        world.round_number = 0
        world.armor = ARMOR_MAX
        world.killed = False
        world.armor_damage = 0
        world.repairs = 0
        world.died_crossing = False
        world.wasted = 0
        world.useful = 0
        world.houses = [House(*world.free_spot()) for _ in range(HOUSE_COUNT)]
        world.house_index = 0
        world.stay = 0
        world.travelling = False
        world.x, world.y = world.houses[0].x, world.houses[0].y
        world.last_seen_house = 0
        # Points are per match, because the two of them only mean anything next to
        # each other: a shooter's damage against a hare's seconds.
        self.chaser.points = 0.0
        self.hider.points = 0.0
        self.transitions = {}
        self.match_started = time.monotonic()
        self.shots_fired = 0
        self.reload_until = 0.0
        self.begin_round()

    def toggle_pause(self, _event: object = None) -> None:
        self.paused = not self.paused

    def toggle_hide(self, _event: object = None) -> None:
        self.hide = not self.hide

    def change_speed(self, delta: float) -> None:
        self.speed = _clamp(self.speed + delta, 0.5, 12.0)

    def restart(self) -> None:
        self.chaser = make_clicker()
        self.hider = make_evader()
        self.transitions = {}
        self.chaser.write_source()
        self.hider.write_source()
        if self.world is not None:
            self.world.reset()

    def force_rewrite(self) -> None:
        self.chaser.rewrite()
        self.hider.rewrite()
        self.rewrite_banner = 40
        if self.world is not None:
            self.world.rounds.clear()

    def on_resize(self, event: tk.Event) -> None:
        self.width = float(event.width)
        self.height = float(event.height) - 330
        if self.world is None:
            self.world = World(self.width, self.height)
            self.begin_round()
        else:
            self.world.width = self.width
            self.world.height = self.height

    # ── decisions ─────────────────────────────────────────────────────────
    def hider_move(self) -> int | None:
        """Return the house to run to, or None to stay."""
        w = self.world
        assert w is not None
        p = self.hider.params
        mode = self.hider.mode
        current = w.houses[w.house_index]
        pressure = 1.0 - current.hp / HOUSE_HP

        # With trained tables loaded, the hare's decision is the policy's and the
        # hand-written modes are not consulted at all. That is the point of the
        # exercise: the same state it learned on, answered from what it learned.
        if self.policy is not None:
            best_hp = max(h.hp for h in w.houses)
            action = self.policy.hare_action(w.armor, w.stay, best_hp)
            if action == "stay" and w.stay < MAX_STAY:
                return None
            options = [i for i in range(len(w.houses)) if i != w.house_index]
            if not options:
                return None
            if action == "far":
                return max(options, key=lambda i: w.houses[i].hp)
            return random.choice(options)

        threshold = 1.0 - p.get("patience", 0.5) * 0.85
        should_leave = pressure >= threshold
        # The rule that keeps the game alive. Without it a hider whose house is not
        # being broken never moves, so there are no crossings, so the chaser has
        # nothing to intercept and the score runs 155 to 3 while nothing happens.
        if w.stay >= MAX_STAY:
            should_leave = True
        # Armour only comes back on arrival, so a damaged hider has to cross to
        # repair - and crossing is exactly when it can be hit. The lower the armour,
        # the stronger the pull to run, which is the trade the mechanic creates.
        if w.armor < ARMOR_MAX:
            urge = 0.3 + 0.5 * (1.0 - w.armor / ARMOR_MAX)
            if random.random() < urge:
                should_leave = True
        if random.random() < p.get("panic", 0.3) * 0.35:
            should_leave = True
        if mode == "restless" and w.round_number % 4 == 0:
            should_leave = True
        if not should_leave:
            return None

        options = [i for i in range(len(w.houses)) if i != w.house_index]
        if not options:
            return None
        if mode in ("far", "leave-late") and w.last_click is not None:
            # Prefer distance from where the chaser last aimed.
            options.sort(
                key=lambda i: -math.hypot(w.houses[i].x - w.last_click[0],  # type: ignore[index]
                                          w.houses[i].y - w.last_click[1]),  # type: ignore[index]
            )
            weight = p.get("corner", 0.5)
            if random.random() < weight:
                return options[0]
        return random.choice(options)

    def chaser_aim(self) -> tuple[float, float]:
        """Where to click. Almost all of the game is in this function.

        The hider is untouchable inside a house, so a click that lands in one only
        costs the house a life. The only reachable moment is the crossing, so the
        chaser has to aim at a line between two houses rather than at a house, and
        it has to guess which line.
        """
        w = self.world
        assert w is not None
        p = self.chaser.params
        mode = self.chaser.mode
        spread = (1.0 - p.get("commit", 0.5)) * HOUSE_W * 0.5
        # The armour is on screen, so the chaser knows when the next hit is the last
        # one. It tightens up: this is the shot worth being careful about, and a
        # strategy that cannot tell a graze from a kill wastes its best chances.
        if w.armor == 0:
            spread *= 0.35

        if mode == "spread" or random.random() < p.get("spread", 0.15):
            x = random.uniform(0, self.width)
            y = random.uniform(0, self.height)
            return x, y

        if w.last_seen_house is None:
            house = random.choice(w.houses)
            return house.x + random.uniform(-spread, spread), house.y + random.uniform(-spread, spread)

        origin = w.houses[w.last_seen_house]
        others = [h for i, h in enumerate(w.houses) if i != w.last_seen_house]
        others.sort(key=lambda h: math.hypot(h.x - origin.x, h.y - origin.y))

        # What this hider has actually done before, when it left this house. The
        # chaser has watched every arrival, so using it is not cheating; not using
        # it is why the first versions of this game never caught anything.
        counts = {
            index: self.transitions.get((w.last_seen_house, index), 0)
            for index in range(len(w.houses))
            if index != w.last_seen_house
        }
        predicted: int | None = None
        if counts and max(counts.values()) > 0:
            predicted = max(counts.items(), key=lambda item: item[1])[0]

        target = others[0] if others else origin
        if mode == "guess" and len(others) > 1:
            target = others[-1]
        if predicted is not None and mode in ("intercept", "camp", "siege"):
            target = w.houses[predicted]
        if predicted is not None and mode == "guess" and random.random() < 0.5:
            target = w.houses[predicted]

        # The siege: work on the house while the hider is comfortably inside it,
        # and move to the crossing once it is nearly down and the run is coming.
        if mode == "siege":
            nearly_down = origin.hp <= 5 or (w.stay >= MAX_STAY - 2)
            if not nearly_down and random.random() < p.get("break", 0.7):
                return (origin.x + random.uniform(-spread, spread),
                        origin.y + random.uniform(-spread, spread))

        if mode == "camp" and origin.hp > HOUSE_HP * 0.35 and random.random() < p.get("break", 0.8):
            # Keep the pressure on the house it is sitting in, so it is forced out.
            return origin.x + random.uniform(-spread, spread), origin.y + random.uniform(-spread, spread)

        # Halfway along the line it must cross.
        mid_x = (origin.x + target.x) / 2
        mid_y = (origin.y + target.y) / 2
        return (
            _clamp(mid_x + random.uniform(-spread, spread), 0, self.width),
            _clamp(mid_y + random.uniform(-spread, spread), 0, self.height),
        )

    def begin_round(self) -> None:
        w = self.world
        assert w is not None
        target = self.hider_move()
        aim = self.chaser_aim()
        self.pending = {"run_to": target, "aim": aim}
        if target is not None:
            w.travelling = True
            w.from_house = w.house_index
            w.to_house = target
            w.progress = 0.0
            # Which way the crossing bows. The shooter can see the lean - it is the
            # cue the policy was trained on - but not how far the path really bends.
            w.lean = random.choice((-1, 0, 1))
        if self.policy is not None and w.travelling:
            self.pending["rl"] = self.policy.shooter_action(w.armor, self.shots_fired, w.lean)
        self.phase = "move"
        self.phase_tick = 0

    def finish_round(self) -> None:
        w = self.world
        assert w is not None
        aim = self.pending["aim"]
        ax, ay = aim                                          # type: ignore[misc]

        hit_house: int | None = None
        for index, house in enumerate(w.houses):
            if house.contains(ax, ay):
                hit_house = index
                break

        # A click on a house is taken by the house, never by whoever is inside.
        w.last_click = (ax, ay)
        outcome = "MISS"
        killed_now = False
        struck_hider = False

        if hit_house is not None:
            w.houses[hit_house].hp -= 1
            w.houses[hit_house].flash = 4
            w.useful += 1
            self.chaser.points += POINTS_HOUSE
            outcome = "HOUSE"
        elif w.travelling:
            spread = (1.0 - self.chaser.params.get("commit", 0.5)) * HOUSE_W * 0.5
            if w.armor == 0:
                spread *= 0.35

            # With trained tables the aim is the policy's: the straight midpoint,
            # shifted sideways by the offset it learned. Without them it is whatever
            # the hand-written modes decided, which is also the straight midpoint
            # plus a little noise - which is exactly why the untrained shooter cannot
            # hit a curved crossing as well, and what the comparison is for.
            rl_action = self.pending.get("rl")
            mid_x, mid_y = w.middle()
            perp_x, perp_y = w.perpendicular()
            if rl_action is not None and rl_action != "reload":
                offset = int(rl_action) * OFFSET_PX
                ax = mid_x + perp_x * offset
                ay = mid_y + perp_y * offset

            landed = 0
            for _ in range(CROSS_TICKS):
                now = time.monotonic()
                if rl_action == "reload":
                    continue                        # the whole crossing is given up
                if now < self.reload_until:
                    continue
                if self.shots_fired >= SHOTS_PER_MAGAZINE:
                    self.reload_until = now + RELOAD_SECONDS
                    self.shots_fired = 0
                    continue
                self.shots_fired += 1

                shot_x = ax + random.uniform(-spread, spread)
                shot_y = ay + random.uniform(-spread, spread)
                shot_hit = False
                for step in range(17):
                    px, py = w.path_point(step / 16)
                    if math.hypot(shot_x - px, shot_y - py) <= EVADER_RADIUS + 6:
                        shot_hit = True
                        break
                if not shot_hit:
                    continue

                landed += 1
                struck_hider = True
                if w.armor > 0:
                    w.armor -= 1
                    w.armor_damage += 1
                    self.chaser.points += POINTS_HIT
                    outcome = f"HIT armour {w.armor}"
                elif not killed_now:
                    # Stripped, and this is the extra hit: the hare dies and the
                    # match is over.
                    killed_now = True
                    w.died_crossing = True
                    self.chaser.points += POINTS_KILL
                    outcome = f"KILLED after {landed} hit(s)"
            if landed:
                w.useful += 1
            else:
                w.wasted += 1
        else:
            w.wasted += 1

        # The hare is paid in time and in nothing else, so its score is simply how
        # long it has been alive. Read live rather than accumulated, because that is
        # exactly what it means: the clock is the score.
        self.hider.points = time.monotonic() - self.match_started

        w.rounds.append({"hit": struck_hider, "aim": (ax, ay), "house": hit_house})
        if len(w.rounds) > 24:
            w.rounds.pop(0)
        w.round_number += 1

        # Arrive, and remember who saw what. This happens after the click, because
        # the click was resolved against the crossing.
        if w.travelling:
            w.progress = 1.0
            w.travelling = False
            if w.to_house != w.from_house:
                key = (w.from_house, w.to_house)
                self.transitions[key] = self.transitions.get(key, 0) + 1
            w.house_index = w.to_house
            w.last_seen_house = w.to_house
            w.stay = 0
            house = w.houses[w.house_index]
            w.x, w.y = house.x, house.y

            # Shelter repairs the armour, and the house pays for every point of it.
            # That is the hare's whole economy: safety costs the thing it hides
            # behind, so a hare that repairs often destroys its own cover. No points
            # change hands for it - the hare is paid in seconds, and a repair buys
            # exactly that.
            missing = ARMOR_MAX - w.armor
            if missing > 0 and house.hp > 0 and not killed_now:
                paid = min(missing, house.hp)
                house.hp -= paid
                w.armor += paid
                w.repairs += paid
                outcome = f"REPAIRED {paid}"
        else:
            w.stay += 1

        # A house that runs out returns at least a hundred pixels away.
        for index, house in enumerate(w.houses):
            if house.hp > 0:
                continue
            old = House(house.x, house.y)
            x, y = w.free_spot(avoid=old)
            w.houses[index] = House(x, y, born=w.round_number)
            w.destroyed += 1
            if w.house_index == index and not w.travelling:
                # Its shelter vanished underneath it: exposed until it reaches one.
                w.x, w.y = x, y
                w.house_index = index
                w.last_seen_house = index

        # The rope is the points, normalised. Two different currencies, so it is a
        # balance rather than a tally: the hider is paid for time and repairs, the
        # chaser for damage and for the kill.
        # The rope is the points, normalised: the shooter's damage against the
        # hare's seconds alive, on one scale so the balance is visible at a glance.
        total = max(12.0, float(self.chaser.points + self.hider.points))
        w.rope = _clamp((self.chaser.points - self.hider.points) / total, -1.0, 1.0)
        if struck_hider:
            w.match_catches += 1
        w.rope_history.append(w.rope)
        if len(w.rope_history) > 900:
            w.rope_history.pop(0)

        # Which shape is worth keeping is a different question from who is winning,
        # and confusing the two threw away the pressure strategy earlier: it scored
        # nothing, because pressure wins nothing immediately.
        self.chaser.score(hit_house is not None or struck_hider)
        self.hider.score(not killed_now)
        self.flash = outcome
        self.flash_left = 8
        if killed_now:
            self.flash = outcome
            self.flash_left = 20

        if killed_now:
            self.end_match(killed=True)
            return

        if w.round_number % ROUNDS_PER_GENERATION == 0:
            self.chaser.rewrite()
            self.hider.rewrite()
            self.rewrite_banner = 30

    # ── loop ──────────────────────────────────────────────────────────────
    def tick(self) -> None:
        if not self.paused and self.world is not None and self.width > 0:
            self.phase_tick += 1
            if self.phase == "move":
                steps = CROSS_TICKS
                world = self.world
                # The crossing is animated to the halfway point, because halfway is
                # where the click lands. Resolving it after the hider had arrived
                # made the traveller unhittable, which removed the entire game: the
                # only moment the chaser can see it is the only moment it cannot
                # be hit.
                if self.pending.get("run_to") is not None:
                    world.progress = min(0.5, world.progress + 0.5 / steps)
                    # Along the curve, not along a line.
                    world.x, world.y = world.path_point(world.progress)
                if self.phase_tick >= steps:
                    self.phase = "click"
                    self.phase_tick = 0
            else:
                for house in self.world.houses:
                    house.flash = max(0, house.flash - 1)
                if self.phase_tick >= 3:
                    self.finish_round()
                    self.begin_round()
                    if self.match_seconds_left() <= 0:
                        self.end_match()
        if self.match_banner > 0:
            self.match_banner -= 1
        self.draw()
        self.root.after(max(16, int(1000 / (self.speed * 8))), self.tick)

    # ── drawing ───────────────────────────────────────────────────────────
    def draw(self) -> None:
        c = self.canvas
        c.delete("all")
        w, h = self.width, self.height
        if w <= 10 or h <= 10 or self.world is None:
            return
        world = self.world

        c.create_rectangle(2, 2, w - 2, h - 2, outline="#1d2530", width=2)
        for gx in range(0, int(w), 60):
            c.create_line(gx, 0, gx, h, fill="#141a22")
        for gy in range(0, int(h), 60):
            c.create_line(0, gy, w, gy, fill="#141a22")

        # the houses
        for index, house in enumerate(world.houses):
            occupied = (not world.travelling) and index == world.house_index
            edge = "#3f7fbf" if occupied else "#2b3644"
            fill = "#16202c" if occupied else "#121820"
            width = 3 if occupied else 1
            if house.flash > 0:
                fill = "#3a2020"
            c.create_rectangle(house.left, house.top, house.right, house.bottom,
                               fill=fill, outline=edge, width=width)
            # the life strip: twenty clicks
            ratio = max(0.0, house.hp / HOUSE_HP)
            bx0, by0 = house.left + 6, house.bottom - 12
            bx1 = house.right - 6
            c.create_rectangle(bx0, by0, bx1, by0 + 6, fill="#241a1c", outline="")
            tone = "#2fbf71" if ratio > 0.5 else ("#e0a419" if ratio > 0.25 else "#e05561")
            c.create_rectangle(bx0, by0, bx0 + (bx1 - bx0) * ratio, by0 + 6, fill=tone, outline="")
            c.create_text((house.left + house.right) / 2, house.top + 12,
                          text=f"house {index + 1}   {max(0, house.hp)}/{HOUSE_HP}",
                          fill="#7f8b98", font=("Consolas", 10))
            if occupied and not self.hide:
                self.draw_armour(house.x, house.y - 26)

        # the hider, visible only while it is between houses
        if world.travelling:
            start = world.houses[world.from_house]
            end = world.houses[world.to_house]
            # The path as it really is: a curve, drawn as a chain of segments.
            points: list[float] = []
            for step in range(19):
                px, py = world.path_point(step / 18)
                points.extend([px, py])
            c.create_line(*points, fill="#4a4130", dash=(4, 4))
            c.create_oval(world.x - EVADER_RADIUS, world.y - EVADER_RADIUS,
                          world.x + EVADER_RADIUS, world.y + EVADER_RADIUS,
                          fill="#f0c419", outline="#fff3c4", width=2)
            self.draw_armour(world.x, world.y - 24)
            # Where a shooter that knows nothing would aim, against where this one did.
            mid_x, mid_y = world.middle()
            c.create_line(mid_x - 5, mid_y - 5, mid_x + 5, mid_y + 5, fill="#39424e", width=2)
            c.create_line(mid_x - 5, mid_y + 5, mid_x + 5, mid_y - 5, fill="#39424e", width=2)

        # Where the armour stands, drawn wherever the hider is known to be. Three
        # pips: full means three more clicks will not kill it, empty means the next
        # click does.
        if not world.travelling:
            house = world.houses[world.house_index]
            self.draw_armour(house.x, house.y + HOUSE_H / 2 + 14, hint=True)

        # clicks of the recent rounds
        for entry in world.rounds:
            ax, ay = entry["aim"]                              # type: ignore[misc]
            if entry["hit"]:
                colour, size = "#e05561", 11
            elif entry["house"] is not None:
                colour, size = "#8a6d1f", 6
            else:
                colour, size = "#3a4550", 5
            c.create_line(ax - size, ay, ax + size, ay, fill=colour, width=2)
            c.create_line(ax, ay - size, ax, ay + size, fill=colour, width=2)

        aim = self.pending.get("aim")
        if aim and self.phase == "move":
            ax, ay = aim                                        # type: ignore[misc]
            c.create_line(ax - 14, ay, ax + 14, ay, fill="#e05561", width=2)
            c.create_line(ax, ay - 14, ax, ay + 14, fill="#e05561", width=2)

        if world.last_seen_house is not None and self.phase == "move":
            house = world.houses[world.last_seen_house]
            c.create_text(house.x, house.bottom + 14, text="last seen here",
                          fill="#5f6b77", font=("Consolas", 10))

        self.draw_panels()

    def draw_armour(self, cx: float, cy: float, hint: bool = False) -> None:
        """Three pips. Filled means the click will be absorbed, empty means it kills."""
        c = self.canvas
        world = self.world
        assert world is not None
        gap = 11
        for index in range(ARMOR_MAX):
            x = cx + (index - (ARMOR_MAX - 1) / 2) * gap
            filled = index < world.armor
            if hint:
                colour = "#2f6fbf" if filled else "#3a4550"
                size = 4
            else:
                colour = "#59b0ff" if filled else "#3a4550"
                size = 5
            c.create_oval(x - size, cy - size, x + size, cy + size,
                          fill=colour, outline="#0e1116" if filled else "")

    def draw_panels(self) -> None:
        c = self.canvas
        w = self.width
        world = self.world
        assert world is not None
        mid = w / 2

        bar_y = self.height + 26
        c.create_rectangle(40, bar_y, w - 40, bar_y + 26, fill="#161c24", outline="#26303c")
        c.create_text(70, bar_y + 13, text="CHASER", anchor="w", fill="#e05561",
                      font=("Consolas", 13, "bold"))
        c.create_text(w - 70, bar_y + 13, text="HIDER", anchor="e", fill="#f0c419",
                      font=("Consolas", 13, "bold"))
        if world.rope > 0:
            c.create_rectangle(mid, bar_y + 2, mid + (mid - 44) * world.rope, bar_y + 24, fill="#4b1d24")
        else:
            c.create_rectangle(mid + (mid - 44) * world.rope, bar_y + 2, mid, bar_y + 24, fill="#4b4020")
        c.create_line(mid, bar_y - 4, mid, bar_y + 30, fill="#7b8794", width=2)
        marker = mid + (mid - 44) * world.rope
        c.create_polygon(marker, bar_y - 6, marker - 9, bar_y - 18, marker + 9, bar_y - 18,
                         fill="#f0c419", outline="")
        c.create_text(mid, bar_y + 13, text=f"rope {world.rope:+.2f}", fill="#c8d2dc",
                      font=("Consolas", 11))

        graph_top = bar_y + 36
        graph_height = 34
        c.create_rectangle(40, graph_top, w - 40, graph_top + graph_height,
                           fill="#10161d", outline="#1d2530")
        middle = graph_top + graph_height / 2
        c.create_line(40, middle, w - 40, middle, fill="#26303c")
        history = world.rope_history[-400:]
        if len(history) > 1:
            step = (w - 80) / max(1, len(history) - 1)
            points: list[float] = []
            for index, value in enumerate(history):
                points.extend([40 + index * step, middle - value * (graph_height / 2 - 3)])
            c.create_line(*points, fill="#f0c419", width=2)
        c.create_text(44, graph_top + 8, text="+ chaser", anchor="w", fill="#e05561",
                      font=("Consolas", 9))
        c.create_text(44, graph_top + graph_height - 8, text="+ hider", anchor="w",
                      fill="#f0c419", font=("Consolas", 9))
        c.create_text(w - 44, graph_top + 8, text=f"houses broken {world.destroyed}",
                      anchor="e", fill="#7f8b98", font=("Consolas", 10))

        strip_y = graph_top + graph_height + 22
        c.create_text(46, strip_y, text="rounds", anchor="w", fill="#7b8794", font=("Consolas", 11))
        for index, entry in enumerate(world.rounds):
            x = 110 + index * 22
            if entry["hit"]:
                colour = "#e05561"
            elif entry["house"] is not None:
                colour = "#8a6d1f"
            else:
                colour = "#2a323c"
            c.create_oval(x - 6, strip_y - 6, x + 6, strip_y + 6, fill=colour, outline="#3a4550")

        if self.flash_left > 0:
            self.flash_left -= 1
            text = self.flash
            if text.startswith("ARMOUR"):
                tone = "#e05561"
            elif text.startswith("KILLED"):
                tone = "#ff2d55"
            elif text.startswith("REPAIRED"):
                tone = "#59b0ff"
            elif text == "HOUSE":
                tone = "#8a6d1f"
            else:
                tone = "#5a6672"
            c.create_text(mid, self.height - 60, text=text, fill=tone,
                          font=("Consolas", 34, "bold"))
        if self.rewrite_banner > 0:
            self.rewrite_banner -= 1
            c.create_text(mid, self.height - 86, text="REWRITING THE PROGRAM",
                          fill="#f0c419", font=("Consolas", 20, "bold"))

        self.draw_agent(self.chaser, 40, strip_y + 26, "left", "#e05561")
        self.draw_agent(self.hider, w - 40, strip_y + 26, "right", "#f0c419")
        c.create_text(mid, strip_y + 22,
                      text=f"round {world.round_number}   generation {self.chaser.generation}"
                           f"   speed {self.speed:.1f}x   hiding {'on' if self.hide else 'shown'}"
                           f"   {'PAUSED' if self.paused else 'running'}",
                      fill="#7b8794", font=("Consolas", 12))

        # The match clock. Three minutes is long enough for the agents to rewrite
        # themselves a dozen times, so a match is a unit of evolution rather than a
        # unit of play.
        left = self.match_seconds_left()
        minutes, seconds = divmod(int(left), 60)
        reloading = time.monotonic() < self.reload_until
        magazine = "RELOAD" if reloading else f"mag {self.shots_fired}/{SHOTS_PER_MAGAZINE}"
        # Kept short on purpose: the centre band between the two agent panels is
        # about fifty characters wide, and a longer line runs straight through them.
        clock = (f"match {world.match_number}  {minutes}:{seconds:02d}  {magazine}"
                 f"  |  shooter {self.chaser.points:.1f} vs hare {self.hider.points:.0f}s")
        c.create_text(mid, strip_y + 42, text=clock,
                      fill="#f0c419" if left < 30 else "#98a4b0", font=("Consolas", 12, "bold"))
        if world.last_match:
            c.create_text(mid, strip_y + 60, text=textwrap.shorten(world.last_match, 52, placeholder=" …"),
                          fill="#5f6b77", font=("Consolas", 10))
        c.create_text(mid, strip_y + 96,
                      text="space pause · ←/→ speed · w rewrite · h hiding · r restart · Esc",
                      fill="#4a5560", font=("Consolas", 10))
        if self.match_banner > 0:
            c.create_text(mid, self.height - 130, text="NEW MATCH — the strategies carry over",
                          fill="#f0c419", font=("Consolas", 18, "bold"))

    def draw_agent(self, agent: Agent, x: float, y: float, side: str, colour: str) -> None:
        c = self.canvas
        anchor = "w" if side == "left" else "e"
        c.create_text(x, y, text=f"{agent.name.upper()}  gen {agent.generation}",
                      anchor=anchor, fill=colour, font=("Consolas", 13, "bold"))
        c.create_text(x, y + 17, text=f"shape {agent.mode}   {agent.points:.1f} pts   kept {agent.accepted}/{agent.rejected}",
                      anchor=anchor, fill="#98a4b0", font=("Consolas", 10))
        c.create_text(x, y + 33, text="  ".join(f"{k}={v:.2f}" for k, v in list(agent.params.items())[:3]),
                      anchor=anchor, fill="#6b7783", font=("Consolas", 10))
        shapes = "  ".join(
            f"{name}:{score:.2f}{'*' if name == agent.mode else ''}"
            for name, score in sorted(agent.scores.items(), key=lambda kv: -kv[1])[:3]
        )
        c.create_text(x, y + 49, text=shapes, anchor=anchor, fill="#5f6b77", font=("Consolas", 9))
        c.create_text(x, y + 65, text=f"rewrite: {textwrap.shorten(agent.last_note, 58, placeholder=' …')}",
                      anchor=anchor, fill="#5a6672", font=("Consolas", 10))


def main() -> int:
    parser = argparse.ArgumentParser(description="Four houses, twenty clicks each, one hider.")
    parser.add_argument("--windowed", action="store_true")
    parser.add_argument("--speed", type=float, default=2.5)
    parser.add_argument("--no-hide", action="store_true", help="draw the hider inside houses too")
    parser.add_argument("--rl", action="store_true", help="drive both agents from the trained tables")
    parser.add_argument("--rl-dir", type=Path, default=RL_DIR)
    args = parser.parse_args()

    policy = None
    if args.rl:
        if not (args.rl_dir / "shooter_q.json").exists():
            print(f"no trained tables in {args.rl_dir} - run rl_train.py first")
            return 1
        policy = RlPolicy(args.rl_dir)
        print(f"driving both agents from {args.rl_dir}")

    root = tk.Tk()
    root.title("Houses: chaser vs hider" + (" [RL]" if policy else ""))
    Arena(root, windowed=args.windowed, speed=args.speed, hide=not args.no_hide, policy=policy)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
