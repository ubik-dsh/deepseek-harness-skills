# Three hearings, and what they calibrated

The ratings in this skill are not a scale invented in advance. They came from three
hearings run on real rival skills, and this is the record so that a fourth can be
compared rather than guessed at.

The pattern that made the skill necessary is in the last column: **every one was
rejected, and every one had something worth taking.** A rubric would have scored all
three respectably and told nobody what to do next.

| skill | prosecutor | defence | verdict | taken |
|---|---|---|---|---|
| `gateguard` | **6** | 5 | reject the skill, take these parts | 2 |
| `delivery-gate` | **7** | 4 | reject the skill, take these parts | 1 |
| `rules-distill` | **6** | 5 | reject the skill, take these parts | 2 |

---

## `gateguard` — 6 against 5

**The claim.** A hook that blocks the first edit to a file and demands four concrete
facts — importers, affected public surface, data schema, and the user's instruction
quoted verbatim — before allowing a retry. Measured improvement: **+2.25 points**.

**The prosecution's best charge** (premise-level, severity 8/10) cited the skill's own
table:

> *Two independent A/B tests, identical agents, same task.*

That is the evidence offered for an average. It is the mean of **two** measurements, with
no variance, no interval and no rubric. An average of two numbers reads as evidence and
is an anecdote with a decimal point.

Its second-strongest was structural: the artefact is bound to one harness
(`CLAUDE_PROJECT_DIR`, `hooks.json`, `PreToolUse`), so even a true claim cannot run
elsewhere, leaving only the idea.

**The defence's best point** did not dispute the number — it separated the number from
the mechanism:

> *The number is weak and the mechanism behind it is separately checkable without it.
> One task, two runs, a rubric fixed before either: that costs an hour and settles the
> question the number was trying to settle.*

It also pointed out that the four facts are well chosen, and that the **schema** item has
a concrete failure behind it: both A/B agents assumed ISO-8601 while the real data was
`%Y/%m/%d %H:%M`. Our own work keeps making the same class of error — three defects in
one session came from acting on a restatement of the request rather than the request.

**Decided by.** The prosecutor holds the **artefact**; the defence holds the
**mechanism**. A mechanism that can be trialled here outlives a number that cannot be
checked, but it does not rescue the file it came in.

**The order.** Two parts, each with its own trial:
- state the facts before the first edit — trial: one task, two runs, rubric fixed first;
- a destructive-command gate with its trigger list written down — trial: check the list
  against the destructive commands actually run and see whether it catches them.

---

## `delivery-gate` — 7 against 4

**The claim.** A stop hook that will not let a session finish until quality checks pass:
disk space, whether learning files were touched today, and "rationalization patterns" in
the transcript. Deterministic only, no AI inference.

**The prosecution won on the skill's own limitations section**, which is the strongest
kind of evidence there is:

> *The hook enforces the **habit** of touching learning libraries, not the **quality** of
> what was recorded. If `output-index.md` is updated but `growth-log` is skipped, the
> hook passes.*

The failure it exists to prevent — *"over many sessions of ship and forget, the human
hasn't grown"* — is **fully reachable with the gate installed**. Update one file with
garbage and pass.

That is not a flaw in the execution. It is **the exact defect our own reward rules name**:
a reward that can be satisfied without the task being done. This skill is a worked
example of a rule we wrote for a different reason, and its author says so.

Two more charges: its one interesting idea — regex on prose for rationalization — **never
blocks**, by the author's own decision, and its thresholds are absolute (50 GB means
something different on a laptop and on a workstation).

**The defence's best point** was about design, not about this skill:

> *Where `gateguard` asks a model to be honest, this checks filesystem facts. An mtime
> cannot be talked out of its answer.*

That is the better instinct, and the skill applied it to the **wrong fact**. Presence is
not learning.

**Taken:** one thing — the idea of a delivery gate on a **deterministic** fact, pointed
at a fact that actually correlates with the goal. *"Tests ran and the deployment check
passed"* rather than *"a file was touched."*

---

## `rules-distill` — 6 against 5

**The claim.** Scan all skills, cross-read them, find principles appearing in **2+**
skills, and propose promoting them into rule files. Scripts collect; a model judges;
the user approves.

**The prosecution's best charge** was that we do not have the architecture it serves. It
distils skills into **global rule files**; our cross-cutting principles live in
`references/` inside each skill, and its inventory script reads a path we do not have.
Its promotion criterion is also weak: **a principle in two skills often means two skills
quoting one source.** In our own family `find-a-skill` and `create-a-skill` both say
"search before creating" — because the second points at the first. Promoting that would
duplicate both.

**The defence's best point** was a single filter:

> *Include a candidate ONLY if … it can be written as "do X" or "don't do Y" — not "X is
> important".*

That test rejects the sentence that looks like advice and changes nothing, and our own
skills contain some. It is the sharpest single line in the whole survey.

The defence also named the phrase worth keeping — **"deterministic collection, LLM
judgment: scripts guarantee exhaustiveness; the LLM guarantees contextual
understanding"** — which is precisely the shape of our best tools.

**Taken:** the verdict vocabulary (Append / Revise / New Section / New File / **Already
Covered** / **Too Specific** — the last two make *doing nothing* a named outcome), and
that filter.

---

## What the three hearings calibrated

**A close score with a clear winner is the useful result.** Two of the three were 6–5:
the arguments were nearly equal and the prosecutor's held. That is exactly the condition
under which there is something worth salvaging, and it is the condition a scorecard can
never express.

**The severest charge usually comes from the artefact's own text.** `delivery-gate` lost
on its limitations section; `gateguard` lost on its own evidence table. Reading the body
rather than the description is not a stylistic preference — it is where the losing
sentences live.

**A defence can lose and still be right about something.** In all three, the defence
supplied the part that was taken. `gateguard`'s four facts, `delivery-gate`'s
deterministic instinct, `rules-distill`'s filter — none of them was in the prosecution's
case, and none of them would have been found by scoring the skill and stopping.

**And the defence must be *made* to name what survives.** The first run of the
`gateguard` hearing was refused by the recorder for filing a salvage verdict with
nothing in the order. That rule exists because the temptation is real: a defence that
has lost tends to stop arguing rather than say what should be carried out.
