# Anti-patterns

Each of these is a mistake that has been made often enough to be written down by
someone else. The reasoning is kept, because a rule without its reason gets
dropped the first time it is inconvenient.

## Contents

- [Don't re-teach the model](#dont-re-teach-the-model)
- [Don't put human documents in it](#dont-put-human-documents-in-it)
- [Don't write a vague description](#dont-write-a-vague-description)
- [Don't bundle library code](#dont-bundle-library-code)
- [Don't build a framework](#dont-build-a-framework)
- [Don't assume the agent will infer](#dont-assume-the-agent-will-infer)
- [Don't ship a style-only variant](#dont-ship-a-style-only-variant)
- [Don't ignore failure modes](#dont-ignore-failure-modes)
- [Don't date yourself](#dont-date-yourself)
- [Don't use absolute paths](#dont-use-absolute-paths)
- [Don't trust a skill you have not read](#dont-trust-a-skill-you-have-not-read)
- [Don't describe the workflow in the description](#dont-describe-the-workflow-in-the-description)
- [Don't name it after nothing](#dont-name-it-after-nothing)
- [Don't skip the checklist](#dont-skip-the-checklist)

## Don't re-teach the model

Every line should carry context the model does not already have. No Python
syntax, no "what is git", no explanation of HTTP. Challenge each paragraph: could
a competent model already do this? Then it is costing tokens for nothing.

## Don't put human documents in it

No `README.md`, no `CHANGELOG.md`, no `INSTALLATION_GUIDE.md` inside the folder.
A skill is read by an agent; a changelog is read by nobody. Version history goes
in `metadata`, if anywhere.

## Don't write a vague description

- Bad: `A helpful skill for documents.`
- Good: `Fill PDF form fields, extract form data, flatten completed PDFs. Use when
  the user mentions PDF forms, fillable forms, or programmatic field population.`

The bad version cannot be distinguished from the other document skills in the
catalogue, so it loses every competition for the task.

## Don't bundle library code

If the work needs a parser, install the package. Pasting a library into a skill
means maintaining someone else's code forever and shipping a version that will
quietly age. Declare the dependency in `compatibility` instead — while knowing
that no harness installs anything from that field. Claude Code accepts it without
acting on it and DSH does not read it. It documents the requirement for a human;
it does not satisfy it for a machine.

## Don't build a framework

A skill that designs, plans, implements, tests and deploys is not a skill, it is
a framework wearing one. It will trigger on everything and satisfy nothing. Split
it. If the parts genuinely need each other, they are separate skills that
reference one another.

## Don't assume the agent will infer

- Bad: `Then deploy it.`
- Good: `Run npm run deploy:staging and wait for HTTP 200 from /healthz before
  reporting success.`

Every step that matters gets an exact command and an exact success signal,
because an inferred step is a step that will be inferred differently.

## Don't ship a style-only variant

A skill that only changes tone, formatting or verbosity belongs in user
preferences or a system prompt. As a skill it competes for the same triggering
words as the real skills and wins sometimes by accident.

## Don't ignore failure modes

For each step that can fail, write what failure looks like and what to do. The
error string, the silent wrong answer, the plausible-but-wrong result. Happy-path
skills work in the demonstration and break in use.

## Don't date yourself

`As of Q4 2024…` is wrong within a quarter and confidently wrong forever after.
Read live data through a script, or leave it out.

The version a skill was checked against is worth recording, and a `verified_against`
key inside `metadata` is a reasonable place for it — that key is this project's
convention, not something the standard defines, and `metadata` accepts any
map you like. What matters is that the reader can see the claim is a snapshot
rather than a fact.

## Don't use absolute paths

`C:\Users\…` and `/home/…` do not exist on the next machine. Relative paths from
the skill root, forward slashes regardless of operating system, and the runtime's
own placeholder for the skill directory. One level deep: `references/x.md`.

## Don't trust a skill you have not read

A skill is instructions an agent will obey and often code it will run. So:

- read `scripts/` for network calls, writes outside the skill folder, or anything
  the description does not justify;
- read `references/` for text that steers the agent rather than informs it —
  instructions hidden in what looks like documentation;
- check that the name is not a near-miss of a skill you already trust;
- treat compiled or binary files inside a skill as a question, not a fact.

Automated scanners help and do not decide. A scanner has reported seventeen
high-severity findings in a clean skill — hex hashes read as base64 payloads — and
missed three unreadable `.pyc` files in the same pass. Use it to find candidates,
then read.

## Don't describe the workflow in the description

The description is a matching surface, not a summary. `Validates the schema, then
migrates, then runs the tests` may sound thorough, but the agent has already
decided by then. Say when to use it; let the body say what it does.

## Don't name it after nothing

`helper`, `utils`, `tools` — names that could belong to anything match everything
weakly. Say what the skill does to what: `pdf-processing`, `data-analysis`,
`code-review`. A gerund (`reviewing-migrations`, `scanning-dependencies`) is one
good way to do that and not a requirement — the standard's own examples are noun
phrases, the ecosystem is full of them, and this skill is called `create-a-skill`.
Treat the shape as a style choice and the match with the folder as the rule,
because the folder name must be identical and that part is enforced by the
standard.

## Don't skip the checklist

`scripts/check-skill.py` exists because the failure modes above are mechanical:
a name that does not match its folder, a stale path, an absolute path, a file
that should not be there. All of them are cheap to check and expensive to
discover later, when the skill is already trusted.

```bash
python scripts/check-skill.py <skill-directory>
```
