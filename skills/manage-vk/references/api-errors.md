# VK errors, and which of them are measured

**Half of this file is measured and half is received, and the two are marked.** The
received half came from reading the source of four VK skills that were put through a
hearing and all rejected; their code is evidence of what they expected, not of what VK does.

## The shape that costs the most

```bash
curl 'https://api.vk.com/method/groups.getById?group_id=123456789&v=5.199'
```

```
HTTP 200
{"error":{"error_code":15,"error_msg":"Access denied: token required",
          "request_params":[{"key":"group_id","value":"123456789"},{"key":"v","value":"5.199"}]}}
```

**Measured, on this machine, against the live API.** VK answers **HTTP 200** and puts the
failure in the body. A client that reads `status_code` treats a refused call as a delivered
post, and the mistake is invisible until someone looks at the wall.

So the rule is: **parse the body, then look for `error` before you look for `response`.**
Every method behaves this way, and there is no status code that tells you otherwise.

Also in that reply: `request_params` echoes what was sent. When a call fails for no visible
reason, it is worth reading — it shows what VK actually received, which is not always what
was meant.

## The codes

| code | meaning | measured? | what to do |
|---|---|---|---|
| 15 | `Access denied: token required` | **measured** | **no token was sent at all.** Set it and try again |
| 5 | `User authorization failed: invalid access_token (4)` | **measured** | **a token was sent and VK refused it.** Check it is the **community** key and that the API section is enabled for the group. *Some sources attribute this to IP binding on tokens from the implicit flow; that was not verified here and is not relied on* |
| 6 | too many requests per second | received | retryable. Wait longer and send fewer. Never retry in a tight loop |
| 9 | too many requests per day | received | not retryable today. The quota is gone until it resets |
| 14 | captcha required | received | interactive. A community token normally avoids it; a user token hammering the API does not |
| 27 | `group authorization failed` | received | usually a missing scope, or the group key was revoked or regenerated |
| 100 | one of the parameters is wrong | received | read `error_msg` — it names the parameter. Usually `owner_id` with the wrong sign |
| 214 | the wall is not writable | received | the wall is disabled, or this token may not post to it |

**15 and 5 are different faults and this is worth having measured.** Both were produced here
on the same day, against the live API, and the difference is not in the message but in the
cause:

```
no token sent          -> error_code 15  "Access denied: token required"
a token sent, invalid  -> error_code  5  "User authorization failed: invalid access_token (4)"
```

Reading a 5 as "I need a token" sends the reader to look for a token that is already there.
Reading a 15 as "the token is wrong" sends them to regenerate a key that was never the
problem. **The first question after either is which of the two it is.**

**Codes that are worth retrying: 6, and a transport failure.** Everything else is either a
fact about the token or a fact about the request, and asking again produces the same answer
more slowly.

## The method set of a community token, measured

**This is the most useful table in the skill, and nothing documents it.** A community key
carries a `wall` permission in its mask and still cannot call six of the eight `wall.*`
methods. The mask says what the key is *for*; it does not say what VK will *accept*.

Measured against the live API with a full community key — mask 134623237, permissions
`photos`, `docs`, `messages`, `wall`, `manage`, `stories`, `market`:

| method | result |
|---|---|
| `groups.getById` | ok |
| `groups.getTokenPermissions` | ok |
| `groups.getMembers` | ok |
| `groups.edit` | **ok** — proved by changing the community's own visibility and reading it back |
| `messages.getConversations` | ok |
| `users.get` | ok (an empty list, having no user context) |
| **`wall.post`** | **ok** — returned `post_id=1` |
| `wall.closeComments` | ok |
| `wall.get` | **error 27** |
| `wall.getById` | **error 27** |
| `wall.getComments` | **error 27** |
| `wall.delete` | **error 27** |
| `wall.edit` | **error 27** |
| `wall.restore` | **error 27** |
| `photos.getWallUploadServer` | **error 27** |
| `photos.getUploadServer` | **error 27** |
| `photos.getMessagesUploadServer` | **ok** — returns an `upload_url` and `album_id: -64` |
| `photos.getChatUploadServer` | **ok** — returns an `upload_url` |
| `docs.getWallUploadServer` | **error 15**, and the message is different: *"User can't upload docs to this group"*. That is a **community setting**, not a method refusal — documents are disabled for the group, and the method itself is not forbidden |
| `stats.get` | **error 27** |
| `board.getTopics` | **error 27** |
| `market.get` | **error 27** |
| `account.getAppPermissions` | **error 27** |

Every failure is the same sentence: `Group authorization failed: method is unavailable with
group auth.`

### What follows from that, and it is not small

**A community token can write and cannot read.** There is no way to list a wall, read a post
back, or confirm through the API that a post exists. Confirmation is the returned `post_id` and
a human looking at the community.

**A community token can write and cannot undo.** `wall.post` is accepted; `wall.delete`,
`wall.edit` and `wall.restore` are all refused. **A post published with a community key can
only be removed by hand in the interface.** Worth knowing before the first post, not after.

**Photos cannot be attached to a wall post.** `photos.getWallUploadServer` is refused, so the
wall-album route cannot begin — **but the upload itself is not impossible, which the first version
of this table got wrong.** `photos.getMessagesUploadServer` works, the file uploads, and
`photos.saveMessagesPhoto` returns a real photo owned by the community. `wall.post` with
`attachments=photo<owner_id>_<id>` then **accepts the call, returns a `post_id`, and drops the
attachment in silence** — confirmed by the `wall_post_new` event reporting `attachments: []` and
by the page rendering text with no picture. One method being refused is not the same as the
capability being absent, and this reference said "cannot upload photos" on the strength of one
call while three upload servers were standing open.

**Reading the wall needs a different key.** A **service token** (сервисный ключ доступа), tied
to an application rather than to a person, reads public data without acting as anyone — a
better answer than a user token for anything that is only a read, and it cannot post. A full
workflow may therefore need two credentials with different scopes, and that is a design
decision rather than a workaround.

**Callback API is not one of these.** It is not an access token at all: it is a secret for
*receiving* events — VK calls you when something happens in the community. It grants no right
to call a method and does not change error 27 for a single one of them.

## Two mistakes that look like permission problems

**The sign of `owner_id`.** A community's id is positive — `123456789`. The wall's
`owner_id` is the same number **negated** — `-123456789`. Sending the positive form asks
about a *user* with that id, who does not exist, and the error that comes back talks about
access rather than about the argument. `preflight.py` flips the sign and says so out loud.

**`from_group`.** Posting to a community wall with a community token needs `from_group=1`.
Without it the call is made as the token's owner and the post either fails or lands
somewhere nobody expected.

## What is not in here

- **Callback API and Long Poll.** A different surface, with its own confirmation handshake.
- **Anything about `messages`.** The scope has its own errors and its own rules about who
  may write to whom.
- **The article API.** A claim circulated that VK has no import route for articles and that
  pasting rich text into the editor is the only way. VK's own FAQ has a page titled exactly
  that question and it will not serve its body to an unauthenticated reader, and the matching
  StackOverflow question answers 403. **The claim is unverified**, and it is recorded here as
  unverified rather than repeated as fact.
