# Eagle Tag Governance

English | [简体中文](readme/README.zh-CN.md)

An [Agent Skills](https://agentskills.io)-standard skill that governs the **tag vocabulary** of an [Eagle](https://eagle.cool/) library via the `eagle-mcp` MCP server — merging, renaming, normalizing, deduplicating, and retiring existing tags so the taxonomy stays clean and consistent. It runs in any Agent Skills-compatible AI agent (WorkBuddy, Claude Code, Cursor, Codex, …).

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

Install the skill folder into your AI agent's skills directory:

| Agent | User-level skills dir | MCP config file |
|---|---|---|
| WorkBuddy | `~/.workbuddy/skills/` | `~/.workbuddy/mcp.json` |
| Claude Code | `~/.claude/skills/` | `.mcp.json` or `claude mcp add` |
| Cursor | `~/.cursor/skills/` (also reads `~/.claude/skills/`) | `~/.cursor/mcp.json` |
| Codex CLI | `~/.agents/skills/` | `~/.codex/config.toml` |

```bash
git clone https://github.com/ChosenXu/eagle-tag-governance.git \
  <skills-dir>/eagle-tag-governance
```

Or copy the folder manually into the skills directory of your agent.

## Prerequisites

- The Eagle desktop app must be running.
- `eagle-mcp` must be registered as a stdio MCP server in your agent's MCP config:

```json
{
  "mcpServers": {
    "eagle-mcp": {
      "command": "node",
      "args": ["<home>/Library/Application Support/Eagle/Plugins/mcp-server/modules/mcp-proxy.js"]
    }
  }
}
```

> Codex CLI uses TOML instead: in `~/.codex/config.toml`, add `[mcp_servers.eagle-mcp]` with `command = "node"` and `args = ["<home>/Library/Application Support/Eagle/Plugins/mcp-server/modules/mcp-proxy.js"]`.

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
