# Changelog / 更新日志

All notable changes to this skill are documented in this file.
本文件记录本技能所有重要变更。

The format is based on [Keep a Changelog](https://keepachangelog.com/), and this project adheres to [Semantic Versioning](https://semver.org/).
格式参考 Keep a Changelog，版本号遵循语义化版本（SemVer）。

## [1.0.0] - 2026-09-07

### Added / 新增

- Initial release: a vocabulary-level Eagle tag governance skill.
  初版发布：一个词表级（vocabulary-level）的 Eagle 标签治理技能。
- Audit workflow: `tag_get` / `tag_count` to list every tag with usage count.
  审计流程：通过 `tag_get` / `tag_count` 列出每个标签及其使用次数。
- Opportunity detection: synonyms, spelling/case/space variants, low-frequency noise (count 0/1), and drift from the three-dimension controlled taxonomy.
  机会识别：同义标签、拼写 / 大小写 / 空格变体、低频噪声（使用次数 0/1），以及偏离三维受控词表的标签。
- Editable `merge_plan.json` (`merges` / `renames` / `retire`).
  可编辑的 `merge_plan.json`（合并 / 重命名 / 退役）。
- Dry-run preview (Phase 3a) + authorization gate (Phase 3b) before any write.
  写入前提供干跑预览（Phase 3a）＋ 授权门槛（Phase 3b）。
- Execution via `tag_merge` / `tag_update`, plus `item_remove_tags` for the retire-without-merge path.
  执行阶段经 `tag_merge` / `tag_update` 写入，退役无合并目标时额外用 `item_remove_tags` 从素材剥离。
- Verification (Phase 5): read tags back to confirm source disappeared and counts are correct.
  校验（Phase 5）：回读标签，确认源标签已消失、计数正确。
- Undo mapping export (`tag_undo_mapping.json`) before any write.
  写入前导出撤销映射（`tag_undo_mapping.json`）。
- Eight-language normative vocabulary (`vocabulary*.md`) shared with `eagle-untagged-organizer` as the canonical target.
  八语种规范词表（`vocabulary*.md`），与 `eagle-untagged-organizer` 共享，作为治理的规范目标。
- `references/gotchas.md` (irreversible, name-based, no `tag_delete`, group full-replacement) and `references/merge-templates.md`.
  `references/gotchas.md`（不可逆、按名称操作、无 `tag_delete`、分组全量替换）与 `references/merge-templates.md`。

### Notes / 说明

- Eagle's MCP has **no `tag_delete` tool** — "retire" can only merge into a canonical target or strip the tag from items; full deletion is a manual UI step.
  Eagle 的 MCP **没有 `tag_delete` 工具**——「退役」只能合并进规范目标或从素材剥离，彻底删除需在 Eagle 界面手动完成。
- Split out from `eagle-untagged-organizer` per the earlier split-plan; this skill handles tag vocabulary only, not asset naming/annotation.
  依据早前的拆分方案从 `eagle-untagged-organizer` 剥离而出；本技能只管标签词表，不涉及素材命名 / 标注。
