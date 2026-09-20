# Events are not permissions, and they are the read path a community token lacks

## Three different things on one screen

The VK community settings page has three tabs, and they answer three unrelated questions. They
look alike and they are not.

| tab | the question it answers |
|---|---|
| **Ключи доступа** | which tokens exist, and what each may be used for |
| **Callback API / Long Poll API → Настройки** | how events are *delivered* — a public HTTPS URL and a secret for Callback, an API version for Long Poll |
| **Типы событий** | which events VK will **send you** |

**A tick in "Типы событий" grants no permission to call anything.** It cannot make `wall.get`
work, cannot make `photos.getWallUploadServer` work, and does not change error 27 for a single
method. Permissions live on the token; this screen is a subscription list.

The confusion is worth naming because it is expensive in one direction only: someone who believes
the ticks are permissions will conclude the key is broken when a method is refused, and go looking
for a permission that was never the problem.

## What was measured

**A community token can reach the event stream**, even though it cannot read the wall:

| method | result |
|---|---|
| `groups.getLongPollServer` | **ok** — a server and a key are issued |
| `groups.getLongPollSettings` | **ok** — the whole subscription reads back, 62 flags |
| `groups.getCallbackConfirmationCode` | **ok** |
| `messages.getLongPollServer` | **ok** — a Bots Long Poll server |
| `groups.getCallbackSettings` | error 100 — `server_id` is a required parameter, not a permission fault |

And the transport reports itself: `api_version "5.199"`, `is_enabled True`.

So the capability set of a community key is stranger than the mask suggests: **it cannot read the
wall it can post to, and it can subscribe to everything that happens on that wall.**

## Why that matters: the event stream is the read path

`wall.get` is refused. But a subscribed community receives, with content:

```
wall_post_new              a post appeared
wall_post_edit             a post changed
wall_post_delete           a post was removed
wall_schedule_post_new     a post was scheduled
wall_schedule_post_delete  a scheduled post was removed
wall_repost, like_add, like_remove
```

**The last one closes a loop this skill could not close any other way.** A community token cannot
delete a post, so the first write probe left one behind with a human told to remove it by hand —
and nothing could confirm that the human did. `wall_schedule_post_delete` is that confirmation,
delivered as an event, to a key that cannot read the wall.

### And the limit of it, which matters as much

**Events are not history.** The stream carries what happens *while you are listening*. It cannot
tell you what is on the wall now, what was there yesterday, or whether the post you are about to
publish duplicates an older one. It is a read path for the future, not for the past.

Anyone who reads "you can subscribe to wall events" as "you can read the wall" has replaced one
wrong belief with another. The wall as it stands still needs a service token.

## Long Poll or Callback, for this shape of work

**Long Poll needs no server of your own.** You ask for a server and a key, hold a connection, and
read batches. Nothing has to be reachable from the internet.

**Callback API needs a public HTTPS endpoint** with a valid certificate, plus a confirmation code
handshake. It is the right choice when the receiver already exists and is always up.

For an agent driving a community from a desktop, **Long Poll is the only one that works**, and the
choice is not a preference.

## The lesson about screenshots

This file exists partly because a screenshot of the event list was read by eye and disagreed with
VK on 37 of 48 flags — and there was no way to tell whether the reading was wrong or the setting
had not been saved yet.

**A screenshot is a claim about a setting. `groups.getLongPollSettings` is the setting.** Read it
back from the API before acting on what a picture appears to show, and save the picture for
explaining rather than for deciding.
