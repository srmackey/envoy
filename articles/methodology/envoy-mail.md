---
id: methodology/envoy-mail
title: Envoy mail
description: "Envoy mail subscriber: the bell, ack on awareness, and sending an export to the nexus. The agent writes the letter; it lands in a queue that is triaged on command. Carries a settle contract at the source tier: bells are cleared, letters are not. A chair in the sensitive operator class takes methodology/envoy-mail-discreet instead."
tags: [methodology, envoy]
---

# Envoy mail

This chair opted into Envoy `mail` in `project.yaml`. The note is a bell. The letter is the inbox file.

Every Envoy call sends `chair` as this chair's map name, or `nexus` when this chair is the bulletin's nexus.

## Send (node to nexus)

**What triggers one.** A finding this chair cannot close: a step another chair has to take, a defect in someone else's product, a decision that is not this chair's to make. It does not belong in this project's own open loops, where only this chair will ever read it.

**First, is a letter the right instrument?** If this same sitting will hold the receiving chair's lens again before it ends, the item is a carry-back, and mail is the expensive way to cross a boundary you are about to cross anyway. `methodology/carry-back` holds that choice. A letter is for what outlives the sitting, or for a chair this sitting will not hold.

**Then write it.** Writing into the nexus inbox does not wait on the principal. That inbox is triaged on command and never because a file arrived, so a letter starts a queue rather than an action, and anything moving onward into a `sensitive` chair passes the nexus mail gate.

1. Write the letter into the nexus inbox (`kind: export`) through that chair's overlay home, path under `inbox/`. A title, the finding written for the receiver, a pointer home, and why it was sent. Not a dump of the source.
2. `note_post` the bell (`intended_for`, `inbox` path, `why`).
3. Later, `note_list` own notes. On ack, persist anything still unpersisted, then `note_remove`.

## Receive

Only nexus writes a node inbox (`kind: deliver`). The folder and what happens to a letter in it are `methodology/node-inbox`, or `methodology/post-office` when this chair is the nexus.

Do not write another node's inbox. Do not treat the note as the letter.

Delivery into a `sensitive` chair still needs the principal's confirmation. That is a hold or foul until they say proceed.

## Ack on awareness

The inbox file is the durable signal. The note is only the wake-up. Awareness does not process the letter, and it does not copy the letter into STATUS.

`note_list` acks `shown` when the calling chair is `intended_for` and the note has no ack yet. Listing as the intended chair is awareness. Do not wait for `process the inbox`. Explicit `note_ack` remains for other actions.

`shown` means this chair has the bell and can find the letter. It lets the sender's remove loop run. It is not a claim that the letter was filed.

Ack and removal are settled work under `methodology/autonomy-gate-provenance`, never proposals: the letter is the durable copy, so neither is worth a turn of the principal's.

**Exception: the nexus mail gate.** A note intended for `nexus` goes through the gate in `methodology/post-office` before it is acked, but only where that gate fires. Where it does not, ack `shown` like any other note. That article holds the condition; do not restate it here.

If Envoy is down, skip ack. The pending file in `inbox/` still holds the work.

## Settle contract

**Tier: source.** The inbox file is the durable letter, so mail settles before any digest that reads it.

**Surface:** open notes intended for this chair, and open notes this chair authored.

**Settled means** what the sections above already say, run without being asked: an unacked note intended for this chair is acked `shown`; a note this chair authored whose letter is filed or archived is removed; and a note bearing on the next move reaches the sitrep, which is the status article's half of the same run.

**What satisfies the gate here:** the inbox file. The note is the bell and the letter is the record, so acking or removing a note can never destroy the only copy.

**Not settled by this contract:** the letters. Processing an inbox stays on command only. A settle run clears bells, never mail.

A chair in the `sensitive` operator class takes `methodology/envoy-mail-discreet` instead of this article, never beside it. That article is the guard: a letter has to pass the same test that chair's constitution applies to saving a file. `guarded` is not that class.

**Class: single-system.** Groups with Envoy. The mail gate it names is composition on the nexus chair.
