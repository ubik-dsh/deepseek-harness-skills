# Borrowed practices

Every rule in this skill came from somewhere else. This file records the ones
that were taken most recently, where they came from, and what they mean when the
work is authoring a skill rather than doing the thing the skill is about.

The source for all six is the `skill-creator` skill in that vendor's own collection, found by
running both skills against the same three tasks — mathematics, logic, and
ancient-language decipherment — and having a third agent read the six results
blind. That comparison is why they are here: a judge named each one as something
the other skill did better.

A borrowed practice is a hypothesis until it has been tried here. Each of these
says how to tell whether it worked.

## Mark how each claim was established

**Source.** The other skill's status vocabulary: *proved*, *verified
numerically*, *conjectured* — three words for three different levels of certainty,
never collapsed into "done".

**Here.** A skill about a tool is full of claims: that a flag exists, that a
field is required, that a command returns zero. Say which ones you ran and which
ones you read. `verified_against` in the metadata is the coarse version; inside
the body, a fact you executed and a fact you inferred look identical, and the
reader cannot tell which is which.

**Apply it.** Where a body states behaviour, say where the statement came from in
the same breath — "returns 0 (observed)", "must match the folder (spec §name)",
"rejects the camelCase spelling (source: `dsh-skill-filesystem`)". It costs a
clause and it is the difference between a fact and a rumour.

**Whether it worked.** Ask a reader who did not write the skill to sort the claims
in the body into *ran it* and *read it*. If they cannot, this practice is not in
the file yet.

## Declare what you did not cover

**Source.** Early-stop disclosure: *"stopped early — the grid was not covered"*,
stated in the output rather than discovered later by whoever relies on it.

**Here.** A skill that says what it handles and stays silent about the rest is
read as covering everything. The silence is not neutral; it is a claim.

**Apply it.** A `## What this does not cover` section in the body, and the same
section in the record of any measurement. Name the inputs you did not try, the
harnesses you did not test on, the case you skipped because it was slow.

**Whether it worked.** Read only the sections that describe what the skill does.
Is there anything a reasonable reader would assume is included that is not? That
assumption, written down, is the missing line.

## Give bounds instead of refusing

**Source.** Where the other skill computes an interval for a value it cannot
evaluate exactly, the first version of ours refused outright. Refusal is easy and
loses information the reader needed.

**Here.** "I could not verify this" is almost never the whole truth. You can
usually say what you did check, over what range, and where the uncertainty starts.

**Apply it.** Replace a flat refusal with the boundary: not "cannot confirm the
count" but "the count is correct through line 400; the file continues past what
this command read". The same applies when authoring — an instruction that cannot
be perfectly verified should still say how far it holds.

**Whether it worked.** Find a refusal in the artifact. Can it be turned into a
range, a partial result, or a named boundary? Then it was a refusal where a bound
would have done.

## Calibrate against a skill that already works

**Source.** Two habits from the other skill: a check for forged or imitated
material, and calibration against a draft written by the person who owns the
problem.

**Here.** The most expensive way to discover that a skill is useless is to publish
it and wait. The cheap way is to read a skill that already does something close
and say how yours differs. If it does not differ, you have written a restatement,
and restatements do not help anyone.

**Apply it.** Find one existing skill in the same area — installed, published, or
written by the person asking — and write one sentence: *this differs by X*. If X
is "it is clearer", look again.

**Whether it worked.** The sentence exists, and it names a difference a reader
could act on.

## Form first, then substance

**Source.** The other skill separated the form of an answer from its substance and
said to fix the form first.

**Here.** It is the order this skill already implies with its checker and its
evaluation, but has never said out loud: a beautiful body behind malformed
frontmatter never loads, so judging the prose before the contract wastes the
judgement.

**Apply it.** Run the checker before you read the draft for quality. A skill that
fails the form is not ready to be judged, and reviewing it teaches you nothing
about the part that is actually hard.

**Whether it worked.** You fixed a mechanical defect before you formed an opinion
about the writing.

## Claim the work in the description

**Source.** The other skill's description names situations directly — *"who is
lying"*, *"even if they never say the word logic"* — where ours described its own
contents.

**Here.** Measured, not argued: a trigger evaluation of this skill missed exactly
one query out of ten positives, and that query went to the other skill because
its description claimed description optimization and ours did not. One line in a
description moved a real decision.

**Apply it.** Write the description from the user's side. Name the implicit asks —
the ones where the need is obvious to the person and invisible in their words.
Then measure it: twenty queries, ten should-trigger and ten near-misses, judged by
an agent that sees only the catalogue.

**Whether it worked.** The near-misses are still not claimed, and the positives
are. A description that gains a positive by claiming a near-miss has got worse.
