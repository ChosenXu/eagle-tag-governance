---
name: eagle-tag-governance
description: Use when the user wants to merge, normalize, rename, dedupe, or retire existing Eagle tags / the tag vocabulary (via the eagle-mcp connector). Triggers on mentions of Eagle, eagle-mcp, or tag-governance intents like 合并标签 / 整理标签 / 标签太乱 / 同义标签 / 重命名标签 / 规范化标签 / 清理标签词表 / 标签去重 / 低频标签清理 / 退役无用标签. Does NOT trigger for untagged-asset naming, tagging, or annotation — those are handled by eagle-untagged-organizer.
agent_created: true
version: 1.0.0
---

# Eagle Tag Governance

## Overview

Govern the **tag vocabulary** of an Eagle library — not the assets. This skill scans every existing tag, spots synonyms / spelling variants / case-space inconsistencies / low-frequency noise / tags that drift away from the controlled three-dimension taxonomy, then produces a merge / rename / retire plan, and executes it through `tag_merge` / `tag_update` only after a dry-run preview and an explicit authorization gate.

It has a single workflow — the **Tag governance**: for every tag-management request, audit the vocabulary, propose cleanups, and apply them safely.

For tag governance, every operation is **global and permanent**:
- `tag_merge` deletes the source tag and moves all its items to the target.
- `tag_update` renames a tag everywhere it is used.
- Eagle has **no undo and no `tag_delete` tool** — once applied, the change is irreversible through MCP.

## Output Language

The skill body (instructions, logic, workflow) stays in English. Tag names in the plan and the final `tag_merge` / `tag_update` calls are taken **verbatim** from the matching `vocabulary*.md` file (the normative target), never invented or translated.

**Tag vocabulary selection (by the language of the tags being governed):**

| Tag language in library | Vocabulary file | Role |
|---|---|---|
| 简体中文 | `references/vocabulary.md` | 规范目标（canonical） |
| 繁體中文（港式） | `references/vocabulary-zh-Hant.md` | 规范目标 |
| English | `references/vocabulary-en.md` | 规范目标 |
| 日本語 | `references/vocabulary-ja.md` | 规范目标 |
| 한국어 | `references/vocabulary-ko.md` | 规范目标 |
| Русский | `references/vocabulary-ru.md` | 规范目标 |
| Español | `references/vocabulary-es.md` | 规范目标 |
| Deutsch | `references/vocabulary-de.md` | 规范目标 |

Plan explanations (the human-readable summary) follow the user's instruction language; the tag names themselves must always match the library's tag language exactly.

## When to Use

- The user mentions Eagle, eagle-mcp, or tag-vocabulary cleanup.
- The user wants to merge / consolidate / normalize / rename / dedupe / retire existing tags.
- The user says things like "标签太乱" / "合并同义标签" / "清理标签词表" / "低频标签太多" / "统一标签大小写".

## When NOT to Use (negative triggers)

- Naming, tagging, or annotating **untagged assets** ("给未打标签素材打标签" / "批量命名 Eagle 素材" / "分析这些图片") — that is `eagle-untagged-organizer`'s job.
- Moving items between folders, deleting assets, or deduplicating assets.
- Adding new assets (`item_add`).

## Prerequisites

- Eagle desktop app must be running, because `eagle-mcp` is a proxy that connects to Eagle itself.
- `eagle-mcp` must be configured in `~/.workbuddy/mcp.json` under `mcpServers` and trusted in the connector panel.
- The connector must expose the **tag** tools. The core tools used by this skill are `tag_get`, `tag_count`, `tag_merge`, and `tag_update`. Optional group tools: `tag_group_get` / `tag_group_create` / `tag_group_update` / `tag_group_delete` / `tag_group_add_tags` / `tag_group_remove_tags`. Optional cross-check tools: `item_get` / `item_count` / `item_query` / `item_remove_tags`. This skill does **not** use asset-write tools such as `item_update` or `item_add`.

## Supporting Files

Load these `references/` files only when needed:

| File | When to read |
|---|---|
| `references/vocabulary*.md` | Before judging whether a tag deviates from the canonical spelling — the normative target for the governed language |
| `references/gotchas.md` | Before the first `tag_merge` / `tag_update` of a session, and whenever a call behaves unexpectedly |
| `references/merge-templates.md` | Before producing the `merge_plan.json` — the plan schema and examples |

The `scripts/` folder holds three helpers that run locally (no Eagle writes unless you pass `--apply`):
- `build_tag_plan.py` — turn a `tag_get` dump + a `vocabulary*.md` into an editable `merge_plan.json` (variant clustering, canonical-casing renames, low-frequency retire).
- `apply_tag_governance.py` — bulk-drive `tag_merge` / `tag_update` over the MCP stdio proxy for large plans. **Dry-run by default; pass `--apply` to actually write.** It rejects merge cycles and folds `retire`-with-target into merges.
- `export_undo_mapping.py` — emit `tag_undo_mapping.json` (reversible renames + merge audit) before any write.

Small plans can be applied with direct tool calls; see `references/gotchas.md` for usage.

## Hard Constraints (non-negotiable)

1. **Authorization gate cannot be bypassed** — no `tag_merge` / `tag_update` before Phase 3a dry-run + Phase 3b confirmation.
2. **Irreversible** — every write is global and permanent; Eagle has no undo. Always state "全局、不可逆、永久" before executing.
3. **Operate by tag name, not ID** — `tag_merge` / `tag_update` key on the exact tag string (case- and space-sensitive). Verify the exact spelling with `tag_get` before writing.
4. **Merge direction is fixed** — `source` disappears, `target` is kept. Reversing it deletes the correct tag.
5. **Undo mapping is mandatory** — export `tag_undo_mapping.json` (source→target / old→new) before any write.
6. **Retire ≠ delete** — MCP has no `tag_delete`. Retiring means merging into a canonical target, or stripping the tag from items via `item_remove_tags`; full deletion must be done manually in Eagle's UI.
7. **Vocabulary sync obligation** — `vocabulary*.md` is shared with `eagle-untagged-organizer` as the normative target; if you change it here, sync the other skill.
8. **Trigger boundary** — only respond to tag-vocabulary governance; never drift into asset naming/annotation.
9. **Version & backup discipline** — version starts at `1.0.0`; increment semantically (MINOR for new capability, MAJOR for breaking change).
10. **No revision traces** — the skill text keeps only currently-valid rules; no inline edit notes, changelogs, or explanatory comments.

## Workflow

### Phase 0 — Pre-flight checks (must pass before any writes)

**Step 0a. Connection check.**
- Confirm `eagle-mcp` is configured under `mcpServers` in `~/.workbuddy/mcp.json` and Eagle is running. Test the connection if needed.

**Step 0b. Tag-tool readiness probe (once per environment).**
- Call `tag_get` to confirm it returns the full tag vocabulary with usage counts, and `tag_count` to confirm a total count. The two cross-validate that the environment is healthy.
- **Note:** this skill does **not** need a multimodal (image-reading) capability check — governance is metadata-only and never reads asset pixels.

### Phase 1 — Scan existing tags

- Call `tag_get` (optionally `coreFieldsOnly: true` to fetch only `name`/`count`) to list every tag with its usage count.
- Call `tag_count` for the total tag count, optionally with `minCount` to focus on high-frequency tags.
- Optionally `tag_group_get` to capture the current group structure.

### Phase 2 — Identify governance opportunities

For each tag, classify it against the normative `vocabulary*.md` for its language:
- **Synonyms / spelling variants** — e.g. `网页UI` / `网页 UI` / `网页界面`; `Web UI` / `webui` / `WebUI`.
- **Case / space inconsistency** — compare against the canonical casing in `vocabulary*.md`.
- **Low-frequency tags** — `count = 0` (pure noise) and `count = 1` (doubtful value) listed separately.
- **Drift from normative taxonomy** — tags not in `vocabulary*.md` but semantically mergeable into a listed term.
- Optionally use `item_query` to sample how a tag is actually used, so you do not guess meaning from the name alone.

### Phase 3a — Dry-run preview (required before any write)

Produce a structured `merge_plan.json` so the user can review and prune before anything is written. Do **not** write to Eagle in this phase.

```json
{
  "merges":  [ { "source": "网页 UI", "target": "网页UI" } ],
  "renames": [ { "oldName": "WebUI",  "newName": "Web UI" } ],
  "retire":  [ { "tag": "闲置标签", "note": "count=0，建议剥离后手动删除" } ]
}
```

- Build it via `scripts/build_tag_plan.py` or by hand. Present a human-readable summary: total operations, and for each, the source/target names with the affected item count.
- Invite the user to edit the file: delete a line to skip that operation, or change `target` / `newName` to redirect it.

### Phase 3b — Authorization gate (required before any write)

Based on the reviewed plan, require explicit confirmation:
- **Scope**: how many operations remain, and their tag names.
- **Per-operation impact**: source→target / old→new, each with its current item count.
- **Side effects**: merges delete the source tag globally; renames affect every item using the tag; these are irreversible.
- **Undo mapping**: state that `tag_undo_mapping.json` will be exported before writing.
- **Confirmation**: small plans (≤ 10 operations) may proceed with a single confirmation; large plans require an explicit "confirm all" acknowledging irreversibility.

Do not proceed to Phase 4 until the user confirms the final plan.

### Phase 4 — Execute governance

- **Merge** → `tag_merge` with `operations: [{ "source", "target" }]`.
- **Rename** → `tag_update` with `tags: [{ "oldName", "newName" }]`.
- Small plans: call the tool directly. Large plans: feed the reviewed `merge_plan.json` to `scripts/apply_tag_governance.py`.
- Export `tag_undo_mapping.json` (source→target / old→new) before the first write.

### Phase 5 — Verify

**Verify at the item level first (primary check).** Eagle stores tags per-item; the `tag_get` aggregate index is computed in memory and is **not always invalidated by programmatic edits** (a known Eagle quirk — `tag_merge` / `tag_update` / `item_remove_tags` persist to item files, but the tag-count index can lag until Eagle re-indexes). So:

1. **Item-level truth (authoritative):** for each affected item, call `item_get` / `item_query` (or read the item's tag list) and confirm:
   - the `source` tag is **absent**;
   - the `target` tag is **present** (merges / renames), or the retired tag is **stripped** (retire-without-merge).
2. **Index cross-check (may be stale):** call `tag_get` to see the aggregate counts. If `tag_get` still lists a disappeared `source` or shows pre-merge counts, **do not treat it as a write failure** — it is a stale index. Ask the user to **restart Eagle (or close & re-open the library)** to force re-index, then re-run `tag_get` to confirm.
3. **Count reconciliation:** the number of items carrying the `target` tag should equal the sum of the pre-merge counts of `source` + `target`.

- If an item-level check fails (a source tag is still present on items), report it immediately. There is no automated rollback, but `tag_undo_mapping.json` lets you manually reverse the direction (renames are reversible; merges require re-merging back to the original name).

## Scope & Out of Scope

**In scope**:
- Auditing the Eagle tag vocabulary.
- Merging, renaming, normalizing, deduplicating, and retiring existing tags via `tag_merge` / `tag_update` and (for retire-without-merge) `item_remove_tags`.

**Out of scope** (do not perform these unless the user separately asks and confirms):
- Naming, tagging, or annotating untagged assets — that is `eagle-untagged-organizer`.
- Folder reorganization or moving items into/out of folders.
- Deleting or moving assets to trash.
- Deduplicating or detecting near-duplicate assets.
- Adding new assets (`item_add`).
- Any write to Eagle without passing the Phase 3a dry-run preview and the Phase 3b authorization gate.
