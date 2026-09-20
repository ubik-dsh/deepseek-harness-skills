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
