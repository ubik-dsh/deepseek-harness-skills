# Editing a post in the interface, because the API cannot

## The composer, and the other button with the same name

**Two controls on a community wall both say «Создать». Only one of them composes a post.**

```
Создать   beside «Видео | Клипы»   ->  Создать видео
                                       Начать трансляцию
                                       Создать плейлист

+ Создать  on the wall row         ->  Пост          <- the composer, and the default
                                       Пост в канал
                                       История
                                       Клип
                                       Видео
                                       Трансляция
                                       Статья
```

**The difference is a leading `+` and a row.** A fresh agent found the first button, concluded there
was no composer, and that conclusion reached this repository before anyone checked it — so this
section exists to stop the next reader repeating the search.

**`Статья` is the interesting one.** A VK article is the thing this family had recorded as having no
route at all, on the strength of an FAQ page that would not serve its body; the route is here, in a
menu three rows below the wall's own compose button.

**The account that can see this menu can also see `Управление` in the community sidebar**, with
`Сообщения`, `Статистика`, `Монетизация`, `Комментарии` and `События` beneath it. If those are
absent, the account is a plain member, the composer is absent too, and posting is API-only.

## Ordering the community's own sections

**`Порядок разделов` is a drag-order editor with no API at all.** It opens from the community page
and offers draggable rows — `Посты`, `Видео`, `Клипы` — with `Отмена` and `Сохранить`. The
description above the list is its own: *"Перетаскивайте блоки, чтобы изменить порядок разделов в
своём сообществе. Для некоторых блоков вы можете выбрать способ отображения."*

Two things follow. **A drag is not a click**, so `manage-windows`'s rule applies with the cursor
release as well as the press — and the dialog saves on `Сохранить`, so a drag that lands wrong is
recoverable until then. And **the order of a community's sections is a thing an operator may ask
for and no method can do**, which makes it a capability of the interface and not of the credential.

**A VK community token cannot touch any of this.**

**A community token cannot edit a post.** `wall.edit` answers error 27, and `wall.delete` and
`wall.restore` with it. So there is no API route to adding a photo to a post that already exists —
and the interface route does exist, is not documented anywhere in this family, and was learned by
watching someone do it, recorded with the `screenwatch.ps1` script that belongs to the
`learn-an-interface` skill beside this one.

The demonstration is what produced this file. The coordinates are from a 2560x1440 monitor at 100%
with the browser maximised; **re-measure them before use**, because they depend on the window, the
DPI and the scroll position — the rule `manage-windows` states and this file obeys.

## The path, measured

```
1  …  on the post            (1399, 759)     opens the post menu
2  Редактировать             (1300, 866)     third item in that menu
3  Загрузить с устройства    (1267, 590)     the editor's photo area
4  type the path, Enter                      the Windows file dialog is already focused
5  Далее                     (1469, 909)
6  Сохранить                 (1452, 909)
```

**The menu, complete, because knowing what else is on it is what keeps the wrong item from being
clicked:**

```
Статистика   Закрепить   РЕДАКТИРОВАТЬ   Отключить комментарии
Сохранить в закладках   Скопировать ссылку   Удалить
```

`Удалить` sits two items below `Редактировать`, about 130 px, with no confirmation step between
the click and the deletion that this family has seen. **Measure the menu before clicking it** — as
this skill's neighbour `manage-windows` insists, a click that lands on the wrong row is an action
on someone else's work.

## Deleting a post, and the same menu

`Удалить` is the last item of that menu, two rows below `Редактировать`. **A deletion offers an
undo** — VK shows `Пост удалён. Восстановить` where the post was, and it is the only reversible
destructive action in this interface. It does not last; treat it as a grace period, not a safety
net.

**The row above it is the one an agent is told to click.** `Скопировать ссылку` is the row that
reads the post's URL out, and `Удалить` sits about **155 px** below it — closer than the 130 px
between `Редактировать` and `Удалить` that the first version of this file warned about. Measure the
menu; never aim at a row by counting from another row.

**One item changes its own label once it has been used.** The fifth row reads `Сохранить в
закладках` on a post that is not bookmarked and **`Удалить из закладок`** on one that is. A reader
checking their menu against this table and seeing the second form has the right post, not the wrong
one.

## The dialog between «Далее» and a saved picture

**A second screen is not always what follows `Далее`.** With unsaved work in the editor VK raises
**`Сохранить черновик?`** with `Выйти без сохранения` and `Сохранить`, and the two are about
**95 px apart**. `Выйти без сохранения` discards the picture silently — no confirmation, no toast,
and the post returns to text only.

So the last step is not "click the blue button". It is: **read the dialog.** If it offers three
ways out rather than two, the one that saves is named `Сохранить` and it is on the right.

**The menu flips.** With a post near the bottom of the window it opens **upward**, and `Удалить`
then sits *above* the `…` button rather than about 250 px below it. A coordinate measured from a
menu that opened downward deletes nothing there and lands on the post instead. **Measure the menu
every time; never carry a coordinate from one opening to the next** — this is the same rule
`manage-windows` states and the same one that a mis-click here proved.

## Three things the interface does that cost a step each

- **The `…` button is about 20 px wide.** Clicking from a full-screen capture lands on the post
  body, which opens the post in a modal instead — `Escape` closes it and nothing is lost, but the
  step is. **Crop and magnify the button before clicking it**, which is how its centre was
  measured here after one miss.
- **Page Down does not scroll this page.** It scrolls its own container, not the document, so the
  key does nothing. **The mouse wheel works**, but not while the pointer is over a photo, which
  swallows it — park the cursor over the post text.
- **A confirmation screen sits between the editor and the save.** The first screen is the content,
  `Далее` moves to the second, and the second is where attachments are listed and `Сохранить`
  lives. **An attachment is removed on the second screen**, by the ✕ beside its name — not in the
  editor, where it does not appear at all.

## The whole menu, walked from top to bottom

**None of this is in the API.** `wall.edit`, `wall.delete`, `wall.getById` and `stats.get` are all
refused to a community token, so every one of these seven items is interface-only. Each was opened
on a live post and the result recorded.

| item | what it does | visible effect on the wall |
|---|---|---|
| **Статистика** | opens a panel over the wall | see the readings below |
| **Закрепить** | pins the post | a 📌 appears beside the author's name; the item becomes «Открепить» |
| **Редактировать** | opens the editor | — (the editor is above) |
| **Отключить комментарии** | closes the post to comments | the 💬 disappears from the action row: `❤ 💬 ↪` becomes `❤ ↪` |
| **Сохранить в закладках** | saves to the account's bookmarks | **nothing at all** — it is personal, and the post is unchanged |
| **Скопировать ссылку** | puts the post URL on the clipboard | none, and the clipboard is the point |
| **Удалить** | deletes the post | a `Пост удалён. Восстановить` toast where it was |

### Статистика, read off the panel

```
Статистика записи
  Просмотры записи   3        (3 / 0 - подписчиков / не подписчиков)
  Обратная связь     ❤ 0   ↪ 0   💬 0
  0 перехода в группу         0 скрытия
  0 подписки на сообщество    0 жалобы
  0 переходов по ссылке       0 скрытия всех записей
```

**This is post analytics, and no API method gives a community token anything like it** —
`stats.get` is refused and that is community statistics in any case, not a single post's. The panel
is the only way to know whether a post was seen.

### Скопировать ссылку is the interface's output channel

It put `https://vk.ru/wall-241624898_4` on the clipboard, which is **both** the canonical address of
the post **and** its numeric id — the same `post_id` that `wall.post` returned. Two uses:

- **it is the address to give a human**, in the form VK itself uses;
- **it is a way to read the id back** for a post whose id was not recorded, on a credential that
  cannot call `wall.getById`.

Together with `Ctrl+A`/`Ctrl+C` on a text field, that is a general point rather than a VK one:
**the clipboard is how an agent reads what an interface knows**, and it needs no API at all. It is
the operator's clipboard, so G7 governs it exactly as it governs a screenshot.

### The two items with no undo

`Сохранить в закладках` and `Скопировать ссылку` change nothing on the post, so there is nothing to
undo. `Закрепить` and `Отключить комментарии` **do** change it and are reversed by opening the same
menu again — the item reads «Открепить», and comments are turned back on the same way.
`Удалить` offers the toast, and that is the only undo in the interface and it does not last.

## Editing the text: replace the whole field, never position a caret

**The clipboard is the way in and the way out.** Click once in the text field, then:

```
Ctrl+A          select all of it
Ctrl+C          copy        -> Get-Clipboard  gives the agent the text as a value
edit the value  in a variable, with the tools the agent already has
Set-Clipboard   write it back
Ctrl+A, Ctrl+V  paste it over the whole field
```

The first attempt at adding a line of text did it the obvious way — click where the line should go,
press Ctrl+Home, type. It **split a word in the middle**, because a click lands where the pixels
say and not where the sentence does. Recovering cost two undos and a second attempt.

**Replacing the field does three things that positioning a caret cannot.** It makes the edit
idempotent, so running it twice is the same as running it once. It repairs damage already done,
because the old content is not edited — it is discarded. And it removes the need to know where the
insertion point is, which is the part no screenshot can tell you.

**It also turns the interface into something the agent can READ.** `Get-Clipboard` returned the
post's text as a string, which no API call with this token can do — `wall.get` is refused. Copying
a field out and editing it in a variable is the general form of that trick, and it applies to any
interface that will let you select text.

**The clipboard is the operator's.** Reading and writing it is covered by G7 in `route-a-task` for
the same reason a screenshot is: it is a view of what the operator was doing. Take it when the
operator asked for the work; put back what you took if the work did not need to change it.

## What this editor does to a pasted text

A blank line between the new first line and the body **does not survive the save** — VK renders the
two lines adjacent. Nothing is lost but a paragraph break, and the text reads correctly either way;
it is recorded so that the next reader does not go looking for a bug in their paste.

## What the editor does that the API does not
- **it takes a photo.** The dashed area accepts a file, the file uploads, a thumbnail appears, and
  `Сохранить` puts a **full-width image** on the post. This is the one thing no API route with a
  community token can do: `photos.getWallUploadServer` and `photos.saveWallPhoto` are both refused,
  and the messages-album upload is dropped at the wall.
- **it shows the document attachment separately**, as a `name.png — NN КБ` row with an X beside it.
  A document attached by API and a photo added in the interface are different objects and both
  can sit on the same post.
- **it is the only place a mistake is still cheap.** After `Сохранить` the change is live and the
  API cannot undo it.

## What it costs, said plainly

The route goes through **the browser session, acting as the person**, not through the scoped
community key. That is a different authority and it should be named when it is used: the token
can only touch what the community owns, and this can touch anything the signed-in account can.

It is the right route when the operator asks for something no credential can do, on the operator's
own machine, with the operator watching. It is the wrong route for a skill to reach for when the
API would have done — and a skill that ships it as a default has quietly replaced a scoped
credential with a person's whole account.

## Verifying it worked

**The API cannot read the wall**, so there is one witness and it is the screen: the post renders
with the image, and the human confirms it. The event stream does not help here — an edit is not a
new post, and VK offers no `wall_post_edit` event to subscribe to. **Do not claim an edit succeeded
without looking.**
