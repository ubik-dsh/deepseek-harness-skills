# Editing a post in the interface, because the API cannot

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
