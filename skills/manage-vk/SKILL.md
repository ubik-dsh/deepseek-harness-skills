---
name: manage-vk
description: Work with VK (VKontakte) from an agent - read a community before writing to it, publish a post or photos to a wall, and tell a refusal from an empty answer. Covers the community access token and the places it must never travel, the confirmation gate that stands before anything is published, the rate ceiling, the photo upload sequence, and the error codes that look like success because VK answers HTTP 200 with the failure in the body. Ships a read-only preflight that must pass before the first write, and a Russian typography linter with the range rule narrowed so it cannot corrupt ГОСТ or telephone numbers. Use when the user asks to post to VK, to check a VK community, to read a VK wall, when a VK API call returns a surprising result, when a token has to be configured, or when Russian text is being prepared for VK.
license: MIT
compatibility: Agent Skills standard. SKILL.md is plain text. scripts/preflight.py and scripts/typo_lint.py need Python 3.8 or newer and the standard library only; the network is used by preflight alone, and only for reads.
metadata:
  spec: https://agentskills.io/specification
  version: 0.1.0
  status: first formulation, written after four adversarial hearings over existing VK skills. All four were rejected and this takes only the parts that survived, naming each source
  borrowed_from: the gate-before-write idea and the confirmation requirement come from dexterfire/vk-wall-poster-universal, which the hearing rejected for reading a personal session token out of the browser and never asking. The honesty contract of distinguishable exit codes comes from antonbru/vk-video-skill. The Russian typography table comes from Shadowru/crosspost-design-skill, AGPL-3.0, reimplemented rather than copied, with its range rule narrowed
  sibling: manage-windows covers the machine this runs on, route-a-task decides whether this skill is required at all
---

# Working with VK from an agent

VK is not hard to call. It is easy to call **wrongly and be told you succeeded**, which is
why this skill is mostly about what happens before and after the request.

Four things decide whether the work is real, and every one of them came out of a hearing
over a skill that got it wrong:

1. **The token's authority must be the community's, not the account's.** A community token
   can post to that community and nothing else. A browser session can do anything the
   signed-in person can, invisibly. **This skill uses the community token only.**
2. **The agent never receives the credential.** It comes from the environment. Nothing
   pastes a token into a chat, a command line, or a file the transcript can see.
3. **Nothing is published without a confirmation the code enforces**, not one the prose
   requests. A rule in a document is not a gate.
4. **A refusal must look different from an empty answer.** VK answers `HTTP 200` with
   `{"error": {...}}` in the body, so a client that checks the status code reports every
   failure as a success.

---

## Step 0 — the preflight, and it must pass before anything else

```bash
python scripts/preflight.py
```

It is **read-only by construction**. It reads the token from the environment, asks VK who
the token is, what it is allowed to do, and what is on the target wall. It posts nothing,
writes nothing, opens no browser, and has no flag that makes it do any of those — the
`--check` of the skill this was built from could launch a browser, which is how a dry run
became an action.

It prints, and exits:

```
  0   the token works, the target resolves, and the permissions are listed
  2   no token in the environment, with the exact place to set it
  3   the token works but cannot do what is about to be asked of it
  4   VK answered with an error object - the code and its meaning are printed
```

**Exit 3 is the one people skip.** A token that reads is not a token that writes, and a
token that writes to a wall is not one that can upload a photo (`photos` scope). The
preflight asks VK for the permission mask rather than guessing from the fact that a read
succeeded.

## Step 1 — the token lives in the environment, and nowhere else

```bash
VK_COMMUNITY_TOKEN=<the community key>     # a user environment variable, not a file
VK_GROUP_ID=241624898                      # the community's numeric id, positive
```

Rules, and they are not stylistic:

- **Never ask the user to paste a token into the chat.** A credential in a transcript is a
  credential in a log, in a backup, and in whatever the transcript syncs to.
- **Never pass it as a command-line argument.** Arguments are visible in the process list
  and are saved in shell history.
- **Never write it to a file the agent created.** If the user keeps one, that is theirs.
- **The community token is the whole of the authority.** It is scopeable, it is revocable
  without touching the person's account, and its failures are the community's failures.

**When the environment variable is not reachable, use `--env-file` and pass the path only.**

```bash
python scripts/preflight.py --env-file "$DSH_HOME/vk.env"
```

Measured, and it is why this flag exists: `setx` writes the variable to
`HKCU\Environment`, and **a process spawned by an already-running harness never sees it**,
because that harness's own environment block was fixed when it started. Only the path of
the file travels, so the value still never reaches a command line, a process list or a
transcript. The script prints a fingerprint — a length and the first four characters — and
never the value.

**The file must not be inside a repository.** `preflight.py` refuses one that is, because a
credential in a working tree is one `git add -A` from being published, and a warning about
that is a warning that gets read after the push. `$DSH_HOME` is outside every repository,
which is why the file belongs there.

**Where the key comes from**, for the human, in VK's own interface: the community →
**Управление** → **Настройки** → **Работа с API** → **Создать ключ**, with the scopes
`wall` and `photos` (add `docs` only if documents are to be attached). The same screen
enables **Long Poll API**, which a bot needs and publishing does not.

**The community id is positive; the wall's owner id is negative.** `VK_GROUP_ID=241624898`
becomes `owner_id=-241624898` at the call. Getting this sign wrong is the most common
single mistake in this API, and it fails in a way that looks like a permissions problem.

## Step 2 — what a community token can and cannot do, measured

**A community token can write and cannot read, and it can write and cannot undo.** Both were
measured against the live API, and both change the shape of the work:

```
CAN     groups.getById   groups.getTokenPermissions   groups.getMembers   groups.edit
        messages.getConversations   users.get
        wall.post            <- publishing works
        wall.closeComments
CANNOT  wall.get   wall.getById   wall.getComments      <- no reading at all
        wall.delete   wall.edit   wall.restore          <- no undo at all
        photos.getWallUploadServer                      <- no photo upload
        stats.get   board.getTopics   market.get   account.getAppPermissions
```

Every refusal is `error 27 Group authorization failed: method is unavailable with group auth`,
and **the permission mask says nothing about it** — this key carries a `wall` permission and
still cannot call six of the eight `wall.*` methods. The mask says what the key is for; it does
not say what VK will accept.

So **"read the wall before writing to it" is not possible with this credential**, and the first
version of this skill promised exactly that. What replaces it:

- **Read with a different key.** A **service token** reads public data without acting as
  anyone, and cannot post. Two credentials with two scopes is a design, not a workaround.
- **Confirm by `post_id`, and by eye.** `wall.post` returns the id; the human opens the
  community and looks. That is the verification this credential allows.
- **The preflight still runs first**, and still changes nothing: it resolves the community,
  lists the permissions, flips a positive id to a negative owner, and reports which reads this
  token cannot do instead of failing on them.

**Never call `wall.delete` and assume it worked.** It answers error 27 on a community token, and
a post published with one **can only be removed by hand**.

## Step 3 — the confirmation gate

Before the first write, all of the following are printed and the run **stops** until the
human answers:

```
target      the community, by name and by id, as VK reports it
authority   community token, owner_id=<id>, from_group=1
content     the exact text, and the exact files, with sizes
effect      a public post, visible immediately - or scheduled, at <time>
```

Three rules make it a gate rather than a courtesy:

- **The gate is in the code.** A script that says "never publish without confirmation" in
  its documentation and never blocks on input has not implemented the rule; it has
  described it. This family's rejection of the skill this was built from turned on exactly
  that sentence.
- **An unanswered question is a refusal, not a default.** No answer, no write.
- **The confirmation covers the content, not the intention.** "Publish it" before the text
  existed is not a confirmation of the text.

## Step 4 — publish, or schedule

```bash
python scripts/preflight.py --target -241624898 --dry-run     # what would be sent
```

**A post that can wait should be scheduled** (`publish_date`, a unix timestamp). A scheduled
post is reviewable between the decision and the effect, and a wrong one can be removed
before anyone sees it.

## The photo sequence is four steps, and none of them works with a community token

1. `photos.getWallUploadServer` with `group_id` → a one-use upload URL;
2. `POST` the file to that URL → it returns `server`, `photos`, and a `hash`;
3. `photos.saveWallPhoto` with those three → a photo object with an `owner_id` and an `id`;
4. `wall.post` with `attachments=photo<owner_id>_<id>`.

**Step 1 answers error 27 on a community token**, so the sequence cannot start. It is written
down because the shape is right and a service or user token would need it — not because this
credential can run it. Text posts are what a community token is for.

**Each step's output is the next step's input, and none of them is a URL you can reuse.** The
upload host is not the API host; the `hash` is not the `photos` field; and a photo saved once
does not need saving again. A failure in step 3 leaves an uploaded file nobody will look at,
which is harmless and should simply be retried.

## Errors do not arrive as HTTP errors

Measured, without a token:

```
GET https://api.vk.com/method/groups.getById?group_id=241624898&v=5.199
-> HTTP 200
   {"error":{"error_code":15,"error_msg":"Access denied: token required"}}
```

**Check the body, always.** A client that reads `status_code` treats a refused call as a
delivered post. Full list, and which codes are worth retrying, in
[references/api-errors.md](references/api-errors.md).

## The rate ceiling

VK allows a small number of requests per second per token, and the ceiling is not the same
for every method. **Space the calls.** One request every 400 ms is well inside every limit
and costs nothing on a task that publishes one post; a loop without a delay is how a working
token gets temporarily blocked, and the block looks like a broken token.

Retry a rate error with a growing delay, and **do not retry a permission error** — it will
be refused exactly as many times as it is asked.

## Russian text, before it is pasted anywhere

```bash
python scripts/typo_lint.py article.md            # report
python scripts/typo_lint.py article.md --fix      # rewrite in place
```

Nine rules, of which **eight are mechanical and the ninth is not** — see
[references/typography-ru.md](references/typography-ru.md). The ninth is the one that
matters most to know about, because the table it came from lists it as mandatory and no
rule can decide it: whether `кто — то` is a hyphenated word or two words with a dash is a
question about meaning.

**The range rule is narrower here than in the table it came from, and the reason is
measured.** `ГОСТ 7.32-2017` is not a range, `8-800-555-35-35` is not a range, and `1-2-3`
is not a range. A rule that turns those into en dashes corrupts a document while reporting
success.

## What this skill does not cover

- **Messages and bots.** A community token with `messages` scope and Long Poll is a
  different job with a different failure surface, and it is not in here yet.
- **VK video, subtitles and transcripts.** A sibling concern, arriving later.
- **The other social platforms.** Cross-posting is its own problem.
- **Anything the API does not expose.** VK articles have no import route that this skill
  has been able to verify; a claim to the contrary is marked unverified in the references
  rather than repeated here.

## Refining this skill

Version 0.1.0. What is least trustworthy:

- **The error table is half measured and half received.** Error 15 and the HTTP 200 shape
  were measured without a token. The rest came from reading four rejected skills' source,
  and is marked in the reference as unverified until a real token produces it.
- **The permission check assumes `groups.getTokenPermissions` is available to a community
  token.** That is the documented behaviour and it has not been run here.
- **The typography rules are trialled** — 8 of 9 mechanised, 0 false positives against 14
  control traps — and the ninth is deliberately left to the reader.
- **Nothing here has published to a live wall yet.** The preflight is untested against the
  API, and the first real run is the trial that matters.
