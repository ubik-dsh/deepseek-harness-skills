#!/usr/bin/env python3
"""Stack the SAME SCREEN COLUMN from many frames of a cursor-centred recording, side by side.

Each frame is cropped around the pointer, so a column of the interface sits at a different place in
every one. `cursor.csv` maps it back: screen (X, Y) is frame (X - (cx - w/2), Y - (cy - h/2)). With
that, ten frames taken minutes apart can be laid side by side in the same screen coordinates, and a
vertical shift of the interface shows up as the same text sitting at different heights.

A red line is drawn at one fixed screen y across every column. If the interface has not moved, the
line crosses the same words in all of them.

    python stack_column.py <folder> --box 1480,180,180,700 --label-y 300 --max 10
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PIL import Image, ImageDraw

sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")

ap = argparse.ArgumentParser()
ap.add_argument("folder", type=Path)
ap.add_argument("--box", required=True, help="x,y,w,h in SCREEN coordinates")
ap.add_argument("--label-y", type=int, default=None, help="screen y for the reference line")
ap.add_argument("--max", type=int, default=10)
ap.add_argument("--cursor-y", default="480,600", help="only frames whose pointer y is in this range")
ap.add_argument("--cursor-x", default="1060,2100", help="only frames whose pointer x is in this range")
args = ap.parse_args()

sx, sy, sw, sh = (int(v) for v in args.box.split(","))
ylow, yhigh = (int(v) for v in args.cursor_y.split(","))
xlow, xhigh = (int(v) for v in args.cursor_x.split(","))

rows = []
for line in (args.folder / "cursor.csv").read_text(encoding="utf-8-sig").splitlines()[1:]:
    parts = line.split(",")
    if len(parts) == 4:
        rows.append(tuple(int(p) for p in parts))

with Image.open(sorted(args.folder.glob("frame_*.png"))[0]) as probe:
    fw, fh = probe.size

usable = []
for frame, ms, cx, cy in rows:
    ox, oy = cx - fw // 2, cy - fh // 2
    bx, by = sx - ox, sy - oy
    if bx < 0 or by < 0 or bx + sw > fw or by + sh > fh:
        continue
    if not (ylow <= cy <= yhigh and xlow <= cx <= xhigh):
        continue
    if (args.folder / f"frame_{frame:06d}.png").exists():
        usable.append((frame, cx, cy, bx, by))

print(f"  {len(usable)} frame(s) have this column fully on-frame with the pointer parked")
if not usable:
    raise SystemExit("  nothing to stack - widen --cursor-y")

# Evenly spaced across the recording, so the columns span the whole session.
step = max(1, len(usable) // args.max)
chosen = usable[::step][: args.max]
print(f"  stacking {len(chosen)} of them, evenly spaced")

canvas = Image.new("RGB", (sw * len(chosen), sh + 26), "white")
draw = ImageDraw.Draw(canvas)
for index, (frame, cx, cy, bx, by) in enumerate(chosen):
    with Image.open(args.folder / f"frame_{frame:06d}.png") as image:
        piece = image.crop((bx, by, bx + sw, by + sh))
    canvas.paste(piece, (index * sw, 26))
    draw.text((index * sw + 4, 6), f"f{frame} cy{cy}", fill="black")
    draw.line([(index * sw, 26), (index * sw, sh + 26)], fill="black", width=1)

if args.label_y is not None:
    ly = 26 + (args.label_y - sy)
    draw.line([(0, ly), (sw * len(chosen), ly)], fill="red", width=2)

out = args.folder.parent / "column_stack.png"
canvas.save(out)
print(f"  wrote {out}")
print(f"  the red line is screen y {args.label_y}; the same words under it in every column means no shift")
