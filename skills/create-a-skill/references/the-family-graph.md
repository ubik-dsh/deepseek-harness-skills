# The family graph: four marks, and four versions of the tool that were wrong

`scripts/graph-skills.py` builds a graph of this whole repository — nodes, edges, and **a mark on every
edge saying how it was established**. None of the marks is hand-written; each is computed from the shape
of the text. The point of that is simple: **a reader can tell a surveyed road from a guess without
trusting anybody's memory.**

| mark | on a map | in the files |
|---|---|---|
| `EXTRACTED` | the road is signposted | a written link whose target resolves |
| `INFERRED` | the place is named, no road drawn | the name appears in the text with no link |
| `AMBIGUOUS` | one sign, two places | a bare name matching more than one file |
| `DANGLING` | a sign pointing at nothing | a link whose target is not there |
| `ORPHAN` | a road with no sign to it | neither linked nor named anywhere |

**Named-but-not-linked and named-nowhere are different problems.** The first is reachable by somebody
who reads the page that names it; the second is invisible. Reporting them together hides the one that
matters.

## Four versions, each reporting confident nonsense

**A tool that prints numbers deserves the same suspicion as a reply that reports success.** This one
printed four sets of them and three were largely wrong, and **every fix was forced by checking a number
against a different tool** — which is the argument for keeping two that overlap.

```
version 1   scanned EVERY file for markdown links, so the eight "dangling" links were fixtures inside
            a test file and an example in a docstring. REPORTED 8 DANGLING. The real number was 0 -
            and test-links.mjs already said so, which is what exposed it.
version 2   skipped every name containing a slash, so a script named the way scripts are actually named
            - by its path - never counted. REPORTED 28 ORPHANS, including every script in the family,
            while their own SKILL.md named them on line one.
version 3   looked only inside backticks, so a name in a fenced command block or in the frontmatter
            still did not count. The command that runs the preflight is in a fence; the compatibility
            line is in the frontmatter.
version 4   treated a skill-relative script path as ambiguous across the whole family and reported 243
            of them - because a document that writes a path without the skill name plainly means its
            own, and the context resolves it.
```

**What the four have in common is the defect this family spent a day collecting**: a conclusion drawn
from the shape of the code rather than from the effect of running it. Version 1 did not ask whether a
Python test contains links; version 2 did not ask how a script is named in practice.

## What it found when it stopped lying

Run against the repository it lives in, the honest version reports a small number of real problems —
files named nowhere at all, and sentences that appear verbatim in two places. **The second list is the
one with teeth**: a rule written twice is how a file comes to contradict itself, and this family found
two such contradictions by eye in one day, which is two more than it should need.

**Read the counts as leads, not as verdicts.** `INFERRED` in particular is broad — it fires on any
mention of a unique name anywhere in a file — so a high number there is expected and is not by itself a
problem. The lists worth acting on are the short ones.

## Opening it

The output is markdown with relative links, so **opening the repository as an Obsidian vault makes the
graph pane work with no plugin and no copying.** Nothing is duplicated: the pages point at the real
files, which is the only version of a generated view that cannot go stale.
