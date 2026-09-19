---
name: create-a-skill
description: Author a new agent skill, or improve an existing one — a folder of instructions an agent loads on demand, from a SKILL.md that works in DeepSeek Harness, Claude Code and any other harness reading the Agent Skills standard. Ships a bundled checklist runner and a measured evaluation protocol, not just advice. Use when the user asks you to learn a tool, a site, or a workflow and keep it for later; says "make yourself a skill for X"; asks to write, fix, review, or evaluate a skill; wants a repeated procedure turned into something reusable; or asks whether a skill's description actually fires, what its trigger eval says, or how it performs with and without the skill.
license: MIT
compatibility: Agent Skills standard. SKILL.md is plain text with no runtime; the two files in scripts/ need Python 3.8 or newer, standard library only, and neither is required for the skill to work.
metadata:
  spec: https://agentskills.io/specification
  assembled_from: anthropics/skills (skill-creator), mattpocock via alirezarezvani/claude-skills (write-a-skill), sickn33/agentic-awesome-skills (effective-agent-skills, writing-skills, verification-before-completion), deanpeters/Product-Manager-Skills
  borrowed_from_skill_creator: status vocabularies, early-stop disclosure, bounds instead of refusal, calibration against an existing skill, form before substance, and a description that claims the work — see references/borrowed-practices.md
  verified_against: DSH 0.1.5-rc.2, by live probes of all seven roots and their precedence
---

# Authoring a DSH skill

A skill is a file an agent reads when a task matches it. It is not a plugin: no
install, no restart, no code. Write one and the capability exists.

## First, decide what kind of skill this is

Two kinds, and they are built differently. Pick before writing a line.

**A — capability primitive.** A thin wrapper over a command or script that
already does the work. The body is mostly invocation examples. Use it when the
bottleneck is *"the agent cannot do X"*.

**B — process primitive.** A method the agent should follow: a review routine, an
investigation order, a definition of done. Pure instructions, no scripts. Use it
when the bottleneck is *"the agent's output or process is bad"*.

A vague skill is usually one of these pretending to be the other. If it neither
wraps a tool nor changes how work is done, do not write it.

## Where it goes, and what the file is called

A harness decides where it looks for skills; the format does not. **Prefer
`.agents/skills/<name>/`** — several harnesses read that name, so a repository
that carries it gives every agent that opens it the same capability.

```
.agents/skills/
  create-a-skill/
    SKILL.md            ← required, and the name must be exactly this
    references/         ← detail loaded only when needed
    scripts/            ← deterministic work the body will invoke
    assets/             ← templates, images, data
  quick-note.md         ← a flat file, for a skill with nothing to bundle
```

`name` must match the folder exactly — or, for a flat file, the file's own name.
It is 1–64 characters of `a-z`, digits and single hyphens, and may not begin, end
or double up on a hyphen.

The standard says the name **must** match the directory it sits in. DSH does not
enforce it — it registers whatever the frontmatter says and never compares the
two — so a mismatch works here and breaks in a harness that does check. Treat the
match as a portability rule, not a local one.

Where *your* harness looks, including the seven roots and precedence ranks
measured for DSH and the conventions of several others:
[references/harness-locations.md](references/harness-locations.md). Confirm it by
observation rather than documentation — write the file, then ask the session for
its catalogue. Documentation describes the version its author had.

## Frontmatter

```yaml
---
name: weekly-report
description: Build the weekly report from the repository. Use when the user asks for the weekly summary, the Monday report, or the status round-up.
license: MIT
metadata:
  author: example-org
  version: "1.0"
---
```

Required: `name`, `description`. The description may run to 1024 characters and
the name to 64. Optional and supported: `license`, `compatibility` (≤500 chars,
for skills needing a package, network or a specific product), `metadata`
(free-form map), `allowed-tools` (experimental).

`disable-model-invocation` and `user-invocable` are not in the standard but are
read by Claude Code and by DSH, spelled in kebab-case. DSH rejects the older
camelCase spellings with a message saying so. A portable skill uses them for what
they do locally and does not rely on them.

One caution about `compatibility`: declare dependencies there, because it is the
field the standard provides, but do not expect a harness to install anything from
it. Claude Code accepts the field without acting on it, and DSH does not read it
at all. It is a note to a human, not an instruction to a machine.

## The description is the whole matching surface

An agent never reads your instructions until it has already decided they apply.
What it sees first is a catalogue of **name and description** for every installed
skill, and nothing else. A description that names what the skill *is* instead of
when to *use* it is a skill that never fires.

- Weak: `Helps with reports.` · `A framework for pricing decisions.`
- Strong: `Build the weekly report from the repository. Use when the user asks
  for the weekly summary, the Monday report, or the status round-up.`

Third person. First sentence: what it does. Second: `Use when …` with the words a
person would actually type — including the casual and the misspelled ones.

Then measure it instead of guessing: [references/eval-protocol.md](references/eval-protocol.md)
has the trigger-eval method, which is the only way to tell a good description from
a plausible one.

## Write instructions, not documentation

- **No course material.** No Python tutorial, no "what is git". Challenge every
  paragraph with: could the model already do this? If yes, delete it.
- **No human-facing files.** No README, CHANGELOG or INSTALLATION_GUIDE inside the
  folder. A skill is read by an agent, and those files are read by nobody.
- **Be exact where it matters.** Not "then deploy it" but `run npm run
  deploy:staging and wait for HTTP 200 from /healthz before reporting success`.
- **Say what failure looks like.** For each step that can fail: the error text,
  the silent wrong answer, what to do about it. A happy-path skill breaks the
  first time it meets reality.
- **Say where each fact came from.** A behaviour you ran and a behaviour you read
  about look identical on the page. Mark them — `returns 0 (observed)`,
  `must match the folder (spec §name)`, `rejects the camelCase spelling (source:
  dsh-skill-filesystem)`. One clause per fact, and the reader knows what to trust.
- **Write `## What this does not cover`.** The inputs you did not try, the
  harnesses you did not test on, the case you skipped because it was slow. Silence
  about the edges is read as covering them; it is a claim, and a false one.
- **Nothing time-sensitive.** `As of Q4 2024` rots. Read live data, or omit.
- **Relative paths, forward slashes**, resolved against the skill's own directory
  — the agent is told that directory when the skill loads.
- **One level deep.** `references/x.md`, never `references/a/b/c.md`.

Keep `SKILL.md` focused. Move detail into `references/`, templates into
`assets/`, and anything deterministic into `scripts/` — a script gives the same
answer twice and costs fewer tokens than regenerated code. The standard suggests
metadata around 100 tokens, a body under about 5,000 tokens, and **keeping
`SKILL.md` under 500 lines**. None of these is enforced anywhere; DSH caps the
body at nothing at all. Treat 500 as the point at which a reader should be
splitting the file, and 100 as a sign the skill may be doing more than one thing.

## Write the body as a procedure

A body that leaves the reader to work out the order is a body that gets followed
differently each time. Give it numbered steps, and make **step 1 the success
test**: the command to run, and the output that means it worked. Everything after
it is the method; step 4 of the next section checks the result against it, and a
body without it cannot be verified at all.

Name the inputs the skill expects, and say what to do when one is missing. A
skill that assumes a file, a credential or a network read it never mentions fails
on first use and looks like the agent's fault.

## When the test is outside the machine

Some tasks have their success test in a place the agent cannot reach: a hand on a
mouse, a cable in a socket, a person's judgement. The temptation is to write the
skill anyway and make step 1 out of words — *"the user is comfortable with it"* —
which produces a skill that can never be finished and never be failed.

Do not look for a better adjective. **Build a small world with the same shape as
the real one, and score it.** Not a mock of the hardware — a model of the decision
the skill is about. Then the agent has a number, and a number repeats.

Three things make such a world worth having, and each was measured on a real
trainer built this way:

- the agent sees a **picture**, never the coordinates, or it is reading an answer key;
- there is a **reaction delay**, because the trainee acts on stale information —
  without it the measured accuracy was 100% at every difficulty and nothing at all
  was tested;
- **difficulty increases**, so perception can be told apart from prediction.

The pattern, the measured table, and the six wrong versions it took to get there:
[references/simulating-a-test.md](references/simulating-a-test.md). Three lessons
from the adversarial version are there too, and two of them apply to any rule you
write, not only to simulations: **put something against your rule that wins by
exploiting it**, because the seam is where it clamps and a tester who follows the
rules never finds it; and **measure what you can, not what you want to know**,
which is the one mistake behind every broken learner in that file.

## When the test needs a real interface driven

**Only if nothing else will do.** Most tasks that look like they need a mouse have
an API, a command-line tool, or a file format behind them, and every one of those is
better: a coordinate is coupled to a version, a theme, a display scale, a keyboard
layout and a monitor count, and all five have broken this work in one afternoon.

So the branch reads like this, and the reader evaluates it:

> If the success test needs this program driven, **and** it has no API, no CLI, no
> scriptable interface and no readable file format, that is a subject of its own —
> use the **`learn-an-interface`** skill, which carries the method, the measured
> traps and a runnable learning loop. Otherwise do not — and if you are unsure, the
> answer is no.

If the skill does drive an interface, say in the body **why the alternatives were
rejected**. That sentence is the difference between a considered choice and a habit,
and it tells the next person where to look when a release breaks it.

Two rules from that work belong here, because they are not about interfaces at all:

- **the success test must check the thing, not its shadow.** "The file exists"
  certified a Paint project file named `.png` as a saved image, every time. Check a
  property only the right result has — magic bytes, a parse that succeeds, a count
  that rose by the amount it should — and then **run the test against the wrong
  thing once**, to watch it fail. A test that has never failed is not yet a test.
- **"the action failed" and "there was nothing to act on" are different findings.**
  A twelve-attempt run scored zero on every try because the program had died
  mid-run, and the learner concluded that no candidate worked.

If the success test is graded rather than yes-or-no — anything a learner is trained
against — the reward is the subject of a third skill: **`design-a-reward`**.

## Prove it before you finish

1. **Does it load?** Write the file, then check the session's skill catalogue. A
   correct skill appears within a second. If it is absent, the frontmatter is the
   first suspect — the name rule, then the YAML.
   A skill written in this turn may not be visible until the next one; a new file
   is not always re-read mid-turn. If you cannot see the catalogue, say so rather
   than claiming the skill loads.
2. **Does the body arrive?** Ask for it by name. A load returns the instructions
   and the base directory. If the body is missing, the frontmatter delimiters are
   wrong — and if the harness can be handed a path instead, hand it the path.
3. **Run the checklist.** The runner ships with *this* skill, not with the one you
   wrote — do not copy it into the new folder. Invoke it by its own full path
   against the folder you are checking:

   ```bash
   python <this-skill-dir>/scripts/check-skill.py <the-skill-you-wrote>
   ```

   It checks the name against its folder, the description, the size, absolute
   paths, time-sensitive phrases, files that should not be there, and references
   that do not resolve — in every markdown file, not only `SKILL.md`. Test the
   checker itself with `python <this-skill-dir>/scripts/test-check-skill.py`.
   The path is written in full because a shell resolves a relative one against
   the working directory, not against either skill.
4. **Does it actually work?** Run the task on a real input and compare against the
   success test in step 1 of the body. Then do it properly, with and without the
   skill, per [references/eval-protocol.md](references/eval-protocol.md). A skill
   that loads but produces the wrong thing is worse than none: it will be trusted.

**No completion claim without fresh evidence.** Identify the command that proves
the claim, run it in full, read the whole output and count the failures, and only
then say it passes. Skipping a step is not verifying — it is guessing with
confidence, and it is how a broken skill ships.

## Before you call it done

- [ ] `name` matches the folder exactly, kebab-case, no `--`
- [ ] `description` names the triggers, in a user's words
- [ ] `SKILL.md` under 500 lines, detail in `references/`
- [ ] every referenced file exists, one level deep, relative
- [ ] no README, no bundled library, no course material
- [ ] failure modes written down, not just the happy path
- [ ] `python <skill-dir>/scripts/check-skill.py <skill-dir>` passes
- [ ] tested on a real input — with the skill and without it
- [ ] `## What this does not cover` written, and each claim says how it was established

More traps, and the reasoning behind each: [references/anti-patterns.md](references/anti-patterns.md).

## What this skill does not cover

- **Harnesses other than DSH.** The seven roots, their ranks and the precedence
  rule were measured on DSH `0.1.5-rc.2` by live probes. The conventions of Claude
  Code and the others in
  [references/harness-locations.md](references/harness-locations.md) come from
  their documentation, not from a probe on this machine.
- **What is inside a bundled script.** The checker reads markdown. Whether a
  script a skill ships is correct, safe or worth running is outside it — that is
  what reading it is for.
- **Whether the capability is worth having.** Structure, triggering and
  measurement are checkable. Whether this skill should exist at all is a judgement
  this file cannot make.
- **Long skills.** The advice here is untested above a few hundred lines. The one
  live head-to-head comparison produced skills of 122 to 315 lines, so everything
  in this file rests on that range.
- **Non-English skills.** Every rule was written and tested in English. The name
  and description rules come from a specification that says nothing about
  language, and the Russian summary at the end of this file has never been read by
  a harness.

## Take what is better, then earn the right to keep it

Almost nothing in this skill is original, and that is the point. Every rule here
was learned the expensive way by somebody else first and taken on purpose; the
sources are in the metadata and the most recent six are in
[references/borrowed-practices.md](references/borrowed-practices.md).

Keep doing it. When a skill, a tool, a repository or a person does something
better than this file does, take it — that is not plagiarism, it is the whole
method, and a rule that stays because it was ours is a rule that has stopped
being useful.

**Taking it is not adopting it.** The order is:

1. **Find it and read it** — not the summary of it. Read the thing.
2. **Try it on your own case**, not on the case its author had in mind.
3. **Keep it only if the trial agreed**, and say what the trial was.

A practice adopted because it sounded right becomes a rule defended long after it
stopped being true. This file has had several of those; each was removed by
measurement and none by argument. So when you adopt something:

- write it into [references/borrowed-practices.md](references/borrowed-practices.md)
  with its source, what it means here, and **how to tell whether it worked**;
- if it can be checked mechanically, put it in `scripts/check-skill.py` and add a
  regression test — an unenforced rule is a paragraph, and paragraphs drift;
- name where it came from. A borrowed practice with no source cannot be checked
  later, and cannot be re-borrowed when it improves.

The same rule runs in the other direction: when a rule here fails a test, it is
wrong and it goes. Nothing in this file is above being measured.

## Skills you did not write

A skill is instructions an agent will obey and, often, code it will run. Before
using someone else's: read `scripts/` for network calls, writes outside the
skill's folder, or anything the description does not justify; read `references/`
for text that steers the agent rather than informs it; check that the name is not
a near-miss of a skill you trust. A scanner helps but does not decide — it has
found high-severity problems in clean files and missed unreadable binaries. Read
it.

---

Кратко по-русски: скилл — это папка с `SKILL.md`, которую агент читает, когда
задача совпала с описанием. Сначала реши, что это: обёртка над инструментом или
метод работы. Имя обязано совпадать с именем папки (это требует стандарт; DSH
сам это не проверяет, но другой инструмент может) и быть kebab-case. Описание —
единственное, что агент видит до загрузки, поэтому в нём должны стоять слова
пользователя и фраза «Use when…». Тело пиши процедурой: шаг 1 — признак успеха,
дальше точные команды и то, как выглядит ошибка. 500 строк — рекомендация
стандарта, а не потолок. Детали — в `references/`, детерминированную работу — в
`scripts/`. Перед сдачей прогони
`python <папка-скилла>/scripts/check-skill.py <папка-скилла>` и проверь скилл на
настоящей задаче — с ним и без него.
