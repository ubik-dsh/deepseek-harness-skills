"""The trainee. Sees pixels, decides where to click, learns from being wrong.

This never sees the target's coordinates. It is handed a frame and must find the
target the way anything with eyes would: the background and the grid are grey, and
the target is the only saturated thing in the picture. So the search is a
saturation threshold, the aim is the centre of what survives, and the aim point
for a moving target is that centre plus a lead the class has to learn.

The learning is a hill climb on one number because there is only one thing the
player can be told: whether the last attempt hit. Nothing here knows which way it
missed, so it cannot compute a correction - it has to try a direction and keep it
if the score improves. That is exactly the position a person is in, which is why
the exercise is worth running at all.

    from player import Aim
    aim = Aim(width=480, height=320, radius=14)
    x, y = aim.decide(frame)
    aim.learn(hit)
"""

from __future__ import annotations

from PIL import Image, ImageChops

# A pixel is "coloured" when its brightest and dimmest channels differ by more
# than this. The grid and the background differ by less than 10, so the threshold
# has a lot of room; 60 was chosen by looking at a frame, not by theory.
SATURATION_THRESHOLD = 60


class Aim:
    def __init__(self, width: int, height: int, radius: int, lead: float = 0.0) -> None:
        self.width = width
        self.height = height
        self.radius = radius
        self.lead = lead
        self.rate = 0.5           # how much of each measurement to believe
        self.last_dx = 0.0        # the previous frame's displacement
        self.last_dy = 0.0
        self.previous: tuple[float, float] | None = None
        self.pending: tuple[float, float] | None = None   # where the last shot went
        self.seen = 0            # turns on which a target was found at all
        self.shots = 0
        self.hits = 0
        self.last_box: tuple[int, int, int, int] | None = None

    # ── seeing ────────────────────────────────────────────────────────────
    @staticmethod
    def find_target(frame: Image.Image) -> tuple[float, float, tuple[int, int, int, int]] | None:
        """Return the centre of the only saturated region, and its bounding box.

        Done with channel arithmetic rather than a pixel loop: max(r,g,b) minus
        min(r,g,b) is a saturation map, and Pillow's getbbox finds the extent of it
        in C. The player is not allowed to be slow, because a slow player misses a
        moving target for reasons that have nothing to do with aiming.
        """
        red, green, blue = frame.split()
        brightest = ImageChops.lighter(ImageChops.lighter(red, green), blue)
        dimmest = ImageChops.darker(ImageChops.darker(red, green), blue)
        saturation = ImageChops.subtract(brightest, dimmest)
        mask = saturation.point(lambda value: 255 if value > SATURATION_THRESHOLD else 0)
        box = mask.getbbox()
        if box is None:
            return None
        left, top, right, bottom = box
        return (left + right) / 2, (top + bottom) / 2, box

    # ── deciding ──────────────────────────────────────────────────────────
    def decide(self, frame: Image.Image) -> tuple[float, float]:
        found = self.find_target(frame)
        if found is None:
            return self.width / 2, self.height / 2
        self.seen += 1
        x, y, box = found
        self.last_box = box

        vx = vy = 0.0
        jumped = False
        if self.previous is not None:
            vx = x - self.previous[0]
            vy = y - self.previous[1]
            # A hit moves the target somewhere else entirely. That is a jump, not
            # motion, and mistaking one for the other costs accuracy twice over.
            #
            # Three attempts got this wrong, each in a new way, which is the point
            # worth keeping. A fixed threshold chosen from the world's top speed
            # read every frame of a moving target as a teleport, because the
            # observation interval includes the reaction delay. A threshold
            # relative to the average displacement could not tell a static target's
            # respawn from motion, because a static target has no average. And
            # teaching the average over the first few frames taught it a respawn.
            #
            # What distinguishes a jump is not speed but *discontinuity*: real
            # motion changes displacement smoothly, and a teleport does not. So
            # compare this frame's displacement with the last one, which needs no
            # calibration, no warm-up and no knowledge of the world.
            change = ((vx - self.last_dx) ** 2 + (vy - self.last_dy) ** 2) ** 0.5
            steadiness = (self.last_dx * self.last_dx + self.last_dy * self.last_dy) ** 0.5
            if change > max(60.0, 2.5 * steadiness):
                jumped = True
                vx = vy = 0.0
                self.lead = 0.0
                self.rate = 0.5
            self.last_dx, self.last_dy = vx, vy

        # Correct before aiming. The previous shot has already landed and this
        # frame shows where the target actually went, which is a measurement, not
        # an opinion - see correct() for why that distinction is the whole game.
        if self.pending is not None and not jumped and (vx or vy):
            self.correct(x, y, vx, vy)

        self.previous = (x, y)

        # Aim ahead by the lead, and never past the wall: a click outside the
        # frame is a miss no matter how good the arithmetic was.
        aim_x = min(max(x + vx * self.lead, 0), self.width - 1)
        aim_y = min(max(y + vy * self.lead, 0), self.height - 1)
        self.pending = (aim_x, aim_y)
        return aim_x, aim_y

    def correct(self, x: float, y: float, vx: float, vy: float) -> None:
        """Move the lead towards the one measurement the player can actually make.

        The first version received one bit per shot - hit or miss - and nudged the
        lead in a fixed direction on a miss. It diverged: 9% on a moving target,
        with the lead pinned to the ceiling, because a miss has many causes and
        only one of them is "not enough lead".

        Neither is the second mistake available: the player does not observe the
        target's speed. It observes how far the target moved *between two frames*,
        and that distance already includes the reaction delay, so the number it
        measures is several times the real per-tick speed and a correction built on
        it lands in the wrong place entirely. That version oscillated to zero and
        scored 2%.

        What it can measure is this. Aim was at `observed + D * lead`, where D is
        the displacement it saw. One frame later the target is at `observed + D`.
        So the signed gap between where it aimed and where the target now is,
        measured along D, equals `D * (lead - 1)` - no knowledge of the delay or
        the speed required. Driving that gap to zero drives the lead to 1, which is
        aiming at the next observed position, and that is a target the player can
        hit without knowing anything it was not told.
        """
        aim_x, aim_y = self.pending
        speed = (vx * vx + vy * vy) ** 0.5
        if speed < 0.5:
            return
        gap_in_turns = ((x - aim_x) * vx + (y - aim_y) * vy) / (speed * speed)
        if gap_in_turns > 4.0 or gap_in_turns < -4.0:
            return
        # The gap is `1 - lead`, so closing it means adding it. Subtracting it -
        # which this did first - drives the lead to zero and scores 2%, which is
        # the same as not aiming ahead at all.
        self.lead = min(6.0, max(0.0, self.lead + self.rate * gap_in_turns))

    # ── learning ──────────────────────────────────────────────────────────
    def learn(self, hit: bool) -> None:
        """Keep the score, and let a hit shrink the correction rate.

        The correction itself happens in correct(), from geometry. This only
        decides how much to trust the next measurement: a hit means the current
        lead is close, so later corrections get smaller and the number settles
        instead of oscillating around the answer.
        """
        self.hits += 1 if hit else 0
        self.shots += 1
        if hit:
            self.rate = max(0.15, self.rate * 0.95)
        else:
            self.rate = min(1.0, self.rate * 1.02)
