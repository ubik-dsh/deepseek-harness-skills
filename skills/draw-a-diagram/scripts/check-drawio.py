#!/usr/bin/env python3
"""Check a .drawio file against the vendor's own list, plus the two traps measured here.

The rules are from draw.io's published generation reference and its mxfile.xsd, and every one of them is
something a generator gets wrong sooner or later. The two the vendor does NOT document are marked
[ours] and were found by generating a file and opening it.

    python check-drawio.py <file.drawio> [<file2.drawio> ...]

Exit 0 clean, 1 something a reader should be told, 2 the file will not open at all.
"""
from __future__ import annotations

import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")

# The shapes whose perimeter must be named in the style, or a connector meets the bounding box instead
# of the figure and the arrow appears to stop in mid-air.
PERIMETER = {
    "rhombus": "rhombusPerimeter",
    "triangle": "trianglePerimeter",
    "hexagon": "hexagonPerimeter2",
    "ellipse": "ellipsePerimeter",
}

problems: list[str] = []
notes: list[str] = []


def check(path: Path) -> int:
    problems.clear()
    notes.clear()
    raw = path.read_text(encoding="utf-8", errors="replace")

    if "-->" in raw:
        problems.append("XML comments are forbidden in a .drawio file")

    try:
        root = ET.fromstring(raw)
    except ET.ParseError as trouble:
        print(f"WILL NOT OPEN  {path.name}: {trouble}")
        return 2

    # [ours] A bare mxGraphModel is documented as valid and opens as an EMPTY PAGE in Desktop 28.2.5.
    # Silence about a structure the program accepts and then does nothing with is the expensive kind.
    if root.tag == "mxGraphModel":
        problems.append(
            "[ours] bare <mxGraphModel>: draw.io Desktop opens this as an EMPTY PAGE with the right "
            "filename shown. Wrap it in <mxfile><diagram> - one line, and it renders"
        )
    elif root.tag != "mxfile":
        problems.append(f"root element is <{root.tag}>, expected <mxfile>")

    diagrams = list(root.iter("diagram")) if root.tag == "mxfile" else []
    if root.tag == "mxfile" and not diagrams:
        problems.append("an mxfile with no <diagram> in it")

    for diagram in diagrams:
        if diagram.get("compressed") == "true":
            problems.append("compressed content: the vendor says never to generate it")
        model = diagram.find("mxGraphModel")
        if model is None:
            problems.append(f"diagram {diagram.get('id')} has no mxGraphModel")
            continue
        cells = [c for c in model.iter("mxCell")]

        ids = [c.get("id") for c in cells]
        duplicates = {i for i in ids if ids.count(i) > 1}
        if duplicates:
            problems.append(f"duplicate cell ids: {sorted(duplicates)[:5]}")

        if "0" not in ids:
            problems.append('the root cell <mxCell id="0" /> is missing')
        layer = next((c for c in cells if c.get("id") == "1"), None)
        if layer is None or layer.get("parent") != "0":
            problems.append('the default layer <mxCell id="1" parent="0" /> is missing')

        for cell in cells:
            cell_id = cell.get("id")
            if cell_id in {"0", None}:
                continue
            if cell.get("parent") is None:
                problems.append(f"cell {cell_id} has no parent")
            if cell.get("vertex") == "1" and cell.get("edge") == "1":
                problems.append(f"cell {cell_id} is both a vertex and an edge")
            if cell.get("vertex") != "1" and cell.get("edge") != "1" and cell_id != "1":
                notes.append(f"cell {cell_id} is neither vertex nor edge - it will not be drawn")

        for edge in (c for c in cells if c.get("edge") == "1"):
            for end in ("source", "target"):
                ref = edge.get(end)
                if ref and ref not in ids:
                    problems.append(f"edge {edge.get('id')} {end}={ref} does not exist")

        for cell in cells:
            style = cell.get("style") or ""
            shape = next((token for token in style.split(";")
                          if "=" not in token and token.strip()), "")
            if shape in PERIMETER and f"perimeter={PERIMETER[shape]}" not in style:
                notes.append(f"cell {cell.get('id')} is a {shape} without {PERIMETER[shape]}")

            geometry = cell.find("mxGeometry")
            if cell.get("vertex") == "1" and geometry is not None:
                for attribute in ("x", "y", "width", "height"):
                    value = geometry.get(attribute)
                    if value is None:
                        problems.append(f"vertex {cell.get('id')} has no {attribute}")
                    elif float(value) < 0:
                        problems.append(f"vertex {cell.get('id')} has a negative {attribute}")

    # A label that CONTAINS an entity is being drawn as text, which is what double escaping looks like.
    for match in re.finditer(r'value="([^"]*)"', raw):
        if "&amp;lt;" in match.group(1) or "&amp;gt;" in match.group(1):
            problems.append(
                '[ours] a label contains "&amp;lt;" - HTML was escaped twice and draw.io will DRAW THE '
                'MARKUP as text. Build the label with real <b> and escape once'
            )
            break

    print(f"{path.name}")
    print(f"  cells {len(list(root.iter('mxCell')))}   diagrams {max(len(diagrams), 1)}")
    for one in problems:
        print(f"  PROBLEM  {one}")
    for one in notes[:6]:
        print(f"  note     {one}")
    if not problems:
        print("  ok       no comments, wrapped, structural cells present, ids unique, "
              "targets exist, geometry complete")
    return 1 if problems else 0


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    worst = 0
    for name in sys.argv[1:]:
        worst = max(worst, check(Path(name)))
    return worst


if __name__ == "__main__":
    raise SystemExit(main())
