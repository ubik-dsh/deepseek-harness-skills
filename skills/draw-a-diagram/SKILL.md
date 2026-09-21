---
name: draw-a-diagram
description: Produce a diagram as a FILE an agent writes directly - draw.io XML, its rules and its traps - instead of driving a diagram editor or describing the picture in prose. Use when the user says "show me the structure", "пиши схему", "draw this", "нарисуй", "покажи схему", or when a document would be clearer as a picture. Covers the ladder rung that matters (a diagram is a file format, so never automate the editor), the vendor's XML rules, the wrapper that Desktop silently requires, double escaping, layout that a human can read, and a validator. Ships a checker for any .drawio file.
compatibility: Agent Skills standard. SKILL.md is plain text. scripts/check-drawio.py needs Python 3.10 and no packages. Verified against draw.io Desktop 28.2.5 on Windows 11.
license: MIT
metadata:
  spec: https://github.com/agentskills/agentskills/blob/main/docs/specification.mdx
  verified_against: draw.io Desktop 28.2.5, by generating a file and opening it rather than by reading the documentation
---

# Drawing a diagram

**The request "show me the structure" is a request for a file, not for a paragraph.** A scheme described
in prose is not a scheme: the reader has to rebuild the picture in their head, and they will build a
different one.

This skill is about producing that file correctly and quickly, and about the one decision that makes the
rest easy.

## Step 1 — A diagram is a file format, so do not automate the editor

**This is the third rung of `learn-an-interface`'s ladder and it is the rung people skip.** The order is
API, command line, **file format**, library, automation tree, macro, pixels. A diagram editor is a
program that reads and writes XML: writing that XML is exact, instant, reviewable and diffable, while
driving the editor with a mouse is none of those.

| the temptation | what it costs |
|---|---|
| driving the editor to place boxes | coordinates, focus, DPI, and a picture nobody can diff |
| describing the diagram in words | the reader rebuilds it, differently |
| rendering to PNG and shipping that | a dead image; the file is editable and the picture is not |

**`.drawio` is XML.** Write it.

**Start from data, not from a blank canvas.** Everything in this family's own graph comes from one script
that emits `graph.json`; the drawing is a second projection of the same facts, so **a picture can never
disagree with the numbers it came from.**

## Step 2 — The rules, and the two that bite

Full detail with the vendor's own text: [references/the-drawio-format.md](references/the-drawio-format.md).

- **Wrap the whole thing in `<mxfile><diagram>`.** A bare `<mxGraphModel>` is documented as valid and
  **draw.io Desktop opens it as an empty page with the right filename in the title bar** — no error, no
  warning. Measured; see the reference.
- **Two structural cells are mandatory**: `<mxCell id="0" />` and `<mxCell id="1" parent="0" />`.
  Everything else has `parent="1"`.
- **No XML comments.** They are forbidden in the file.
- **Uncompressed only.** Do not generate `compressed="true"` content.
- **Escape HTML exactly once.** Labels are HTML, so `<b>` becomes `&lt;b&gt;` in the XML — and escaping a
  string that already holds entities gives `&amp;lt;b&amp;gt;`, which draw.io **draws as text**.
- **One type flag per cell** — `vertex="1"` or `edge="1"`, never both. IDs unique.

```python
import html
def esc(text: str) -> str:
    return html.escape(str(text), quote=True)     # once, at the point of writing
```

## Step 3 — Draw what a person can read, not everything you know

**A complete graph is unreadable.** The family's own graph has 480 edges over 69 nodes; drawn whole it is
a hairball, and the drawing takes **the 49 declared ones**. The data keeps everything; the picture keeps
what a human can follow. **Filter by default and offer the rest behind a flag.**

- **Columns, not a cloud.** Group nodes by what they are — one column per kind, in the order the reader
  meets them.
- **The label is the meaning, and the identifier is secondary.** The reader needs to know *what this is*;
  the path is how they find it. Both, the meaning in bold and the path small and grey beneath.
- **Say the state in words on the node**, not only in colour: `назван, но не связан` is readable to
  someone who cannot see the difference between amber and red.
- **Use the reader's language for the meaning.** A diagram is for a person even when an agent wrote it.

## Step 4 — Put the legend inside the diagram

**A legend in a separate document is a legend nobody reads.** Draw it as text cells in a corner, and say
three things: what each **colour** means, what each **border** means, and what each **arrow** means.

Colour answers *what is this*, border answers *was it found*, arrow answers *how was the connection
established*. Those are three different questions and a reader will ask all of them.

## Step 5 — Validate before delivering

Run the checker on your own output — it applies the vendor's checklist, and every item on it is one a
generator gets wrong sooner or later.

```
python scripts/check-drawio.py <file.drawio>
```

Exit **0** clean, **1** something a reader should know, **2** the file will not open. Then **open the file
and look at it**: the checker reads structure, and only the eye catches a label drawn as markup, a box
off the page, or a colour that says the wrong thing.

## Step 6 — Open it for the operator

**Deliver the open diagram, not the path.** If the editor is installed, launch it on the file; a
delivered file the operator has to go and find is half a delivery.

```powershell
Start-Process "<path to the editor>" -ArgumentList "`"<path to the file>`""
```

**Keep the generator, not the drawing.** The `.drawio` is output: regenerate it whenever the data
changes, and never hand-edit it, or the next regeneration will silently undo the edit and the file will
become the source of truth for something it does not know.

## What this skill does not cover

- **Other diagram formats.** Mermaid, Graphviz and PlantUML are different syntaxes with the same
  principle; nothing here was trialled on them.
- **The vendor's XSD.** `mxfile.xsd` exists and validates the structure properly; this skill ships a
  checklist instead of assuming an XML-schema library is installed.
- **Icon sets and shape libraries.** Drawing a branded architecture diagram needs the vendor's stencils,
  which are not part of the plain format.
- **Interactive HTML embedding.** The generated XML can be embedded in a page with the viewer library;
  that was read about and not tried.
- **One version, one platform.** Everything measured here is draw.io Desktop 28.2.5 on Windows 11. The
  behaviour of the bare `mxGraphModel` may differ in the web editor, and nobody checked.

## Where this came from

The vendor's own reference — [draw.io diagram generation](https://www.drawio.com/docs/reference/diagram-generation/)
and its [style reference](https://github.com/jgraph/drawio-mcp/blob/main/shared/style-reference.md) —
is the primary source and it is better than any third-party skill: it is extracted from the draw.io
source and it names the shapes, the palette and the pitfalls. **Read it before trusting this file.**

The wrapper trap and the double-escaping trap were both found by generating a file and opening it, and
neither is in the vendor's documentation. **[ours]**
