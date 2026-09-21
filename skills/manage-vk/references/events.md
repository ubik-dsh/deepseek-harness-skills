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

## The page and the API agree, once the page is read properly

The comparison was completed at native resolution across every section, and **there are no
disagreements at all**:

| section | the page | `groups.getLongPollSettings` |
|---|---|---|
| Сообщения, Фотографии, Аудио, Видео, Комментарии, Обсуждения | all ticked | all `1` |
| Записи на стене, including «Удаление отложенной записи из расписания» | all ticked | all `1` |
| **Товары** | all clear | all `0` |
| **Пользователи** | all four ticked | all `1` |
| **Донаты** | all seven clear | all `0` |
| **Прочие** | only «Изменение настроек» | `group_change_settings 1`, the rest `0` |

**The API also returns flags the interface never shows** — 62 against roughly 48 rows —
including `message_reaction_event`, `lead_forms_new`, `music_subscription_update`,
`inapp_order_*` and `market_order_*`. So the read-back is not a mirror of the page; it is a
superset, and it is the one to trust.

So the capability set of a community key is stranger than the mask suggests: **it cannot read the
wall it can post to, and it can subscribe to everything that happens on that wall.**

## Why that matters: the event stream is the read path

`wall.get` is refused. But a subscribed community receives wall activity as events, and the
flags VK actually reports are these — read off `groups.getLongPollSettings`, not off a
documentation page:

```
wall_post_new              a post appeared
wall_repost                a repost appeared
wall_reply_new             a comment was added
wall_reply_edit            a comment was edited
wall_reply_delete          a comment was removed
wall_reply_restore         a comment was restored
wall_schedule_post_new     a post was scheduled
wall_schedule_post_delete  a scheduled post was removed
like_add / like_remove     a like arrived or was taken back
```

**There is no `wall_post_edit` and no `wall_post_delete` flag.** VK does not offer them, so an
edit to, or the removal of, an *already published* post is not delivered. The first version of
this file listed both, because they seemed obviously necessary — which is exactly the mistake
this reference exists to warn about, made in the reference itself. The list above is the one VK
returned.

**`wall_schedule_post_delete` is the one that closes a loop this skill could not close any other
way.** A community token cannot delete a post, so the first write probe left one behind with a
human told to remove it by hand — and nothing could confirm that the human did. This event is
that confirmation, delivered to a key that cannot read the wall.

### The first real post, observed

Measured, on a live community, minutes after the first post was published with this credential:

```
EVENT wall_post_new
  {"inner_type": "wall_wallpost", "type": "post", "from_id": -123456789,
   "date": 1789909506, "created_by": 4341552, "can_edit": 1, "can_delete": 1,
   "comments": {"count": 0}, "attachments": [], "marked_as_ads": 0,
   "post_author_data": {"author": 4341552}}
```

**A token that cannot call `wall.get` learned in real time that a post had appeared, and was
handed its content.** That is the reading gap answered, and it is worth being precise about what
it does and does not replace: this arrived because a subscription was already open and the event
happened while it was. Nothing in it can be replayed, and it says nothing about the wall as it was
before.

### `can_delete` does not mean this token can delete

The event says `can_delete: 1` and `can_edit: 1`. **That describes the post, not the credential.**
These fields are about the rights a *human administrator* has over the post; `wall.delete`,
`wall.edit` and `wall.restore` all answer error 27 for a community token, immediately before and
after this event arrived.

**An agent that reads `can_delete: 1` and calls `wall.delete` gets the same refusal it would have
got without the event** — and one more reason to be sure before posting, because the field reads
like a permission it does not have. Where a returned value describes someone else's rights, say
whose.

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
VK on 37 of 48 flags, and the disagreement was written down as *"either the reading is wrong or
the setting had not been saved"* — leaving the reader to wonder which.

**It was the reading, and that was established by looking properly.** The screen was captured
directly at native resolution and cropped into 1650-pixel slices, and at that size every
checkbox in the visible region is ticked — which is exactly what `groups.getLongPollSettings`
had said all along. The page and the API agree. The 37 disagreements were an artefact of a
277-pixel-wide image, and the honest move was available the whole time: **the API had already
answered, and it should have been believed instead of doubted.**

Two lessons, and the second is the one worth keeping:

- **A screenshot is a claim about a setting. `groups.getLongPollSettings` is the setting.**
- **When a cheap authoritative measurement exists, do not report a doubt about a person's
  configuration before checking it.** "Either I misread or you did not save" is a real
  possibility and a bad thing to publish, because one of the two readings accuses the reader of
  a mistake the tool can rule out in one call.

The labels on the live page ("Действие с сообщением") also differ from the earlier screenshot's
("Удаление сообщения"), so the first image was a different version of the page entirely — which
is worth knowing before treating any screenshot as a record of anything.

## The interface has an audit log, and this credential has no other one

**Журнал действий at ?act=event_log records what the community's own administrators and the API key
did** - section headings, the actor, the action in a sentence and a timestamp, newest first, with
filters for action type, role and range. It logs Работа с API, Изменение настроек and Работа со
стеной, it lists the Long Poll event toggles, and **it records the token's own creation**
(создал ключ доступа vk1.********8_WA).

**This matters more here than anywhere else in the skill, because a community token cannot read its own
writes back.** wall.get is refused, wall.delete is refused, and a post that was dropped an
attachment returns the same post_id as one that was not. **The audit log is the only trail of what
this key has done** - and it is on a page, not in a method: groups.getEvents and groups.getEventLog
both answer **err 27**, so a community token cannot read it either.

**So read it by hand when a write matters**, and say in the record that you did.
