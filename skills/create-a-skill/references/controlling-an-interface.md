# Controlling an interface, and when not to

A skill sometimes has to do something for which the only handle is a picture of a
window: click a button, choose from a menu, type into a field. This reference is
about that case — how to decide whether to build it at all, and how to build one
that learns instead of one that has coordinates written into it.

Read this **only** if the skill's success test needs a real interface driven. Most
skills do not, and reaching for a mouse is the most expensive way to do almost
anything.

---

## 1. The gate: do not build this unless nothing else will do

Driving a GUI is the last resort, not the first. Before writing a line of it, the
question is not "can this be automated?" — it always can — but "is there a
supported way in?" Work down this list and stop at the first yes.

| ask | if yes |
|---|---|
| Is there an API, SDK, or service for this? | use it |
| Is there a command-line tool that does it? | use it |
| Is the thing a file format you can read and write directly? | do that |
| Is there a library that reads or writes it? | use that |
| Can the interface be scripted by the application itself (a macro, a plugin, a config file, a URL scheme)? | use that |
| **None of the above, and the only way in is pixels and clicks** | build what this reference describes |

The reason for the order is not purity, it is brittleness. An interface automator
is coupled to things nobody promised to keep:

- the **version** — a ribbon is rearranged between releases and every coordinate
  silently means something else;
- the **theme and scale** — the same build on a 125% display puts the buttons
  somewhere else;
- the **keyboard layout** — typed text goes through the layout unless it is sent
  as Unicode;
- the **monitor count and arrangement** — a coordinate on the second screen is not
  a coordinate on the first;
- **someone else's window on top**, a modal prompt, a first-run dialog, a licence
  notice, an update nudge.

Every one of those has caused a failure in the work this reference is drawn from.
An API has none of them.

**Say so in the skill.** If the skill drives an interface because nothing else was
available, write that sentence down: the reader deserves to know this was the last
resort and why the alternatives were rejected. It also tells the next person where
to look when a release breaks it.

### The gate is a condition, not a preamble

The skill should build the automator **only when the test requires it**, and should
say what makes it required. A skill that always reaches for the mouse is worse than
one that never does. Phrase it as a branch the reader can evaluate:

> If the task's success test needs this program driven and it exposes no API, CLI
> or file format, use `references/controlling-an-interface.md`. Otherwise do not —
> and if you are unsure, the answer is no.

---

## 2. Learn it, do not hard-code it

The useful shape of an interface automator is not a script. It is a **loop that
tries, checks, and remembers** — because the thing being found is usually a detail
nobody documents, like which row of a dropdown is the one you want.

The measured difference, from the same task done both ways:

```
done by hand          the row was found after six attempts, and the number was
                      written into the script. On a new build, or a scaled display,
                      it is wrong again and someone re-measures it by hand.

done by learning      six attempts to explore, then no further misses. The file
                      on disk holds the counts. A later run goes straight there
                      with no exploration at all.
```

The learning loop is a **contextual bandit**:

- **actions** — a small finite set of candidates. Coordinates near the target, rows
  in a list, offsets around a guess. Small on purpose: ten candidates converge in
  ten attempts.
- **reward** — a number from a *verified* outcome. See §3; this is where it goes
  wrong.
- **selection** — UCB1. Try each action once, then pick the one with the best upper
  confidence bound: `mean + sqrt(2 * ln(total) / n)`. It needs no learning rate,
  it is deterministic, and exploration comes out of the same formula as
  exploitation instead of being a separate knob to tune.
- **memory** — counts and totals per action, per task, in a JSON file next to the
  script. That file *is* the learning. Losing it costs exactly one exploration
  sweep.

`scripts/learn-an-interface.py` is a runnable template of this. Copy it, replace
the task, keep the bandit.

### Reward shape matters more than the algorithm

A binary reward throws away information that costs real time to get. Use a graded
one where a partial result exists:

```
1.0   the thing that was wanted happened        (a real PNG was written)
0.3   something happened, and not that thing    (a file was written, as TIFF)
0.0   nothing happened                          (no file at all)
```

With only 1.0 and 0.0 the learner cannot tell "close" from "nowhere", and it spends
attempts relearning what it already knew.

---

## 3. The success test must check the thing, not its shadow

**This is the single most valuable lesson in this file.**

The test "did the file get saved?" passed. The file's name was `picture.png`.

Its first eight bytes were `00 00 00 20 66 74 79 70` — an ISO media container.
A PNG starts `89 50 4E 47 0D 0A 1A 0A`. The program had a **Paint project file
wearing an image's extension**, and a test that asked whether a file existed
certified it as a success every time.

The same failure has three shapes, and all three appeared in one afternoon:

| the weak test | what it certified |
|---|---|
| "a file exists" | a project file named `.png` |
| "the screen changed" | a menu opening, a highlight moving, nothing done |
| "a value came back" | an error page parsed as if it were data |

So: name the artifact, then check a property only the right artifact has. Magic
bytes. A parse that succeeds. A value in range. A count that went up by the amount
it should have. And then **run the test against the wrong thing once**, to watch it
fail — a success test that has never failed is not yet a test.

For the learning loop this is not a nicety: the reward *is* the test. A weak reward
does not merely fail to help, it trains the policy on the wrong target, and the
learner settles confidently on the wrong action.

---

## 4. The traps, all of them measured

Each of these was found by running something and reading a number. None by reading
the code.

**Coordinates read off a scaled screenshot.** A screenshot displayed at 1086 wide
from a window of 1936 is not the window. Every click landed 40% short, and the
report said "the pencil does nothing" rather than "the aim is wrong". Always convert
back to the window's own pixels, and draw the target points onto a capture and
*l**ook** at it before trusting a single one.

**The deprecated input APIs do not reach a modern application.** Measured on Paint:
a drag across the canvas through `mouse_event` changed **exactly zero pixels** — and
the same drag through `SendInput` left a line. `keybd_event` is the same trap for
keys: Escape and Ctrl+S were seen, `Ctrl+Z` never was, so an undo that had visibly
happened was measured as not having happened. **Use `SendInput`.** The legacy calls
still move the pointer and still open menus, which is what makes the failure look
like a logic bug for an hour.

**Moving the pointer and giving it to nobody.** `mouse_event` with
`MOUSEEVENTF_ABSOLUTE` addresses the **primary monitor** unless
`MOUSEEVENTF_VIRTUALDESK` is also set. On a two-monitor desktop it threw the cursor
back to the other screen and the click landed in a stranger's browser window.
`SetCursorPos` alone is right about monitors and wrong about drags: with no move
events, an application sees press and release in one place — a dot, not a stroke —
so a drawing program records nothing. `SendInput` with `ABSOLUTE | VIRTUALDESK` is
right about both.

**Verify before you press.** After moving the pointer, read its position back, and
**raise** if it is not where it was asked to go. This turns "I clicked something
unintended on a live desktop" into a stopped run. It is four lines and it is not
optional when the desktop belongs to someone.

**Typing goes through the keyboard layout.** `VkKeyScanW` answers with the key that
produces the character *in the current layout*. On a Russian layout, typing a folder
path with backslashes in it produced `\\W/Y\/L/.` and the dialog answered "The file
name is not valid." Send the character as a `KEYEVENTF_UNICODE` scan code and the
layout stops mattering.

**A modal dialog blocks everything and reports nothing.** One failed save left a
"file already exists" prompt up, and the next six attempts were blocked by it while
the log said "nothing was written". Before each attempt, dismiss anything modal;
after each attempt, check whether a dialog is still standing.

**"The action failed" and "there was nothing to act on" are different findings.** A
twelve-iteration run scored zero on every attempt, so the learner concluded that no
candidate worked — Paint had died partway through and the harness was gone. Check
the world exists before judging the action, and make the distinction explicit.

**Shapes are drawn from corner to corner.** A drawing tool that inscribes its shape
in the drag rectangle draws nothing when the drag is a straight line along one edge.
A zero-height triangle, then a fill that landed on bare canvas, then a page flooded
one colour.

**A safe action can become a trap.** Reloading cost a little and avoided the
penalty for missing, and missing is what an *untried* aim looks like — so the agent
learned two of three mappings and answered "reload" to the third. If the action set
contains a safe fallback, either price it honestly or initialise optimistically.

---

## 5. What to write down in the skill

- The **gate**, as a branch the reader evaluates, with the alternatives that were
  rejected and why.
- The **verified success test**, and the wrong-thing run that proved it fails.
- The **learned values** if they are learned, or a note that they are measured and
  will need re-measuring when the program changes.
- The **traps that bit**, in the imperative — the next person has the same two hours
  to lose.
- The **cost**: how many attempts exploration took, so the reader knows what a fresh
  memory costs.

And one honest line about the whole approach: an interface automator is a bet that
the pixels will keep meaning what they meant. Say how the bet can be lost.
