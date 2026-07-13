---
name: wewrite-style
description: |
  WeWrite 风格设置模块：首次使用引导（onboard）+ 重设公众号写作风格配置（style.yaml）。
  触发关键词：重新设置风格、修改风格配置、设置公众号风格、公众号首次设置、换写作人格、
  改排版主题偏好。也由主入口 wewrite 在缺 style.yaml 时自动激活。
  不应被通用的"改文风"、"润色"触发——那是编辑动作，不是配置动作。
allowed-tools:
  - Bash
  - Read
  - Write
  - Edit
  - Glob
---

# wewrite-style — 风格设置 / Onboard

<!-- wewrite:standalone-start -->
## 运行约定

- **CLI**：确定性操作走 `wewrite` 命令（需在 PATH；缺失则引导 `uv tool install git+https://github.com/oaker-io/wewrite.git`，或在仓库里 `bash install.sh`）。
- **{home}**：用户状态目录 = `$WEWRITE_HOME` 或 `~/.wewrite`（`wewrite home` 可查）。config/style/history/playbook/output/exemplars 全在 {home}，不在仓库；references 文档中的状态路径同此约定。
- **`读取: <路径>`** = 用文件读取工具真实读完该文件再继续，不是注释。
- **references/**：本 skill 自带 `{skill_dir}/references/`；references 文档内的 `{skill_dir}` 即本 skill 目录。
- 本模块是**交互式**的（需要问用户问题），不受主管道"全自动"约束。
<!-- wewrite:standalone-end -->

## 执行

**触发场景**：
1. 主入口 Step 1 发现 `{home}/style.yaml` 不存在（首次使用）
2. 用户说"重新设置风格"、"修改配置"

两种场景都执行：

```
读取: {skill_dir}/references/onboard.md
```

按 onboard.md 的 Phase 1-4 完成：交互式收集信息 → 生成 `{home}/style.yaml` →
可选 Playbook 建库 → 试跑询问。重设风格时以现有 style.yaml 为基线，只改用户要改的字段，
改完展示全文让用户确认。

**完成后**：若由主管道激活（首次 onboard），回到主管道 Step 1 继续；若用户单独触发，
告知"配置已更新，下次写作自动生效"。
