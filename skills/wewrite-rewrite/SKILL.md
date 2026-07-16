---
name: wewrite-rewrite
description: |
  WeWrite 多平台改写模块：把一篇公众号文章（或指定源稿）内容级真改写成其他平台版本，
  当前支持小红书（图文笔记）、抖音（口播脚本），检查编辑质量与源稿相似度。
  触发关键词：改写成小红书、小红书版、抖音版、口播稿、多平台分发、一稿多发、平台改写。
  不应被"翻译"、"缩写"、"换个标题"触发——那些是单平台编辑动作。
allowed-tools:
  - Bash
  - Read
  - Write
  - Edit
  - Glob
---

# wewrite-rewrite — 一源多平台改写

## 运行约定

- **CLI**：确定性操作走 `wewrite` 命令（需在 PATH；缺失则引导 `uv tool install wewrite`，或在仓库里 `bash install.sh`）。
- **{home}**：用户状态目录 = `$WEWRITE_HOME` 或 `~/.wewrite`（`wewrite home` 可查）。config/style/history/playbook/output/exemplars 全在 {home}，不在仓库；references 文档中的状态路径同此约定。
- **`读取: <路径>`** = 用文件读取工具真实读完该文件再继续，不是注释。
- **references/**：本 skill 自带 `{skill_dir}/references/`；references 文档内的 `{skill_dir}` 即本 skill 目录。
- **任务状态**：用 `wewrite run show` 读取当前任务。

## 前置

1. **源文章**：按优先级解析——用户指定的文件/粘贴内容 > 当前任务的
   `artifacts.article`。都没有 → 问用户"要改写哪篇？给我文件路径
   或直接粘贴全文"。确定后把源复制/保存到当前任务目录的 `source.md`（质量门要用）。
2. **目标平台**：用户点名了就用；没点名 → 列出 `{skill_dir}/platforms/` 下的可用
   平台（当前：xiaohongshu 小红书、douyin 抖音）问用户要哪几个，或"全部"。

## 执行

```
读取: {skill_dir}/references/multiplatform-rewrite.md
```

对每个目标平台：

1. `读取: {skill_dir}/platforms/<id>.yaml`，按其 `rewrite_brief`、字数区间、
   标签数、输出格式改写。
2. 遵守 multiplatform-rewrite.md 的原创铁律（内容级真改，重构信息顺序/开头/表达，
   不是洗稿）与人设一致要求（persona 内核不变，只适配表达方式）。
3. 过双质量门（multiplatform-rewrite.md「质量门」小节）：quality_score ≥ 60、
   与源及其他平台版本的 `max_similarity` ≤ 0.6；不过重写该版本，最多 2 次。
4. 写到当前任务目录的 `<platform 的 output_filename>`，不覆盖源稿或其他任务。

## 完成

汇报每个平台版本的产出路径、字数、质量门结果；小红书版说明配图情况（复用了源稿
哪几张图，或"需补图"）。提醒：各平台账号发布是用户手动动作，WeWrite 当前只发
公众号草稿箱。
