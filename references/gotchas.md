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

## Call shape (schema-wrapping mistakes)

- **Array params: pass plain JSON arrays, never wrap in `{item: …}`.** The WorkBuddy MCP wrapper does **no** transformation — it validates your `params` verbatim against the server's JSON schema. So `operations` / `tags` / `names` MUST be `[{…}, {…}]`, and `ids` MUST be `["…"]`. Wrapping like `{operations: [...]}` or `{tags: [...]}` violates `additionalProperties:false` and returns a schema error. This is a call-shape mistake, not a tool-chain bug.
- **Different failure mode:** the rule above is about wrapper *validation* of your payload. In some sessions the wrapper additionally rejects even *correctly-formed* arrays with `/operations: must be array` — that is a serialization quirk, covered in the next section; drive those writes through `scripts/apply_tag_governance.py` instead.

## Bulk-apply gotchas

- **Never hand-paste a 50+ tag array into a tool call.** Long arrays reliably drop entries when transcribed inline. For large plans, drive `tag_merge` / `tag_update` through `scripts/apply_tag_governance.py` reading from `merge_plan.json`, then re-read the tags afterwards to confirm the result matches the plan.
- **Save the undo mapping first.** Export `tag_undo_mapping.json` (source→target / old→new) *before* the first write. Without it, a bad merge is unrecoverable through MCP.

## WorkBuddy harness may reject array params (tag_merge / tag_update)

- **Symptom:** calling `tag_merge` / `tag_update` with a correctly-formed `operations` / `tags` array returns `/operations: must be array` (or `/tags: must be array`) — even for a single-element array. This is a harness/tool-wrapper serialization limitation, **not** a problem with your payload.
- **Workaround:** do not fight the inline tool call. Drive the writes through `scripts/apply_tag_governance.py`, which speaks JSON-RPC to the MCP proxy directly and bypasses the wrapper. Dry-run first (no `--apply`), review, then `--apply`. The script also validates for cycles and `source == target`.
- **Scope:** this affects only the *write* calls that take array params. Read calls (`tag_get`, `tag_count`, `item_query`) work through the normal tool call. (If `item_query` returns 0 for tags that clearly have items, the Eagle search index is also stale post-edit — restart Eagle / re-open the library to refresh; rely on the apply script's per-op `affectedItems` for item-level truth.)
- *Not the same as the schema-wrapping mistake in the previous section:* that one fails on malformed params; this one rejects well-formed arrays. When in doubt, drive the writes through the script either way.

## tag_merge / tag_update can both fail SILENTLY on session-created targets (CRITICAL)

- **Symptom A — `tag_merge` lies.** When the `target` tag was created via the API *in the same session* (e.g. just auto-created by a rename), `tag_merge` returns `success:true`, `sourceRemoved:true` but **`affectedItems: 0`** — it moves **nothing** and the `source` tag remains. Trusting the response loses the operation. `tag_merge` into **long-pre-existing, user-created** targets works fine (items move, source gone).
- **Symptom B — `tag_update` rename duplicates instead of merges.** Renaming a `source` to an *existing* target name does **not** merge into that target — it creates a **second tag object with the same display name** (verified: 5 separate tags all named `瑞士风`, 4 all named `扁平色`, each holding one source's items). So never use "rename source → existing target" to consolidate; you get duplicates.
- **Net effect:** once a target tag has been API-created this session, you **cannot** reliably merge additional sources into it through MCP — both tools are broken for that case. `tag_get` will then show duplicate-named tags; `item_query` is also globally stale post-edit (returns 0), so it cannot confirm item-level truth.
- **Why it happens (hypothesis):** Eagle's merge/rename-by-name resolves the target by an internal ID that isn't registered for session-created tags, so the call no-ops (merge) or spawns a new same-named object (rename).
- **Mitigation / recovery:**
  - **Same-name duplicates self-heal on re-open.** Verified on a scratch library: an API rename duplicated `AAA`; `tag_get` returned two `AAA` rows in the same session, but after closing and re-opening the library (forced re-index) Eagle merged them into a single `AAA` with the summed count and no items lost. The Eagle tag panel lists tags **per object**, so it is the authoritative object count — if it shows one entry, the duplicate is gone. For duplicates alone you usually do **not** need to merge in the UI.
  - Merges between **distinct** names into a session-created target still cannot be driven reliably through MCP — finish those in Eagle's native UI (Eagle resolves IDs correctly there), then re-check.
  - Prefer merging into **pre-existing** canonical targets so the whole plan lands in one API pass.
  - `apply_tag_governance.py` is now hardened against Symptom A/B: (a) auto-creates a missing target by renaming *one* source into it; (b) parses per-op `affectedItems` from the live proxy response and **retries** merges that report 0 moved items with back-off (catches Symptom A's false success); (c) re-reads tags afterwards and **flags duplicate-named tags** (catches Symptom B). A `--selftest` mode runs the parsers offline (no Eagle). BUT the script still cannot *defeat* A/B — if the run prints `ZERO-MOVE` or `CRITICAL: duplicate tag names` (it also exits non-zero in that case), STOP and switch to the UI rather than re-running. For the duplicate-name case specifically, re-opening the library merges them automatically (see above) — verify in the tag panel, no re-run needed.

## Scanning efficiency

- `tag_get` with `coreFieldsOnly: true` returns only `name` / `count` — use it for the initial audit to save tokens on large libraries. Use the full `tag_get` only when you need group/other metadata.
- `tag_count` with `minCount` is a cheap way to count how many tags meet a frequency threshold (e.g. low-frequency `minCount: 2`).
