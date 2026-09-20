# Testing a skill whose test is outside the machine

Moved out of `SKILL.md` when the family's token budget was enforced: the skill was over the 5,000-token body the standard recommends, while passing the 500-line check that used to stand in for it.

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
[simulating-a-test.md](simulating-a-test.md). Three lessons
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

## The author cannot test the skill

**If independent testing is possible, it is not optional.** This is the strongest rule here,
and it is the one that found the most.

A skill is written by someone who knows what it means. That person reads `verify the target
before anything is pressed` and understands it, because they wrote it about a specific click
that went wrong. **A reader with no context does not have that click.** They have a sentence,
and whether the sentence carries the meaning is exactly what has not been tested.

So the test is not the author reading it again. It is **a fresh agent, given no context and no
history, told the skill exists, and asked to do a real task with it.** Then asked, bluntly,
where it had to guess.

### How to run one

1. **Start an agent with no context.** Not a summary of the work, not a fork of the
   conversation — a fresh one. Anything carried over is context the real reader will not have.
2. **Name the skill and give a task that exercises it.** The task must be one where the skill
   changes what happens; a task the agent could do anyway tests nothing.
3. **Do not explain the skill.** If it needs explaining, that is the finding.
4. **Ask these six questions, in this order**, and require quotes rather than paraphrase:
   - Did you find it, and did the `description` make it clear it applied? Quote the part.
   - What did it tell you to do that you would not have done anyway? For each: followed,
     or not, and why not.
   - **Where did you have to guess?** A complete skill leaves nothing to guess.
   - Was anything wrong, stale, or contradicted by what actually happened?
   - **Its centre, in one sentence.** If the agent cannot state it, the skill has none.
   - The three changes you would make, ranked.
5. **Tell it to say "the skill was silent"** rather than inventing what the skill probably
   meant. You are testing the skill, not the agent's charity.
6. **Change nothing in the skill during the test**, or the report describes a version that
   no longer exists.

### What one found here

A single fresh agent, one pass, on a skill four other checks had passed:

- **Two of six skills did not load at all.** A colon inside a frontmatter value, which the
  author could not see because the author knew the skills existed. `skill <name>` answered
  *"unknown or no longer available"*. **Every unit test passed while neither skill existed.**
- **The skill warning loudest about encoding corruption carried a corrupted character** in its
  own reference file — typed by the author, copying from a console that had already mangled it.
- A directory the skill tells you to use, **unnamed**, so the agent invented one.
- "Use a UTF-8-aware tool" **naming no tool**, while the only encoding type the skill names
  **emits a byte-order mark by default** — the fault the skill exists to prevent.
- An exemption from the checking step, **unstated**, so the agent had to decide whether it
  applied.

**Nothing on that list was reachable by reading the skill.** Every item needed a reader who
did not already agree with it.

### The uncomfortable part

The author's own tests passed. Six skills, all checks green, and two of them were not skills
anyone could load. **A test written by the author shares the author's blind spot, and passes
for the same reason the defect exists.**

If you cannot run an independent test — no fresh agent available, no way to isolate one — then
say so where the skill records its state, and do not write that it was verified. The honest
entry is `not independently tested`, and it is worth more than a green check that means
nothing.
