---
name: judge-a-skill
description: Put one skill on trial before adopting it — a prosecutor argues why it is not needed, a defence argues why it is, and a judge decides from a fixed set of verdicts, including the one that matters most - reject the skill, take these parts. Charges must cite something checkable in the artefact, a clean verdict is a first-class outcome, and the two cases are rated so a close call is visible as a close call. Ships a runnable recorder that refuses a charge with no evidence. Use when deciding whether to adopt, keep, fork or drop a skill; after reading an external or marketplace skill; when asked to review, audit, judge or score a skill; when a skill "seems useful" but nobody can say why; when several skills overlap and one has to go.
license: MIT
compatibility: Agent Skills standard. SKILL.md is plain text. The script in scripts/ needs Python 3.8+, standard library only, and is a recorder rather than a judge — it formats and validates, it does not decide.
metadata:
  spec: https://agentskills.io/specification
  version: 0.1.0
  status: first formulation, to be sharpened by use
  measured_on: three real hearings over rival skills, two adopted in part and one rejected
  borrowed_from: maan2003/public-skills (autonomous-designer-prosecutor) for the charge discipline — evidence-backed charges, premise versus execution, no pay per charge, and naming what a revision must not destroy; makinux/adversarial-panel for independence, adversariality, synthesis without averaging, and the triage trap; mertpaker/aie26-skill-judge for the structural check that comes before any scoring — found by a survey of 247 repositories shipping a skill-evaluation SKILL.md
  sibling: find-a-skill, which decides whether to look; create-a-skill, which writes what survives this
---

# Judging a skill

A score says how good a skill is at being a skill. It does not say **whether it should
exist**, and that is the question that decides adoption. Three rival skills were put
through this and all three were rejected — while each contained one idea worth keeping.
A rubric would have scored all three respectably and told nobody what to do.

So the shape is a hearing, not a table:

> **Prosecutor** — why this is not needed. **Defence** — why it is. **Judge** — a
> verdict from a fixed list, and a rating of the two arguments, because a close call is
> information.

---

## Step 0 — Is a hearing worth it?

Do not convene one for everything. A hearing costs three readings and pays only when
the question is **consequential** and either **contested** or **checkable**. If the
skill is obviously thin, say so and stop. If you already know it should be kept and why,
say that and stop.

**But beware the triage trap**, and this one is not optional:

> The gate is run by **the same judgement whose blind spots the hearing exists to catch**.
> The skills you are most confidently wrong about are exactly the ones that will not
> trip it.

So: if the user asked for a hearing, run it regardless of your certainty. And for a
skill that will be adopted, let **stakes** decide, not your felt confidence.

## Step 1 — The structural check, before any argument

A hearing about the content of a malformed file is a waste. Check the mechanical things
first, and **do not proceed to argument while any of them fails** — report each with the
fix instead:

- frontmatter present, `name` matching the folder, kebab-case, ≤64 characters;
- `description` present, non-empty, and carrying **trigger language** — the words a user
  would actually say;
- under 500 lines of body, detail moved into `references/`;
- every relative link resolves.

These are checkable by machine, and the sibling skill `create-a-skill` ships a checker
that runs them. Run it. If it fails, the hearing has not started.

## Step 2 — Write the charge sheet before hearing anything

Before reading the skill's defence of itself, write down what the verdict has to
decide. This is the sheet both sides argue against, and writing it first is what stops
the hearing from becoming a description of the skill.

```
The claim      : what this skill says it does, in one sentence.
Worth keeping  : what would have to be true for it to earn its place.
Worthless      : what would make it not worth keeping, said before looking.
Falsifiable by : a concrete observation that would settle it. "Fails on input X",
                 "the stated measurement is absent", "a rival does the same thing".
```

A falsification condition that cannot be checked — *"if evidence emerges to the
contrary"* — is calibration theatre. Write the checkable one or leave the line empty and
say the question is undecidable.

**If another skill already does it, that is a charge the prosecutor must address with
evidence, not an assumption.** `find-a-skill` is where that evidence comes from.

## Step 3 — The prosecution

Argue that the skill should not be kept. Rules, all of them borrowed from a working
prosecutor and all of them load-bearing:

- **Every charge cites something checkable in the artefact** — a line, a heading, a
  missing measurement, an assumption the file states. *"Vague unease is not a charge."*
- **You are not paid per charge.** A manufactured charge poisons the record worse than
  silence. **A clean verdict is a first-class outcome** — if nothing concrete survives,
  say so and show what you looked at.
- **Distinguish the two levels**, because they lead to different verdicts:
  - **premise-level** — the skill's underlying bet is wrong. *"This assumes a hook
    mechanism that the harness does not have."* → the skill goes.
  - **execution-level** — the bet is fine and this file betrays it. *"The idea is right
    and the procedure assumes an architecture we do not have."* → the file is fixed.
- **Attack the strongest version**, not the wording. A charge against a sentence the
  author would happily rewrite is not a charge against the skill.
- **Rank by severity**, and name the single severest charge. If everything is equally
  bad, nothing is.
- **Where a claim is checkable, check it.** Run the command, fetch the file, count the
  lines. *"Refute by reproduction, not by assertion."*

## Step 4 — The defence

Argue that the skill should be kept. Three obligations, and skipping any of them makes
the defence worthless:

1. **Answer each charge.** Not the charge sheet as a whole — each charge, by name.
   Conceding one with a reason is stronger than ignoring it.
2. **Name what any outcome must not destroy.** Even a defence that loses must say
   which part of the skill is worth carrying out of the wreck. This is the sentence the
   judge's order is built from.
3. **Argue from the artefact, not the description.** A description is a claim the author
   made about their own work, written to be matched. Quoting it back is not a defence.

A defence is allowed to lose, and a defence that wins by restating the skill's own
marketing has not won anything.

**Sycophancy check.** If the defence concedes everything and reverses completely under
the first charge, ask for the ground of the reversal before accepting it. An unexplained
full reversal is a flag, not a conversion.

## Step 5 — The judge

Decide. Three rules:

- **Adjudicate, do not average.** Splitting the difference between two positions destroys
  the signal. Say which case was stronger and why.
- **Weigh by evidence, not by volume.** When one side has something reproducible and the
  other has an impression, decide in favour of the reproducible one. Presenting them as
  symmetric *"both views have merit"* is **false balance, not neutrality**.
- **Separate real disagreement from vocabulary.** Two sides slicing the same conclusion
  differently is not a conflict.

### The verdicts

| Verdict | When |
|---|---|
| **Acquit** | no concrete charge survived. Keep it whole. |
| **Keep with a boundary** | it works, and only under stated conditions. Write the conditions beside it. |
| **Fix** | the bet is right, the file betrays it. Say what to change. |
| **Reject the skill, take these parts** | **the skill is not worth keeping and parts of it are.** The order names each part and the trial that would confirm it. |
| **Reject entirely** | nothing survives. |

The fourth is the one this skill exists for. A rubric cannot produce it: it scores the
whole and has nowhere to put *"the thing is not worth having and this one idea is."*
Every one of the three rival skills judged so far landed there.

## Step 6 — Rate the two cases

Two numbers out of ten, and who won. **A close score with a clear winner is the most
useful result there is**, because it says: *the arguments were nearly equal, and the
prosecutor's held* — which is precisely when there is something worth salvaging.

```
prosecutor  X/10     the strongest single charge, in one line
defence     Y/10     the strongest single point, in one line
verdict     who won, and the one sentence that decided it
```

## Step 7 — Record it

Write the charge sheet, both cases, the rating, the verdict and the order where the next
person will find it — beside the skill if it is kept, or in the family's borrowing record.

`scripts/hearing.py` builds and validates the record. **It refuses a charge with no
evidence citation**, and a defence that answers no charge — the mechanical half of
*"a vague unease is not a charge"* and *"answer each charge"*, enforced rather than
requested.

```bash
python scripts/hearing.py --new <skill-name> > hearing.json   # a blank sheet
python scripts/hearing.py hearing.json                        # validate and render
```

## Three hearings, for calibration

The ratings are not a scale invented in advance. Three rival skills were judged with
this procedure and the record is in
[three-hearings.md](references/three-hearings.md): all three rejected, each with
something taken, two of them decided **6 against 5**. A close score with a clear winner
is the useful result — it says the arguments were nearly equal and the prosecutor's
held, which is exactly when there is something worth salvaging.

## The appeal — judging the judgement

A hearing decides whether a skill is worth keeping. **An appeal decides whether that hearing
was any good.** They are different questions, and running the first one twice answers neither.

**An appeal does not re-hear the case.** The appellant who argues the skill again has filed the
wrong document — the skill was already read, and a second reading produces a second opinion
rather than a check. **Two opinions are not better than one; they are two.**

### What the appellant attacks

The first hearing's **reasoning**, with the same evidence rule that binds a charge:

| what to attack | what it looks like |
|---|---|
| **a misread charge** | the artefact does not say what the charge claims it says |
| **evidence weighed wrongly** | an impression was preferred to something reproducible |
| **the two levels confused** | a premise-level fault used to condemn the file, or the reverse |
| **a manufactured charge** | it cites nothing checkable, or something the author would rewrite |
| **averaging instead of adjudicating** | "both sides make good points" where the evidence was unequal |
| **a verdict that does not follow** | the charges support a different entry from the fixed list |
| **an unexamined part** | a section of the artefact no charge and no defence point touched |

That last one is the most productive and the least used. **A hearing reads what it argues
about**, and what nobody argued about is exactly where a defect survives — the battery probe
that SKILL.md promised and the tool never had was found by a reader, not by the first hearing,
because no charge had a reason to open that sentence.

**And the recorder cannot enforce it.** It checks that the grounds name something from the
list; it cannot check that the body argues it. The first appeal run said so itself: a filing
whose grounds read `unexamined part` while its body re-argues the artefact is recorded as
valid. **The distinction holds because it is stated, not because the sheet makes it** — so
state it, and read the filing.

`--artefact` takes any number of paths and a directory, and searches all of them, because a
skill's checkable prose and its behaviour are usually in different files. The first version
opened one file and refused a correct citation of a bundled script, which is a check that
teaches an author to cite only what the checker reads.

### The respondent

The respondent defends **the first hearing**, not the skill: the charge was read correctly, the
evidence did support it, the verdict does follow. Conceding a point is allowed and does not
lose the appeal — what loses it is defending the reasoning with a new argument about the skill.

### The decision

| | |
|---|---|
| **Uphold** | the reasoning holds; the first verdict stands |
| **Vary** | the verdict was right and the reasoning was not, or the remedy was wrong — say which |
| **Overturn** | the reasoning does not hold, and the verdict it produced is replaced |

**A rating of the two cases, as in the first hearing.** An appeal decided 6–5 tells the reader
the first hearing was nearly right, which is different from 9–2 and is worth knowing.

### What an appeal is not for

- **Changing the verdict because a different verdict is defensible.** Most verdicts are. The
  question is whether *this* reasoning supports *this* one.
- **A second opinion on the skill.** If the appellant's best material is about the artefact
  rather than the hearing, the appeal fails and says so.
- **A tie-break by seniority.** The appeal has no more authority than the first hearing; it has
  a different job.

## Failure modes, all of them observed

- **The hearing becomes a description.** Nothing was charged, so the output summarises
  the skill. The charge sheet in step 2 is the cure.
- **The prosecutor manufactures charges** to look useful. Hence: not paid per charge,
  clean verdicts are first-class.
- **The defence restates the description.** Hence: argue from the artefact, and name what
  must not be destroyed even when losing.
- **The judge averages.** *"Both sides make good points"* is not a verdict. Adjudicate.
- **The judge performs balance.** Two sides are not equal because there are two of them.
- **A status line is mistaken for a case.** If a delegated case returns *"started in
  background"* or an error dump, that is not a contribution — a later stage would be
  judging a ghost. Re-run it.
- **Certainty skips the hearing.** The triage trap. Stakes decide, not confidence.

## What this skill does not cover

- **Finding the candidate.** `find-a-skill` searches and triages; this judges one that
  has been found.
- **Writing or fixing the skill.** `create-a-skill`. The order says what to change; it
  does not change it.
- **Scoring a skill against a rubric.** That exists, widely, and it answers a different
  question — how good is this at being a skill, not whether it should be one. If a
  scorecard is what is wanted, say so rather than running a hearing.
- **Compliance.** Whether a skill is *followed* once adopted is a third question, and a
  harder one: a skill can win this hearing and still not change behaviour.

## Refining this skill

Version 0.1.0. Most likely to be wrong:

- **the ratings are uncalibrated** — three hearings is not a scale, and 7/4 means what it
  means only by comparison with the other two recorded ones;
- **the two-level distinction** (premise versus execution) has been applied three times
  and could yet turn out to be a distinction without a difference on cases where both
  are true;
- **nothing here stops a hearing from being run by the same model that wrote the skill**,
  which is the triage trap one level down. A separate agent for each case is the obvious
  answer and has not been tried.

When a use contradicts something here, the use wins: change the file, keep the
counter-example.
