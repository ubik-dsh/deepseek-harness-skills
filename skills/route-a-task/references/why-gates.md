# Why the gates exist, and what this regulation is not

Moved out of `SKILL.md` when the family's token budget was enforced: the skill was over the 5,000-token body the standard recommends, while passing the 500-line check that used to stand in for it.

## What a gate is for

**A gate is not a checklist to consult.** It is a forcing function, and the difference decides
whether the regulation works.

An agent that has forgotten a step does not need to be pointed at a skill. **It needs the step
handed to it at the moment it is standing at the gate** — or "I forgot, let us redo it" is the
normal outcome, and the work is thrown away rather than corrected.

So every gate below carries **the literal step**, the command where there is one, the rule that
decides, and the record it owes. `route.py` prints the steps. **An agent reading only the gate
can comply without going anywhere else.**

And what follows from that: **a gate that was passed without a record can be found at the end.**

```bash
python scripts/route.py "download a skill and publish it" --verify record.json
```

**The record is a mapping from a gate to the evidence, and the format was undocumented until
the agent routed by G6 tried to write one and had to probe for it nine times.** It is:

```json
{"gates": {"G6": "named the check before computing; second route via mpmath; bound over all
 135,107,990 doubles in the zone; what remains unverified: the region outside it"}}
```

It names the gates that fired, the gates with a record, and the difference — and **for each
missing one it reprints what that gate wanted.** Exit 1 when something is missing, so a check
can stop on it.

**A name is not a record, and the two have different exit codes.** `{"gates": ["G6"]}`, or a
gate mapped to `true`, names a gate and says nothing about it. That is a **claim**, exit **4**,
and the output says so in those words. The first version of this flattened both into "has a
record" and returned 0 for a file whose entire content was a list of one name — **the same
not-examined-read-as-clear failure as the empty record, arriving through a different door**,
and found the same way: by the agent who had a reason to write such a file and ask what it was
supposed to contain.

| exit | meaning |
|---|---|
| 0 | every gate that fired carries evidence |
| 1 | a gate that fired is absent from the record |
| 2 | the record cannot be read, or the plain router matched nothing at all |
| 3 | no gate fired — `--verify` mode only (the plain router returns 2 for this) |
| 4 | a gate was named and nothing was written against it |

**That is the whole exchange:** the omission is found *before* the redo, not after, and the
instruction arrives with the finding.

**The router is tested, because a router is a keyword list and a keyword list is wrong until
something fails.** `python scripts/test-route.py` holds cases in both directions — the ones a
gate must fire on and the ones it must not — plus every exit code, the record format, and the
routes that must not be suggested. It exits 1 on any case. Two of its checks exist because a
tool in this family failed them: the `--json` output must decode as UTF-8 **on a console
without `PYTHONIOENCODING`**, since a Russian console defaults to cp1251 and 31 of the 75
trigger phrases are Russian; and a gate named with no evidence must not be reported as
recorded.

## How a trigger is matched, and why that became a finding

**A trigger is matched as words, not as a run of letters**, and this was not always true. The
first version tested `needle in text`, and the result was on screen for two days:

| trigger | fired on | so the regulation ordered |
|---|---|---|
| `repo` | "re**po**rt" | a malware scan before summarising a report |
| `ship` | "relation**ship**" | an independent agent before changing a setting |
| `form` | "**from**", "**form**at", "in**form**ation" | the Windows preflight before anything at all |
| `ratio` | "ope**ratio**ns", "configu**ratio**n" | a second route for a documentation task |

**Every one of those is a gate telling an agent to stop and do something the task never called
for**, which is how a regulation stops being read. `from` alone put the interface route into
almost every sentence in the language.

The form is now written into the trigger, so a new one cannot be added by accident:

```
repo        the whole word, nowhere inside a longer one
install*    a stem - install, installs, installed, installing, installation
sum of      a phrase, bounded at both ends
```

**Measured, over 54 sentences of this family's own skill descriptions and the A/B tasks:**
11 gate firings removed, all of them substring artefacts; 9 route suggestions removed, every
one of them `form` inside `from`, `format` or `information`; **0 route suggestions added**. The
gates that were added are G6, on the tasks it exists for.

**And the lesson was already in this repository.** `find-a-skill`'s scanner carries a
word-boundary helper — it needed one after producing forty false positives on this family's own
files. This router was written afterwards, by the same hand, and did not inherit it. **A
practice learned in one tool does not travel to the next one on its own**, and that is worth
more than the bug it caused.

---

## When two apply

**They are ordered, not ranked.** The gates run in the order they appear when both are
relevant, because each one protects against a different failure and the cheapest comes first.

- **Scan before search.** A search query is not a use, but a fetched result is content from
  outside — and a search that returns a payload is a scan waiting to happen.
- **Scan before check.** G6's first step is to name the check *before* the computation, so G6
  runs early. G1 still runs first: a payload that has not been read is a payload that could
  choose the check for you.
- **Search before write.** Always. The point of G2 is the authoring it prevents.
- **Read before change.** Always, and it is not a preference: the change destroys the reading.
- **Judge before adopt, and read independently before done.** A hearing you ran yourself is not
  G4.

**A gate that is inconvenient is still a gate.** The moment it becomes optional-in-practice is
the moment the family's rules go back to being advice.

## A fault outside the harness's domain

**The third agent's task was a car that would not start, and the regulation had no row for
it.** That is not a gap to fill with advice about cars - it is the row this family was
missing: **work that is outside every tool here, which still has to be done properly.**

The obligation is small and it is the same one G5 asks for:

```
say so     name what you checked, so the gap is a finding rather than an oversight
method     carry the frame across even where the tool does not - evidence before
           hypothesis, a falsifiable test named before the observation, a reading not
           taken is not a reading that came back clean
record     what you did, so the next agent does not redo it
```

**The frame travels; the commands do not.** That agent's whole method came from the body of a
Windows skill whose commands were useless to it. **That is the argument for a gate handing over
the referral as well as the step**, and it is why the router now prints both.

## What this regulation is, and what it is not

**It is a safety and process ontology.** Its triggers are about content arriving from outside,
machines being changed, work being published, tools being chosen, and results being checked.
That is a real and useful set, and it is not everything.

**It had no row for correctness, and that gap was found three times before it was closed.** A
task whose difficulty is that an answer might quietly be wrong — a numerical result, a proof, a
measurement, a classification — matched nothing here. The third agent to be routed by this
regulation had exactly that task, and the honest verdict it returned was that **neither design
served it**, because neither covered it. **G6 is that row**, and the reason it works is that it
is keyed to the shape of the deliverable instead of to the subject: the subject is what a
keyword cannot see, and the shape is what it can.

**The router still matches vocabulary, not intent.** "Verify the result independently" now fires
G6, but it fires because the phrase is in the table — not because the router understood it. A
task can be quietly wrong in words this table does not hold, and then nothing fires. Adding the
word "install" to any sentence fires G1; that is the price of keyword triggers and it should be
known before the output is trusted.

**The exit codes are not one number.** The plain router returns **2** when nothing matched at
all; **3** is returned by `--verify` when no gate fired, and it means something different —
*not covered*, not *not understood*. `SKILL.md` claimed the router "exits 3" without saying
which mode, which the agent that ran the gate caught by measuring the two.

**And the gate was edited while its own trial was running.** `route.py` and `test-route.py`
changed at 15:20 while the agent was still working, which is a defect in how the trial was run
rather than in the skill: the artefact under test moved. Every finding was re-verified against
the finished router afterwards, so nothing here is a verdict on an intermediate version — but
the next trial should freeze the file first, and this is recorded so that the next trial does. `test-route.py` holds the counter-examples in both
directions, and a phrase that fires wrongly is a case to add there rather than a sentence to
reword here.

**So when nothing fires, that is a statement about this document, not about the work.** The
router now says so in those words and exits 3, distinct from 0 — because "nothing applied" and"everything that applied passed" are different sentences, and printing the second when the
first is true turns *not examined* into *checked and clear*.

## Refining this skill

Version 0.2.0, written on the day the family reached seven tools without an entry point and
revised on the day the correctness gate was added.

- **The strengths now have a test, and it was written by the author of the defects.** It caught
  sixteen failures against the previous router, and it is the reason the trigger rewrite could
  be attempted at all. Run it with `python scripts/test-route.py`; it exits 1 on any case.
- **The trigger tables are matched by words, and the counter-examples are in that file.** Every
  false positive found so far is a case there rather than a sentence here, which is deliberate:
  a rule about words is worth less than a test that fails.
- **G6 has never been routed on a real task by a fresh agent.** It was written from the record
  of the agent it would have served, not from that agent's trial of it. That is the same
  "author tests their own work" defect G4 exists to catch, and it is recorded here rather than
  repaired.
- **The rows are the situations met so far**, which is a small sample and biased toward the
  work that produced them.
- **G4 is the weakest in practice.** It depends on an independent agent existing, and it says
  what to write when none does rather than what to do about it.

When a use contradicts something here, the use wins: change the file, keep the counter-example.
