#!/usr/bin/env python3
"""Learn your way around an interface instead of hard-coding coordinates.

A template. The parts worth keeping are the bandit, the memory file and the shape
of the loop; the part to replace is `class Task`. Copy it, swap the task, delete the
example once you have your own.

Why a learner rather than a script: the detail you need is usually something nobody
documented - which row of a dropdown, which of four similar buttons, what offset
makes the click land. Measured on such a task, exploring six candidates once and
remembering the result cost six attempts; doing it by hand cost six attempts too,
and then the number was written into a script that goes stale on the next release.

    python learn-an-interface.py --iterations 12     # explore and remember
    python learn-an-interface.py --apply             # use it, no exploring
    python learn-an-interface.py --show              # what it knows

Read `references/controlling-an-interface.md` first, and only build this if the
gate there says you must.
"""

from __future__ import annotations

import argparse
import ctypes
import json
import math
import sys
import time
from pathlib import Path

MEMORY = Path(__file__).with_name("interface_memory.json")

# ── the learner ───────────────────────────────────────────────────────────────


class Bandit:
    """UCB1 over a small set of candidate actions, with counts kept on disk.

    Try every action once; after that prefer the best upper confidence bound:

        score = mean reward + sqrt(2 * ln(total pulls) / pulls of this action)

    One formula, no learning rate, and exploration falls out of it: an action with
    few samples has a wide bound and gets another go. Ten candidates converge in
    about ten attempts.

    Reward should be graded, not binary, wherever a partial result exists:

        1.0   the wanted thing happened          (a real PNG was written)
        0.3   something happened, not that thing (a file was written, as TIFF)
        0.0   nothing happened

    With only 1.0 and 0.0 the learner cannot tell "nearly" from "nowhere".
    """

    def __init__(self, name: str, actions: list, prior: dict | None = None) -> None:
        self.name = name
        self.actions = list(actions)
        self.stats = {str(a): {"n": 0, "total": 0.0} for a in self.actions}
        self.history: list = []
        if prior:
            for key, value in prior.get("stats", {}).items():
                if key in self.stats:
                    self.stats[key] = {"n": value["n"], "total": value["total"]}
            self.history = prior.get("history", [])

    @property
    def pulls(self) -> int:
        return sum(s["n"] for s in self.stats.values())

    def choose(self):
        untried = [a for a in self.actions if self.stats[str(a)]["n"] == 0]
        if untried:
            return untried[0]
        total = max(1, self.pulls)

        def bound(action) -> float:
            stat = self.stats[str(action)]
            return stat["total"] / stat["n"] + math.sqrt(2 * math.log(total) / stat["n"])

        return max(self.actions, key=bound)

    def update(self, action, reward: float) -> None:
        stat = self.stats[str(action)]
        stat["n"] += 1
        stat["total"] += reward
        self.history.append({"action": action, "reward": reward})

    def best(self):
        tried = [a for a in self.actions if self.stats[str(a)]["n"] > 0]
        return max(tried, key=lambda a: self.stats[str(a)]["total"] / self.stats[str(a)]["n"],
                   default=None)

    def to_json(self) -> dict:
        return {"stats": self.stats, "history": self.history[-40:]}


def load_memory() -> dict:
    if MEMORY.exists():
        try:
            return json.loads(MEMORY.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}
    return {}


def save_memory(data: dict) -> None:
    MEMORY.write_text(json.dumps(data, indent=1), encoding="utf-8")


# ── input, when you are on Windows ────────────────────────────────────────────
#
# These are the calls that actually reach a modern application. Measured: a drag
# through the older `mouse_event` changed exactly zero pixels of a canvas, and the
# same drag through SendInput left a line. Use SendInput, and check where the
# pointer landed before pressing anything.

if sys.platform == "win32":
    _user32 = ctypes.windll.user32

    class _MOUSEINPUT(ctypes.Structure):
        _fields_ = [("dx", ctypes.c_long), ("dy", ctypes.c_long),
                    ("mouseData", ctypes.c_ulong), ("dwFlags", ctypes.c_ulong),
                    ("time", ctypes.c_ulong), ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong))]

    class _INPUT(ctypes.Structure):
        class _UNION(ctypes.Union):
            _fields_ = [("mi", _MOUSEINPUT)]

        _anonymous_ = ("u",)
        _fields_ = [("type", ctypes.c_ulong), ("u", _UNION)]

    def _send(flags: int, dx: int = 0, dy: int = 0) -> None:
        item = _INPUT(type=0, u=_INPUT._UNION(mi=_MOUSEINPUT(dx, dy, 0, flags, 0, None)))
        _user32.SendInput(1, ctypes.byref(item), ctypes.sizeof(_INPUT))

    LEFTDOWN, LEFTUP, MOVE, ABSOLUTE, VIRTUALDESK = 0x0002, 0x0004, 0x0001, 0x8000, 0x4000

    def move_to(screen_x: int, screen_y: int) -> None:
        """Absolute move across the whole virtual desktop, then verify it landed.

        Absolute coordinates without VIRTUALDESK address the primary monitor only,
        which throws the cursor to the other screen on a multi-monitor desktop. And
        plain SetCursorPos is right about monitors but generates no move events, so
        a drag is seen as a single dot.
        """
        left = _user32.GetSystemMetrics(76)
        top = _user32.GetSystemMetrics(77)
        width = _user32.GetSystemMetrics(78)
        height = _user32.GetSystemMetrics(79)
        nx = int((screen_x - left) * 65535 / max(1, width - 1))
        ny = int((screen_y - top) * 65535 / max(1, height - 1))
        _send(MOVE | ABSOLUTE | VIRTUALDESK, nx, ny)
        time.sleep(0.004)

        class POINT(ctypes.Structure):
            _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

        landed = POINT()
        _user32.GetCursorPos(ctypes.byref(landed))
        if abs(landed.x - screen_x) > 2 or abs(landed.y - screen_y) > 2:
            # Refuse to press. On a real desktop a wrong coordinate is somebody
            # else's window, and a stop is much cheaper than an apology.
            raise RuntimeError(
                f"pointer did not arrive: wanted ({screen_x}, {screen_y}), "
                f"got ({landed.x}, {landed.y})")

    def click(screen_x: int, screen_y: int, settle: float = 0.35) -> None:
        move_to(screen_x, screen_y)
        _send(LEFTDOWN)
        time.sleep(0.05)
        _send(LEFTUP)
        time.sleep(settle)

    def drag(points: list[tuple[int, int]], settle: float = 0.03) -> None:
        if not points:
            return
        move_to(*points[0])
        time.sleep(0.12)
        _send(LEFTDOWN)
        time.sleep(0.08)
        for x, y in points[1:]:
            move_to(x, y)
            time.sleep(settle)
        _send(LEFTUP)
        time.sleep(0.25)


# ── your task goes here ───────────────────────────────────────────────────────


class Task:
    """The example: which row of a file-type list produces the format we want.

    Replace this. Keep the two contracts:

      * `actions` is a small finite list of candidates;
      * `run(action)` returns a reward from a *verified* outcome - not "the screen
        changed" and not "a file exists", but a property only the right result has.

    Verified means checked, and checked means you have watched the check fail on the
    wrong thing once.
    """

    name = "example-task"
    actions = [0, 1, 2, 3]

    def run(self, action) -> float:
        # Do the thing at `action`, then look at the world and grade it.
        # If the target is not there at all, raise - a missing world is not a
        # failed action, and averaging the two together teaches the wrong lesson.
        raise NotImplementedError(
            "replace Task.run: perform the action, verify the outcome, return a reward")


# ── the loop ──────────────────────────────────────────────────────────────────


def learn(iterations: int, task) -> int:
    data = load_memory()
    bandit = Bandit(task.name, task.actions, data.get(task.name))
    print(f"  learning '{task.name}' over {len(task.actions)} candidates, {iterations} iterations")
    print(f"  {'iter':>4}{'action':>10}{'reward':>8}{'best so far':>14}")
    for i in range(1, iterations + 1):
        action = bandit.choose()
        try:
            reward = task.run(action)
        except RuntimeError as trouble:
            print(f"  {i:>4}{str(action):>10}   stopped: {trouble}")
            print("  nothing recorded for this attempt")
            break
        bandit.update(action, reward)
        print(f"  {i:>4}{str(action):>10}{reward:>8.1f}{str(bandit.best()):>14}")
    data[task.name] = bandit.to_json()
    save_memory(data)
    print(f"\n  best action: {bandit.best()}\n  memory: {MEMORY}")
    return 0


def apply_(task) -> int:
    data = load_memory()
    prior = data.get(task.name)
    if not prior:
        print("  nothing learned yet - run without --apply first")
        return 1
    bandit = Bandit(task.name, task.actions, prior)
    action = bandit.best()
    print(f"  applying the learned action: {action}")
    reward = task.run(action)
    print(f"  reward {reward:.1f}")
    return 0 if reward >= 1.0 else 1


def show(task) -> None:
    data = load_memory()
    prior = data.get(task.name)
    if not prior:
        print("  nothing learned yet")
        return
    print(f"  what it knows about '{task.name}':")
    print(f"  {'action':>10}{'tries':>7}{'mean reward':>13}")
    for action, stat in prior["stats"].items():
        mean = stat["total"] / stat["n"] if stat["n"] else 0.0
        print(f"  {action:>10}{stat['n']:>7}{mean:>13.2f}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--iterations", type=int, default=12)
    parser.add_argument("--apply", action="store_true", help="use what was learned")
    parser.add_argument("--show", action="store_true", help="print what is known")
    args = parser.parse_args()

    task = Task()
    if args.show:
        show(task)
        return 0
    if args.apply:
        return apply_(task)
    return learn(args.iterations, task)


if __name__ == "__main__":
    raise SystemExit(main())
