# Eagle Tag Governance

[English](README.md) | [简体中文](README.zh-CN.md)

A [WorkBuddy](https://www.workbuddy.cn/) skill that governs the **tag vocabulary** of an [Eagle](https://eagle.cool/) library via the `eagle-mcp` connector — merging, renaming, normalizing, deduplicating, and retiring existing tags so the taxonomy stays clean and consistent.

## What it does

Instead of looking at individual assets, this skill works on the *tag list itself*:

1. **Audit** — lists every tag with its usage count (`tag_get` / `tag_count`).
2. **Detect** — spots synonyms, spelling/case/space variants, low-frequency noise (`count = 0/1`), and tags that drift away from the controlled three-dimension taxonomy.
3. **Plan** — produces an editable `merge_plan.json` (`merges` / `renames` / `retire`).
4. **Preview & authorize** — surfaces every operation with its blast radius; you review and confirm (and nothing is written without your okay).
5. **Execute** — applies `tag_merge` / `tag_update` safely.
6. **Verify** — reads the tags back to confirm the source is gone and counts are correct.

## Highlights

1. **Safe by design** — every write is dry-run first, then authorized. Tag merges/renames are global and irreversible, so the skill never skips the preview or the confirmation gate.
2. **Undo mapping** — exports `tag_undo_mapping.json` (source→target / old→new) before any write, so a bad merge can be manually reversed.
3. **Normative target** — judges "drift" against the same controlled three-dimension vocabulary (`vocabulary*.md`) used by `eagle-untagged-organizer`, keeping both skills aligned.
4. **Honest about limits** — Eagle's MCP has no `tag_delete`; retiring a tag can only merge it or strip it from items (full deletion is a manual UI step), and the plan says so plainly.

## Install

Clone this repository into your WorkBuddy skills directory:

```bash
git clone https://github.com/ChosenXu/eagle-tag-governance.git \
  ~/.workbuddy/skills/eagle-tag-governance
```

Or copy the folder manually into `~/.workbuddy/skills/`.

## Prerequisites

- The Eagle desktop app must be running.
- `eagle-mcp` must be configured in `~/.workbuddy/mcp.json` and trusted in the connector panel.

## Usage

Mention Eagle / `eagle-mcp` / tag cleanup with an intent like "合并标签" / "整理标签" / "规范化标签" / "清理标签词表", and the skill drives the workflow. See [`SKILL.md`](SKILL.md) for the full workflow (pre-flight → scan → detect → dry-run → authorize → execute → verify).

> Need to name, tag, or annotate **untagged assets** instead? Use [`eagle-untagged-organizer`](https://github.com/ChosenXu/eagle-untagged-organizer). The two skills are independent.

## Structure

```
SKILL.md                     # skill definition & workflow
references/
  vocabulary.md              # 简体中文 normative tag taxonomy (canonical target)
  vocabulary-zh-Hant.md      # 繁體中文（港式） normative tag taxonomy
  vocabulary-en.md           # English normative tag taxonomy
  vocabulary-ja.md           # 日本語 normative tag taxonomy
  vocabulary-ko.md           # 한국어 normative tag taxonomy
  vocabulary-ru.md           # Русский normative tag taxonomy
  vocabulary-es.md           # Español normative tag taxonomy
  vocabulary-de.md           # Deutsch normative tag taxonomy
  gotchas.md                 # tag-operation pitfalls (irreversible, name-based, no tag_delete…)
  merge-templates.md         # merge_plan schema & examples
scripts/
  apply_tag_governance.py    # bulk-apply tag_merge / tag_update via MCP stdio proxy (stage 3)
  build_tag_plan.py          # build merge_plan.json from analysis (stage 3)
  export_undo_mapping.py     # export tag_undo_mapping.json before write (stage 3)
```

## License

[MIT](LICENSE)
