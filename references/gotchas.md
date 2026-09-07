# Key Gotchas — Tag Governance

## The single most important fact

**Eagle has no undo and no `tag_delete` tool.** Every `tag_merge` / `tag_update` is global and permanent. Once applied, the change cannot be reversed through MCP — you can only *manually reverse the direction* using the exported `tag_undo_mapping.json`. Always run the dry-run (Phase 3a) and the authorization gate (Phase 3b) before any write.

## Tag operations are name-based, not ID-based

- `tag_merge` keys on `source` / `target` tag **strings**; `tag_update` keys on `oldName` / `newName` strings.
- Matching is **exact and case/space-sensitive**: `Web UI`, `WebUI`, and `webui` are three distinct tags. Verify the exact spelling with `tag_get` before writing — a typo either fails or silently merges the wrong tag.

## Merge direction is fixed

- In `tag_merge`, `source` is **removed** and all its items move to `target`. `target` is kept.
- Reverse the two and you delete the *correct* canonical tag. Always confirm which spelling is canonical (the one in `vocabulary*.md`) before setting source/target.

## tag_merge also rewrites groups / stars / history

- `tag_merge` updates not just items, but also tag groups, starred tags, and history tags that reference the source. This is good (consistency) but means the blast radius is wider than "just the items" — factor it into the impact description at the authorization gate.

## "Retire" does not mean "delete"

- There is no `tag_delete` tool. To "retire" a useless tag you can only:
  1. `tag_merge` it into a canonical target (preferred when a synonym exists); or
  2. `item_remove_tags` to strip it from every item (the tag still lingers in the vocabulary with `count = 0`, and only disappears when the user deletes it manually in Eagle's UI).
- Be honest in the plan: mark retiring-without-merge as "需用户在 Eagle 界面手动删除".

## tag_group_update replaces tags wholesale

- `tag_group_update`'s top-level `tags` (and per-group `tags`) is a **full replacement**, not incremental.
- To add or move tags without wiping existing associations, use `tag_group_add_tags` (`removeFromSource: true` to move) / `tag_group_remove_tags`.
- Misusing `tag_group_update` with `tags` will silently drop every other tag in the group.

## item_remove_tags only detaches, never deletes

- `item_remove_tags` removes a tag from items but leaves the tag in the vocabulary. Use it for the "strip then manual-delete" retire path, not as a substitute for deletion.

## tag_get index can be stale after programmatic edits

- Eagle stores tags per-item and computes the `tag_get` aggregate (name + count) **in memory**. `tag_merge` / `tag_update` / `item_remove_tags` persist to the item files correctly, but the in-memory index is **not always invalidated** by programmatic (MCP/API) edits — so `tag_get` may still list a just-merged `source` or show pre-merge counts for several minutes or until Eagle re-indexes.
- **Verified in practice:** after a real `tag_merge` + `item_remove_tags` on a test library, item files showed the source gone and the target present, yet `tag_get` kept returning the old 5-tag list. The data was correct; only the index lagged.
- **Implication for verification:** do not treat a stale `tag_get` as a write failure. Verify at the **item level** (read affected items' tag lists via `item_get` / `item_query`), and only trust `tag_get` after the user **restarts Eagle or re-opens the library** to force a re-index. See Phase 5 in `SKILL.md`.

## Call shape (the only common failure mode)

- **Array params: pass plain JSON arrays, never wrap in `{item: …}`.** The WorkBuddy MCP wrapper does **no** transformation — it validates your `params` verbatim against the server's JSON schema. So `operations` / `tags` / `names` MUST be `[{…}, {…}]`, and `ids` MUST be `["…"]`. Wrapping like `{operations: [...]}` or `{tags: [...]}` violates `additionalProperties:false` and returns a schema error. This is a call-shape mistake, not a tool-chain bug.

## Bulk-apply gotchas

- **Never hand-paste a 50+ tag array into a tool call.** Long arrays reliably drop entries when transcribed inline. For large plans, drive `tag_merge` / `tag_update` through `scripts/apply_tag_governance.py` reading from `merge_plan.json`, then re-read the tags afterwards to confirm the result matches the plan.
- **Save the undo mapping first.** Export `tag_undo_mapping.json` (source→target / old→new) *before* the first write. Without it, a bad merge is unrecoverable through MCP.

## Scanning efficiency

- `tag_get` with `coreFieldsOnly: true` returns only `name` / `count` — use it for the initial audit to save tokens on large libraries. Use the full `tag_get` only when you need group/other metadata.
- `tag_count` with `minCount` is a cheap way to count how many tags meet a frequency threshold (e.g. low-frequency `minCount: 2`).
