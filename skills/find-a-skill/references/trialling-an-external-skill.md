# Trialling an external skill

Reading a skill tells you what it claims. Running it on your own case tells you what it
does. The distance between those two is where borrowed practice goes wrong, and it is
almost never zero.

This is the checklist. It has two halves: what to read for, and what to run.

---

## Part 1 — Read it in full, not its description

A description is a **claim the author makes about the skill they wrote**, written to be
matched rather than to be accurate about the limits. Read the body, and read what the
skill ships.

**Does it do the thing, or something adjacent?** Most matches are adjacent. A skill
described as automating interfaces turned out to be a **catalogue** of one program's
controls with no way to operate them — found by reading the body, invisible in the
description.

**What does it assume?** A platform, an installed tool, a permission, a network, a
language runtime, a harness. An assumption you do not share is the most common reason a
good skill is useless here.

**What does it explicitly not cover?** The honest ones say. That section is the most
useful part of somebody else's skill, because it tells you where the trial will fail
before you spend the time.

**Is it maintained?** Last commit, whether issues are answered. A skill coupled to a
program's version is a liability the moment it stops being updated.

### What it ships, and what that can do

A skill is not only prose. Anything in `scripts/`, `assets/`, or referenced by the body
can act on your machine. Before running anything:

- **shell commands** — what do they run, and with what arguments;
- **file writes** — where, and outside the skill's own folder or not;
- **network calls** — to where, sending what;
- **credential handling** — reading environment variables, config files, keychains;
- **package installs** — which package manager, and whether it is pinned;
- **anything the description does not justify.** The description and the body must agree
  about what the thing does. When they disagree, believe the body and stop.

And **never edit an installed original in place.** Copy it to a branch or a scratch
folder, review the diff, and keep the original intact — otherwise the next update
silently reverts your work and nobody can tell which version behaved how.

---

## Part 2 — Design the trial before running it

A trial that is not designed first becomes an impression. Two questions, written down
before anything runs:

> **If this skill is good, what will I see?**
> **If it is wrong for my case, what will I see instead?**

If those two answers are the same, the trial proves nothing and should not be run.

### Then run it on your own case, and get a number

Not on the skill's example. On the thing you actually need. And the result should be a
**number or an artifact**, not a feeling — because the decision that follows has to
survive the next person reading it.

Measured examples from one survey of rival interface skills:

| what was borrowed | what the trial showed | kept? |
|---|---|---|
| UI Automation with `AutomationId` selectors | `Pencil` found by `PencilTool` and toggled `Off → On` with no cursor; palette exposed as named colours | **kept**, with the boundary below |
| "bring the target window forward and set focus explicitly" | our own `click()` never checked this, and a click **landed in a stranger's browser window** | **kept** — it found a defect in our code |
| `cv2.matchTemplate` as the control fallback | 1.000 in place; after moving the window 260 px, **0.889 against a 0.85 threshold, on the wrong button** | **rejected** for that role |
| patterns over visual input (`SetValue` over typing) | a toggle changed state with no cursor and no keyboard | **kept** |
| a notes-file "learning" loop | six exploratory attempts by hand, then stale on the next run | **kept as a habit, rejected as the mechanism** |
| sandbox tiers, job objects, OS-level isolation | correct for an unattended agent on a foreign machine | **set aside** — a different problem |

### Write the boundary into the skill you keep

A kept practice without its boundary gets applied where it fails. The UI Automation
trial did not merely say "use the tree" — it established **where the tree stops**:

```
the tree reaches      tools, menus, colours, list rows, readable values
the tree does not     a custom-drawn canvas  (only ScrollViewer panes are exposed)
```

That boundary is the most valuable sentence the trial produced, and it is the sentence a
description would never have contained.

---

## Part 3 — Four outcomes, and only one of them is "no"

1. **kept** — the trial agreed; take it, name the source, record the evidence.
2. **kept with a boundary** — it works, and only in these conditions; write the
   conditions down next to it.
3. **rejected with a number** — it failed the trial; record the measurement. **A
   rejection by opinion does not stay rejected; a rejection with a number does.**
4. **set aside as a different problem** — it is right for a case that is not yours.
   Record it anyway, and say which case it is for, because the moment your case changes
   it becomes the starting point.

The one thing not on the list is silently dropping it. The next person repeats the work
and reaches the same fork with no idea it has been visited.

---

## Part 4 — The record

For each candidate, in whatever file the skill family uses for this:

```
what it was       <name and repository>
where it came from <link, and how it was found>
what was taken    <the specific practice, not the skill>
the trial         <what was run, on what, and the number>
kept or rejected  <and, for a rejection, the number that decided it>
```

**Name the source.** Borrowed practice is worth more when the reader can go and read the
original — and a rule that survives only because it was ours has stopped being useful.

---

## The short version

- read the **body**, not the description;
- know what it **assumes** and what it **does not cover**;
- know what its **scripts can do** before running them;
- **design the trial first**, and make sure the good outcome and the bad outcome would
  look different;
- run it **on your own case**, and get a **number**;
- write down the **boundary**, the **number**, and **where it came from**.
