---
name: wewrite
description: |
  微信公众号内容主入口：完成选题、素材、写作和审稿，并按用户要求独立追加配图、排版或草稿箱发布。
  也负责把风格设置、学习修改、数据复盘和多平台改写分发给对应 wewrite-* 模块。
  触发关键词：公众号、微信文章、微信推文、草稿箱、微信排版、写公众号、写一篇。
  通用文章、博客、邮件、短视频和网站 SEO 不触发。
allowed-tools:
  - Bash
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - WebSearch
  - WebFetch
---

# WeWrite — 公众号内容主入口

## 运行原则

- 默认连续完成内容流程，不在每一步停下来。用户说“交互模式”时，才在选题和框架处确认。
- 每篇文章必须用独立任务目录，不能覆盖另一篇文章。
- “写一篇”默认只交付审过的本地稿；生成图片和发布都不是默认动作。
- 配图、排版和发布是正文完成后的独立动作；不得为了排版或发布自动触发生图。
- “完整制作”是正文、配图和本地预览的组合快捷方式；只有明确说“推到草稿箱/发布”才允许调用发布命令。
- 搜索失败时可以继续写分析和经验判断，但不得把模型记忆包装成已核实的事实。

`{home}` 是 `wewrite home` 返回的状态目录。`{skill_dir}` 是本 skill 目录。确定性操作走 `wewrite` 命令。

## 路由

| 用户意图 | 模块 |
|---|---|
| 重设风格 | `wewrite-style` |
| 只要选题 | `wewrite-topic` |
| 检查文章 | `wewrite-review` |
| 封面或配图 | `wewrite-visual` |
| 排版、预览、草稿箱、图片帖 | `wewrite-publish` |
| 学习修改、范文、主题 | `wewrite-learn` |
| 数据复盘 | `wewrite-stats` |
| 多平台改写 | `wewrite-rewrite` |

环境有 Skill 工具时激活同名 skill；否则完整读取兄弟目录的 `SKILL.md` 后执行。

## 内容流程

### 1. 建立或恢复任务

先运行 `wewrite diagnose --json`。命令缺失或依赖失败才引导安装；缺少风格文件是正常首次设置，转 `wewrite-style`。

根据用户原话选择模式：

```bash
# 默认“写一篇”：不生图、不发布
wewrite run start --topic "{选题，可空}" --mode draft --visual-mode none

# “完整制作”：先完成正文；正文封存后再独立配图和预览
wewrite run start --topic "{选题，可空}" --mode complete --visual-mode none

# “推到草稿箱”：用户已明确授权发布，但不因此自动生图
wewrite run start --topic "{选题，可空}" --mode publish --visual-mode none
```

把 diagnose 的 flags 和当天日期写入任务：

```bash
wewrite run update --patch '{"flags": {"skip_publish": false, "skip_image_gen": false, "use_writer_model": false, "needs_onboard": false, "diagnosed_at": "YYYY-MM-DD"}}'
```

如果用户说“继续上次”，先 `wewrite run list`，明确唯一任务后 `wewrite run resume <run_id>`；不要新建任务。

### 2. 选题

用户已给选题就记录并跳过选择；否则执行 `wewrite-topic`。完成后：

```bash
wewrite run step topic completed
```

### 3-4. 文章任务、证据与初稿

执行 `wewrite-write`。先保存 `artifacts.brief` 和 `artifacts.claims`，再把初稿保存到
`artifacts.draft`；所有网页素材同步记录到本任务的 `sources.yaml`。初稿不是成稿。

### 5. 编辑审稿

执行 `wewrite-review`。事实、观点、实用性、账号声音和可读性是主标准；发现可修问题要直接
改稿并复审。只有编辑决定为 `pass` 且 `artifacts.review_report` 显示
`publishable=true`，才能把最终正文写入 `artifacts.article`。工具分数只提示可能的问题。

### 6. 封存正文

确认文章存在、编辑已通过且报告已保存后立即执行：

```bash
wewrite run finish
```

该命令封存正文和来源并写入历史。封存后仍可在当前文章上追加配图、预览和发布结果，
但不得改写原始正文。

## 可选后续动作

### A. 配图

- 用户说“配个封面”时，把 `visual.mode` 设为 `cover`。
- 用户说“完整配图”或“完整制作”时，把 `visual.mode` 设为 `full`。
- 用户只要提示词时设为 `prompts`；缺少图片配置也自动降级为提示词。
- 执行 `wewrite-visual`。它只能生成独立图片和带图副本，不得覆盖 `artifacts.article`。

文章已经完成也直接使用当前任务，不要新建写作任务。严格遵守 `max_images` 与 `max_cost`。

### B. 排版与发布

执行 `wewrite-publish`。它优先排版带图副本，没有则排版原始正文，且不自动调用
`wewrite-visual`。用户本轮明确要求发布时先执行 `wewrite run permission publish allow`；
用户撤回时执行 `wewrite run permission publish deny`。只有 `permissions.publish=true` 且发布
配置可用、封面存在时才推草稿箱；其他情况一律生成本地预览。

### C. “完整制作”快捷方式

先完整跑完内容流程并封存正文，再依次执行 `wewrite-visual` 的 `full` 模式和
`wewrite-publish` 的本地预览。它是三个独立动作的连续调用，不赋予发布权限。

最后告诉用户标题、原始文章路径、带图副本路径、来源数量、图片/预览结果、是否进入
草稿箱，以及发生的降级。

## 失败与恢复

步骤失败时记录：

```bash
wewrite run step <topic|write|review|visual|publish> failed --error "简短原因"
```

内容步骤失败时保留当前任务，下次恢复后只重做失败或未完成的步骤。正文已经封存时，
配图或发布失败不改变文章的完成状态；发布失败回退到本地预览，图片失败保留提示词。
搜索失败要删掉无法核实的具体数字和引述。
