# The family, as a graph

**Every edge carries how it was established, and none of those marks was written by hand — each is computed from the shape of the text.**

| mark | what it means |
|---|---|
| `EXTRACTED` | a written link that resolves. The author declared it |
| `INFERRED` | a name mentioned in prose with no link. Named, not linked |
| `AMBIGUOUS` | a mention that matches more than one file |
| `DANGLING` | a link whose target is not there |
| `ORPHAN` | nothing links to it |

103 nodes.

## What wants attention

**Invisible — neither linked nor named anywhere.** A reader cannot find these:

- [skills/check-hardware/assets/diagram.drawio](../../skills/check-hardware/assets/diagram.drawio)
- [skills/create-a-skill/assets/diagram.drawio](../../skills/create-a-skill/assets/diagram.drawio)
- [skills/create-a-skill/scripts/check-external-links.py](../../skills/create-a-skill/scripts/check-external-links.py)
- [skills/design-a-reward/assets/diagram.drawio](../../skills/design-a-reward/assets/diagram.drawio)
- [skills/draw-a-diagram/assets/diagram.drawio](../../skills/draw-a-diagram/assets/diagram.drawio)
- [skills/find-a-skill/assets/diagram.drawio](../../skills/find-a-skill/assets/diagram.drawio)
- [skills/judge-a-skill/assets/diagram.drawio](../../skills/judge-a-skill/assets/diagram.drawio)
- [skills/judge-a-skill/scripts/draw-the-hearing.py](../../skills/judge-a-skill/scripts/draw-the-hearing.py)
- [skills/learn-an-interface/assets/diagram.drawio](../../skills/learn-an-interface/assets/diagram.drawio)
- [skills/manage-vk/assets/diagram.drawio](../../skills/manage-vk/assets/diagram.drawio)
- [skills/manage-vk/scripts/draw-the-vk-flow.py](../../skills/manage-vk/scripts/draw-the-vk-flow.py)
- [skills/manage-windows/assets/diagram.drawio](../../skills/manage-windows/assets/diagram.drawio)
- [skills/route-a-task/assets/diagram.drawio](../../skills/route-a-task/assets/diagram.drawio)
- [skills/route-a-task/scripts/draw-the-gates.py](../../skills/route-a-task/scripts/draw-the-gates.py)

**Named but not linked — 43 file(s).** Reachable by someone who reads the page that names them, which is a weak sign rather than no sign:

- [skills/check-a-deck/scripts/deck_gates.py](../../skills/check-a-deck/scripts/deck_gates.py)
- [skills/check-a-deck/scripts/test-deck-gates.py](../../skills/check-a-deck/scripts/test-deck-gates.py)
- [skills/check-a-sheet/scripts/sheet_gates.py](../../skills/check-a-sheet/scripts/sheet_gates.py)
- [skills/check-a-sheet/scripts/test-sheet-gates.py](../../skills/check-a-sheet/scripts/test-sheet-gates.py)
- [skills/check-hardware/references/readings.md](../../skills/check-hardware/references/readings.md)
- [skills/check-hardware/scripts/collect.py](../../skills/check-hardware/scripts/collect.py)
- [skills/computer-use/scripts/computer.py](../../skills/computer-use/scripts/computer.py)
- [skills/create-a-skill/scripts/check-skill.py](../../skills/create-a-skill/scripts/check-skill.py)
- [skills/create-a-skill/scripts/check-translations.py](../../skills/create-a-skill/scripts/check-translations.py)
- [skills/create-a-skill/scripts/draw-a-skill-flow.py](../../skills/create-a-skill/scripts/draw-a-skill-flow.py)
- [skills/create-a-skill/scripts/draw-the-family.py](../../skills/create-a-skill/scripts/draw-the-family.py)
- [skills/create-a-skill/scripts/family-glossary.json](../../skills/create-a-skill/scripts/family-glossary.json)
- [skills/create-a-skill/scripts/graph-skills.py](../../skills/create-a-skill/scripts/graph-skills.py)
- [skills/create-a-skill/scripts/skill-glosses.ru.json](../../skills/create-a-skill/scripts/skill-glosses.ru.json)
- [skills/create-a-skill/scripts/test-check-skill.py](../../skills/create-a-skill/scripts/test-check-skill.py)
- [skills/design-a-reward/references/rules-of-a-reward.md](../../skills/design-a-reward/references/rules-of-a-reward.md)
- [skills/design-a-reward/scripts/probe-reward.py](../../skills/design-a-reward/scripts/probe-reward.py)
- [skills/draw-a-diagram/references/making-it-look-right.md](../../skills/draw-a-diagram/references/making-it-look-right.md)
- [skills/draw-a-diagram/scripts/check-drawio.py](../../skills/draw-a-diagram/scripts/check-drawio.py)
- [skills/find-a-skill/scripts/check-external-skill.py](../../skills/find-a-skill/scripts/check-external-skill.py)
- [skills/find-a-skill/scripts/scout.py](../../skills/find-a-skill/scripts/scout.py)
- [skills/judge-a-skill/scripts/hearing.py](../../skills/judge-a-skill/scripts/hearing.py)
- [skills/learn-an-interface/scripts/drag.ps1](../../skills/learn-an-interface/scripts/drag.ps1)
- [skills/learn-an-interface/scripts/find_shift.py](../../skills/learn-an-interface/scripts/find_shift.py)
- [skills/learn-an-interface/scripts/learn-an-interface.py](../../skills/learn-an-interface/scripts/learn-an-interface.py)
- [skills/learn-an-interface/scripts/mouse_game.py](../../skills/learn-an-interface/scripts/mouse_game.py)
- [skills/learn-an-interface/scripts/mousewatch.ps1](../../skills/learn-an-interface/scripts/mousewatch.ps1)
- [skills/learn-an-interface/scripts/read_demo.py](../../skills/learn-an-interface/scripts/read_demo.py)
- [skills/learn-an-interface/scripts/screenwatch.ps1](../../skills/learn-an-interface/scripts/screenwatch.ps1)
- [skills/learn-an-interface/scripts/stack_column.py](../../skills/learn-an-interface/scripts/stack_column.py)
- [skills/make-a-template/scripts/templates.py](../../skills/make-a-template/scripts/templates.py)
- [skills/make-a-template/scripts/test-templates.py](../../skills/make-a-template/scripts/test-templates.py)
- [skills/manage-vk/scripts/post.py](../../skills/manage-vk/scripts/post.py)
- [skills/manage-vk/scripts/preflight.py](../../skills/manage-vk/scripts/preflight.py)
- [skills/manage-vk/scripts/test-typo-lint.py](../../skills/manage-vk/scripts/test-typo-lint.py)
- [skills/manage-vk/scripts/typo_lint.py](../../skills/manage-vk/scripts/typo_lint.py)
- [skills/manage-windows/scripts/fix-layout.py](../../skills/manage-windows/scripts/fix-layout.py)
- [skills/manage-windows/scripts/preflight.py](../../skills/manage-windows/scripts/preflight.py)
- [skills/manage-windows/scripts/test-fix-layout.py](../../skills/manage-windows/scripts/test-fix-layout.py)
- [skills/review-a-change/scripts/check-review.py](../../skills/review-a-change/scripts/check-review.py)
- [skills/review-a-change/scripts/test-check-review.py](../../skills/review-a-change/scripts/test-check-review.py)
- [skills/route-a-task/scripts/route.py](../../skills/route-a-task/scripts/route.py)
- [skills/route-a-task/scripts/test-route.py](../../skills/route-a-task/scripts/test-route.py)

**Dangling — a sign pointing at nothing:**

- `skills/draw-a-diagram/https:/github.com/jgraph/drawio-mcp/blob/main/shared/style-reference.md`
- `skills/draw-a-diagram/references/https:/github.com/jgraph/drawio-mcp/blob/main/shared/style-reference.md`

**Repeated verbatim — 7 — by design or by drift?** A rule written in two places is how a file comes to contradict itself:

- skills/design-a-reward/SKILL.md: 0   the wanted thing happened            a real PNG was written
0.3   somethi
    - also in skills/learn-an-interface/SKILL.md: 0   the wanted thing happened            a real PNG was written
0.3   some
- skills/manage-vk/references/capabilities.md: 1  boundaries   what this credential can touch at all
2  function
    - also in skills/manage-vk/SKILL.md: 1  boundaries   what this credential can touch at all
2  functions    the exact cal
- skills/design-a-reward/references/diagnosing-a-flat-curve.md: Measured: over 150 iterations against a hare tha
    - also in skills/design-a-reward/SKILL.md: Measured: over 150 iterations against a hare that was also learning, accuracy
- skills/learn-an-interface/references/input-and-demonstration.md: SendInput goes to whatever is focused, not to
    - also in skills/learn-an-interface/references/traps.md: SendInput goes to whatever is focused, not to whatever rectangl
- skills/manage-vk/references/api-errors.md: The mask says what the key is for; it does not say what VK will acc
    - also in skills/manage-vk/SKILL.md: The mask says what the key is for; it does
not say what VK will accept.
- skills/create-a-skill/SKILL.md: What must
not happen is the search being skipped silently, because then nobody
    - also in skills/find-a-skill/SKILL.md: What must not happen is the search being skipped silently,
because then nobody k
- skills/check-hardware/SKILL.md: When a use contradicts something here, the use wins: change the file, keep the
    - also in skills/design-a-reward/SKILL.md: When a use contradicts something here, the use wins: change the file, keep th
    - also in skills/find-a-skill/SKILL.md: When a use contradicts something here, the use wins: change the file, keep the
c
    - also in skills/judge-a-skill/SKILL.md: When a use contradicts something here, the use wins: change the file, keep the

    - also in skills/manage-windows/SKILL.md: When a use contradicts something here, the use wins: change the file, keep the
    - also in skills/route-a-task/references/why-gates.md: When a use contradicts something here, the use wins: change the f

## By skill

- [check-a-deck](skills/check-a-deck.md)
- [check-a-sheet](skills/check-a-sheet.md)
- [check-hardware](skills/check-hardware.md)
- [computer-use](skills/computer-use.md)
- [create-a-skill](skills/create-a-skill.md)
- [design-a-reward](skills/design-a-reward.md)
- [draw-a-diagram](skills/draw-a-diagram.md)
- [find-a-skill](skills/find-a-skill.md)
- [judge-a-skill](skills/judge-a-skill.md)
- [learn-an-interface](skills/learn-an-interface.md)
- [make-a-template](skills/make-a-template.md)
- [manage-vk](skills/manage-vk.md)
- [manage-windows](skills/manage-windows.md)
- [review-a-change](skills/review-a-change.md)
- [route-a-task](skills/route-a-task.md)