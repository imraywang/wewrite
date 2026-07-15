---
name: wewrite-learn
description: |
  WeWrite 自学习模块：从用户的人工修改中学习写作偏好（playbook 飞轮）、导入范文建风格库、
  从公众号文章学习排版主题。
  触发关键词：学习我的修改、我改了学习一下、导入范文、学习这篇文章、查看范文库、
  学习排版、学排版。
  不应被通用的"学习"、"总结这篇文章"触发——需要公众号/WeWrite 上下文。
allowed-tools:
  - Bash
  - Read
  - Write
  - Edit
  - Glob
  - WebFetch
---

# wewrite-learn — 自学习（改稿飞轮 / 范文库 / 排版学习）

## 运行约定

- **CLI**：确定性操作走 `wewrite` 命令（需在 PATH；缺失则引导 `uv tool install wewrite`，或在仓库里 `bash install.sh`）。
- **{home}**：用户状态目录 = `$WEWRITE_HOME` 或 `~/.wewrite`（`wewrite home` 可查）。config/style/history/playbook/output/exemplars 全在 {home}，不在仓库；references 文档中的状态路径同此约定。
- **`读取: <路径>`** = 用文件读取工具真实读完该文件再继续，不是注释。
- **references/**：本 skill 自带 `{skill_dir}/references/`；references 文档内的 `{skill_dir}` 即本 skill 目录。

## 子功能分发

| 用户说 | 动作 |
|--------|------|
| 学习我的修改 / 我改了，学习一下 | `读取: {skill_dir}/references/learn-edits.md`，按其流程执行。支持本地 markdown 修改与微信草稿箱同步（`wewrite learn-edits --from-wechat`） |
| 学习排版 / 学排版 + URL | `wewrite learn-theme <url> --name <name>`，提取后提示用户设置 style.yaml 的 theme 字段 |
| 学习这篇文章 / 导入范文 + URL | `wewrite fetch-article <url> -o /tmp/article.md && wewrite exemplar /tmp/article.md -s <账号名>`；默认第三方 |
| 导入范文 + 本地文件 | `wewrite exemplar <文件路径>`；用户明确为本人文章时加 `--user-authored` |
| 查看范文库 | `wewrite exemplar --list` |

**范文库的用途**：exemplars 会在写作模块（wewrite-write）按框架类型注入初稿 prompt，
只用于校准结构和节奏，不能复用其中的观点、句子或个人经历。导入完成后告知用户库里现有
多少篇、覆盖哪些 category 和所有权标记。

**改稿飞轮的价值**：每次学习让下一篇初稿更接近用户风格。learn-edits.md 的
只有重复出现或用户明确确认的同范围规则才会成为硬约束；单次修改始终只是软参考。
