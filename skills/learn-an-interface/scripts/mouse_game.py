#!/usr/bin/env python3
"""A calibration game: nine gestures on a cube, with the whole checklist visible and bilingual.

WHY A GAME AND NOT A LOG. A log says what the system received; it cannot say whether what arrived is
what the hand did. Here every gesture has a known shape and a visible tick, so a mismatch is a finding
rather than an ambiguity - and the wheel's direction, a double click's interval and a drag's two
endpoints are all named by the window that had to react to them.

IT ALSO CROSS-CHECKS THE HOOK. The Win32 mouse hook reports the side buttons as X1 and X2; tkinter
reports buttons by NUMBER, and the two schemes disagree - measured here, not looked up. Running both at
once is how the mapping gets established.

Two languages, switchable in the window, because a calibration nobody can read is not a calibration.

    python mouse_game.py [--out log.csv] [--lang ru]
"""
from __future__ import annotations

import argparse
import sys
import time
import tkinter as tk

sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")

ap = argparse.ArgumentParser()
ap.add_argument("--out", default="mouse_game.csv")
ap.add_argument("--lang", default="ru", choices=["ru", "en"])
args = ap.parse_args()

W, H = 1000, 800
PLAY_H = 460
CUBE = 110
LEFT_LIMIT = W // 2
CUBE_X, CUBE_Y = 130, 170

STEPS = ["click", "double", "right", "middle", "side1", "side2", "wheel_up", "wheel_down", "drag"]

TEXT = {
    "ru": {
        "title": "Калибровка мыши",
        "drop": "СЮДА БРОСИТЬ",
        "cube": "КУБИК",
        "click":      "левый клик по кубику",
        "double":     "двойной левый клик по кубику",
        "right":      "правый клик по кубику",
        "middle":     "средняя кнопка — нажать колесо",
        "side1":      "боковая кнопка — ЗАДНЯЯ",
        "side2":      "боковая кнопка — ПЕРЕДНЯЯ",
        "wheel_up":   "колесо ОТ СЕБЯ, курсор на кубике",
        "wheel_down": "колесо НА СЕБЯ, курсор на кубике",
        "drag":       "зажать кубик, ПЕРЕТАЩИТЬ в правую половину, отпустить",
        "done_n":     "{n}/9 пройдено",
        "next":       "СЛЕДУЮЩЕЕ",
        "all_done":   "всё пройдено — окно закроется само",
        "switch":     "English",
        "esc":        "Esc — закончить",
    },
    "en": {
        "title": "Mouse calibration",
        "drop": "DROP HERE",
        "cube": "CUBE",
        "click":      "left-click the cube once",
        "double":     "double-click the cube",
        "right":      "right-click the cube",
        "middle":     "middle-click the cube (press the wheel down)",
        "side1":      "side button - the BACK one",
        "side2":      "side button - the FORWARD one",
        "wheel_up":   "wheel AWAY from you, over the cube",
        "wheel_down": "wheel TOWARD you, over the cube",
        "drag":       "hold the cube, DRAG it into the right half, let go",
        "done_n":     "{n}/9 done",
        "next":       "NEXT",
        "all_done":   "all nine done - the window closes by itself",
        "switch":     "Русский",
        "esc":        "Esc - finish",
    },
}

lang = args.lang

root = tk.Tk()
root.geometry(f"{W}x{H}+160+60")
root.configure(bg="#0e1216")

# A GUI started by an agent opens BEHIND whatever is in front, because nothing gave it focus. The
# first run was launched from a background job and appeared underneath the browser, so the operator
# saw nothing and the calibration could not start.
root.attributes("-topmost", True)
root.lift()
root.focus_force()

header = tk.Frame(root, bg="#0e1216")
header.pack(fill="x", padx=16, pady=(10, 0))

switcher = tk.Button(header, text="", font=("Segoe UI", 13, "bold"), bg="#1d4e79", fg="#eaf4ff",
                     activebackground="#2a6ba3", activeforeground="#ffffff", relief="flat", padx=18,
                     pady=6, cursor="hand2")
switcher.pack(side="right")

hint = tk.Label(header, text="", font=("Segoe UI", 11), bg="#0e1216", fg="#6b7c8f", anchor="w")
hint.pack(side="left")

canvas = tk.Canvas(root, width=W, height=PLAY_H, bg="#0e1216", highlightthickness=0)
canvas.pack()

checklist = tk.Label(root, text="", font=("Consolas", 14), bg="#0e1216", fg="#cfd8e3",
                     anchor="nw", justify="left")
checklist.pack(fill="both", expand=True, padx=22, pady=(8, 12))

drop_rect = canvas.create_rectangle(LEFT_LIMIT, 0, W, PLAY_H, outline="#2b3a4a", dash=(8, 8), width=2)
drop_text = canvas.create_text(LEFT_LIMIT + (W - LEFT_LIMIT) // 2, 34, text="",
                               fill="#3f5568", font=("Consolas", 16, "bold"))

cube = canvas.create_rectangle(CUBE_X, CUBE_Y, CUBE_X + CUBE, CUBE_Y + CUBE,
                               fill="#3d7ebf", outline="#9fd0ff", width=4)
cube_text = canvas.create_text(CUBE_X + CUBE // 2, CUBE_Y + CUBE // 2, text="",
                               fill="#eaf4ff", font=("Consolas", 14, "bold"))

log = open(args.out, "w", encoding="utf-8", newline="")
log.write("t,event,x,y,note\n")
start = time.time()

done: set[str] = set()
last_left_down = 0.0
drag_from: tuple[float, float] | None = None
drag_last: tuple[float, float] | None = None
drag_moved = 0.0
raw_seen: dict[str, int] = {}


def t(key: str) -> str:
    return TEXT[lang][key]


def record(event: str, x: int, y: int, note: str = "") -> None:
    log.write(f"{time.time() - start:.3f},{event},{x},{y},{note}\n")
    log.flush()
    raw_seen[event] = raw_seen.get(event, 0) + 1


def refresh() -> None:
    lines = []
    for index, key in enumerate(STEPS, 1):
        lines.append(("[x] " if key in done else "[ ] ") + f"{index}. " + t(key))
    ticked = len(done)
    nxt = next((k for k in STEPS if k not in done), None)
    lines.append("")
    if nxt:
        lines.append(f"{t('done_n').format(n=ticked)}        {t('next')}:  {t(nxt)}")
    else:
        lines.append(t("all_done"))
    checklist.config(text="\n".join(lines))
    canvas.itemconfig(drop_text, text=t("drop"))
    canvas.itemconfig(cube_text, text=t("cube"))
    hint.config(text=t("esc"))
    switcher.config(text=t("switch"))
    root.title(f"{t('title')} - {ticked}/9" + (f" - {t('next')}: {t(nxt)}" if nxt else ""))


def switch_language() -> None:
    global lang
    lang = "en" if lang == "ru" else "ru"
    record("LANGUAGE", 0, 0, lang)
    refresh()


switcher.config(command=switch_language)


def complete(key: str) -> None:
    if key not in done:
        done.add(key)
        record(f"DONE-{key}", 0, 0, "step completed")
        refresh()
    if len(done) == len(STEPS):
        root.after(1200, finish)


def finish() -> None:
    record("FINISHED", 0, 0, ";".join(f"{k}={v}" for k, v in sorted(raw_seen.items())))
    log.close()
    print(f"  finished with {len(done)}/9; {sum(raw_seen.values())} raw events")
    for name, count in sorted(raw_seen.items(), key=lambda kv: -kv[1]):
        print(f"    {name:16} {count}")
    root.destroy()


def over_cube(x: int, y: int) -> bool:
    box = canvas.coords(cube)
    return box[0] <= x <= box[2] and box[1] <= y <= box[3]


def on_press(event: tk.Event) -> None:
    global last_left_down, drag_from, drag_moved, drag_last
    x, y = event.x, event.y
    record(f"Button-{event.num}", x, y, "press")
    hit = over_cube(x, y)

    if event.num == 1:
        now = time.time()
        if hit:
            if 0 < now - last_left_down < 0.45:
                complete("double")
            complete("click")
            drag_from = (x, y)
            drag_last = (x, y)
            drag_moved = 0.0
        last_left_down = now
    elif event.num == 2 and hit:
        complete("middle")
    elif event.num == 3 and hit:
        complete("right")
    # MEASURED, not looked up. tkinter accepts Button-1..5 on this Windows build and no more, and its
    # numbering is NOT Win32's: the side buttons arrive as Button-4 and Button-5, the right button is
    # Button-3 and the middle is Button-2. The first version awaited 6, 7, 8 and 9 - numbers tkinter
    # had already refused to bind - so the side-button steps could never be ticked and the game sat at
    # six of nine while the operator pressed the right buttons.
    elif event.num in (4, 5) and hit:
        complete("side1" if event.num == 4 else "side2")


def on_wheel(event: tk.Event) -> None:
    delta = getattr(event, "delta", 0)
    record("MouseWheel", event.x, event.y, f"delta={delta}")
    if over_cube(event.x, event.y) and delta:
        complete("wheel_up" if delta > 0 else "wheel_down")


def on_motion(event: tk.Event) -> None:
    global drag_moved, drag_last
    if drag_from is not None:
        # Against the PREVIOUS point, not the origin. Comparing with the origin each time makes the
        # total the sum of growing distances - a 572 px drag was reported as 36421 px of movement.
        # The number is still evidence that motion arrived in many steps, but it is not a distance.
        if drag_last is not None:
            drag_moved += abs(event.x - drag_last[0]) + abs(event.y - drag_last[1])
        drag_last = (event.x, event.y)
        canvas.coords(cube, event.x - CUBE // 2, event.y - CUBE // 2,
                      event.x + CUBE // 2, event.y + CUBE // 2)
        canvas.coords(cube_text, event.x, event.y)


def on_release(event: tk.Event) -> None:
    global drag_from
    if event.num == 1 and drag_from is not None:
        # BOTH the instance and the rule. The pixels are what a calibration needs - they are how a
        # drag is told from a stray click, and how the path is proved continuous. The NAMES are what a
        # skill needs, because the drop point belongs to the situation: "MOVE cube -> right-half", not
        # "release at 754,235". Recording only the second is how a rule turns into a coordinate
        # somebody later reuses in a window where it means something else.
        target = "right-half" if event.x > LEFT_LIMIT else "left-half"
        start_target = "right-half" if drag_from[0] > LEFT_LIMIT else "left-half"
        record("DRAG", event.x, event.y,
               f"from={start_target} to={target} moved={int(drag_moved)}")
        if event.x > LEFT_LIMIT:
            complete("drag")
        drag_from = None


bound = []
for n in range(1, 12):
    try:
        canvas.bind(f"<Button-{n}>", on_press)
        bound.append(n)
    except tk.TclError:
        pass
for seq, handler in (("<MouseWheel>", on_wheel), ("<B1-Motion>", on_motion),
                     ("<ButtonRelease-1>", on_release)):
    try:
        canvas.bind(seq, handler)
    except tk.TclError:
        pass
root.bind("<Escape>", lambda _e: finish())

refresh()
print(f"  tkinter accepted Button-{bound}")
print(f"  the game is open in '{lang}'; logging to {args.out}")
record("BOUND", 0, 0, "buttons=" + "|".join(str(b) for b in bound))
root.mainloop()
