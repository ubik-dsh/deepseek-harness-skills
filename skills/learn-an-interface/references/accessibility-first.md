# Look for the automation tree before you look for pixels

This rung was **missing from the first version of this skill**, and a survey of what
already exists on GitHub is what found the gap. Credit where it is due: the skills
that use it are `youngjunning/windows-app-automation` (Windows UI Automation with
`AutomationId` / `Name` / `ControlType` selectors), `affaan-m/ECC`'s
`windows-desktop-e2e` (pywinauto over UIA), `BanmaXM/operate-ui-by-screenshot`
("UI Automation" as one rung of a ladder that starts at API), and
`alchaincyf/huashu-mac-use` for the macOS equivalent. The trial below is ours; the
practice is theirs.

**Accessibility is a supported interface into a graphical program.** It is documented,
it is versioned by the platform rather than by the application's pixels, and where it
works it is better than a coordinate on every axis that matters. It belongs **above**
pixels in the gate, not below.

---

## The trial

Run on Paint (the Microsoft Store build), Windows 11. The question: can this program
be operated through the automation API alone, with no cursor and no coordinates?

### Finding things by identifier

```
168 descendants: 54 Button, 43 ListItem, 38 Image, 10 Group, 4 Pane,
                 4 RadioButton, 3 Slider, 3 MenuItem, 1 MenuBar, 1 Edit

FOUND  Pencil      type=Button      automationId='PencilTool'
FOUND  Eraser      type=Button      automationId='EraserTool'
FOUND  Rectangle   type=ListItem
FOUND  Oval        type=ListItem
FOUND  Triangle    type=ListItem
FOUND  Undo        type=Button
FOUND  File        type=MenuItem
FOUND  Colors      type=Group
```

### Operating them with no cursor at all

```
Pencil  supports: Toggle
  toggle state before: Off
  toggle state after Toggle(): On
  RESULT: the program's state changed through the API alone
```

No mouse move, no click, no pixel read. The state changed and the state was read back
through the same API.

### The palette has names

This is the part that stings. An earlier session spent a long time measuring the
colour swatches by scanning pixels — establishing that they were 24 apart from x 800
rather than 28.6 from 806, after getting green where yellow was wanted. The tree had
the answer the whole time:

```
[RadioButton] name='Color 1: Black'
[RadioButton] name='Color 2: White'
[ListItem]    name='Black'      [ListItem] name='Gray'
[ListItem]    name='Dark red'   [ListItem] name='Red'
[ListItem]    name='Orange'     [ListItem] name='Yellow'
[ListItem]    name='Green'      [ListItem] name='Turquoise'
[ListItem]    name='Indigo'
```

**A palette is not a row of pixels. It is a list of named colours.** Scanning for the
pitch was solving a problem that only existed because nobody asked the program.

### And where it stops

```
Pane elements:
  name='' class='Microsoft.UI.Content.DesktopChildSiteBridge'
  name='' class='InputSiteWindowClass'
  name='' class='ScrollViewer'
  name='' class='ScrollViewer'
```

**The drawing surface is not in the tree.** It is custom-drawn, so its contents do not
exist as elements, and nothing about a stroke can be expressed as an automation call.

That is the boundary, and it is a clean one:

| through the automation tree | needs coordinates |
|---|---|
| choosing a tool, a colour, a menu item | drawing on a canvas |
| setting a value, toggling a checkbox, selecting a list row | dragging a path |
| reading a label, a state, a selection | interacting with a custom-drawn surface |

Everything on the left is what the earlier work did by clicking at measured points.

## How to use it

### Windows — UI Automation

PowerShell, no install, no Python package:

```powershell
Add-Type -AssemblyName UIAutomationClient, UIAutomationTypes
$auto  = [System.Windows.Automation.AutomationElement]
$scope = [System.Windows.Automation.TreeScope]
$root  = $auto::RootElement

# find the window - match on a substring, because titles change with the document
$windows = $root.FindAll($scope::Children,
    (New-Object System.Windows.Automation.PropertyCondition(
        $auto::ControlTypeProperty, [System.Windows.Automation.ControlType]::Window)))
$app = $windows | Where-Object { $_.Current.Name -like "*Paint*" } | Select-Object -First 1

# find a control by a stable identifier
$pencil = $app.FindFirst($scope::Descendants,
    (New-Object System.Windows.Automation.PropertyCondition(
        $auto::AutomationIdProperty, 'PencilTool')))

# operate it
$toggle = $null
if ($pencil.TryGetCurrentPattern(
        [System.Windows.Automation.TogglePattern]::Pattern, [ref]$toggle)) {
    $toggle.Toggle()
}
```

The patterns worth trying, in order: `Invoke` (press a button), `Toggle` (a checkbox or
a ribbon toggle), `SelectionItem` (a list row), `ExpandCollapse` (a menu or a combo),
`Value` (a text field). If an element supports one, **use it** — it is atomic, it does
not care where the window is, and it cannot miss.

Python equivalents: `pywinauto` (the mature one), `uiautomation`, or `comtypes` against
the raw COM interface.

### macOS and Linux

- **macOS** — the AX API (`AXUIElement`), reachable from Python via
  `pyobjc-framework-ApplicationServices`, or from the command line via
  `osascript`'s System Events. Needs the Accessibility permission, which is granted by
  a human once.
- **Linux** — AT-SPI, over D-Bus. `dogtail` and `pyatspi` are the usual clients.

### Before reaching for any of it, probe what the program exposes

A diagnostic worth running once per application, because the answer decides the whole
approach:

1. list the control types present;
2. search for the specific controls the task needs, by name and by identifier;
3. **check which patterns each one supports** — an element that cannot be invoked is
   only a coordinate;
4. check whether the surface the task acts on is in the tree at all.

`operate-ui-by-screenshot` calls this ladder explicitly — API, CLI, HTML, DOM,
Playwright, CDP, UIA, screenshot — and that ordering is right.

## The caveats, measured

- **`SetFocus()` can fail** with *"Target element cannot receive focus"* even on a
  window that is plainly on screen. It did here, and the `Toggle()` worked anyway. Do
  not treat a focus failure as an automation failure.
- **`BoundingRectangle` was unusable** on this setup. Paint was on the second of two
  monitors and the reported rectangles came back as large negative numbers
  (`-31832, -31996`). So the tree gives you the element but **not** a trustworthy
  position — which matters only if you were planning to fall back to a click. If the
  element supports a pattern, you do not need the position.
- **Names are not always what you would guess.** `File` and `Pencil` were found;
  `Save as` and `Fill with color` were **not** found by those exact strings. Search by
  identifier where one exists, and enumerate rather than assume.
- **Not every application exposes much.** This is a modern build of a first-party
  program. An older or custom-drawn application may publish almost nothing, and the
  probe in the previous section is how you find that out in a minute rather than an
  hour.
- **A UWP or WinUI application may need the window to be realised** before its
  descendants exist. Enumerate once, and if the count is implausibly low, bring the
  window to the front and enumerate again.

## What this changes in the method

- **The gate gains a rung.** API, CLI, file format, library, **automation tree**,
  macro, and only then pixels. The automation tree goes above macros because it is
  uniform across applications while a macro is per-application.
- **Coordinate measurement is the fallback, not the method.** It remains exactly as
  described in [measuring-a-window.md](measuring-a-window.md) for what the tree cannot
  reach — a canvas, a custom surface, a paletted strip with no names.
- **A task that mixes both is normal.** Choosing the colour by name and drawing the
  stroke by coordinate is the correct answer for the picture this skill was built
  from, and it is a much smaller and much less brittle program than the one that was
  actually written.
- **The learning loop is unchanged** and still needed. The unknown detail in a real
  task is often not a coordinate at all — it is *which* named option among several
  similar ones, and that is a bandit over names rather than pixels. The reward, the
  verification and the memory file all still apply.
