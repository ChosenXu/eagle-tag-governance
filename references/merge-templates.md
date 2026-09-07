# Merge Plan — Templates & Examples

## Schema (the only structure the skill writes)

A `merge_plan.json` has three optional arrays. Each operation is independent; delete a line to skip it, change `target` / `newName` to redirect it.

```json
{
  "merges":  [
    { "source": "<tag to remove>", "target": "<canonical tag to keep>" }
  ],
  "renames": [
    { "oldName": "<current tag>", "newName": "<normalized tag>" }
  ],
  "retire":  [
    { "tag": "<tag to strip>", "note": "<why / manual-delete reminder>" }
  ]
}
```

| Array | Tool | Result | When to use |
|---|---|---|---|
| `merges` | `tag_merge` | source removed, items moved to target | two tags mean the same thing |
| `renames` | `tag_update` | tag renamed everywhere | one tag, wrong spelling/casing |
| `retire` | `item_remove_tags` (then manual UI delete) | tag stripped from items only | no merge target exists (count 0/1 noise) |

## Rules

- **Canonical direction**: for `merges`, `source` must be the *non-canonical* spelling (the one deviating from `vocabulary*.md`); `target` is the canonical spelling kept.
- **Exact names**: every string must match an existing tag exactly (case/space-sensitive). Verify with `tag_get` before writing.
- **Renames do not create new concepts** — they normalize an existing tag to the canonical spelling in `vocabulary*.md`. Do not rename a tag into a term that is not in the normative taxonomy unless the user explicitly asks.
- **Retire ≠ delete**: MCP has no `tag_delete`. A `retire` entry strips the tag from items; the tag itself disappears only when the user deletes it manually in Eagle's UI. Always note this in `note`.

## Example 1 — Merge synonyms

```json
{
  "merges": [
    { "source": "网页 UI",  "target": "网页UI" },
    { "source": "网页界面", "target": "网页UI" },
    { "source": "WebUI",   "target": "Web UI" }
  ]
}
```

Maps three variants onto two canonical tags (`网页UI`, `Web UI` from `vocabulary*.md`).

## Example 2 — Normalize casing / spacing

```json
{
  "renames": [
    { "oldName": "webui",      "newName": "Web UI" },
    { "oldName": "MobileUI",   "newName": "Mobile UI" },
    { "oldName": " 海报 ",     "newName": "海报" }
  ]
}
```

## Example 3 — Retire low-frequency noise

```json
{
  "retire": [
    { "tag": "临时截图", "note": "count=0，剥离后需在 Eagle 界面手动删除" },
    { "tag": "test123",  "note": "count=1，疑似误打标签，剥离后手动删除" }
  ]
}
```

## Example 4 — Mixed plan

```json
{
  "merges":  [ { "source": "UI设计", "target": "UI" } ],
  "renames": [ { "oldName": "ui",    "newName": "UI" } ],
  "retire":  [ { "tag": "草稿1",  "note": "count=0，手动删除" } ]
}
```

## Human-readable summary format (present to user at Phase 3a)

```
治理方案预览（共 N 项操作）：
1. [合并] "网页 UI" → "网页UI"   （影响 12 个素材）
2. [重命名] "webui" → "Web UI"   （影响 3 个素材）
3. [退役] "临时截图"              （影响 0 个素材，需手动删除）
请编辑 merge_plan.json 后确认执行。
```
