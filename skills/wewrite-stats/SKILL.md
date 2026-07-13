---
name: wewrite-stats
description: |
  WeWrite 数据复盘模块：拉取微信公众号文章的阅读/分享/点赞数据，回填历史记录并给出
  选题、标题、框架的调整建议。
  触发关键词：看看文章数据、文章数据怎么样、效果复盘、看看表现、阅读量怎么样。
  需要公众号/WeWrite 上下文；不应被通用的"数据分析"触发。
allowed-tools:
  - Bash
  - Read
  - Write
  - Edit
---

# wewrite-stats — 文章数据复盘

<!-- wewrite:standalone-start -->
## 运行约定

- **CLI**：确定性操作走 `wewrite` 命令（需在 PATH；缺失则引导 `uv tool install git+https://github.com/oaker-io/wewrite.git`，或在仓库里 `bash install.sh`）。
- **{home}**：用户状态目录 = `$WEWRITE_HOME` 或 `~/.wewrite`（`wewrite home` 可查）。config/style/history/playbook/output/exemplars 全在 {home}，不在仓库；references 文档中的状态路径同此约定。
- **`读取: <路径>`** = 用文件读取工具真实读完该文件再继续，不是注释。
- **references/**：本 skill 自带 `{skill_dir}/references/`；references 文档内的 `{skill_dir}` 即本 skill 目录。
<!-- wewrite:standalone-end -->

## 执行

```
读取: {skill_dir}/references/effect-review.md
```

按其流程执行：`fetch_stats.py --days 7` 拉数据 → 匹配并回填 `history.yaml` 的
stats 字段 → 分析最好/最差表现及原因 → 给出后续选题/标题/框架的调整建议。

**前置**：需要 config.yaml 里的微信 API 凭证。缺凭证 → 告知用户"数据复盘需要配置
公众号 API（config.yaml），当前只能基于 history.yaml 已有记录做定性分析"，然后就
history.yaml 现有内容能分析多少分析多少。刚发布的文章 → 告知等 24h 后再看。

**下游影响**：回填的 stats 会被选题模块（wewrite-topic）读取——哪种框架/增强策略
表现好会加权到下次推荐。这是数据闭环的一半，另一半是 wewrite-learn 的改稿飞轮。
