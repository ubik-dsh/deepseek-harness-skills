---
name: create-a-skill
description: Author a new agent skill, or improve an existing one — a folder of instructions an agent loads on demand, from a SKILL.md that works in DeepSeek Harness, Claude Code and any other harness reading the Agent Skills standard. Ships a bundled checklist runner and a measured evaluation protocol, not just advice. Use when the user asks you to learn a tool, a site, or a workflow and keep it for later; says "make yourself a skill for X"; asks to write, fix, review, or evaluate a skill; or wants a repeated procedure turned into something reusable.
license: MIT
compatibility: Agent Skills standard. SKILL.md is plain text with no runtime; only scripts/check-skill.py needs Python 3.8 or newer, standard library.
metadata:
  spec: https://agentskills.io/specification
  assembled_from: anthropics/skills (skill-creator), mattpocock via alirezarezvani/claude-skills (write-a-skill), sickn33/agentic-awesome-skills (effective-agent-skills, writing-skills, verification-before-completion), deanpeters/Product-Manager-Skills
  verified_against: DSH 0.1.5-rc.2
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
3. **Run the checklist.** `python <skill-dir>/scripts/check-skill.py <skill-dir>`
   — the path is written in full because a shell resolves a relative one against
   the working directory, not against the skill. It checks the name against its
   folder, the description, the size, absolute paths, time-sensitive phrases,
   files that should not be there, and references that do not resolve. Test the
   checker itself with `python <skill-dir>/scripts/test-check-skill.py`.
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
- [ ] `python scripts/check-skill.py <skill-dir>` passes
- [ ] tested on a real input — with the skill and without it

More traps, and the reasoning behind each: [references/anti-patterns.md](references/anti-patterns.md).

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
метод работы. Имя обязано совпадать с именем папки и быть kebab-case, иначе
скилл молча игнорируется. Описание — единственное, что агент видит до загрузки,
поэтому в нём должны стоять слова пользователя и фраза «Use when…». Тело пиши
как процедуру: точные команды, признак успеха и то, как выглядит ошибка. Держи
`SKILL.md` до 500 строк, детали — в `references/`, детерминированную работу — в
`scripts/`. Перед сдачей прогони `scripts/check-skill.py` и проверь скилл на
настоящей задаче — с ним и без него.
