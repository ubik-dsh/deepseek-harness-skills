# DeepSeek Harness Skills

Agent skills that work in **DeepSeek Harness**, **Claude Code**, and any other
harness that reads the [Agent Skills](https://agentskills.io/specification)
standard. Plain text, nothing to build, nothing to install.

*Русская версия: [README.ru.md](README.ru.md).*

---

## What is here

| Skill | What it does |
|---|---|
| **[create-a-skill](skills/create-a-skill)** | Teaches an agent to write a good skill — and to measure whether it works. Ships a **checklist runner** and a **measured evaluation protocol**, not advice alone. |

## What is different here

Most skill collections list what they contain. This is what is different about
this one, written so it can be **checked** rather than believed.

| | |
|---|---|
| **Measured, and honest about the gaps** | `create-a-skill` was assembled by collecting every skill about authoring skills published in a repository with **5000+ stars** — twelve of them, from `anthropics/skills` (177k), `ComposioHQ/awesome-claude-skills` (75k), `sickn33/agentic-awesome-skills` (46k) and others — reading them, and keeping what they agreed on. Where a practice was rare but right, it is kept and named. |
| **It ships a tool, not only text** | `scripts/check-skill.py` validates name against folder, description shape, size budgets, absolute paths, ageing phrases, stray human-facing files and unresolved references. Standard library only, so it runs anywhere Python does. |
| **It says what it cannot prove** | The checker reports a judgement call as a warning and only fails on a fact. Writing it produced **three false positives in the skill it ships with** — one matched `scripts/superscripts` inside `subscripts/superscripts` — and the fix is in the code with a comment saying why the guard is load-bearing. |
| **Portable by construction** | The body assumes no harness. Where a harness looks for `SKILL.md` is not part of the standard, so those facts live in a reference file covering DSH's seven roots and precedence ranks, plus the conventions of other tools. |
| **Evaluation, not demonstration** | Running a task once and getting a good-looking result proves nothing. The bundled protocol runs **with and without** the skill in the same turn, keeps both outputs, and compares — which is the only way to know what a skill actually changed. |

The one thing this repository does **not** claim: that any of it is a new idea.
The best parts were learned from other people's work, and the sources are named
in the skill's own metadata.

## Install

A skill is a folder. Copy it where your harness looks:

```bash
# DeepSeek Harness — for one project
cp -r skills/create-a-skill <your-project>/.agents/skills/

# DeepSeek Harness — for every project
cp -r skills/create-a-skill "$DSH_HOME/skills/"

# Claude Code
cp -r skills/create-a-skill <your-project>/.claude/skills/
```

No restart, no build step. DSH watches its skill roots and the skill is live the
moment the file is written. To confirm it loaded, ask the session for its skill
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
