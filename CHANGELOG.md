# Changelog / 更新日志

All notable changes to this skill are documented in this file.
本文件记录本技能所有重要变更。

The format is based on [Keep a Changelog](https://keepachangelog.com/), and this project adheres to [Semantic Versioning](https://semver.org/).
格式参考 Keep a Changelog，版本号遵循语义化版本（SemVer）。

## [1.0.5] - 2026-09-10

### Changed / 变更

- Per-platform documentation extended to Gemini CLI and GitHub Copilot: the README install table gained rows for both (skills directories and MCP config files), the prerequisites section gained their `eagle-mcp` registration commands (`~/.gemini/settings.json` / `gemini mcp add`; `~/.copilot/mcp-config.json` / `copilot mcp add`), and platform listings in the README intro and SKILL.md prerequisites now include both.
  分平台文档扩展至 Gemini CLI 与 GitHub Copilot：README 安装表新增两行（skills 目录与 MCP 配置文件），前置条件补充两家的 `eagle-mcp` 注册方式（`~/.gemini/settings.json` / `gemini mcp add`；`~/.copilot/mcp-config.json` / `copilot mcp add`），README 开篇与 SKILL.md 前置条件的平台列举同步收录。
- Install section now notes the `~/.agents/skills/` interop alias: Codex CLI, Gemini CLI, GitHub Copilot, and Cursor all read it, so one install location serves all four.
  安装章节新增 `~/.agents/skills/` 互操作别名说明：Codex CLI、Gemini CLI、GitHub Copilot 与 Cursor 均读取该目录，一处安装四平台同时发现。

### Notes / 说明

- Version bumped 1.0.4 → 1.0.5 (PATCH: documentation only). Client info and the `--skill-version` default are updated to match; no workflow or write-behavior changes.
  版本 1.0.4 → 1.0.5（PATCH：纯文档）；clientInfo 与 `--skill-version` 默认值同步更新；工作流与写入行为无任何变化。

## [1.0.4] - 2026-09-10

### Changed / 变更

- README restructured for cross-platform use: intro now presents the skill as Agent Skills-standard (not WorkBuddy-specific), and Install / Prerequisites gained a per-platform table (WorkBuddy / Claude Code / Cursor / Codex) covering skills directories and `eagle-mcp` MCP config, with a JSON config example (plus a TOML variant for Codex).
  README 面向跨平台重构：开篇改为「符合 Agent Skills 标准」的定位（不再是 WorkBuddy 专属），安装/前置条件新增四平台对照表（WorkBuddy / Claude Code / Cursor / Codex），覆盖 skills 目录与 `eagle-mcp` 配置，附 JSON 配置示例（Codex 另附 TOML 写法）。
- SKILL.md prerequisites and Phase 0a no longer reference `~/.workbuddy/mcp.json` or the WorkBuddy connector panel — they now describe generic MCP registration and point to the README's per-platform examples.
  SKILL.md 前置条件与 Phase 0a 不再指向 `~/.workbuddy/mcp.json` 与 WorkBuddy 连接器面板，改为通用 MCP 注册描述，并指向 README 的分平台示例。
- Gotchas wording generalized from "WorkBuddy MCP wrapper / harness" to "host agent's tool-calling layer"; the array-param schema rule and the serialization-quirk workaround (drive writes through `apply_tag_governance.py`) are unchanged in substance.
  排障文档措辞泛化：「WorkBuddy MCP wrapper / harness」改为「宿主 Agent 的工具调用层」；数组参数 schema 规则与序列化缺陷绕行方案（改走 `apply_tag_governance.py`）实质不变。

### Notes / 说明

- Version bumped 1.0.3 → 1.0.4 (PATCH: documentation wording only). Client info and the `--skill-version` default are updated to match; no workflow or write-behavior changes.
  版本 1.0.3 → 1.0.4（PATCH：仅文档措辞）；clientInfo 与 `--skill-version` 默认值同步更新；工作流与写入行为无任何变化。

## [1.0.3] - 2026-09-08

### Fixed / 修复

- Gotchas guidance corrected (verified on a scratch library): duplicate-named tags created by a mis-aimed API rename are merged automatically when the library is re-opened (forced re-index) — they usually do **not** require manual UI merging. The Eagle tag panel lists tags per object and is the authoritative object count.
  修正排障文档口径（一次性库实测验证）：误向 API rename 产生的同名标签会在**重开库/重索引时被 Eagle 自动合并**，通常**无需**手动 UI 合并；Eagle 标签面板按对象展示，是对象数目的权威口径。

### Notes / 说明

- Version bumped 1.0.2 → 1.0.3 (PATCH: documentation only). Client info and the `--skill-version` default are updated to match; no code changes.
  版本 1.0.2 → 1.0.3（PATCH：纯文档）；clientInfo 与 `--skill-version` 默认值同步更新；无代码改动。

## [1.0.2] - 2026-09-08

### Fixed / 修复

- The summary `verified_ok` now counts successfully applied renames as well as removed merge sources, so `requested` and `verified_ok` are symmetric for rename-only plans; a rename whose target got duplicated is excluded and surfaced by the duplicate-name check instead.
  修复汇总指标：`verified_ok` 现同时统计成功应用的 rename 与消失的 merge 源——纯 rename 计划下 `requested` 与 `verified_ok` 对称；目标被复制（重名）的 rename 不计入成功，改由重名检测提示。
- Renames that do not verify are now printed individually (`UNVERIFIED <old> -> <new>`) with the live per-op verdict and a stale-index hint, instead of only appearing in the exit code.
  未通过校验的 rename 现在逐条打印（`UNVERIFIED <旧名> -> <新名>`），附实时单操作判定与陈旧索引提示，而不再仅体现在退出码。

### Notes / 说明

- Version bumped 1.0.1 → 1.0.2 (PATCH). Client info and the `--skill-version` default are updated to match.
  版本 1.0.1 → 1.0.2（PATCH）；clientInfo 与 `--skill-version` 默认值同步更新。
- Write behavior is unchanged; this release only aligns the summary metrics and messages with the per-op verdicts introduced in 1.0.1.
  写入行为无变化；本版仅对齐汇总指标与提示文案，与 1.0.1 引入的单操作判定保持一致。

## [1.0.1] - 2026-09-08

### Added / 新增

- Per-operation success verification: parse each op's `affectedItems` from the live proxy response instead of trusting the batch-level `isError` flag (which stays `false` even for silent no-op merges).
  单操作级成功校验：解析代理实时响应中每个操作的 `affectedItems`，不再信任批次级 `isError`（静默 no-op 合并时它仍为 `false`）。
- Auto-create missing merge targets by renaming one source into each missing target before merging the remaining sources.
  合并前自动创建缺失的目标标签：先把其一个源标签改名为目标名，再合并其余源。
- Back-off retry for merges that report `affectedItems: 0` while their source actually has items.
  对「`affectedItems` 为 0 但源标签非空」的合并按退避策略自动重试。
- Duplicate-named tag detection after writes (a mis-aimed rename that copied instead of folded is flagged `CRITICAL`).
  写入后检测同名标签对象（误向 rename 复制而非折叠会被标记为 `CRITICAL`）。
- Offline `--selftest` mode for the parsers (no Eagle connection required).
  新增离线 `--selftest` 自检模式（无需连接 Eagle）。

### Fixed / 修复

- `tag_merge` could report success while moving 0 items when the target tag was created via the API in the same session (silent no-op); it is now retried with back-off and, if still empty, surfaced as `ZERO-MOVE`.
  修复 `tag_merge` 在「目标为本会话内由 API 新建」时假成功（实际移动 0 项）的静默失败——现在会退避重试，仍失败则上报 `ZERO-MOVE`。
- `tag_update` renaming a source onto an existing tag name duplicated the tag instead of merging into it; the run now flags the resulting duplicate names.
  修复 `tag_update` 把源标签改名为已存在标签名时复制出同名对象而非合并——现在会标记产生的同名标签。
- Verification no longer labels a possibly-stale tag index as a write failure; only live per-op verdicts (`ZERO-MOVE` / error) or detected duplicates set the failure outcome.
  校验不再把可能陈旧的标签索引误判为写入失败；仅以实时单操作判定（`ZERO-MOVE` / 报错）或检测到的同名标签作为失败依据。
- The process now exits non-zero when any op fails to verify or duplicate tag names are found, so automation can rely on the exit code.
  任一操作未通过校验或发现同名标签时，进程以非零码退出，自动化可直接依据退出码判断。
- `--selftest` checks are now individually caught and counted instead of aborting on the first assertion.
  修复 `--selftest`：各检查项独立捕获并累计失败数，而非在首个断言处中断。

### Notes / 说明

- Version bumped 1.0.0 → 1.0.1 (PATCH: reliability hardening plus documentation). Client info and the `--skill-version` default are updated to match.
  版本 1.0.0 → 1.0.1（PATCH：可靠性加固＋文档）；clientInfo 与 `--skill-version` 默认值已同步更新。
- `references/gotchas.md` gains two troubleshooting sections: the WorkBuddy array-param harness quirk and the silent session-created-target failures (Symptoms A/B with real-library evidence).
  `references/gotchas.md` 新增两节排障文档：WorkBuddy 工具包装层拒收数组参数、会话内新建标签上的静默失败（A/B 症状，含真实库证据）。
- Known limitation: silent failures on session-created targets cannot be fully defeated from code — if the output shows `ZERO-MOVE` or `CRITICAL: duplicate tag names`, finish the remaining merges in the Eagle UI.
  已知限制：会话内新建标签上的静默失败无法完全用代码绕过——输出出现 `ZERO-MOVE` 或 `CRITICAL` 同名提示时，剩余合并请在 Eagle 界面手动完成。

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
