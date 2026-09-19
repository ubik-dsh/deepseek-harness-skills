"""A fullscreen arena where two agents fight over one target, and rewrite themselves.

One agent owns the click. The other owns the target. The clicker scores by landing
on it; the evader scores by being somewhere else. Neither sees the other's decision
for the round - both commit from the same picture, which is what makes it a game
rather than a demonstration.

Every five rounds each agent rewrites its own program. Not a metaphor: it writes a
real Python file into gen/, and the next round runs that file's strategy. The
rewrite is bounded to a set of modes and numbers rather than free-form generation,
and that bound is the honest limit of this version - swap `Agent.rewrite` for a
call to a model and the rest of the program does not change.

    python arena.py                 # fullscreen
    python arena.py --windowed      # a window, for testing
    python arena.py --speed 2       # rounds per second

Keys:  space pause · ←/→ speed · r restart · w force a rewrite · Esc quit
"""

from __future__ import annotations

import argparse
import math
import random
import textwrap
from dataclasses import dataclass, field
from pathlib import Path

import tkinter as tk

GEN = Path(__file__).with_name("gen")

TARGET_RADIUS = 20
LATENCY = 3              # ticks the target travels between the decision and the click
ROUNDS_PER_GENERATION = 5
TRAIL = 22               # how much target history to keep, for the eye
CLICK_HISTORY = 18


# ── the two brains ────────────────────────────────────────────────────────

@dataclass
class Agent:
    """A strategy that can rewrite itself from what happened to it.

    `modes` are the shapes of program this agent is allowed to become. Keeping the
    score per mode is what makes the rewrite a decision rather than a random walk:
    an agent that changes shape every generation and never remembers which shape
    worked is not learning, it is twitching.
    """

    name: str
    modes: dict[str, dict[str, float]]
    mode: str
    params: dict[str, float] = field(default_factory=dict)
    scores: dict[str, float] = field(default_factory=lambda: {})
    wins: int = 0
    losses: int = 0
    generation: int = 1
    last_note: str = "start"

    def __post_init__(self) -> None:
        if not self.params:
            self.params = dict(self.modes[self.mode])
        if not self.scores:
            self.scores = {name: 0.0 for name in self.modes}

    def score(self, won: bool) -> None:
        if won:
            self.wins += 1
        else:
            self.losses += 1
        # A decaying average per mode, so an early lucky run does not lock a shape
        # in forever and a later bad patch does not erase a good one instantly.
        self.scores[self.mode] = self.scores[self.mode] * 0.7 + (1.0 if won else 0.0) * 0.3

    def rewrite(self) -> str:
        """Choose a shape and tune it. Returns a line describing what changed."""
        self.generation += 1
        previous_mode = self.mode
        previous = dict(self.params)

        best = max(self.scores.items(), key=lambda item: item[1])
        # Mostly keep the best shape; sometimes try another, because a shape that
        # never runs cannot be scored and the search would stall on its first idea.
        self.mode = best[0] if random.random() < 0.75 else random.choice(list(self.modes))
        base = self.modes[self.mode]
        self.params = {
            key: _clamp(value * (1 + random.uniform(-0.35, 0.35)), 0.0, 1.0)
            for key, value in base.items()
        }

        if self.mode != previous_mode:
            note = f"mode {previous_mode} -> {self.mode}"
        else:
            changed = [
                f"{k} {previous.get(k, 0):.2f}->{v:.2f}"
                for k, v in self.params.items()
                if abs(previous.get(k, 0) - v) > 0.02
            ]
            note = ", ".join(changed) if changed else "kept, nothing worth changing"
        self.last_note = note
        self.write_source()
        return note

    def write_source(self) -> Path:
        """Put the current program on disk, so the rewriting is inspectable."""
        GEN.mkdir(exist_ok=True)
        path = GEN / f"{self.name.lower()}_gen{self.generation:02d}.py"
        body = (
            f'"""Generation {self.generation} of the {self.name}.\n\n'
            f"Written by the arena after {ROUNDS_PER_GENERATION} rounds of experience.\n"
            f"Change from the previous generation: {self.last_note}\n"
            f"Score so far - {self.wins} won, {self.losses} lost\n"
            f'"""\n\n'
            f"MODE = {self.mode!r}\n\n"
            f"# Every number is a fraction of what the mode allows.\n"
            f"PARAMS = {{\n"
            + "".join(f"    {k!r}: {v:.3f},\n" for k, v in self.params.items())
            + "}\n\n"
            f"# Scores per shape, used to decide what to become next.\n"
            f"SHAPES = {{\n"
            + "".join(f"    {k!r}: {v:.3f},\n" for k, v in self.scores.items())
            + "}\n"
        )
        path.write_text(body, encoding="utf-8")
        return path


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def make_clicker() -> Agent:
    return Agent(
        name="Clicker",
        mode="hold",
        modes={
            # Aim where it is now.
            "hold": {"lead": 0.0, "noise": 0.05, "smooth": 0.5},
            # Aim where it is going, by a share of the observed displacement.
            "lead": {"lead": 0.8, "noise": 0.05, "smooth": 0.5},
            # Aim ahead and refuse to be fooled by a single jittery frame.
            "patient": {"lead": 0.7, "noise": 0.02, "smooth": 0.85},
            # Aim where the evader tends to end up, not where it is.
            "read": {"lead": 0.6, "noise": 0.10, "smooth": 0.35},
        },
    )


def make_evader() -> Agent:
    return Agent(
        name="Evader",
        mode="drift",
        modes={
            # Keep going the way it was going.
            "drift": {"speed": 0.5, "jitter": 0.1, "flee": 0.0, "warp": 0.0},
            # Move erratically: hard to predict, hard to aim at.
            "jitter": {"speed": 0.6, "jitter": 0.7, "flee": 0.1, "warp": 0.0},
            # Leave from wherever the last shot was aimed.
            "flee": {"speed": 0.7, "jitter": 0.3, "flee": 0.8, "warp": 0.0},
            # Occasionally jump: costs the aimer its whole model of the motion.
            "warp": {"speed": 0.6, "jitter": 0.3, "flee": 0.4, "warp": 0.35},
        },
    )


# ── the world ─────────────────────────────────────────────────────────────

@dataclass
class Round:
    """What happened, kept for the eye and for the score."""

    hit: bool
    aim: tuple[float, float]
    landing: tuple[float, float]
    before: tuple[float, float]


class World:
    def __init__(self, width: float, height: float) -> None:
        self.width = width
        self.height = height
        self.reset()

    def reset(self) -> None:
        self.x = self.width * 0.5
        self.y = self.height * 0.5
        self.vx = 3.0
        self.vy = 2.0
        self.trail: list[tuple[float, float]] = []
        self.rounds: list[Round] = []
        self.rope = 0.0          # -1 the evader is winning, +1 the clicker
        self.rope_history: list[float] = []
        self.round_number = 0

    def step_target(self, vx: float, vy: float) -> None:
        self.x += vx
        self.y += vy
        r = TARGET_RADIUS
        if self.x < r or self.x > self.width - r:
            self.x = _clamp(self.x, r, self.width - r)
            self.vx = -self.vx if vx == 0 else vx
        if self.y < r or self.y > self.height - r:
            self.y = _clamp(self.y, r, self.height - r)
        self.trail.append((self.x, self.y))
        if len(self.trail) > TRAIL:
            self.trail.pop(0)


# ── the arena on screen ───────────────────────────────────────────────────

class Arena:
    def __init__(self, root: tk.Tk, windowed: bool, speed: float) -> None:
        self.root = root
        self.speed = speed
        self.paused = False

        if not windowed:
            root.attributes("-fullscreen", True)
        else:
            root.geometry("1280x820")
        root.configure(bg="#0e1116")
        self.canvas = tk.Canvas(root, bg="#0e1116", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        root.bind("<Escape>", lambda _e: root.destroy())
        root.bind("<space>", self.toggle_pause)
        root.bind("<Left>", lambda _e: self.change_speed(-0.5))
        root.bind("<Right>", lambda _e: self.change_speed(0.5))
        root.bind("r", lambda _e: self.restart())
        root.bind("w", lambda _e: self.force_rewrite())

        self.clicker = make_clicker()
        self.evader = make_evader()
        self._first_generation()

        self.width = 0.0
        self.height = 0.0
        self.world: World | None = None
        self.phase = "move"
        self.phase_tick = 0
        self.pending: dict[str, object] = {}
        self.flash = ""
        self.flash_left = 0
        self.rewrite_banner = 0

        self.canvas.bind("<Configure>", self.on_resize)
        self.tick()

    def _first_generation(self) -> None:
        self.clicker.write_source()
        self.evader.write_source()
        self.clicker.last_note = "born"
        self.evader.last_note = "born"

    # ── controls ──────────────────────────────────────────────────────────
    def toggle_pause(self, _event: object = None) -> None:
        self.paused = not self.paused

    def change_speed(self, delta: float) -> None:
        self.speed = _clamp(self.speed + delta, 0.5, 12.0)

    def restart(self) -> None:
        self.clicker = make_clicker()
        self.evader = make_evader()
        self._first_generation()
        if self.world is not None:
            self.world.reset()

    def force_rewrite(self) -> None:
        self.clicker.rewrite()
        self.evader.rewrite()
        self.rewrite_banner = 40
        if self.world is not None:
            self.world.rounds.clear()
            self.world.round_number = 0

    def on_resize(self, event: tk.Event) -> None:
        self.width = float(event.width)
        self.height = float(event.height) - 250      # leave room for the panels
        if self.world is None:
            self.world = World(self.width, self.height)
            # The first round has to be set up explicitly: nothing else calls
            # begin_round until a round has finished, so without this the first
            # tick reaches for a decision that was never made.
            self.begin_round()
        else:
            self.world.width = self.width
            self.world.height = self.height

    # ── the game ──────────────────────────────────────────────────────────
    def begin_round(self) -> None:
        assert self.world is not None
        w = self.world
        history = w.trail[-2:]
        previous_aim = w.rounds[-1].aim if w.rounds else None

        # Both decide from the same picture and neither sees the other's choice.
        evx, evy = self.evader_move(history, previous_aim)
        aim = self.clicker_aim(history, w.x, w.y)
        self.pending = {
            "ev": (evx, evy),
            "aim": aim,
            "before": (w.x, w.y),
        }
        self.phase = "move"
        self.phase_tick = 0

    def evader_move(self, history: list[tuple[float, float]],
                    previous_aim: tuple[float, float] | None) -> tuple[float, float]:
        p = self.evader.params
        mode = self.evader.mode
        w = self.world
        assert w is not None

        speed = 4.0 + 6.0 * p.get("speed", 0.5)
        vx, vy = w.vx, w.vy
        length = math.hypot(vx, vy) or 1.0
        vx, vy = vx / length * speed, vy / length * speed

        if mode in ("jitter", "warp"):
            jitter = p.get("jitter", 0.3) * 5.0
            vx += random.uniform(-jitter, jitter)
            vy += random.uniform(-jitter, jitter)
        if mode in ("flee", "warp") and previous_aim is not None:
            flee = p.get("flee", 0.5) * 6.0
            away_x = w.x - previous_aim[0]
            away_y = w.y - previous_aim[1]
            away = math.hypot(away_x, away_y) or 1.0
            vx += away_x / away * flee
            vy += away_y / away * flee
        if mode == "warp" and random.random() < p.get("warp", 0.3):
            vx += random.uniform(-14, 14)
            vy += random.uniform(-14, 14)

        # Steering into a wall wastes the whole round; check before committing.
        r = TARGET_RADIUS
        if not (r < w.x + vx * LATENCY < w.width - r):
            vx = -vx * 0.6
        if not (r < w.y + vy * LATENCY < w.height - r):
            vy = -vy * 0.6
        return vx, vy

    def clicker_aim(self, history: list[tuple[float, float]], x: float, y: float) -> tuple[float, float]:
        p = self.clicker.params
        lead = p.get("lead", 0.5)
        noise = p.get("noise", 0.05)

        vx = vy = 0.0
        if len(history) >= 2:
            (px, py), (cx, cy) = history
            if self.clicker.mode in ("patient", "read"):
                # Smooth over the last few frames rather than the last one, so a
                # single jitter does not throw the prediction.
                smooth = p.get("smooth", 0.5)
                vx, vy = (cx - px) * (1 - smooth * 0.6), (cy - py) * (1 - smooth * 0.6)
            else:
                vx, vy = cx - px, cy - py

        aim_x = x + vx * LATENCY * lead
        aim_y = y + vy * LATENCY * lead
        spread = noise * 30.0
        aim_x += random.uniform(-spread, spread)
        aim_y += random.uniform(-spread, spread)
        return _clamp(aim_x, 0, self.width), _clamp(aim_y, 0, self.height)

    def finish_round(self) -> None:
        assert self.world is not None
        w = self.world
        aim = self.pending["aim"]
        before = self.pending["before"]
        hit = math.hypot(aim[0] - w.x, aim[1] - w.y) <= TARGET_RADIUS

        w.rounds.append(Round(hit=hit, aim=aim, landing=(w.x, w.y), before=before))
        if len(w.rounds) > CLICK_HISTORY:
            w.rounds.pop(0)
        w.round_number += 1

        # The rope: a hit pulls it to the clicker, a miss to the evader.
        w.rope = _clamp(w.rope + (0.09 if hit else -0.09), -1.0, 1.0)
        w.rope_history.append(w.rope)
        if len(w.rope_history) > 900:
            w.rope_history.pop(0)
        self.clicker.score(hit)
        self.evader.score(not hit)

        self.flash = "HIT" if hit else "MISS"
        self.flash_left = 6

        if w.round_number % ROUNDS_PER_GENERATION == 0:
            self.clicker.rewrite()
            self.evader.rewrite()
            self.rewrite_banner = 30

    # ── drawing ───────────────────────────────────────────────────────────
    def tick(self) -> None:
        if not self.paused and self.world is not None and self.width > 0:
            interval = 1.0 / self.speed
            self.phase_tick += 1
            if self.phase == "move":
                steps = max(1, int(0.35 / interval))
                if self.phase_tick >= steps:
                    # Land the target on its final position for this round.
                    assert self.world is not None
                    evx, evy = self.pending["ev"]        # type: ignore[misc]
                    for _ in range(LATENCY):
                        self.world.step_target(evx, evy)  # type: ignore[arg-type]
                        self.world.vx, self.world.vy = evx, evy  # type: ignore[assignment]
                    self.phase = "click"
                    self.phase_tick = 0
            else:
                steps = max(1, int(0.3 / interval))
                if self.phase_tick >= steps:
                    self.finish_round()
                    self.begin_round()

        self.draw()
        delay = max(16, int(1000 / (self.speed * 8)))
        self.root.after(delay, self.tick)

    def draw(self) -> None:
        c = self.canvas
        c.delete("all")
        w, h = self.width, self.height
        if w <= 10 or h <= 10 or self.world is None:
            return
        world = self.world

        # play field
        c.create_rectangle(2, 2, w - 2, h - 2, outline="#1d2530", width=2)
        for gx in range(0, int(w), 60):
            c.create_line(gx, 0, gx, h, fill="#141a22")
        for gy in range(0, int(h), 60):
            c.create_line(0, gy, w, gy, fill="#141a22")

        # the trail: where the target has been
        for index in range(1, len(world.trail)):
            x0, y0 = world.trail[index - 1]
            x1, y1 = world.trail[index]
            shade = int(40 + 150 * index / len(world.trail))
            c.create_line(x0, y0, x1, y1, fill=f"#{shade//3:02x}{shade//2:02x}{shade:02x}", width=2)

        # the click history: a cross per round, green hit, red miss
        for entry in world.rounds:
            colour = "#2fbf71" if entry.hit else "#e05561"
            ax, ay = entry.aim
            c.create_line(ax - 8, ay, ax + 8, ay, fill=colour, width=2)
            c.create_line(ax, ay - 8, ax, ay + 8, fill=colour, width=2)
            if not entry.hit:
                lx, ly = entry.landing
                c.create_line(ax, ay, lx, ly, fill="#5a2b30", width=1)

        # the live aim of this round, drawn while the target is still moving
        aim = self.pending.get("aim")
        if aim and self.phase == "move":
            ax, ay = aim                                     # type: ignore[misc]
            c.create_line(ax - 12, ay, ax + 12, ay, fill="#f0c419", width=2)
            c.create_line(ax, ay - 12, ax, ay + 12, fill="#f0c419", width=2)
            c.create_line(ax, ay, world.x, world.y, fill="#4a4130", dash=(3, 3))

        # the target
        r = TARGET_RADIUS
        c.create_oval(world.x - r, world.y - r, world.x + r, world.y + r,
                      fill="#4aa3ff", outline="#dceaff", width=2)

        self.draw_panels()

    def draw_panels(self) -> None:
        c = self.canvas
        w = self.width
        top = self.height + 6
        world = self.world
        assert world is not None

        # tug of war
        bar_y = top + 26
        mid = w / 2
        c.create_rectangle(40, bar_y, w - 40, bar_y + 26, fill="#161c24", outline="#26303c")
        c.create_text(70, bar_y + 13, text="CLICKER", anchor="w", fill="#2fbf71",
                      font=("Consolas", 13, "bold"))
        c.create_text(w - 70, bar_y + 13, text="EVADER", anchor="e", fill="#e05561",
                      font=("Consolas", 13, "bold"))
        # who is ahead right now
        if world.rope > 0:
            c.create_rectangle(mid, bar_y + 2, mid + (mid - 44) * world.rope, bar_y + 24, fill="#1d4b34")
        else:
            c.create_rectangle(mid + (mid - 44) * world.rope, bar_y + 2, mid, bar_y + 24, fill="#4b1d24")
        c.create_line(mid, bar_y - 4, mid, bar_y + 30, fill="#7b8794", width=2)
        marker = mid + (mid - 44) * world.rope
        c.create_polygon(marker, bar_y - 6, marker - 9, bar_y - 18, marker + 9, bar_y - 18,
                         fill="#f0c419", outline="")
        c.create_text(mid, bar_y + 13, text=f"rope {world.rope:+.2f}", fill="#c8d2dc",
                      font=("Consolas", 11))

        # The rope over time. A single position says who is ahead this second; the
        # shape says whether anyone is winning, which is a different question and
        # the one worth watching when two strategies are evolving against each other.
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
        c.create_text(44, graph_top + 8, text="+ clicker", anchor="w", fill="#2fbf71",
                      font=("Consolas", 9))
        c.create_text(44, graph_top + graph_height - 8, text="+ evader", anchor="w",
                      fill="#e05561", font=("Consolas", 9))

        # score strip
        strip_y = graph_top + graph_height + 22
        c.create_text(46, strip_y, text="rounds", anchor="w", fill="#7b8794", font=("Consolas", 11))
        for index, entry in enumerate(world.rounds):
            x = 110 + index * 20
            c.create_oval(x - 6, strip_y - 6, x + 6, strip_y + 6,
                          fill="#2fbf71" if entry.hit else "#2a323c",
                          outline="#2fbf71" if entry.hit else "#3a4550")

        if self.flash_left > 0:
            self.flash_left -= 1
            colour = "#2fbf71" if self.flash == "HIT" else "#e05561"
            c.create_text(mid, self.height - 34, text=self.flash, fill=colour,
                          font=("Consolas", 40, "bold"))

        if self.rewrite_banner > 0:
            self.rewrite_banner -= 1
            c.create_text(mid, self.height - 80, text="REWRITING THE PROGRAM",
                          fill="#f0c419", font=("Consolas", 20, "bold"))

        # the two agents
        self.draw_agent(self.clicker, 40, strip_y + 26, "left", "#2fbf71")
        self.draw_agent(self.evader, w - 40, strip_y + 26, "right", "#e05561")

        c.create_text(mid, strip_y + 22,
                      text=f"round {world.round_number}   generation {self.clicker.generation}"
                           f"   speed {self.speed:.1f}x   {'PAUSED' if self.paused else 'running'}",
                      fill="#7b8794", font=("Consolas", 12))
        c.create_text(mid, strip_y + 42,
                      text="space pause · ←/→ speed · w rewrite now · r restart · Esc quit",
                      fill="#4a5560", font=("Consolas", 10))

    def draw_agent(self, agent: Agent, x: float, y: float, side: str, colour: str) -> None:
        c = self.canvas
        anchor = "w" if side == "left" else "e"
        c.create_text(x, y, text=f"{agent.name.upper()}  gen {agent.generation}",
                      anchor=anchor, fill=colour, font=("Consolas", 13, "bold"))
        c.create_text(x, y + 17, text=f"shape: {agent.mode}    won {agent.wins} / lost {agent.losses}",
                      anchor=anchor, fill="#98a4b0", font=("Consolas", 10))
        params = "  ".join(f"{k}={v:.2f}" for k, v in agent.params.items())
        c.create_text(x, y + 33, text=params, anchor=anchor, fill="#6b7783", font=("Consolas", 10))
        # Why it rewrote: the score of every shape it has tried. Without this the
        # rewrite is a number changing for no visible reason.
        shapes = "   ".join(
            f"{name}:{score:.2f}{'*' if name == agent.mode else ''}"
            for name, score in sorted(agent.scores.items(), key=lambda kv: -kv[1])
        )
        c.create_text(x, y + 49, text=shapes, anchor=anchor, fill="#5f6b77", font=("Consolas", 9))
        note = textwrap.shorten(agent.last_note, width=80, placeholder=" …")
        c.create_text(x, y + 65, text=f"rewrite: {note}", anchor=anchor, fill="#5a6672",
                      font=("Consolas", 10))


def main() -> int:
    parser = argparse.ArgumentParser(description="Two agents, one target, a rope between them.")
    parser.add_argument("--windowed", action="store_true", help="not fullscreen")
    parser.add_argument("--speed", type=float, default=2.0, help="rounds per second")
    args = parser.parse_args()

    root = tk.Tk()
    root.title("Clicker vs Evader")
    Arena(root, windowed=args.windowed, speed=args.speed)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
