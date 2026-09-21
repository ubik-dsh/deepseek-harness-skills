# Harness Skills

Agent skills that work in **this harness**, **other harnesses**, and any other
harness that reads the [Agent Skills](https://agentskills.io/specification)
standard. Plain text, nothing to build, nothing to install.

*Русская версия: [README.ru.md](README.ru.md).*

---

## What is here

| Skill | What it does |
|---|---|
| **[create-a-skill](skills/create-a-skill)** | Teaches an agent to write a good skill — and to measure whether it works. Ships a **checklist runner** and a **measured evaluation protocol**, not advice alone. |
| **[find-a-skill](skills/find-a-skill)** | Look for a skill that already does the job **before** writing a new one: search the seven roots this harness resolves, then GitHub, rank, read the candidates in full, and **trial** them on your own case. Ships a runnable scout and a trial checklist. Written after `learn-an-interface` was published before anyone checked — 105 repositories had already done it. |
| **[manage-windows](skills/manage-windows)** | Work on a Windows machine from an agent: PowerShell without the traps that fail silently, input that actually reaches the application, and a **preflight check that must pass before anything is pressed**. Covers the encoding rules that differ between PowerShell 5.1 and 7, JSON that truncates with no error, the input ladder for XAML and WinUI, DPI and the client-area offset, elevation, and where generated scripts belong. Assembled from twelve hearings with the sources named, plus what this repository learned by getting it wrong. |
| **[route-a-task](skills/route-a-task)** | **The entry point.** Decide which skill a task requires, and which are **obligations rather than options**: content from outside is scanned before it is used, a search happens before a skill is written, a machine is read before it is changed, an independent agent reads a skill before it is called done. A regulation, not a menu — a menu is read once and forgotten, an obligation is checked. Ships a router that prints the obligations in order, and exits `2` when nothing applies so "not covered" is distinguishable from "not understood". |
| **[check-hardware](skills/check-hardware)** | Read what a Windows machine's hardware actually reports, and **tell a healthy component from an unreadable one**. The rule that carries it: *a missing reading is not a good reading*. Covers why a disk reporting `Healthy` may not have been checked at all, the two memory classes that hide an empty slot, where WHEA and disk errors are logged, and the order that keeps a diagnosis read-only until there is evidence. Ships a collector that marks **every reading it could not take**. |
| **[judge-a-skill](skills/judge-a-skill)** | Put one skill on trial before adopting it: a **prosecutor** argues why it is not needed, a **defence** why it is, and a **judge** rules from a fixed set of verdicts — including the one that matters most, *reject the skill, take these parts*. Charges must cite something checkable, a clean verdict is first-class, and the two cases are **rated** so a close call reads as a close call. Ships a recorder that refuses a charge with no evidence. |
| **[learn-an-interface](skills/learn-an-interface)** | Drive a real window, and **learn** its coordinates instead of hard-coding them: a small bandit that finds the unknown detail, grades it by a verified outcome, and remembers it in a file. Opens with the gate that says when *not* to do this at all, and carries the measured traps — `mouse_event` reaching nothing, a cursor thrown onto the wrong monitor, a modal prompt blocking six attempts while the log said nothing happened. Ships a runnable learning loop. |
| **[design-a-reward](skills/design-a-reward)** | Design the number anything learns from — RL, a bandit, a hill climb, a grader. Eleven rules a reward must satisfy, how to find the limits and the step sizes, and an ordered checklist for a curve that will not rise. Ships a **probing harness** that scores degenerate and adversarial policies against your reward, so a reward that can be won without doing the task is caught before it trains anything. |
| **[draw-a-diagram](skills/draw-a-diagram)** | Produce a diagram as a FILE an agent writes directly - draw.io XML, its rules and its traps - instead of driving a diagram editor or describing the picture in prose. |
| **[manage-vk](skills/manage-vk)** | Work with VK (VKontakte) from an agent - read a community before writing to it, publish a post or photos to a wall, and tell a refusal from an empty answer. |

Start with `route-a-task`; the seven fit together: `find-a-skill` finds out whether it already exists, `judge-a-skill` decides whether it is worth keeping, `create-a-skill` writes it, `learn-an-interface` is what
it reaches for when the success test lives behind pixels, and `design-a-reward` is what
it reaches for when the test has to become a number. Each names the other two rather
than repeating them.

## What is different here

Most skill collections list what they contain. This is what is different about
this one, written so it can be **checked** rather than believed.

| | |
|---|---|
| **Measured on a live harness, not argued** | Ten claims about how a harness registers a skill were each turned into a probe file and read back from a live harness session's own catalogue. All ten confirmed. Two of them contradicted what this skill had been asserting, and it was rewritten. The run is published: [docs/EVALUATION.md](docs/EVALUATION.md). |
| **Built to be improved by whoever is better** | The skill carries a standing rule: when something else does the job better, take it — find it, read it, try it on your own case, keep it only if the trial agreed, and name where it came from. Six practices were taken from the vendor's own skill this way, after a head-to-head on three tasks; they are recorded with their sources and their tests in `references/borrowed-practices.md`. A rule that stays because it was ours is a rule that has stopped being useful. |
| **Measured, and honest about the gaps** | `create-a-skill` was assembled by collecting every skill about authoring skills published in a repository with **5000+ stars** — twelve of them, from `anthropics/skills` (177k), `ComposioHQ/awesome-claude-skills` (75k), `sickn33/agentic-awesome-skills` (46k) and others — reading them, and keeping what they agreed on. Where a practice was rare but right, it is kept and named. |
| **It ships a tool, not only text** | `scripts/check-skill.py` validates name against folder, description shape, size budgets, absolute paths, ageing phrases, stray human-facing files and unresolved references. Standard library only, so it runs anywhere Python does. |
| **It says what it cannot prove** | The checker reports a judgement call as a warning and only fails on a fact. Writing it produced **three false positives in the skill it ships with** — one matched `scripts/superscripts` inside `subscripts/superscripts` — and the fix is in the code with a comment saying why the guard is load-bearing. |
| **Portable by construction** | The body assumes no harness. Where a harness looks for `SKILL.md` is not part of the standard, so those facts live in a reference file covering this harness's seven roots and precedence ranks, plus the conventions of other tools. |
| **Evaluation, not demonstration** | Running a task once and getting a good-looking result proves nothing. The bundled protocol runs **with and without** the skill in the same turn, keeps both outputs, and compares — which is the only way to know what a skill actually changed. It has been run once, on one task, and what it changed is in [docs/EVALUATION.md](docs/EVALUATION.md), including the six traps it walked into. |

The one thing this repository does **not** claim: that any of it is a new idea.
The best parts were learned from other people's work, and the sources are named
in the skill's own metadata.

## Install

A skill is a folder. Copy it where your harness looks:

```bash
# this harness — for one project
cp -r skills/create-a-skill <your-project>/.agents/skills/

# this harness — for every project
cp -r skills/create-a-skill "$DSH_HOME/skills/"

# another harness
cp -r skills/create-a-skill <your-project>/.claude/skills/
```

No restart, no build step. This harness watches its skill roots and the skill is
live the moment the file is written. To confirm it loaded, ask the session for its skill
catalogue — the name and description appear there, and nothing else does.

Where each harness actually looks, and why observation beats documentation:
[skills/create-a-skill/references/harness-locations.md](skills/create-a-skill/references/harness-locations.md).

## Use a skill without installing it

A skill does not have to be indexed to be useful. Give an agent the path to a
`SKILL.md` and it can read and follow it. That is the fallback when a harness
offers no user-level skills root at all.

## Check a skill

```bash
python skills/create-a-skill/scripts/check-skill.py skills/create-a-skill
```

```bash
# every skill in this repository at once
python skills/create-a-skill/scripts/check-skill.py skills --recursive
```

Exit code 0 when nothing failed, 1 when something did. Warnings never fail a run.

## Skills you did not write

A skill is instructions an agent obeys and, often, code it runs. Before using
someone else's, read `scripts/` for network calls and writes outside the folder,
read `references/` for text that steers rather than informs, and check the name
is not a near-miss of one you trust. An automated scanner helps and does not
decide — treat it as a source of candidates.

## Contributing

Useful contributions, in the order that helps most:

1. **A skill that was measured** and comes with what it changed, including the
   runs where it did not help.
2. **A correction** with evidence — a link, a command, or an output. Every claim
   here is meant to be checkable, and a wrong one is a bug.
3. **A harness location** you verified, for
   [harness-locations.md](skills/create-a-skill/references/harness-locations.md).

Please keep skills to plain text. A skill that needs a build step or a binary is
a skill most people cannot use.

## Licence

MIT — see [LICENSE](LICENSE).
