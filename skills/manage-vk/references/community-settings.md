# Community settings, and how to change one safely

**The community id in this file is a placeholder.** Every measurement below was taken on a real test
community whose id is written here as `123456789`. The numbers, the method and the dates are real; the
operator's own community is not published. Every example stays correct for any community once the id is
substituted, because the sign of `owner_id`, the URL shapes, the permissions and the error codes do not
depend on which community it is.


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
[Private community](https://vk.com/club123456789)
This is a private community
```

**That is independent evidence.** The name and the member count were gone, which is what
`access 2` promises and no API reply had confirmed.

## Which settings are in the API, and which are only on the page

**A community's settings page looks like somewhere the API cannot reach. Most of it is not.** The
temptation, after seeing a page full of fields no method is named for, is to record the whole thing
as interface-only and send the next reader to the screen for something one request already does.

Measured on 2026-09-20 with a community token, on community `123456789`:

**READ THE TABLE WITH ITS CAVEAT.** Everything below rests on `groups.edit` returning without an error
when each value was written back — and an independent agent then measured that **`groups.edit` ignores
a parameter it does not know and returns `1` anyway**. So the table shows what VK **documents** and what
this key **may call**; it does **not** prove that any named parameter is written. See
[capabilities.md](capabilities.md), *"err 100 does not work on groups.edit"*. Measuring one properly
means changing a harmless field and reading it back, which is a change rather than a probe.

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
| the sidebar: Адреса, Меню, Канал, **Приложения** | **interface only** | — |
| the sidebar: **Журнал действий** | **two methods exist, refused** | `groups.getEvents`, `groups.getEventLog` — both `err 27` |

**The `Журнал действий` row said "interface only" and that was wrong** — an independent agent measured
two methods for it, and it is exactly the error this file warns about forty lines further down:
*"this key cannot"* written as *"the API cannot"*. The row is corrected above.

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

## The community page's own controls

**`Сообщение` sits beside `Ещё`, and `Ещё` opens a menu with six things in it.** Recorded from a
demonstration on 2026-09-20:

```
[ Избранное ]   [ Уведомления ]      <- two tabs across the top of the dropdown
+ Пригласить друзей
  Разрешить сообщения
+ Добавить в левое меню
  Отписаться
```

**`Добавить в левое меню` is the community adding itself to the visitor's own navigation** — it is
the operator's menu, not the community's, which is worth knowing before looking for it under the
community's settings. **`Разрешить сообщения` is a per-visitor toggle**: it decides whether this
account may be written to from the community, and it is nobody else's setting.

**None of it is in the API**, and this is the menu a person means when they say "the community's
menu" on the community page — as opposed to `settings/menu`, which is a different page with a
different subject, described further down.

## Reading a demonstration, and knowing which screen it was on

**A recording made across two monitors can be split by the cursor log alone, before any frame is
opened.** In a two-monitor session the boundary is a number: **any pause with `x` beyond the primary
monitor's width is not a step in the demonstration.**

Measured on a 4480x1440 desktop whose primary monitor is 2568 wide: of 43 pauses in a three-minute
recording, **most sat at `x` between 3000 and 4150** — the harness window on the second monitor — and
the longest of them, 8.6 seconds at `3142,912`, was the operator reading the message that had just
been written to them. **The demonstration itself was the handful of pauses under 2568.**

**A long pause on the other screen is the operator reading, thinking or typing, not the interface
being driven.** Opening that frame confirms it in one look; skipping it saves one. **The coordinates
are cheaper than the pictures, and they are already in the file.**

### `Порядок в меню` — the menu's reorder dialog

**`Меню` (`settings/menu`) has its own order dialog, and it is a drag list.** Recorded from a
demonstration on 2026-09-20:

```
Порядок в меню
  Перетаскивайте пункты, чтобы изменить их порядок в меню
  ≡ [ thumbnail ]  <item name>
  ≡ [ thumbnail ]  <item name>
  [ Сохранить ]
```

Each row carries a **drag handle**, a **thumbnail** and the item's own name, which is user data and
not a label from VK. **The row being held is drawn with a grey background**, which is the only
evidence in a screenshot that a drag is in progress — position alone does not show it, and neither
does a cursor log without button state.

**What a skill should carry here is the shape, not a drop point.** Where to drop depends on what is
being reordered, so a coordinate is worthless: find the row by its **name**, press its handle, move in
steps, **check that the row under the pointer shows the insertion state**, release, and verify the
order changed. The grey background is that state, and reading it is what makes the drop verified
rather than hoped for — see `learn-an-interface`'s *record the logic, not the coordinates*.

**`Порядок разделов` on the community page and `Порядок в меню` here are two different drag lists**
with the same interaction and different subjects.

**AND THE DIALOG AGREEING WITH ITSELF PROVES NOTHING.** This file said *"a wrong drag is recoverable up
to `Сохранить` and not after"*, which is true and hides the failure that matters. An independent agent
dragged, **saw the accept state, released, watched the dialog keep the new order, clicked `Сохранить` —
and the change did not persist.** A second attempt in the opposite direction did. It never established
why, and neither can this file. **Only a reload proves it**, and a new tab proves it harder:
`sections/menu` re-read after a fresh load is the test, and the dialog is not evidence of anything.

The page itself carries `Показывать блоки в сообществе` as a toggle and `Добавить элемент меню` as
the way to add a row. **`groups.getMenu` does not exist** — `err 3` — and `groups.addLink`,
`groups.editLink` and `groups.deleteLink` all want a user token, so with a community token this page
has no API in any direction.

### `Журнал действий` — the community's audit log, and the key's own trail

```
?act=event_log
```

**Newest first, grouped by day, with three filters** — action type (`Все действия`), role (`Все роли`)
and range (`Всё время`) — plus a list/grid toggle. Each row is a section heading, an actor link, the
action in a sentence, a timestamp and an avatar. Sections seen include `Работа с API`,
`Изменение настроек` and `Работа со стеной`.

**It records the token's own history** — the entry for its creation reads `создал ключ доступа
vk1.********8_WA` — and it lists the Long Poll event toggles. **This is the closest thing a community
token has to an audit trail of itself**, in a skill whose central warning is that a write cannot be
undone or read back; `events.md` now points here.

**API: two methods exist and are refused.** `groups.getEvents` and `groups.getEventLog` both answer
**err 27**. Every other plausible name — `groups.getLog`, `getAuditLog`, `getActionLog`, `getHistory`,
`getModerationLog`, `getActions` — answers **err 3, absent**. That the 27s mean anything rests on the
control: a nonsense name must answer 3 first. **Which of the two serves this page is inference from the
names and is not measured**, because no second credential was available to try them.

### `Приложения` — a catalogue with no API at all

```
?act=apps
```

A catalogue of community mini-apps: `Приложения сообществ`, `Приложения для любых задач` with
`Перейти в каталог`, then installable apps each with a `Добавить` button — VK Донат, VK Билеты,
ProSender, ChatRex, CalcPro. Its own sidebar tip says **«Вы можете менять порядок установленных
приложений, перетаскивая их курсором»** — the same drag interaction as the menu, applied to apps.

**The `apps.*` namespace exists and is refused** — `apps.get`, `getCatalog`, `getLeaderboard`,
`getScore`, `getFriendsList`, `deleteAppRequests`, `sendRequest` all answer **err 27**. But **every
community-side name answers err 3**: `groups.getApps`, `getInstalledApps`, `getGroupApps`,
`getAppPermissions`, `editApp`, `addApp`, `getMarketApps` **do not exist**.

**So installing, removing or reordering a community's apps has no API at all** — which is a stronger
statement than a refusal, and the two are worth telling apart. The reorder is interface-only by
construction, not by permission.

## The whole panel's URL map, read without a single click

**The browser's status bar shows a link's target while the pointer is over it, so every row's URL
can be read by hovering — nothing is opened and there is no state to put back.** The whole map
below came from fourteen hovers and one picture, where clicking through would have been fourteen
navigations:

```
1  Настройки        https://vk.ru/club123456789?act=edit
2  Кнопка действия  https://vk.ru/club123456789/settings/cta
3  Разделы          https://vk.ru/club123456789/settings/sections
4  Комментарии      https://vk.ru/club123456789?act=activity
5  Ссылки           https://vk.ru/club123456789/settings/links
6  Адреса           https://vk.ru/club123456789?act=addresses
7  Меню             https://vk.ru/club123456789/settings/menu
8  Канал            https://vk.ru/club123456789/settings/channel
9  Подписчики       https://vk.ru/club123456789/settings/subscribers
10 Сообщения        https://vk.ru/club123456789/settings/messages
11 Чаты             https://vk.ru/club123456789?act=chats
12 Приложения       https://vk.ru/club123456789?act=apps
13 Дополнительно    https://vk.ru/club123456789/settings/extras
14 Журнал действий  https://vk.ru/club123456789?act=event_log
```

**Fourteen rows, fourteen distinct addresses.** Three shapes exist — `?act=<name>`, `settings/<name>`,
and `settings/extras` as a page of its own — which is why the map could not be guessed and had to be
read.

### Адреса — `?act=addresses`

```
Адреса и время работы
  Адреса:  Выключены
           Добавьте адреса и время работы вашей организации.
           Данные будут отображены в блоке информации в вашем сообществе.
[ Сохранить ]
```

An address and opening hours for the organisation, shown in the community's information block once
there is one. `groups.getAddresses` answers **error 27** — present, wants a user token — **but the
writes are callable by this credential**: `groups.addAddress`, `groups.editAddress` and
`groups.deleteAddress` all answer **err 100**, which means the call reached the method and was
allowed and only the arguments were bad. **So addresses can be written and not read**, and the first
version of this entry got that wrong by probing the read first. See the method table in
[capabilities.md](capabilities.md).

### A loading error is transient, and it was nearly written down as a property

**The deep links work, including for `?act=` pages.** Both shapes navigate directly; the map above is
usable as a map.

It was almost not recorded that way. The **first** direct navigation to `?act=addresses` returned
`Ошибка загрузки` / *"Попробуйте обновить страницу"* with a reload button, and clicking the sidebar
row loaded the page immediately — which looked exactly like a finding: *"the app's own navigation
works where a deep link does not."* A second direct navigation to the same URL loaded it normally.
**The failure was transient.**

**This is the majority rule earning its keep inside the hour**, and in its single-reading form: a
reading that is odd against everything around it is a miss until it is repeated. Here there was one
failure among otherwise-working navigations, the page's own error text said *try refreshing*, and
**five minutes of re-measuring replaced a wrong sentence with a right one.**

VK's SPA does fail to load a section now and then and offers a reload. **Retry once before
concluding anything about a URL**, and prefer the app's own navigation when a click is available
anyway — not because deep links are unreliable, but because a retry costs less than a wrong rule.

### Each section has its own settings dialog, and they differ

**A row with a chevron on the `Разделы` page opens `Настройки раздела` for that section — and the
dialog's contents depend on which section it is.** Recorded from a demonstration of six of them:

```
Посты       Кто может публиковать посты
            Кто может предлагать посты
            Запретить делать посты
Музыка      Показывать в разделе        Только треки  |  Треки и плейлисты
            Кто может добавлять         Все подписчики | Администраторы и редакторы
Обсуждения  Кто может создавать темы    Все подписчики | Администраторы и редакторы
Файлы       Кто может добавлять файлы   Все подписчики | Администраторы и редакторы
Материалы   Кто может добавлять файлы   Все подписчики | Администраторы и редакторы
Фото        a single on/off toggle and nothing else
```

**So the dialog's height and its field count change from section to section**, which is a reason to
re-measure after every one of them rather than to carry a coordinate across.

**`Выйти без сохранения?` is a real confirmation.** Leaving a section's settings with unsaved changes
raises it. It is the second place in this interface where the destructive option and the safe one sit
beside each other, and like `Сохранить черновик?` on the post editor, the reading is the point.

**Rows that carry a toggle** — `Клипы`, `Статьи`, `Моменты`, `Товары`, `Мероприятия`, `Чаты`,
`Контакты` — are switched in place, with no dialog at all.

### A demonstration recorded around the pointer cannot be compared without `cursor.csv`

**Three measurement errors in one analysis, all from forgetting that the frames move.** The operator
reported that the interface shifted after a toggle. The recording is 889 frames cropped around the
pointer, so:

- **a fixed box means a different part of the screen in every frame.** Comparing raw frames reported
  that the region was byte-identical for three minutes — impossible while a page is being driven, and
  the zeroes were the only clue. The mapping is `frame = screen - (cursor - size/2)`;
- **comparing two frames by eye compares two different origins.** A "69-pixel shift" of the sidebar
  came from reading frame coordinates instead of screen ones, and vanished when the same screen
  column was stacked from ten frames;
- **a modal's dimming dominates a difference.** Every large change found this way was a dialog
  opening or closing, which darkens the whole region and swamps any real movement.

**The way to see a shift is to stack the same SCREEN column from many frames side by side, with a
reference line at one fixed screen y.** Ten frames minutes apart, mapped back through `cursor.csv`,
put the same text at the same height — and the red line crossing the same words in every column is
the answer, in one look.

**And the honest residue:** the shift the operator saw was **not reproduced**. The sidebar was stable,
the section list was stable, and no measurement found movement. It is recorded as unreproduced rather
than as a finding — which is the rule this file already carries, applied to someone else's report
instead of to my own.

### The two rules this map cost, and they are both about trusting one pass

**The row is measured, not counted.** The panel's rows are about **38 px apart** and the first pass
guessed their positions instead of measuring them, landing up to **22 px out** — more than half a
row. `Чаты` fell into a gap and its status bar stayed **empty**, which was written up as *"this row
is not a link"*. And `Журнал действий`, twenty-two pixels low, landed on `Дополнительно`, which was
written up as *"two rows share a URL"*. **Both sentences were in this file before either was
checked**, and both were wrong: `Чаты` has an address, and every row has its own.

**A surprising finding from one pass is a reason to re-measure, not a sentence to publish.** Both
wrong entries had the shape of a discovery — an exception to a rule is exactly what a reader
remembers — and an exception produced by a bad measurement is indistinguishable from a real one
until someone measures again. The operator caught this one by saying the row exists; nothing in the
file would have.

**And the sharper form of the same rule, which is checkable rather than a matter of judgement: an
empty or odd reading against a unanimous majority is a miss, not a datum.** Thirteen rows gave
addresses and the fourteenth gave none — a panel whose every row is a link does not have one row that
is not a link, it has one row the pointer missed. *If nine out of ten have it, the tenth is probably
"not found" rather than "not there".*

**The two rules are a pair, not a hierarchy.** *Re-measure when a finding surprises you* needs no
majority and so reaches a single reading, and pays for that by needing the reader to notice surprise;
*an anomaly against a majority is a miss* fires with no judgement at all but needs the majority to
exist. Neither reaches the third case, **no majority and nothing surprising** — which is where
`wall.post` lives, returning the same `post_id` twice, once with a picture and once without. That
case is caught by *verify the effect, never the reply*, and by nothing else.

**A blank is the dangerous failure mode precisely because it looks like an answer** — an error would
have been caught, a blank was read as a fact and written down.

The measured positions, for the next reader, with the page scrolled as it was here:

```
Настройки 227   Кнопка действия 265   Разделы 304   Комментарии 342
Ссылки 379      Адреса 418            Меню 456      Канал 494
Подписчики 530  Сообщения 569         Чаты 606      Приложения 644
Дополнительно 684                     Журнал действий 722
```

**Re-measure them anyway** — they depend on the scroll position, and this list is the thing that was
wrong the first time.

**How to read a status bar that is one line tall.** Hover a row, capture the window, crop the strip
at the bottom-left, and **stack the fourteen strips into one image with the row names drawn beside
them**. Fourteen pictures become one, and a single look gives the whole panel. The text sits about
28 px above the window's bottom edge on a 2568x1400 window.

**And the script that does it had to be ASCII.** Windows PowerShell 5.1 reads a `.ps1` with no
byte-order mark as CP1251, so the Russian row names in the first version did not parse at all —
`Unexpected token` on a well-formed line. The labels were transliterated; the row *order* is the
panel's own, so nothing was lost. The trap is written up in `manage-windows`.

## The management pages have URLs, and there are two shapes of them

**Do not click through the panel — read the address after one click, then navigate directly.**
Measured on 2026-09-20:

```
Разделы       https://vk.ru/club123456789/settings/sections
Комментарии   https://vk.ru/club123456789?act=activity
settings/comments                            -> "Такой страницы нет"
```

**Two shapes, and which page uses which cannot be guessed.** `Разделы` is a `settings/<name>` page
and `Комментарии` is an `?act=<name>` page; `settings/comments` looks like the obvious guess for the
second and **is not a page at all**. A wrong management URL answers `Такой страницы нет` and
**collapses the sidebar to its top-level items only** — `Настройки`, `Подписчики`, `Сообщения`,
`Чаты`, `Приложения`, `Дополнительно`, `Журнал действий` — so a reader who guessed wrongly and did
not look at the sidebar could conclude that most of the panel does not exist.

**Read the address bar, and the clipboard is how to read it.** Yandex Browser shows only `vk.ru` for
a trusted page and hides the rest of the URL, so a screenshot of the address bar is not a reading.
Click the field, `Ctrl+A`, `Ctrl+C`, `Get-Clipboard` — the same trick that reads a post's URL out of
`Скопировать ссылку`.

## Comments, and the two kinds of control on the sections page

**`Комментарии` (`?act=activity`)** is two things on one page: the community's comment settings, and
the moderation view of its comments.

```
Обратная связь:   [x] Комментарии включены
Настройки:        [ ] Запретить комментарии от сообществ   (?)
                  [ ] Фильтр нецензурных выражений
                  [ ] Фильтр враждебных высказываний        Beta
                  [ ] Фильтр по ключевым словам
[ Сохранить ]
Все комментарии 0   |   Удалённые фильтром 0
Здесь будут выводиться все комментарии в сообществе
```

**`Ссылки`** is one toggle and a list: `Показывать в сообществе`, described as *"Ссылки будут видны
в разделе «Подробная информация»"*, over an empty `Вы можете добавить в сообщество ссылки на
внутренние страницы ВКонтакте или на внешние сайты`.

**On the sections page, a control's shape says what it can do.** Seven rows carry a **bare toggle** —
`Клипы`, `Статьи`, `Моменты`, `Товары`, `Мероприятия`, `Чаты`, `Контакты` — and eight carry a
**state word and a chevron** — `Посты` *Включены*, `Видео` *Только видео*, `Фото` *Отключено*,
`Музыка`, `Обсуждения`, `Файлы`, `Услуги`, `Материалы`. **A chevron means the row opens sub-settings
and a bare toggle means on or off and nothing else**, which is worth knowing before clicking a row
expecting a page and getting a switch. The full list is fifteen rows: three under `Включены`,
twelve under `Отключённые разделы`.

## A method that does not exist and a method this key may not call

Two error codes that a reader will meet while checking whether a page has an API, and they mean
different things:

```
err 3    Unknown method passed                       the method does not exist
err 27   not available with group auth               the method EXISTS, this credential may not
```

Measured with the community token:

```
groups.getSettings          err 27   exists, needs a user token
groups.getAddresses         err 27
groups.getRequests          err 27
groups.getInvitedUsers      err 27
groups.getLongPollSettings  OK       returns the event subscription list
groups.getMenu              err  3   no such method
```

**So the boundary is not "API against interface". It is "which credential".** `groups.getSettings`
would answer a user token; the community token is deliberately narrow, and a management page that
has no call *for this key* may have one for another. Saying "the API cannot do this" when the truth
is "this key cannot" sends the next reader to the screen for something a different token would do in
one request — and it is the same mistake as reading one refused method as an absent capability.

## The rule that came out of it

**Close the door before you test anything that writes.** A test community is a test community
only if nobody can see it; the first thing to do with a fresh one is make it private and check
from outside. This costs one call and it is the difference between a trial and a publication.

## What `groups.edit` also means

Because `groups.edit` is available and `wall.delete` is not, **the same key has wildly different
powers over different parts of the same community.** A method-by-method table is the only honest
description of a credential, and the permission mask is not it — see
[api-errors.md](api-errors.md).
