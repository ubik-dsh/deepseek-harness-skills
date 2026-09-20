#!/usr/bin/env python3
"""Read a demonstration as numbers before looking at any picture.

Twenty-five pictures are watched; twenty-five coordinates are read. The pauses are where the
hand decided something, and they are the only frames worth opening - the rest is transit.

    python read_demo.py <folder>
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")

folder = Path(sys.argv[1])
rows = []
for line in (folder / "cursor.csv").read_text(encoding="utf-8-sig").splitlines()[1:]:
    parts = line.split(",")
    if len(parts) == 4:
        rows.append((int(parts[0]), int(parts[1]), int(parts[2]), int(parts[3])))

print(f"  frames {len(rows)}   span {rows[-1][1] - rows[0][1]} ms   "
      f"rate {len(rows) / max(1, (rows[-1][1] - rows[0][1]) / 1000):.1f} fps")

# Transit against stay. A hand that is deciding does not move; a hand that is travelling does.
STILL = 4          # px between consecutive frames
RUN = 4            # frames in a row to count as a pause

pauses = []
current = None
travel = 0
for i in range(1, len(rows)):
    frame, ms, x, y = rows[i]
    _, _, px, py = rows[i - 1]
    step = ((x - px) ** 2 + (y - py) ** 2) ** 0.5
    travel += step
    if step <= STILL:
        if current is None:
            current = [frame, frame, ms, x, y, 1]
        else:
            current[1] = frame
            current[2] = ms
            current[5] += 1
            current[3] = (current[3] + x) // 2
            current[4] = (current[4] + y) // 2
    else:
        if current is not None and current[5] >= RUN:
            pauses.append(tuple(current))
        current = None
if current is not None and current[5] >= RUN:
    pauses.append(tuple(current))

print(f"  path length {int(travel)} px")
print()
print(f"  {len(pauses)} pause(s) of {RUN}+ frames - these are the frames worth opening:")
print()
print(f"    {'frames':>13}  {'at ms':>7}  {'held':>5}  position")
for first, last, ms, x, y, held in pauses:
    print(f"    {first:4}..{last:<6}  {ms:7}  {held:4}f  {x},{y}")

print()
print("  the largest single moves, which are jumps rather than pointing:")
moves = []
for i in range(1, len(rows)):
    frame, ms, x, y = rows[i]
    _, _, px, py = rows[i - 1]
    step = ((x - px) ** 2 + (y - py) ** 2) ** 0.5
    moves.append((step, frame, x, y))
for step, frame, x, y in sorted(moves, reverse=True)[:5]:
    print(f"    frame {frame:4}  {int(step):5} px  to {x},{y}")
