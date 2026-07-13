---
name: wewrite-topic
description: |
  WeWrite 选题模块：抓取全网热点 + 历史表现分析 + SEO 关键词，为公众号生成 10 个
  评分排序的选题（含常青选题）。
  触发关键词：公众号选题、找几个选题、今天写什么、热点选题、热搜选题、选题建议。
  需要公众号/微信上下文；不应被抖音/短视频/网站的选题需求触发。
allowed-tools:
  - Bash
  - Read
  - Write
  - WebSearch
---

# wewrite-topic — 选题

<!-- wewrite:standalone-start -->
## 运行约定

- **CLI**：确定性操作走 `wewrite` 命令（需在 PATH；缺失则引导 `uv tool install git+https://github.com/oaker-io/wewrite.git`，或在仓库里 `bash install.sh`）。
- **{home}**：用户状态目录 = `$WEWRITE_HOME` 或 `~/.wewrite`（`wewrite home` 可查）。config/style/history/playbook/output/exemplars 全在 {home}，不在仓库；references 文档中的状态路径同此约定。
- **`读取: <路径>`** = 用文件读取工具真实读完该文件再继续，不是注释。
- **references/**：本 skill 自带 `{skill_dir}/references/`；references 文档内的 `{skill_dir}` 即本 skill 目录。
- **管道状态**：`{home}/output/_state.yaml`（契约见主入口 wewrite 的 `references/pipeline-state.md`）。

## 前置

- `{home}/style.yaml` 存在 → 提取 `topics`、`content_style`。不存在 → 问用户"你的
  公众号主要写哪几个方向？"用回答临时代替 topics，并提示可用 **wewrite-style** 完成完整设置。
<!-- wewrite:standalone-end -->

## 2.1 热点抓取

```bash
wewrite hotspots --limit 30
```

**降级**：脚本报错 → WebSearch "今日热点 {topics第一个垂类}"

## 2.2 历史分析 + SEO

```
读取: {home}/history.yaml（不存在则跳过）
```

```bash
wewrite seo --json {关键词}
```

历史分析（有 stats 数据时）：
- 统计哪种 `framework` 的文章表现最好（阅读量/分享率）→ 推荐框架时加权
- 统计哪种 `enhance_strategy` 的文章表现最好 → 增强策略选择时参考
- 近 7 天已写的关键词降分（去重）

**降级**：SEO 脚本报错 → LLM 判断；history 无 stats → 跳过效果分析，仅做去重

## 2.3 生成选题

```
读取: {skill_dir}/references/topic-selection.md
```

生成 **10 个选题**，其中：
- **7-8 个热点选题**：基于 2.1 的热点，按 topic-selection.md 规则评分
- **2-3 个常青选题**：不依赖热点，从用户的 `topics` 领域生成长尾内容（教程/方法论/经验总结/工具推荐），标注为"常青"。适合 content_style 为干货型/测评型的用户

每个选题含标题、评分、点击率潜力、SEO 友好度、推荐框架。

- 自动模式 → 选最高分
- 交互模式 / 单独激活 → 展示全部，等用户选

## 完成

把选定选题写入 `{home}/output/_state.yaml`：`topic.title`、`topic.keywords`、
`topic.source: "热点抓取"`、`topic.framework_hint`（推荐框架），`steps_done` 追加 `topic`。
单独激活且用户只要选题列表时，展示 10 个选题即可；用户选定后写入状态并提示
"可以直接说'就写这个'进入写作（wewrite-write）"。
