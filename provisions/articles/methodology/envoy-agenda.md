---
id: methodology/envoy-agenda
title: Envoy agenda
description: "Envoy agenda subscriber: one line of install-wide agenda counts on the first turn, posting dated items and todos, and reading the whole agenda or this chair's own rows. Only the root nexus reorders tasks or edits another chair's row. Use when project.yaml lists agenda."
tags: [methodology, envoy]
---

# Envoy agenda

This chair opted into Envoy `agenda` in `project.yaml`. The install has one calendar and one task list, kept by Envoy on the root nexus. Any subscribed chair posts to them and reads them. The board (`FOCUS.md`) stays the principal's ranked week. The agenda does not write it and does not restate it.

Every Envoy call sends `chair` as this chair's address, or `nexus` when this chair is the root nexus.

## First turn

On the first turn of a session, before other work, call `agenda_list` with scope `all` and print one line from `counts`, zeros included:

`{overdue} overdue. {due_soon} due soon. {before_sunday} before Sunday. {next_week} next week. {tasks} tasks on the list.`

Do not print `later`. Do not list the items. The line stands alone. It is not the status pack, it prints whether or not status was asked for, and it does not replace the status offer. If Envoy is down, skip it.

## Asking

The whole install, `agenda_list` scope `all`. Answer only what was asked:

- what's overdue, due soon, due before Sunday, due next week: that bucket.
- what's due next: `next`. An overdue item comes before today.
- give me the todos: `tasks`, in order.
- top 10 todos: the first ten of `tasks`.

This chair's own rows, `agenda_list` scope `mine`:

- what do I have on the calendar: the calendar buckets.
- what do I have on the task list: `tasks`.

From the root, `mine` is the root's own posts, not every row.

Reading never closes a row.

## Posting

- `agenda_post` with `due` (`YYYY-MM-DD`) is a calendar item. `until` makes it a window, both days inclusive.
- Without `due` it is a todo and lands at the bottom. Do not try to place it.
- `agenda_update` changes a row this chair posted. A `due` moves a todo onto the calendar. An empty `due` sends it back to the bottom of the task list. An empty `until` drops the window.
- `agenda_close` when the thing is done or dropped. Closing is its own act.

Post what the principal asks to put there. Do not copy this chair's next steps or open loops onto the agenda unasked: STATUS is this chair's next move, and the agenda is what he wants to see from any chair.

A sensitive chair posts one line with no names and no facts.

## Who may change what

This chair may update or close only rows it posted. The root nexus may update or close any row, and only the root reorders tasks (`agenda_reorder`). Envoy refuses the rest. A refusal is the rule working. Do not route around it by posting a copy.

Relation to `methodology/nexus-board`: the board is the principal's rank for the week at one nexus. The agenda is every chair's dates and todos in one store. Neither writes the other.

Relation to `methodology/envoy-status`: a sitrep is this chair's next move and is overwritten. An agenda row stays until someone closes it.

**Class: single-system.** Groups with Envoy.

Reason: one line of counts tells the principal whether anything across the install needs him, without walking every chair's STATUS. One store means a date posted from any chair is seen from all of them.
