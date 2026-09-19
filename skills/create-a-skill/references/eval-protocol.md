# Measuring a skill

A skill that has never been run is a hypothesis. This is how to turn it into a
finding, in two independent measurements: does it **trigger** when it should, and
does it **work** when it does.

Both are cheap because DSH can spawn subagents. The whole method is: run the same
task twice — once with the skill, once without — and look at the difference.

## Part 1 — Does it trigger?

The description is the only thing an agent sees before deciding, so test the
description on its own, before spending time on the body.

### Write 20 queries

Save them as JSON, ten that should trigger and ten that should not:

```json
[
  { "query": "the user's words, verbatim", "should_trigger": true },
  { "query": "another one", "should_trigger": false }
]
```

Make them realistic. Not `Format this data` but:

> ok so my boss sent me this xlsx, it's in downloads, something like "Q4 sales
> final FINAL v2.xlsx" — she wants a column with the profit margin as a percent.
> revenue is column C, costs are column D i think

Lowercase, abbreviations, typos, backstory, a file path. That is what triggers
actually look like.

### The negative cases are the whole test

A negative that a keyword match obviously rejects tests nothing. `Write a
fibonacci function` against a spreadsheet skill is free to get right. The valuable
negatives are **near-misses**:

- the same words, a different need — "add a column to this CSV" for an `.xlsx` skill;
- adjacent domains — "make me a chart" when the skill builds spreadsheets;
- the skill's own topic in a context where another tool is correct.

If every negative is easy, the score means nothing.

### Run it

Give a fresh subagent the `name` + `description` of this skill **and of its
neighbours**, plus one query, and ask only which skill it would load. No body, no
context. Twenty queries is twenty cheap runs, and they can go out in one turn.

Record per query: expected, chosen, correct. The number that matters is not the
total but **which negatives were chosen** — each one is a description that is too
broad, and the fix is usually a word removed rather than a word added.

## Part 2 — Does it work?

### Run the pair in the same turn

For each task, spawn **two** subagents at once, not one after the other:

| Run | What it gets |
|---|---|
| **with skill** | the skill path, the task, and "read and follow this skill" |
| **baseline** | the same task, and nothing else |

Same turn matters: run them one after the other and the second quietly benefits
from the first. When improving an existing skill, the baseline is the **old
version**, snapshotted before you edit, so the comparison is against what the
skill used to be rather than against nothing.

### Keep the outputs

```
<skill-name>-workspace/
  iteration-1/
    eval-1-descriptive-name/
      with_skill/outputs/
      without_skill/outputs/
      eval_metadata.json
    eval-2-…/
  iteration-2/
```

```json
{
  "eval_id": 1,
  "eval_name": "adds-a-margin-column",
  "prompt": "the task, verbatim",
  "assertions": ["the output .xlsx opens", "column E is a formula, not a number"]
}
```

Create the directories as you go rather than all at once. Name each case after
what it tests; `eval-0` tells you nothing a month later.

### Judge it

Assertions first — the mechanical checks a script can make. Then read both outputs
side by side and answer one question: **what did the skill change?** If the answer
is "nothing", either the skill is redundant or the task was too easy to show it.

Numbers worth having, when the task allows them: turns taken, tokens spent, and
the count of failed attempts. A skill that succeeds in half the turns with the
same result is a better skill.

### Then iterate

Rewrite from what the run showed, not from what you expected it to show. Keep the
workspace: `iteration-2` next to `iteration-1` is the only proof that a change
helped rather than merely felt better.

## The trap this method exists to avoid

It is very easy to run a task once, get a good-looking result, and declare the
skill finished. That is a demonstration, not a measurement — and it is the same
failure as claiming a build passes because the file looks right.

State what you actually ran. "Tested on two tasks, both passed, the third was not
tried" is a stronger claim than "works", because it can be checked.
