---
id: methodology/envoy-syos
title: Envoy syos
description: "Envoy syos subscriber: terse restart brief. Use when project.yaml lists syos, or when asked to syos / syos that change so I can check."
tags: [methodology, envoy]
---

# Envoy syos

This chair opted into Envoy `syos` in `project.yaml`. Syos is a self-addressed brief this chair leaves for its next sitting. The note is the payload. There is no inbox file and no nexus gate.

Every Envoy call sends `chair` as this chair's map name, or `nexus` when this chair is the bulletin's nexus.

## Write

The principal says `syos` or "syos that change so I can check". Do not write one on every materialize, status publish, or mail note.

**Grain.** Two short beats. Nothing else.

1. **Check.** We updated X. Confirm X is available and has B.
2. **Jump-in.** One line: where this chair was, what it was doing, where it was heading.

Do not put STATUS, next steps, evolution, leftover lists, or another spec in the note. Those live in the sitting, `_status/STATUS.md`, or the paper. If there is nothing to check and nowhere to jump, skip the note.

1. `syos_post` with `body` set to that brief. `author` and `intended_for` are this chair.
2. Stop if this sitting's loaded snapshot is already stale.

A chair writes only to itself.

## Read

On session start, and on step-in to this chair, `syos_list` this chair's open notes.

If any are present, present them. Then wait. Do not verify the brief. Do not continue the work because a note arrived. Do not treat the note as a charter to run a second sitting. The principal chooses to act, ack, or skip it. Act means run the check and pick up the jump-in.

`now_view` does not include syos. Mail stays mail. Status stays the next move.

## Ack and remove

Do not ack because you listed the notes. The principal names the action. `syos_ack` takes a short token: `shown`, `checked`, or skip (`ignored` in the tool). Author may `syos_remove` when the brief is done. Acked notes may expire. Unacked ones do not.

If Envoy is down, skip. There is no disk fallback. The note lives only in the Envoy vault.

Reason: Envoy cannot push into a new session. Hosts load files; agents query. The same reliability as the mail bell: if the sitting does not call Envoy, it misses it. The article is what fires the check. The list result is what the agent would otherwise have to remember to go looking for.

Adjacent to `methodology/notice-in-the-result`: that article puts a notice in the result of an operation that already ran. This one is a brief written for a sitting that has not started yet, because there is no result that sitting can ride.

**Class: single-system.** Groups with Envoy.
