# Changelog / 更新日志

All notable changes to this skill are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/), and this
project adheres to [Semantic Versioning](https://semver.org/).

## [1.0.0] - 2026-09-07

### Added
- Initial release: a vocabulary-level Eagle tag governance skill.
- Audit workflow: `tag_get` / `tag_count` to list every tag with usage count.
- Opportunity detection: synonyms, spelling/case/space variants, low-frequency noise (count 0/1), and drift from the three-dimension controlled taxonomy.
- Editable `merge_plan.json` (`merges` / `renames` / `retire`).
- Dry-run preview (Phase 3a) + authorization gate (Phase 3b) before any write.
- Execution via `tag_merge` / `tag_update`, plus `item_remove_tags` for the retire-without-merge path.
- Verification (Phase 5): read tags back to confirm source disappeared and counts are correct.
- Undo mapping export (`tag_undo_mapping.json`) before any write.
- Eight-language normative vocabulary (`vocabulary*.md`) shared with `eagle-untagged-organizer` as the canonical target.
- `references/gotchas.md` (irreversible, name-based, no `tag_delete`, group full-replacement) and `references/merge-templates.md`.

### Notes
- Eagle's MCP has **no `tag_delete` tool** — "retire" can only merge into a canonical target or strip the tag from items; full deletion is a manual UI step.
- Split out from `eagle-untagged-organizer` per the earlier split-plan; this skill handles tag vocabulary only, not asset naming/annotation.
