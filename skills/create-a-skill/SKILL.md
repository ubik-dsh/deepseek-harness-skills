---
name: create-a-skill
description: Author a new agent skill, or improve an existing one - a folder of instructions an agent loads on demand, from a SKILL.md that works in this harness, in other harnesses, and in any harness reading the Agent Skills standard. Ships a bundled checklist runner and a measured evaluation protocol, not just advice. Use when the user asks you to learn a tool, a site, or a workflow and keep it for later; says "make yourself a skill for X"; asks to write, fix, review, or evaluate a skill; wants a repeated procedure turned into something reusable; or asks whether a skill's description actually fires, what its trigger eval says, or how it performs with and without the skill.
license: MIT
compatibility: Agent Skills standard. SKILL.md is plain text with no runtime; the two files in scripts/ need Python 3.8 or newer, standard library only, and neither is required for the skill to work.
metadata:
  assembled_from: a vendor's official collection (skill-creator), mattpocock and a community collection (write-a-skill), sickn33/agentic-awesome-skills (effective-agent-skills, writing-skills, verification-before-completion), deanpeters/Product-Manager-Skills
  borrowed_from_skill_creator: status vocabularies, early-stop disclosure, bounds instead of refusal, calibration against an existing skill, form before substance, and a description that claims the work — see references/borrowed-practices.md
  verified_against: this harness 0.1.5-rc.2, by live probes of all seven roots and their precedence
---

# Authoring a harness skill

A skill is a file an agent reads when a task matches it. It is not a plugin: no
install, no restart, no code. Write one and the capability exists.

## First, find out whether it already exists

Before deciding anything else, **search**. The cheapest skill to maintain is the one
somebody else already wrote and tested, and the skill you write without looking will be
missing whatever the one you did not read had already learned.

This is not advice, it is the procedure: **`find-a-skill`**, a sibling skill, searches
the seven roots this harness resolves, then GitHub, ranks what comes back, and requires
the candidates to be **trialled on your own case** before any of them is kept.

```bash
python <find-a-skill>/scripts/scout.py <keywords> --synonyms <words,you,did,not,think,of>
```

Two things it will tell you that reading a description cannot: whether an existing skill
does the thing or something **adjacent** to it, and **where a borrowed practice stops
working**. Both come from the trial, and the trial is the half of it that this skill
used to leave out.

If the user says to skip the search, skip it and **say that you skipped it**. What must
not happen is the search being skipped silently, because then nobody knows whether the
duplication was a choice.

> This section exists because it was learned the hard way. `learn-an-interface` was
> written and published before anyone checked whether others had done it. **105
> repositories had**, and one of them contained the rung our gate was missing.

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

The standard says the name **must** match the directory it sits in. This harness
does not enforce it — it registers whatever the frontmatter says and never
compares the two — so a mismatch works here and breaks in a harness that does
check. Treat the match as a portability rule, not a local one.

Where *your* harness looks, including the seven roots and precedence ranks
measured for this harness and the conventions of several others:
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
read by other harnesses and by this harness, spelled in kebab-case. This harness
rejects the older camelCase spellings with a message saying so. A portable skill
uses them for what they do locally and does not rely on them.

One caution about `compatibility`: declare dependencies there, because it is the
field the standard provides, but do not expect a harness to install anything from
it. Other harnesses accept the field without acting on it, and this harness does
not read it at all. It is a note to a human, not an instruction to a machine.

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

## The family as a graph, and what a sign is worth

**`scripts/graph-skills.py <repo>` writes `_graph/`** — an index, a page per skill, a machine form. Open
the repository as an Obsidian vault and the graph pane works, because nothing is copied: the pages link
at the real files.

**Every edge carries how it was established, and no mark is hand-written — each is computed from the
shape of the text**, so a reader can tell a surveyed road from a guess without trusting memory. **The
five marks, and the four wrong versions of the tool that produced them, are in
[references/the-family-graph.md](references/the-family-graph.md).**



**A skill is not documentation. It is a program whose interpreter is a model**, and the only question
that decides its form is whether the agent loading it does the job better. **The human is an observer in
this frame** — they author it, approve it, and read it afterwards — **but they are not who it is for**,
and a sentence written to please a person is a sentence the agent pays for and cannot act on.

Four consequences. This family already followed all four; none was written down until an operator said
it plainly: *the agent is what matters, the person is in the frame as an observer, and if English is
optimal then English is the working version.*

- **English by default, and it is a measured choice.** On one meaning, on a modern tokenizer, English is
  30 tokens against Russian's 35, French's 35, German's 40, Japanese's 45 — and against **147 for Russian
  on an older one**. It is also what the body's own identifiers already are: `wall.post`, `post_id`,
  `SKILL.md`, `references/` are Latin in every language, so a body in another script pays for the
  mixture twice (measured: 23% more on a sentence carrying identifiers).
- **A translation is a REFERENCE, never a second skill.** A Russian copy shipped as its own skill is
  paid for in the **always-on** catalogue — all nine descriptions here cost 1,536 tokens on every
  request — and it **competes for the same trigger**, which is the routing failure `route-a-task` exists
  to prevent. Put it in `references/`. There it costs nothing until somebody opens it and cannot steal a
  match.
- **Never let the two drift.** A stale translation is worse than none, because it reads as the skill.
  `scripts/check-translations.py` refuses one that no longer matches the source it names.
- **Write so a model can act on it.** Imperative, one rule per sentence, the condition before the
  action, nothing that only decorates. **"It would be nice to consider" is a token the agent pays for
  and cannot act on.**

**The test is not "is this clear to a person".** It is *"can an agent that has never seen this do the
right thing without asking"* — and an operator reading it afterwards is a benefit, not the target.

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
answer twice and costs fewer tokens than regenerated code.

**The budget is in TOKENS, not in lines or characters, and the two figures this
rule used to carry disagreed.** The standard suggests metadata around 100 tokens
and a body under about 5,000 tokens, and it also suggested staying under 500
lines. **Measured on this family's own nine skills, the density is 12.3 tokens per
line** (10.8 to 13.5 across them), so 500 lines is **6,143 tokens** — the line
limit was 1.23× more permissive than the token limit, and **three skills passed the
line check while sitting over the token one**:

```
route-a-task        6,706 tokens  495 lines   passes the lines, fails the tokens
learn-an-interface  5,971 tokens  453 lines   same
create-a-skill      5,424 tokens  431 lines   same, and this is the rule's own file
```

**So the token figure is the one to keep and the line figure is a convenience.** If
a token count is not to hand, English prose in this house style runs about
**4.4 characters per token**, so characters ÷ 4 is a safe over-estimate; a heading
every ~300 tokens and no paragraph over ~200 keep a file navigable rather than
merely small. **A wall of 500 tokens is harder to read than two files of 250**, and
the same total hides it.

None of this is enforced anywhere upstream; this harness caps the body at nothing
at all. The bundled checker now estimates tokens from characters and warns, which
is the part that was missing when this rule was written.

## Write the body as a procedure

A body that leaves the reader to work out the order is a body that gets followed
differently each time. Give it numbered steps, and make **step 1 the success
test**: the command to run, and the output that means it worked. Everything after
it is the method; step 4 of the next section checks the result against it, and a
body without it cannot be verified at all.

Name the inputs the skill expects, and say what to do when one is missing. A
skill that assumes a file, a credential or a network read it never mentions fails
on first use and looks like the agent's fault.


**When a skill's test is outside this machine, and what an independent run has found here, are in [references/testing-a-skill.md](references/testing-a-skill.md).**

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

- **An independent agent has read it, or the file says it has not.** A skill nobody else
  has tried is a draft, and the entry that says so is not a failure.

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

- **Harnesses other than this one.** The seven roots, their ranks and the
  precedence rule were measured on this harness `0.1.5-rc.2` by live probes. The
  conventions of the other harnesses in
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
метод работы. Имя обязано совпадать с именем папки (это требует стандарт; этот
харнесс сам это не проверяет, но другой инструмент может) и быть kebab-case. Описание —
единственное, что агент видит до загрузки, поэтому в нём должны стоять слова
пользователя и фраза «Use when…». Тело пиши процедурой: шаг 1 — признак успеха,
дальше точные команды и то, как выглядит ошибка. 500 строк — рекомендация
стандарта, а не потолок. Детали — в `references/`, детерминированную работу — в
`scripts/`. Перед сдачей прогони
`python <папка-скилла>/scripts/check-skill.py <папка-скилла>` и проверь скилл на
настоящей задаче — с ним и без него.
