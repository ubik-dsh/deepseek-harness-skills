# VK errors, and which of them are measured

**Half of this file is measured and half is received, and the two are marked.** The
received half came from reading the source of four VK skills that were put through a
hearing and all rejected; their code is evidence of what they expected, not of what VK does.

## The shape that costs the most

```bash
curl 'https://api.vk.com/method/groups.getById?group_id=241624898&v=5.199'
```

```
HTTP 200
{"error":{"error_code":15,"error_msg":"Access denied: token required",
          "request_params":[{"key":"group_id","value":"241624898"},{"key":"v","value":"5.199"}]}}
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
| 15 | `Access denied: token required` | **measured** | the token is absent or empty — set `VK_COMMUNITY_TOKEN` |
| 6 | too many requests per second | received | retryable. Wait longer and send fewer. Never retry in a tight loop |
| 9 | too many requests per day | received | not retryable today. The quota is gone until it resets |
| 5 | `User authorization failed` | received | the token was refused. Check it is the **community** key and that the API section is enabled for the group. *Some sources attribute this to IP binding on tokens obtained through the implicit flow; that was not verified here and is not relied on* |
| 14 | captcha required | received | interactive. A community token normally avoids it; a user token hammering the API does not |
| 27 | `group authorization failed` | received | usually a missing scope, or the group key was revoked or regenerated |
| 100 | one of the parameters is wrong | received | read `error_msg` — it names the parameter. Usually `owner_id` with the wrong sign |
| 214 | the wall is not writable | received | the wall is disabled, or this token may not post to it |

**Codes that are worth retrying: 6, and a transport failure.** Everything else is either a
fact about the token or a fact about the request, and asking again produces the same answer
more slowly.

## Two mistakes that look like permission problems

**The sign of `owner_id`.** A community's id is positive — `241624898`. The wall's
`owner_id` is the same number **negated** — `-241624898`. Sending the positive form asks
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
