# Measuring a window so that clicks land

Every coordinate failure in this work came from reading a number off a picture
without checking what the picture was of. This is the method that stopped it.

---

## 1. Capture the whole window, and be sure it is the whole window

Two things go wrong before any measuring starts.

**The capture is of the wrong screen.** On a two-monitor desktop the virtual screen
was 4480 wide against a primary of 2560. Pillow's `ImageGrab.grab(bbox=...)` without
`all_screens=True` captures the primary monitor only, so a window on the second
screen came back as a **blank white rectangle** — 8.8 kB of nothing where the
program was. The first conclusion drawn was "the app did not paint". It had painted
fine, on the monitor nobody was looking at.

**The capture is of the window's frame, not its content.** The window rectangle
includes an invisible resize border, which is why the first measurement came back at
y = -8. Clicks are given in window coordinates, and the rectangle is the origin, so
this is consistent — but a fractional coordinate copied from a different tool will
be a few pixels out.

Check the capture before trusting it: count the distinct colours. A blank capture
has one or two; a real window had 3101.

## 2. Never read coordinates off a scaled image

This is the whole of it.

A screenshot rendered at 1086 pixels wide, from a window 1936 pixels wide, is not
the window. Reading a position off it and using it directly puts every click **40%
short**. In this work that produced a run that reported *"the pencil does nothing
and the colour has no effect"* — a confident, wrong diagnosis. The clicks were fine;
the aim was not.

**The rule:** any number read off a displayed image is multiplied by

```
window_width / displayed_width
```

before it becomes a coordinate. Do it as a fraction of the window and it survives a
resize; do it as an absolute number and it will not.

## 3. The grid method

1. Grab the window.
2. Crop the region of interest.
3. **Upscale the crop** — 3× to 6× for icon-sized targets.
4. Draw a grid on the upscaled crop whose **labels are window pixel numbers**, not
   crop pixel numbers. Getting this wrong reintroduces the same bug one level down.
5. Read the targets off the grid.
6. Draw the chosen points back onto a **full, unscaled** capture.
7. **Look at it.** Before clicking anything.

Step 7 is not a formality. It is what turned "the tools do not work" into "the
crosses are all 40% from their icons" in one glance.

The overlay that confirmed six targets:

```
file     -> (42, 51)     pencil  -> (266, 99)
fill     -> (284, 127)   eraser  -> (307, 127)
brush    -> (330, 127)   colour1 -> (769, 99)
```

All six were on their icons. And the coordinates were still wrong for a different
reason — the input layer, which no amount of measuring fixes. See
[traps.md](traps.md).

## 4. For rows and grids, do not measure — scan

When the targets are a palette, a toolbar row, or a list, a human estimate is worse
than a loop. Find the runs of non-background pixels along the row and take each
run's centre.

```python
BG = (249, 249, 252)
def near_background(pixel):
    return all(abs(pixel[i] - BG[i]) < 12 for i in range(3))

runs, start = [], None
for x in range(search_from, search_to):
    solid = not near_background(image.getpixel((x, y)))
    if solid and start is None:
        start = x
    elif not solid and start is not None:
        if x - start >= 6:                  # ignore antialiasing specks
            centre = (start + x) // 2
            runs.append((centre, image.getpixel((centre, y))))
        start = None
```

This is how the palette was finally read: **swatches 24 apart starting at x 800**.
Estimating from the picture had given 28.6 apart from 806, which moved every colour
**two places to the right** — asking for yellow and getting green, asking for red and
getting orange. The colours were wrong in a way that looked like a palette problem
and was an arithmetic problem.

Scan two or three rows of `y` and compare. A row that finds nothing has missed the
targets' vertical centre; a row that finds twice as many has cut through the gaps.

## 5. Measure the region boundaries the same way

Regions matter as much as points, because a "did anything change" test is only as
good as the box it looks in.

- the **ribbon** ends where the drawing surface begins; measuring it as the top
  eighth instead of the top sixth meant the canvas region overlapped it, so a ribbon
  probe also registered as a canvas change;
- the **canvas** is the large pale rectangle, not the window minus a guessed margin;
- a probe box that overlaps two regions cannot tell you which one moved.

## 6. Then measure how the window behaves, not only where things are

Coordinates answer "where". They do not answer "what happens if I do this twice" or
"did that stick". For that, see the classification table in `SKILL.md` — the
criterion is whether a change **survives a neutral action**.

And note the trap that cost the most attempts: **a state that is already set does not
change when it is set again.** The first classification run reported "no effect" for
a tool that a previous run had left selected. Reset before probing, or probe a
change rather than a state.

## 7. Keep the captures

Write the screenshot, the overlay, and the before/after pair for every probe to a
folder beside the script. Every diagnosis in this file came from looking at one of
them, and none came from reading the code. A run that does not leave pictures cannot
be debugged after the fact — and a live desktop cannot be paused to look again.
