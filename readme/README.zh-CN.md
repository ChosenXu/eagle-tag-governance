# Eagle Tag Governance

[English](../README.md) | 简体中文

一个 [WorkBuddy](https://www.workbuddy.cn/) Skill，通过 `eagle-mcp` 连接器治理 [Eagle](https://eagle.cool/) 素材库的**标签词表**——合并、重命名、规范化、去重与退役已有标签，让标签体系保持干净一致。

## 它能做什么

这个 Skill 不处理单张素材，而是作用于*标签列表本身*：

1. **审计** — 列出全部标签及使用次数（`tag_get` / `tag_count`）。
2. **识别** — 发现同义词、拼写/大小写/空格变体、低频噪声（`count = 0/1`）、以及偏离三维受控词表的标签。
3. **规划** — 生成可编辑的 `merge_plan.json`（`merges` / `renames` / `retire`）。
4. **预览与授权** — 展示每个操作的影响范围，你审阅并确认（未经你同意绝不写入）。
5. **执行** — 安全地应用 `tag_merge` / `tag_update`。
6. **校验** — 回读标签，确认源标签已消失、计数正确。

## 亮点

1. **安全优先** — 每次写入都先干跑再授权。标签合并/重命名是全局不可逆操作，因此预览与确认门槛绝不跳过。
2. **撤销映射** — 写入前导出 `tag_undo_mapping.json`（source→target / old→new），出错时可手动反向恢复。
3. **规范目标** — 以与 `eagle-untagged-organizer` 共用的三维受控词表（`vocabulary*.md`）作为"规范目标"判断漂移，两个 Skill 保持一致。
4. **坦诚说明限制** — Eagle 的 MCP 没有 `tag_delete`；退役标签只能合并或剥离（彻底删除需在 Eagle 界面手动操作），方案里如实标注。

## 安装

将本仓库克隆到 WorkBuddy 的 skills 目录：

```bash
git clone https://github.com/ChosenXu/eagle-tag-governance.git \
  ~/.workbuddy/skills/eagle-tag-governance
```

或手动将文件夹复制到 `~/.workbuddy/skills/`。

## 前置条件

- Eagle 桌面应用必须处于运行状态。
- `eagle-mcp` 必须在 `~/.workbuddy/mcp.json` 中配置，并在连接器面板中信任。

## 用法

提及 Eagle / `eagle-mcp` / 标签清理意图，如「合并标签」「整理标签」「规范化标签」「清理标签词表」，Skill 即驱动工作流。完整流程见 [`SKILL.md`](../SKILL.md)（预检 → 扫描 → 识别 → 干跑 → 授权 → 执行 → 校验）。

> 如需为**未打标签素材**命名 / 打标签 / 写标注，请改用 [`eagle-untagged-organizer`](https://github.com/ChosenXu/eagle-untagged-organizer)。两个 Skill 相互独立。

## 结构

```
SKILL.md                     # Skill 定义与工作流
references/
  vocabulary.md              # 简体中文规范词表（canonical 目标）
  vocabulary-zh-Hant.md      # 繁體中文（港式）规范词表
  vocabulary-en.md           # English 规范词表
  vocabulary-ja.md           # 日本語规范词表
  vocabulary-ko.md           # 한국어规范词表
  vocabulary-ru.md           # Русский 规范词表
  vocabulary-es.md           # Español 规范词表
  vocabulary-de.md           # Deutsch 规范词表
  gotchas.md                 # 标签操作专用坑（不可逆、按名称、无 tag_delete 等）
  merge-templates.md         # merge_plan 结构与示例
scripts/
  apply_tag_governance.py    # 批量执行 tag_merge / tag_update（stdio MCP 客户端，阶段3）
  build_tag_plan.py          # 从分析结果生成 merge_plan.json（阶段3）
  export_undo_mapping.py     # 写入前导出 tag_undo_mapping.json（阶段3）
```

## 许可证

[MIT](../LICENSE)
