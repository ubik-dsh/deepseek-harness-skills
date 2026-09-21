# Making it look right

**The vendor publishes no numbers.** `drawio.com`'s best-practice pages are qualitative — "be consistent",
"include a legend" — and the style reference at `jgraph/drawio-mcp` is a **property dictionary, not a
design guide**: it says `fontSize` defaults to 12, `spacing` to 2, `spacing*` to 0, and that `arcSize` is a
percentage. Every usable number below comes from third-party agent skills, and the strongest evidence is a
49 KB validator in `Will-hxw/drawio-diagram-builder` that **enforces thresholds in code**.

**Four rules in this file are mechanically checkable** and `scripts/check-drawio.py` enforces them. The
rest are conventions, and the ones that are conventions are marked.

## The four that a machine can check

```
1  any gap below 3px is a FAIL
2  box height / fontSize must be between 1.3 and 10
     under 1.3  "cramped"
     over 10    "cavernous - the text looks tiny and lost"
3  max fontSize / min fontSize must be >= 1.5
     below that is "no typography hierarchy, typical amateur output"
4  more than 8 distinct fills, or more than 6 strokes, "the palette is scattered"
```

**These four are the only mechanically enforceable aesthetic rules found in the whole ecosystem**, which is
why they are worth more than the other twenty-two.

## Spacing

- **8px base grid.** Every coordinate, width and height is a multiple of 8.
- **A gap is measured CLEAR, not centre to centre.** Two 165px boxes 200px apart have 35px of clear
  space, not 200. This is the commonest arithmetic mistake in a generated diagram.
- **Two gap regimes, and using one where the other belongs is the mistake:**
  - **between distinct steps: 40–60px**, roughly one box height;
  - **between siblings inside a container: 10–20px**, well under half a box height.
- **Padding is not free.** `spacing` defaults to 2 and every `spacing*` to 0. Text touches the border
  unless `spacingLeft` / `spacingTop` / `spacingBottom` are set. **16–24px inside a container, 8–12px
  for text inset.**

## Type

- **Height by role**, and this is the rule that decides whether a diagram reads as a hierarchy or as a
  paragraph:

  | role | height | width |
  |---|---|---|
  | detail / leaf | 40 | 80–120 |
  | step | 50–60 | 160 |
  | rich, title plus list | 90 | 200 |
  | xl component | 100 | 200 |

- **Font ladder**: title 18–20 bold, node 13–14, body 10–12, legend 10–12. **The floor is 12**; under 7 is
  a failure.
- **Flow nodes centred. Container and band headers `align=left;verticalAlign=top;spacingTop=8`.**
  Standalone text and legends left and top.

## Colour

- **3–6 fills, 2–3 strokes.** More is scattered. *(Both this and a competing 5–8 are unvalidated
  heuristics — no source measured them.)*
- **Assign by ROLE and never by position or count.** "All boxes one colour" and "one colour per box at
  random" are both documented mistakes. A fixed pair per semantic type is the rule.
- **Light fill with a same-hue saturated stroke.** A blue fill with a red stroke is a documented semantic
  mismatch, not a style choice.
- **Avoid `shadow=1;glass=1`, decorative gradients and coloured connectors.** The vendor's own `blue` /
  `green` / … classes set shadow and glass; **`plain-blue` and its siblings keep the palette and drop
  them.** *(Whether shadow ALONE is noise is a judgement call — the source pairs it with glass, and an
  operator liked it. Colour the fill, not the mood.)*
- **A dark theme needs three extra things** or the text is unreadable: `fontColor` on every vertex,
  `strokeColor` and `fontColor` on every edge, and `background` on `<mxGraphModel>` with
  `adaptiveColors="auto"`.

## Shape, emphasis and grouping

- **One shape per semantic type, every time.** Rounded rectangle for a service, `shape=cylinder3` for a
  database, `rhombus` for a decision, `rounded=1;arcSize=50` for a terminal, `shape=parallelogram` for a
  queue, `ellipse` for a user, `shape=document`, `shape=cloud`, `swimlane;startSize=25` for a container.
- **Emphasis without shouting — four quiet levers, in this order of cheapness:**
  1. **`dashed=1`** for optional, external or ephemeral. The cheapest demotion there is.
  2. `strokeWidth` 1.5 against 2.
  3. the size class.
  4. **delete it.** *"If you cannot answer what it represents in one sentence, the element must not exist."*
- **Group by NESTING and PROXIMITY, not by adding arrows.** A module background distinct from the canvas,
  `opacity=30..60` for bands, `dashed=1` for an optional group, alternating lane fills. **Make the gap
  between groups at least twice the gap inside one**, or proximity stops reading as grouping. One style in
  the survey uses **no arrows at all** and groups purely by blocks.

## The legend

- **Required when there are two or more arrow meanings, or any colour or line style whose meaning is not
  readable from the labels** — and, per the vendor, for "complex diagrams or many abbreviations".
- **One compact multi-line `text` node**, transparent: `fillColor=none;labelBackgroundColor=none`. Each
  line shows the actual mark (▶ ▷ ◆ ◇ —) beside its meaning.
- **Never a white plate.** The source is blunt: it *"occludes connectors and neighbours… makes the diagram
  look pasted together"*. If a panel is used at all, put it where nothing passes behind it.
- **Every entry must map to a category actually present.** A legend may not compensate for missing nodes.

## Layout

- **One dominant direction.** Architecture reads left to right with short vertical branches; a workflow is
  lanes by columns; a lifecycle is phase columns.
- **Node budget**: about 12 primary nodes; ceilings of 30–35 ideal and 60 maximum for architecture, 25–30
  and 50 for workflow. **Fewer than 6 shapes on a canvas over 800×600 reads as sparse.**
- **A dense graph is fixed in this order**: delete low-value edges, then turn edges into spatial nesting,
  then wrap or grid the placement, and only then push detail into cards. **More than five edge segments per
  200×200px cell is "arrow spaghetti".**
- **Whitespace is balanced**: siblings in a row share width, height and gap; the outer padding is about
  equal to the internal gap; no one-sided blank gutter; an incomplete last row is centred.

## The "book description" fix, in payoff order

This is the complaint that produced this file: boxes stacked tightly, uniform, with no air.

1. **Break uniform width.** Every box sized to its longest label makes every row one flat band. Give each
   role a width class; keep only siblings in a row equal.
2. **Break uniform height** by role, and keep height/fontSize inside 1.3–10.
3. **Add air where it separates meaning** — 40–60px between steps, 10–20px inside a container, never
   below 3px.
4. **Build a type ladder** with a ratio of at least 1.5, and add a real title cell and a legend cell:
   they create the top rhythm that breaks the wall.
5. **Put neutral structure behind the boxes** — one band per tier, `swimlane;startSize=26` with a pale
   fill, alternating lanes.

## Traps

- **`arcSize` is a PERCENTAGE of the smaller dimension, not a pixel radius.** The design tokens that say
  "8px corner radius" mean `arcSize ≈ radius_px / height × 100`. For a 60px box, `arcSize=13` is about 8px.
  **The source that states the rule breaks it elsewhere in its own files** — a reminder that a token file
  can be internally inconsistent.
- **The vendor's shape classes carry `shadow` and `glass`.** Using `blue` is not the same as using
  `plain-blue`.
- **`fontSize` has a default of 12 and `spacing*` a default of 0** — inheriting them looks deliberate and
  is not.

## Where this is thin

- **The vendor supplies zero numbers.** Everything measured here is third-party.
- **The legend convention is single-sourced.**
- **Colour-count limits are unvalidated heuristics.**
- **The empirical graph-aesthetics literature — Purchase, Ware, edge crossings, bend minimisation — was
  paywalled, so every routing and crossing rule above is engineering convention, not a measured finding.**
- **The mechanics of `sketch=1` / `comic=1` are undocumented** beyond the preset name.
- **No source was checked for a dark theme in practice**, so the three dark-theme settings are carried
  forward from documentation rather than tried.
