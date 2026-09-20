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

## Which settings are in the API, and which are only on the page

**A community's settings page looks like somewhere the API cannot reach. Most of it is not.** The
temptation, after seeing a page full of fields no method is named for, is to record the whole thing
as interface-only and send the next reader to the screen for something one request already does.

Measured on 2026-09-20 with a community token, on community `241624898`:

| the page shows | in the API? | how |
|---|---|---|
| Название | **yes, writable** | `groups.edit title=…` |
| **Тематика** | **yes, writable** | `groups.edit subject=…` |
| **Сайт** | **yes, writable** | `groups.edit website=…` (read back as `site`) |
| **Телефон** | **yes, writable** | `groups.edit phone=…` |
| **Город** | **yes, writable and readable** | `groups.edit city=<id>`; read as `city {id, title}` |
| Описание, Статус | **yes, writable** | `groups.edit description=…`, `status=…` |
| Обложка | **interface only** | `groups.edit` has no cover |
| Отметки сообщества — Верификация, Подтверждённый бизнес | **interface only** | an application a human submits |
| the sidebar: Адреса, Меню, Канал, Приложения, **Журнал действий** | **interface only** | — |

**So the rule is: check `groups.edit` before opening the browser.** The page and the method overlap
more than the page suggests, and `groups.edit` is one of the calls this credential can actually
make.

### "Accepted" is not "applied"

**Every one of those parameters was accepted when written back with the value it already had**, which
is how the table above was established — an idempotent write proves a parameter is known without
changing anything. But `groups.edit title=""` was **also accepted, and the name did not change**:
VK returns success and ignores an empty value for a field that cannot be empty.

So a `groups.edit` that returns without an error proves the parameter is *known*. It does not prove
the value was written, and the only way to know is to **read it back** — which is the same rule this
file opens with, arriving from a different direction. **Never report a settings change from the
absence of an error.**

And know what is being written before writing it: `groups.getById` returns `city`, `site`,
`description`, `status`, `verified`, `activity`, `wall`, `is_closed`, `members_count` and
`age_limits`, so the current value is one call away and an idempotent write needs no guessing.

## The management sidebar, and the two pages inside it

The `Управление` panel is not one page. Its own sidebar lists:

```
Настройки          -> Кнопка действия
Разделы            -> Изменить порядок, Включены, Отключённые разделы
Комментарии
Ссылки
Адреса
Меню
Канал
Подписчики
Сообщения
Чаты
Приложения
Дополнительно
Журнал действий
```

**`Кнопка действия`** is the "write to us" button on the community page: `Показывать кнопку
действия` (a toggle), `Тип действия` (a list — `Написать на почту` is one), `Почта *` (required,
placeholder `Например, ivanov@mail.ru`), `Текст на кнопке`, and `Сохранить`. **No method sets it.**

**`Разделы`** is where each section of the community is switched on or off — `Посты`, `Видео`
(`Только видео`), `Клипы` under `Включены`; `Фото`, `Музыка`, `Обсуждения`, `Товары`,
`Комментарии`, `Файлы` under `Отключённые разделы` — with `Изменить порядок` on the same page
opening the drag-order dialog described in
[editing-a-post-in-the-interface.md](editing-a-post-in-the-interface.md).

**Several of those toggles probably ARE in the API.** `groups.edit` is documented with parameters
for the wall, photos, video, topics, docs and market sections, so the same reversal as above
applies: check the method before the page. **This is recorded as documented and not as measured**,
and the reason is the next paragraph.

### When an idempotent write stops being idempotent

**An idempotent write needs the current value, and when the current value cannot be read, writing is
not a measurement — it is a change.** The settings table above was built by reading each value with
`groups.getById` and writing it back. For the section toggles that read does not exist: the group
object does not return a flag per section, and the only statement of their state is the screen.

So they were left alone. Writing `photos=0` and then `photos=1` to discover whether the parameter
exists would have switched the community's photo section off and on again in between, and a
demonstration is not a reason to change someone's community. **The honest entry is "documented, not
measured", and it is worth more than a guess written as a table row** — which is the same charge
this skill earned earlier in the session and should not earn twice.

## The rule that came out of it

**Close the door before you test anything that writes.** A test community is a test community
only if nobody can see it; the first thing to do with a fresh one is make it private and check
from outside. This costs one call and it is the difference between a trial and a publication.

## What `groups.edit` also means

Because `groups.edit` is available and `wall.delete` is not, **the same key has wildly different
powers over different parts of the same community.** A method-by-method table is the only honest
description of a credential, and the permission mask is not it — see
[api-errors.md](api-errors.md).
