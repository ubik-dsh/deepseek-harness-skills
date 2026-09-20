# Community settings, and how to change one safely

`groups.edit` **is callable with a community token** — measured, and surprising given that six
of the eight `wall.*` methods are not. It is the only write in this skill that is reversible and
verifiable, which makes it the best place to learn how a VK write behaves.

## The community type, and which value hides what

```
access 0   open      everything visible to anyone, appears in search
access 1   closed    content visible to members only, still listed
access 2   private   not in search, invite only, the name is hidden too
```

`groups.getById` returns it as **`is_closed`** with the same numbering.

**Reading the state back is not optional.** It is the only evidence that a change landed, since
`groups.edit` returns nothing useful — an accepted call and an ignored one look identical from
the reply.

## The sequence, and it is the same one any write should follow

```bash
python scripts/preflight.py --env-file "$DSH_HOME/vk.env"     # read the state first
# change one thing
# read it back
```

Measured on the test community, in full:

```
before   is_closed 0      (open)
groups.edit access=2      accepted
after    is_closed 2      (private)
```

## Verify a visibility change from outside, not with the same key

The key that made the change is the worst possible witness that the change worked — it has
every reason to report what it was told, and `groups.edit` says nothing at all on success.

The community widget is public, needs no token, and renders server-side:

```
https://vk.com/widget_community.php?app=0&width=300&_ver=1&gid=<the numeric id>&mode=0
```

Before the change it returned the community's name and its follower count. After it returned:

```
[Private community](https://vk.com/club241624898)
This is a private community
```

**That is independent evidence.** The name and the member count were gone, which is what
`access 2` promises and no API reply had confirmed.

## The rule that came out of it

**Close the door before you test anything that writes.** A test community is a test community
only if nobody can see it; the first thing to do with a fresh one is make it private and check
from outside. This costs one call and it is the difference between a trial and a publication.

## What `groups.edit` also means

Because `groups.edit` is available and `wall.delete` is not, **the same key has wildly different
powers over different parts of the same community.** A method-by-method table is the only honest
description of a credential, and the permission mask is not it — see
[api-errors.md](api-errors.md).
