---
id: methodology/envoy-status
title: Envoy status
description: "Envoy status subscriber for ordinary chairs: publish the full STATUS digest. Carries a settle contract at the publication tier. Use when project.yaml lists status and this chair is not in the guarded class."
tags: [methodology, envoy]
---

# Envoy status

This chair opted into Envoy `status` in `project.yaml`. Publish a sitrep. Do not use this article on a `guarded` chair; that chair takes `methodology/envoy-status-discreet`.

Every Envoy call sends `chair` as this chair's map name, or `nexus` when this chair is the bulletin's nexus.

## Local record

Keep the local digest at `_status/STATUS.md` (`methodology/status-contract`). Same four sections as today, plus `repo:` when this node uses the repo ritual.

## Publish

After a real change, and on exit from a sitting that changed it:

1. Write the local file.
2. `status_put` the whole digest: `repo:` when present, Forefront, Where I left off, Next steps, Open loops.

Do not enqueue status events. Do not expect an ack. Do not read sibling STATUS files as an API.

A nexus that is also a node publishes its own digest, not a dump of its children.

## Settle contract

**Tier: publication.** The sitrep is derived from the local digest, so it settles last, after that digest is true.

**Surface:** the published sitrep.

**Settled means:** what is published matches the local file, `repo:` included, and reflects any mail settled earlier in the same run that bears on the next move.

**What satisfies the gate here:** `_status/STATUS.md`. The sitrep is derived from it, so republishing can never destroy the only copy, and a settle run republishes rather than waiting for the next real change.

**Class: single-system.** Groups with Envoy.
