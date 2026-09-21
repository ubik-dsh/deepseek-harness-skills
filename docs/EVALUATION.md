# Evaluation record

This file exists because a claim of quality without a record is a claim nobody
can check. Everything here was run; anything that was not is in the last section.

The skill was published on a Friday. On the Saturday it was measured, and the
measurement changed it. Both are recorded.

## What was run

| | |
|---|---|
| **Live loading** | Ten claims about how a harness registers a skill, each turned into a probe file in a live harness 0.1.5-rc.2 session and read back from the session's own skill catalogue |
| **Trigger evaluation** | Twenty realistic prompts, ten that should load the skill and ten near-misses that should not, judged by an agent shown only names and descriptions |
| **With and without** | One task, two agents, same turn — one told to follow the skill, one given nothing — and a third agent comparing the two outputs |

## Live loading: ten claims, all confirmed

Each row was a file written to a real skills root, then observed in the
catalogue the harness pushes to the session.

| Claim | Probe | Observed |
|---|---|---|
| A correct skill registers | `probe-plain` in `<project>/.agents/skills` | appeared |
| The lower rank wins | `rank-probe` in `.dsh/skills` (100) and `.agents/skills` (200), different descriptions | the rank-100 description appeared |
| The user-level root works | `probe-user-root` in `$DSH_HOME/skills` | appeared |
| The flat single-file form works | `probe-flat.md` beside the folders | appeared |
| A missing description is fatal | skill with `name` only | **absent** |
| An invalid name is fatal | skill named `probe-Bad-Name` | **absent** |
| The camelCase invocation key is fatal | `disableModelInvocation: true` | **absent** |
| Registration uses the frontmatter name | folder `probe-folder-name`, `name: probe-other-name` | catalogue lists `probe-other-name` |
| The folder name does not address it | `skill("probe-folder-name")` | **"unknown or no longer available"** |
| A load returns the base directory | `skill("probe-plain")` | returned `Base directory for this skill: …` |

Removing the probe files removed all five from the catalogue before the next
message, with no restart.

**The eighth and ninth rows are the reason this was worth running.** They show
that the harness addresses a skill by the name in the file and does not care what
the folder is called — and that it reports the *folder* as the resource base. A
mismatch therefore works completely on this harness and breaks only where it is enforced.
Before this was measured, this skill asserted the opposite: that the loader
matched on the folder and ignored the file. That was wrong, and the bundled
checker was failing valid skills on the strength of it.

## Trigger evaluation

Twenty prompts written by one agent, then judged by a **different** agent shown
only a catalogue of names and descriptions — never a body.

| | |
|---|---|
| Should load it | 10 |
| Did load it | **9** |
| Near-misses wrongly claimed | **0 of 10** |
| Near-misses correctly routed to a neighbouring skill | 5 |

The one miss is honest and useful: *"does the description on inbox-triage/SKILL.md
actually fire? run the trigger eval thing, 20 prompts"* went to `skill-creator`,
because that skill's description claims description optimization and this one did
not. **The description was changed as a result** — it now says it covers whether a
description fires and what a trigger eval is.

Zero false fires is the number that matters. A skill that claims work it should
not is worse than one that misses work it should take.

## With and without the skill

One task — *"make yourself a skill for checking whether a C# project's README
matches what the program actually does, so you can repeat it later"* — given to
two agents in the same turn. The first was told to follow this skill; the second
had nothing. A third agent read both results and judged them.

114 files were produced. Both agents found **the same defects** on the same
fixture. The skill changed the **shape** of the answer, not its recall:

- the with-skill agent shipped a **second gate** — a linter that rejects a report
  citing a line that does not exist, a verdict outside the fixed vocabulary, a
  `MATCH` witnessed only by the document under audit, or counts that disagree
  with the table;
- it used a six-state verdict vocabulary in which `UNVERIFIED` exists so that "I
  could not run this" is neither correct nor an accusation;
- it wrote its evaluation record **outside** the skill; the other wrote one
  inside.

The judge took the with-skill version, and said why in one line: its quality
claim is enforced by a program rather than by the agent's self-restraint, and
self-restraint is what degrades on run fifty.

The honest caveat, from the judge: the baseline agent was strong, and the report
it produced is arguably the more useful document for a human reader. The skill
won on repeatability, not on prose.

## What the measurement did to the skill

Every change below came from the run, not from reading.

1. **The name/folder claim was corrected.** It had asserted a loader behaviour
   the harness does not have. Measured, then rewritten, then the checker's
   failure message was rewritten with it.
2. **The description learned trigger words** it had been missing.
3. **The protocol now says twenty queries are twenty**, because the first live run
   wrote ten, scored ten out of ten, and recorded a perfect result that meant
   nothing.
4. **Six traps were written into the protocol** — unevaluated assertions, a
   verdict that flips, self-grading, a record kept inside the thing it describes,
   a gate passable by adding a line, and the skill's own rules applied to itself.
5. **The checker's invocation was disambiguated.** The document said
   `python <skill-dir>/scripts/check-skill.py <skill-dir>`, and a live agent read
   `<skill-dir>` as the skill it had just written and cited a path that did not
   exist. It now says the runner ships with this skill and does not go in the new
   folder.

## What was measured here, and what was not

**Measured:** registration and addressing in a live harness; removal; root
precedence; trigger accuracy against near-misses; one with-and-without pair on
one task, judged by a third agent.

**Not measured, and therefore still a claim:** how this behaves in another harness or
any harness other than this one — every cross-harness statement in this repository
rests on documentation, not on a probe. The protocol has been run once, on one
task, by one pair of agents. Everything the checker detects is tested against 46
fixtures written by its own author, which is a weak form of evidence: it proves
the rules work on the cases their author thought of.
