#!/usr/bin/env python3
"""Find the frames where a fixed SCREEN region moved, in a cursor-centred recording.

The frames are cropped around the pointer, so each one has its own origin and a fixed box means a
different part of the screen in every frame. **`cursor.csv` is what makes them comparable**: with the
pointer's position the origin is `(x - width/2, y - height/2)` and a screen region maps into each
frame exactly.

Comparing raw frames without that mapping compares different pieces of the screen and reports that
nothing ever changes - which is what the first version of this script did, over 889 frames, before
the zeroes gave it away. A region that is genuinely static for three minutes is possible; one that is
byte-identical while the page is being driven is not.

    python find_shift.py <folder> --box X,Y,W,H [--top N]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PIL import Image, ImageChops

sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")

ap = argparse.ArgumentParser()
ap.add_argument("folder", type=Path)
ap.add_argument("--box", required=True, help="x,y,w,h in SCREEN coordinates")
ap.add_argument("--top", type=int, default=20)
ap.add_argument("--jump", type=float, default=6.0, help="mean level change that counts as a move")
args = ap.parse_args()

sx, sy, sw, sh = (int(v) for v in args.box.split(","))

rows = []
for line in (args.folder / "cursor.csv").read_text(encoding="utf-8-sig").splitlines()[1:]:
    parts = line.split(",")
    if len(parts) == 4:
        rows.append(tuple(int(p) for p in parts))

# The record is 1200x800 by default; read the real size from one frame so this cannot drift.
with Image.open(sorted(args.folder.glob("frame_*.png"))[0]) as probe:
    fw, fh = probe.size

print(f"  frames are {fw}x{fh}; watching screen x{sx}..{sx+sw} y{sy}..{sy+sh} over {len(rows)} frames")

previous = None
changes = []
skipped = 0
for frame, ms, cx, cy in rows:
    path = args.folder / f"frame_{frame:06d}.png"
    if not path.exists():
        continue
    ox, oy = cx - fw // 2, cy - fh // 2
    bx, by = sx - ox, sy - oy
    if bx < 0 or by < 0 or bx + sw > fw or by + sh > fh:
        skipped += 1
        previous = None          # the region is off-frame; nothing to compare across the gap
        continue
    with Image.open(path) as image:
        region = image.convert("L").crop((bx, by, bx + sw, by + sh))
        if previous is not None:
            diff = ImageChops.difference(region, previous)
            mean = sum(diff.get_flattened_data()) / (sw * sh)
            changes.append((mean, frame, cx, cy))
        previous = region

if skipped:
    print(f"  {skipped} frame(s) had this region off-frame and were skipped")

changes.sort(reverse=True)
print()
print("  the frames where this region changed most:")
for mean, frame, cx, cy in changes[: args.top]:
    print(f"    frame {frame:4}   mean change {mean:7.2f}   pointer at {cx},{cy}")

moved = [(n, c) for m, n, c, _ in changes if m > args.jump]
if moved:
    print()
    print(f"  {len(moved)} frame(s) changed by more than {args.jump}:")
    for number, cx in moved:
        print(f"    frame {number:4}  (the frame before it is the last one before the move)")
else:
    print()
    print(f"  nothing moved by more than {args.jump} - the region is static in this recording")
