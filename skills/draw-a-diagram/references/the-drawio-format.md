# The .drawio format, and the two traps the vendor does not document

Primary sources, both better than this file:
[draw.io — generate and validate diagrams with AI](https://www.drawio.com/docs/reference/diagram-generation/)
and the [style reference](https://github.com/jgraph/drawio-mcp/blob/main/shared/style-reference.md),
extracted from the draw.io source. An XSD for proper validation sits beside it as `mxfile.xsd`.

**A `.drawio` file is XML. That is the whole reason this family writes diagrams instead of driving an
editor.**

## The file, in full

```xml
<mxfile host="dsh">
  <diagram id="page-1" name="Page-1">
    <mxGraphModel dx="0" dy="0" grid="1" gridSize="10" guides="1" tooltips="1" connect="1"
                  arrows="1" fold="1" page="1" pageScale="1" pageWidth="850" pageHeight="1100"
                  math="0" shadow="0">
      <root>
        <mxCell id="0" />
        <mxCell id="1" parent="0" />
        <mxCell id="n1" value="a box" style="rounded=1;whiteSpace=wrap;html=1;" vertex="1" parent="1">
          <mxGeometry x="40" y="40" width="160" height="40" as="geometry" />
        </mxCell>
      </root>
    </mxGraphModel>
  </diagram>
</mxfile>
```

## The vendor's rules, which the checker applies

1. **Two structural cells are mandatory** — `id="0"` with no parent, and `id="1" parent="0"`.
2. **No XML comments.** They are forbidden in the file.
3. **Uncompressed only.** Never generate `compressed="true"`.
4. **IDs unique** within a diagram; any string will do.
5. **One type flag per cell** — `vertex="1"` or `edge="1"`, mutually exclusive.
6. **Edges reference source and target by cell id**; an unconnected edge needs explicit points.
7. **Styles are `key=value;` pairs**, case-sensitive, `0`/`1` for booleans, colours as `#RRGGBB`.
8. **Non-rectangular shapes need their perimeter** or a connector meets the bounding box instead of the
   figure: `rhombus`→`rhombusPerimeter`, `triangle`→`trianglePerimeter`, `hexagon`→`hexagonPerimeter2`.
9. **HTML in `value` must be XML-escaped** — and see the double-escaping trap below.
10. **A group's children use coordinates relative to the group.**
11. **Origin is top-left**, x right, y down, no negative dimensions.

## Trap 1 — the bare `mxGraphModel`, and the empty page

**The documentation says a bare `<mxGraphModel>` is "a valid draw.io XML fragment" and that draw.io wraps
it automatically.**

**It does not, in Desktop 28.2.5.** Handed the fragment on its own, the application opens **an empty
page, with the correct filename in the title bar, and no error of any kind**. Wrapped in
`<mxfile><diagram>`, the identical cells render.

**This is the most expensive shape a failure can take** — the program accepted the input, reported
nothing, and drew nothing. It was found by opening the file, not by reading the documentation about it,
and it is why the checker fails a bare `mxGraphModel` with an explanation instead of a rule number.

## Trap 2 — escaping twice, which looks like a rendering bug

Labels are HTML. So `<b>text</b>` must reach the file as `&lt;b&gt;text&lt;/b&gt;`, and the natural way
to build that is to write the entities into the string and place it in the attribute.

**If the strings are escaped a second time on the way into the attribute, the file contains
`&amp;lt;b&amp;gt;` and draw.io draws the markup as visible text.** Nothing fails; the diagram simply
looks broken, which is why it took opening the file to notice.

```python
# once, at the point where the value enters the XML
import html
value = html.escape(f"<b>{meaning}</b><br><font style='font-size:10px'>{path}</font>", quote=True)
```

## Shapes and colours worth knowing

Core shapes: `rectangle` (default), `ellipse`, `rhombus`, `triangle`, `hexagon`, `cloud`, `cylinder`,
`document`, `folder`, `note`, `card`, `process`, `swimlane`, `actor`, `image`.

The vendor's colour themes, each a fill and a stroke, are enough for most diagrams and are what a reader
already associates with meaning:

| theme | fill | stroke | | theme | fill | stroke |
|---|---|---|---|---|---|---|
| blue | `#DAE8FC` | `#6C8EBF` | | yellow | `#FFF2CC` | `#D6B656` |
| green | `#D5E8D4` | `#82B366` | | red | `#F8CECC` | `#B85450` |
| purple | `#E1D5E7` | `#9673A6` | | orange | `#FFE6CC` | `#D79B00` |
| grey | `#F5F5F5` | `#666666` | | turquoise | `#B0E3E6` | `#0E8088` |

**Colour should answer one question with one meaning.** In this family's own graph: colour says *what
kind of file this is*, a thick red border says *nothing links to it*, and the arrow's colour and dash say
*how the connection was established*. Three questions, three channels, and a reader can hold them.

## Opening it from a script

```powershell
Start-Process "<path to the editor>" -ArgumentList "`"<path to the file>`""
```

Opening the file is part of delivering it. A path handed to an operator who then has to find the file is
half a delivery.
