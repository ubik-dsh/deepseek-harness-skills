"""A trainer for aiming, built because the real task fell out of the digital world.

Mouse control has no command to call and no exit code: its success test lives in a
person's hand. So the test is simulated instead. This file draws the world and
keeps score; player.py looks at the picture and decides where to click. Neither
one knows the other's secrets - the player never sees the coordinates, only the
image, which is the whole point.

    python sim.py            # runs all four stages and reports
    python sim.py --sheet    # also writes a contact sheet of the frames

Stages, in the order the difficulty actually increases:
    1  static, one colour, one shape
    2  static position, colour and shape changing
    3  moving, one colour, one shape
    4  moving, colour and shape changing

Standard library plus Pillow. Pillow is used to draw and to read pixels, which is
also how the player perceives - no numpy, so the vision is honest rather than
convenient.
"""

from __future__ import annotations

import argparse
import json
import math
import random
from pathlib import Path

from PIL import Image, ImageDraw

W, H = 480, 320
RADIUS = 14
TARGET_COLORS = [(214, 40, 40), (36, 150, 60), (40, 84, 214), (230, 140, 20), (196, 44, 176)]
SHAPES = ("circle", "square", "triangle")
BACKGROUND = (236, 236, 240)
GRID = (224, 224, 230)
FRAMES = Path(__file__).with_name("frames")


def blank_frame() -> Image.Image:
    img = Image.new("RGB", (W, H), BACKGROUND)
    draw = ImageDraw.Draw(img)
    for x in range(0, W, 40):
        draw.line([(x, 0), (x, H)], fill=GRID)
    for y in range(0, H, 40):
        draw.line([(0, y), (W, y)], fill=GRID)
    return img


def draw_target(img: Image.Image, shape: str, color: tuple[int, int, int], cx: float, cy: float) -> None:
    draw = ImageDraw.Draw(img)
    r = RADIUS
    if shape == "circle":
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=color)
    elif shape == "square":
        draw.rectangle([cx - r, cy - r, cx + r, cy + r], fill=color)
    else:
        draw.polygon([(cx, cy - r - 2), (cx - r, cy + r), (cx + r, cy + r)], fill=color)


class Target:
    """The thing to be hit. Knows its own position; the player does not."""

    def __init__(self, stage: int, seed: int) -> None:
        self.rng = random.Random(seed)
        self.stage = stage
        self.moving = stage in (3, 4)
        self.changing = stage in (2, 4)
        self.shape = "circle"
        self.color = TARGET_COLORS[0]
        self.x = W / 2
        self.y = H / 2
        self.vx = 0.0
        self.vy = 0.0
        self.ticks = 0
        self.respawn()

    def respawn(self) -> None:
        r = RADIUS + 12
        self.x = self.rng.uniform(r, W - r)
        self.y = self.rng.uniform(r, H - r)
        if self.moving:
            speed = 5.0 + self.stage
            angle = self.rng.uniform(0, 2 * math.pi)
            self.vx = speed * math.cos(angle)
            self.vy = speed * math.sin(angle)
        if self.changing:
            self.shape = self.rng.choice(SHAPES)
            self.color = self.rng.choice(TARGET_COLORS)

    def step(self) -> None:
        self.ticks += 1
        if not self.moving:
            return
        self.x += self.vx
        self.y += self.vy
        r = RADIUS
        if self.x < r or self.x > W - r:
            self.vx = -self.vx
            self.x = min(max(self.x, r), W - r)
        if self.y < r or self.y > H - r:
            self.vy = -self.vy
            self.y = min(max(self.y, r), H - r)

    def render(self) -> Image.Image:
        img = blank_frame()
        draw_target(img, self.shape, self.color, self.x, self.y)
        return img

    def score(self, x: float, y: float) -> bool:
        return math.hypot(x - self.x, y - self.y) <= RADIUS


def run_stage(stage: int, rounds: int, seed: int, save_frames: bool = False, latency: int = 3) -> dict:
    """Play one stage. The player is imported here so the two halves stay separate.

    `latency` is the ticks the target keeps moving between the frame being drawn
    and the click landing. It is not a detail: with no latency the first version of
    this trainer scored 100% at every stage and the player never had to learn
    anything, because a target that moves six pixels per turn cannot escape a
    fourteen-pixel radius. Latency is what a person actually has, and it is what
    makes aiming ahead necessary rather than optional. Stages 1 and 2 stand still,
    so latency cannot matter there.
    """
    from player import Aim

    if save_frames:
        FRAMES.mkdir(exist_ok=True)

    target = Target(stage, seed)
    aim = Aim(width=W, height=H, radius=RADIUS, lead=0.0)
    effective_latency = latency if target.moving else 0
    hits = 0
    misses = 0
    history = []
    leads = []

    for turn in range(rounds):
        frame = target.render()
        if save_frames and turn % max(1, rounds // 6) == 0:
            frame.save(FRAMES / f"stage{stage}_turn{turn:03d}.png")

        # The player sees pixels and nothing else.
        x, y = aim.decide(frame)

        # Time passes before the click lands. This is the whole difficulty.
        for _ in range(effective_latency):
            target.step()

        hit = target.score(x, y)
        aim.learn(hit)
        leads.append(aim.lead)
        if hit:
            hits += 1
            target.respawn()
        else:
            misses += 1
        history.append(1 if hit else 0)
        target.step()

    early = history[: max(1, rounds // 3)]
    late = history[-max(1, rounds // 3) :]
    return {
        "stage": stage,
        "rounds": rounds,
        "hits": hits,
        "misses": misses,
        "accuracy": round(hits / rounds, 3),
        "first_third": round(sum(early) / len(early), 3),
        "last_third": round(sum(late) / len(late), 3),
        "final_lead": round(aim.lead, 3),
        "lead_first_third": round(sum(leads[: max(1, rounds // 3)]) / len(leads[: max(1, rounds // 3)]), 2),
        "latency": effective_latency,
        "changing": target.changing,
        "moving": target.moving,
    }


def contact_sheet() -> Path:
    """One image showing a frame from each stage, for a human to look at."""
    images = []
    for stage in (1, 2, 3, 4):
        target = Target(stage, seed=stage * 11)
        for _ in range(stage + 3):
            target.step()
        images.append(target.render().resize((W // 2, H // 2)))
    sheet = Image.new("RGB", (W, H), (255, 255, 255))
    for index, img in enumerate(images):
        sheet.paste(img, ((index % 2) * (W // 2), (index // 2) * (H // 2)))
    out = Path(__file__).with_name("contact-sheet.png")
    sheet.save(out)
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="Aiming trainer: does practice improve the hit rate?")
    parser.add_argument("--rounds", type=int, default=60, help="rounds per stage")
    parser.add_argument("--latency", type=int, default=3, help="ticks between deciding and the click landing")
    parser.add_argument("--sheet", action="store_true", help="write a contact sheet of one frame per stage")
    parser.add_argument("--frames", action="store_true", help="write sample frames")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    results = [
        run_stage(stage, args.rounds, seed=1000 + stage, save_frames=args.frames, latency=args.latency)
        for stage in (1, 2, 3, 4)
    ]

    if args.sheet:
        print(f"contact sheet: {contact_sheet()}")

    if args.json:
        print(json.dumps(results, indent=2))
    else:
        print(f"{'stage':<7}{'moving':<8}{'changing':<10}{'latency':>8}{'accuracy':>9}{'first ⅓':>9}{'last ⅓':>9}{'lead ⅓':>8}{'lead end':>9}")
        for r in results:
            print(
                f"{r['stage']:<7}{str(r['moving']):<8}{str(r['changing']):<10}{r['latency']:>8}"
                f"{r['accuracy']:>9.3f}{r['first_third']:>9.3f}{r['last_third']:>9.3f}"
                f"{r['lead_first_third']:>8.2f}{r['final_lead']:>9.2f}"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
