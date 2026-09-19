#!/usr/bin/env python3
"""Prove the target before anything is pressed.

A click that lands on the wrong window is not a failed experiment. It is an action taken on
someone else's work, and in the session that produced this skill it happened twice: the
coordinates were right and the window was wrong. Every check here is cheap and mechanical, and
the point is that they run **before** the input rather than after the damage.

It reports and never acts. Nothing in this file moves the pointer, presses a key, or changes
a window.

    python preflight.py --title "Notepad"
    python preflight.py --title "Notepad" --point 400,300
    python preflight.py --list

Exit codes:  0 every check passed,  1 a check failed,  2 the target was not found.
A failed check is a reason to stop, not to nudge the coordinates and try again.
"""

from __future__ import annotations

import argparse
import ctypes
import sys
from ctypes import wintypes

if sys.platform != "win32":                       # pragma: no cover - reported, not raised
    print("  this checks a Windows desktop; the platform is " + sys.platform, file=sys.stderr)
    raise SystemExit(2)

user32 = ctypes.WinDLL("user32", use_last_error=True)
shcore = ctypes.WinDLL("shcore", use_last_error=True)

# The handle types matter. Left as the default c_int, a handle comes back truncated on a
# 64-bit machine and every later comparison is against a number that means nothing.
user32.GetForegroundWindow.restype = wintypes.HWND
user32.GetAncestor.restype = wintypes.HWND
user32.WindowFromPoint.restype = wintypes.HWND
user32.GetAncestor.argtypes = (wintypes.HWND, wintypes.UINT)

GA_ROOT = 2


class Rect(ctypes.Structure):
    _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long),
                ("right", ctypes.c_long), ("bottom", ctypes.c_long)]


def window_title(handle: int) -> str:
    length = user32.GetWindowTextLengthW(handle)
    buffer = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(handle, buffer, length + 1)
    return buffer.value


def find_windows(fragment: str) -> list[tuple[int, str]]:
    """Every visible top-level window whose title contains the fragment."""
    found: list[tuple[int, str]] = []

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def visit(handle, _param):
        if user32.IsWindowVisible(handle):
            title = window_title(handle)
            if fragment.lower() in title.lower():
                found.append((handle, title))
        return True

    user32.EnumWindows(visit, 0)
    return found


def rect_of(handle: int) -> Rect:
    box = Rect()
    user32.GetWindowRect(handle, ctypes.byref(box))
    return box


def dpi_of(handle: int) -> int:
    """The window's DPI, or 0 when it cannot be read.

    GetDpiForWindow lives in user32 from Windows 10 1607 on, and its signature has to be
    declared: without a restype ctypes assumes c_int, which is right here but wrong for the
    handle parameters that call it. It is guarded because the fallback — read the DPI of the
    whole desktop — is only correct on a single-monitor machine, and saying 0 is more honest
    than saying the wrong number.
    """
    try:
        user32.GetDpiForWindow.argtypes = (wintypes.HWND,)
        user32.GetDpiForWindow.restype = ctypes.c_uint
        return int(user32.GetDpiForWindow(handle))
    except (AttributeError, OSError):
        return 0


def is_elevated() -> bool:
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except OSError:
        return False


def pid_of(handle: int) -> int:
    """The process that owns a window."""
    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(handle, ctypes.byref(pid))
    return int(pid.value)


def check_point(spec: str | None, handle: int, box: Rect,
                failures: list[str]) -> int | None:
    """Fourth and fifth checks: the point is inside, and the window under it agrees."""
    if not spec:
        return None
    try:
        x_text, y_text = spec.split(",")
        x, y = int(x_text), int(y_text)
    except ValueError:
        print(f"  --point must be X,Y, not {spec!r}", file=sys.stderr)
        return 2
    inside = box.left <= x < box.right and box.top <= y < box.bottom
    print(f"  point     {x},{y}  inside the target: {inside}")
    if not inside:
        failures.append(f"the point {x},{y} is not inside the target window")
    under = user32.WindowFromPoint(wintypes.POINT(x, y))
    root = user32.GetAncestor(under, GA_ROOT) if under else 0
    print(f"  under it  {root:#010x}  {window_title(root)[:48]!r}")
    if root != handle:
        failures.append(
            f"the window at {x},{y} is {window_title(root)!r}, not the target")
    return None


def report(failures: list[str]) -> int:
    print("")
    if failures:
        print(f"  FAIL — {len(failures)} check(s) did not pass:", file=sys.stderr)
        for one in failures:
            print(f"    - {one}", file=sys.stderr)
        print("", file=sys.stderr)
        print("  Do not adjust and try again. Re-find the target by identity, re-measure "
              "it, and re-check.", file=sys.stderr)
        return 1
    print("  PASS — the target is where the input will land.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--title", help="a fragment of the target window's title")
    parser.add_argument("--point", help="the coordinate about to be pressed, as X,Y")
    parser.add_argument("--pid", type=int,
                        help="the process id the target must belong to; given, the window is matched by identity rather than by title")
    parser.add_argument("--allow-title-only", action="store_true",
                        help="proceed although the target was matched by title alone")
    parser.add_argument("--list", action="store_true", help="list visible top-level windows")
    args = parser.parse_args()

    if args.list or not args.title:
        print(f"  {len(find_windows(''))} visible top-level windows")
        for handle, title in sorted(find_windows(""), key=lambda pair: pair[1].lower())[:40]:
            box = rect_of(handle)
            print(f"    {handle:#010x}  {box.left:>6},{box.top:>6}  "
                  f"{box.right - box.left:>5}x{box.bottom - box.top:<5} {dpi_of(handle):>4}dpi  {title[:52]}")
        return 0

    failures: list[str] = []

    if args.pid is not None:
        owned = [pair for pair in find_windows(args.title or "") if pid_of(pair[0]) == args.pid]
        print(f"  target: pid {args.pid} — {len(owned)} window(s) belong to it")
        for handle, title in owned[:8]:
            print(f"    {handle:#010x}  {title[:64]}")
        if not owned:
            print("", file=sys.stderr)
            print(f"  FAIL  no window titled {args.title!r} belongs to pid {args.pid}.",
                  file=sys.stderr)
            print("        The process may have exited, or the window belongs to something "
                  "else that happens to share the title.", file=sys.stderr)
            return 2
        handle, title = owned[0]
        box = rect_of(handle)
        foreground = user32.GetForegroundWindow()
        print("")
        print(f"  window    {handle:#010x}  {title!r}")
        print(f"  pid       {args.pid}  (matched by identity, not by appearance)")
        print(f"  rect      {box.left},{box.top} → {box.right},{box.bottom}  "
              f"({box.right - box.left}x{box.bottom - box.top})")
        print(f"  dpi       {dpi_of(handle)}")
        print(f"  elevated  {is_elevated()}")
        if foreground != handle:
            failures.append(
                f"the target is not the foreground window (foreground is "
                f"{window_title(foreground)!r})")
        point_result = check_point(args.point, handle, box, failures)
        if point_result is not None:
            return point_result
        return report(failures)

    matches = find_windows(args.title)
    print(f"  target: {args.title!r} — {len(matches)} window(s) match")
    for handle, title in matches[:8]:
        print(f"    {handle:#010x}  {title[:64]}")

    if not matches:
        print("", file=sys.stderr)
        print(f"  FAIL  nothing titled {args.title!r} is on screen.", file=sys.stderr)
        print("        A window that does not exist cannot be focused, and a click sent "
              "anyway lands on whatever is.", file=sys.stderr)
        return 2

    if not args.allow_title_only:
        failures.append(
            "the target was matched by title alone, which is how a window belonging to "
            "something else gets chosen — pass --pid to match by identity, or "
            "--allow-title-only to accept the risk deliberately")

    if len(matches) > 1:
        failures.append(
            f"{len(matches)} windows match — the title is not specific enough to say which one "
            "will receive the input")

    handle, title = matches[0]
    box = rect_of(handle)
    foreground = user32.GetForegroundWindow()

    print("")
    print(f"  window    {handle:#010x}  {title!r}")
    print(f"  rect      {box.left},{box.top} → {box.right},{box.bottom}  "
          f"({box.right - box.left}x{box.bottom - box.top})")
    print(f"  dpi       {dpi_of(handle)}  (100 = unscaled; coordinates scale with this)")
    print(f"  elevated  {is_elevated()}  (an elevated agent can do anything and ask nothing)")

    # 1. exists — established above
    # 2. foreground, checked now rather than a moment ago
    if foreground != handle:
        failures.append(
            f"the target is not the foreground window (foreground is {window_title(foreground)!r}) "
            "— SendInput goes to the focused window, so the input would land there instead")

    # 3. the point is inside the target
    if args.point:
        try:
            x_text, y_text = args.point.split(",")
            x, y = int(x_text), int(y_text)
        except ValueError:
            print(f"  --point must be X,Y, not {args.point!r}", file=sys.stderr)
            return 2
        inside = box.left <= x < box.right and box.top <= y < box.bottom
        print(f"  point     {x},{y}  inside the target: {inside}")
        if not inside:
            failures.append(
                f"the point {x},{y} is not inside the target window — it would land on "
                "another window, or on the desktop")
        # 4. and the window under the point agrees
        under = user32.WindowFromPoint(wintypes.POINT(x, y))
        root = user32.GetAncestor(under, GA_ROOT) if under else 0
        print(f"  under it  {root:#010x}  {window_title(root)[:48]!r}")
        if root != handle:
            failures.append(
                f"the window at {x},{y} is {window_title(root)!r}, not the target — the "
                "coordinate belongs to something else now")

    print("")
    if failures:
        print(f"  FAIL — {len(failures)} check(s) did not pass:", file=sys.stderr)
        for one in failures:
            print(f"    - {one}", file=sys.stderr)
        print("", file=sys.stderr)
        print("  Do not adjust the coordinates and try again. Re-find the target, re-measure "
              "it, and re-check.", file=sys.stderr)
        return 1

    print("  PASS — the target is where the input will land. It can be pressed, and it is "
          "worth checking again immediately before, because focus changes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
