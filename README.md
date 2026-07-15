<div align="center">

# WeWrite · 公众号内容全流程 Skill

**一句话完成选题、素材、写作和审稿——配图、排版与发布随时按需追加**

选题 · 写作 · 编辑审稿 · 可选 AI 配图 · 18 主题排版 · 草稿箱推送 · 多平台改写 · 越用越像你

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://github.com/imraywang/wewrite/blob/main/LICENSE)
[![Checks](https://github.com/imraywang/wewrite/actions/workflows/checks.yml/badge.svg)](https://github.com/imraywang/wewrite/actions/workflows/checks.yml)
[![PyPI](https://img.shields.io/pypi/v/wewrite?color=059669&label=PyPI)](https://pypi.org/project/wewrite/)
[![Skills](https://img.shields.io/badge/skills-1%20主入口%20%2B%209%20模块-8b5cf6)](#-模块速查)
[![Themes](https://img.shields.io/badge/themes-18%20%2B%20learn--theme-f59e0b)](#-排版引擎)
[![Agents](https://img.shields.io/badge/Claude%20Code%20·%20Codex%20·%20OpenClaw%20·%20Hermes-supported-6366f1)](#-快速开始)

</div>

---

一个给 AI Agent（Claude Code / Codex / OpenClaw / Hermes 等）用的公众号内容 Skill。你说「写一篇公众号文章」，它会抓热点、评选题、搜真实素材、按你的人格风格出稿并完成编辑审稿。正文完成后，你可以直接交付，也可以再单独要求配图、排版预览或推送草稿箱。原始正文始终保留；配图会生成独立图片和带图副本。想改就按自己的意思改，再让它「学习我的修改」，下一篇会更像你。

```
"写一篇公众号文章"
  → 抓热点 → 选题评分 → 文章任务书 → 主张与来源清单
  → 安全内容增强 → 初稿（真实信息锚定 + 风格注入）
  → 编辑判断 → 必要时改稿并复审 → 交付成稿

完成后按需追加：
  ├─ 配封面 / 完整配图 → 图片 + 带图副本
  ├─ 排版预览           → 微信兼容 HTML
  └─ 推到草稿箱         → 明确授权且条件满足后发布
```

## ✨ 核心特性

- **一句话完成正文**：选题、素材、写作和审稿连续完成；说「交互模式」可在选题或框架处暂停确认。
- **后续动作真正独立**：配图、排版、发布都能在文章完成后单独执行；排版和发布不会偷偷触发生图。
- **模块化，one step at a time**：主入口 + 9 个独立 skill，只要选题说 `/wewrite-topic`、只要封面说 `/wewrite-visual`，缺前置会自己补齐。
- **写出能直接用的文章**：先明确读者问题、核心判断与证据边界，再写初稿；审稿不通过就直接改稿并复审，禁止编造作者经历。
- **7 套写作人格**：像选主题一样选文风，从深夜老友到冷静分析师，一行配置切换。
- **越用越像你**：编辑飞轮（学习你的修改）+ 范文风格库（SICO 式 few-shot）+ 阅读数据回填反哺选题。
- **18 主题排版引擎**：样式全内联、微信兼容修复、暗黑模式；`learn-theme` 还能从任意公众号文章学习一套新主题。
- **一稿多发**：小红书图文 / 抖音口播稿，内容级真改，检查编辑质量和源稿相似度。
- **成本可控**：可选把正文出稿路由给独立写作模型，实际费用取决于所选服务、模型和文章长度。

## 👀 效果预览

同一篇示例文章（[docs/demo-article.md](https://github.com/imraywang/wewrite/blob/main/docs/demo-article.md)）× 6 个主题，`wewrite preview` 真实渲染长图（含 label 小标签、steps 步骤卡、callout / timeline / quote / summary 组件与 AIGC 声明脚注）：

<table>
<tr>
<td width="33%" align="center"><img src="https://raw.githubusercontent.com/imraywang/wewrite/main/docs/screenshots/professional-clean.png" width="250"><br><sub><b>professional-clean（默认）</b></sub></td>
<td width="33%" align="center"><img src="https://raw.githubusercontent.com/imraywang/wewrite/main/docs/screenshots/sspai.png" width="250"><br><sub><b>sspai</b></sub></td>
<td width="33%" align="center"><img src="https://raw.githubusercontent.com/imraywang/wewrite/main/docs/screenshots/warm-editorial.png" width="250"><br><sub><b>warm-editorial</b></sub></td>
</tr>
<tr>
<td width="33%" align="center"><img src="https://raw.githubusercontent.com/imraywang/wewrite/main/docs/screenshots/tech-modern.png" width="250"><br><sub><b>tech-modern</b></sub></td>
<td width="33%" align="center"><img src="https://raw.githubusercontent.com/imraywang/wewrite/main/docs/screenshots/bauhaus.png" width="250"><br><sub><b>bauhaus</b></sub></td>
<td width="33%" align="center"><img src="https://raw.githubusercontent.com/imraywang/wewrite/main/docs/screenshots/midnight.png" width="250"><br><sub><b>midnight</b></sub></td>
</tr>
</table>

> 全部 18 个主题：装好后 `wewrite gallery` 在浏览器里并排对比 + 一键复制。

## ✅ 适合 / ❌ 不适合

**✅ 适合**：公众号创作者的日常出稿（热点文/干货文/故事文/测评文）· 只想要某个环节的人（选题灵感、封面配图、质量自检、排版发布）· 想把已有文章一稿多发到小红书/抖音 · 想让 AI 逐渐学会自己文风的长期使用者。

**❌ 不适合**：普通网页/落地页排版（用前端 skill）· PPT/邮件/blog · 非公众号生态的 SEO · 追求组件级设计定制的纯排版需求（可以只用 `wewrite-publish`，但更推荐专门的排版 skill）。

## 🚀 快速开始

### 方式一：一键安装（推荐）

```bash
git clone --depth 1 https://github.com/imraywang/wewrite.git ~/wewrite
cd ~/wewrite && bash install.sh
```

`install.sh` 做三件事：装 `wewrite` CLI（uv/pipx，无则回退 venv）、把 10 个 skill 链接到 `~/.claude/skills/` 与 `~/.agents/skills/`（检测到 OpenClaw / Codex 时一并链接其 skills 目录）、把旧版用户状态迁到 `~/.wewrite/`。

### 方式二：skills.sh 按需挑模块

```bash
npx skills add imraywang/wewrite
```

skill 目录自包含、复制即用；CLI 另装一条：`uv tool install wewrite`（或 `pipx install wewrite`）。

### 方式三：让 AI 自己装

对任意 Agent 说一句：

> 请帮我安装 https://github.com/imraywang/wewrite 这个 skill（跑仓库里的 install.sh）

装好后直接开聊：

```
你：写一篇公众号文章                → 审过的本地成稿（默认不生图、不发布）
你：完整制作一篇公众号文章          → 成稿 + 配图 + 本地预览
你：推到公众号草稿箱                → 明确授权后才发布
你：今天写什么                      → 只要选题
你：检查一下                        → 生成档案 + 质量自检
你：改写成小红书                    → 多平台改写
你：学习我的修改                    → 编辑飞轮
你：看看有什么主题 / 换成 sspai 主题 → 主题画廊 / 重排版
你：做一个小绿书                    → 图片帖（横滑轮播）
你：更新                            → 升级到最新版
```

<details>
<summary><b>OpenClaw / Codex / Hermes</b>（三家均原生支持 folder-per-skill，无需构建转换）</summary>

**OpenClaw / Codex**：方式一的 `install.sh` 检测到 `~/.openclaw` / `~/.codex` 时已自动链接。手动装：

```bash
for s in ~/wewrite/skills/wewrite*; do ln -sfn "$s" ~/.openclaw/skills/$(basename "$s"); done
# Codex 同理，目标换成 ~/.codex/skills/
```

**Hermes**（自带技能管理器）：

```bash
hermes skills install imraywang/wewrite
```

各家均需 CLI 在 PATH：`uv tool install wewrite`。

</details>

### 配置（可选）

```bash
cp config.example.yaml ~/.wewrite/config.yaml
```

填入微信公众号 `appid`/`secret`（推送需要）和图片 API key（生图需要）。**写作不需要这些配置**；排版可以直接生成本地 HTML，请求配图但没有图片服务时会输出图片提示词。配了 `WEWRITE_WRITER_API_KEY` 则正文可交给独立写作模型；实际费用以你使用的服务为准。

## 🧩 模块速查

管道的每一段都是独立 skill。每篇文章保存在 `~/.wewrite/runs/<任务编号>/`，进度可恢复，
多篇同时进行也不会互相覆盖。上午选完题，下午说“继续上次”就能接上。

| 你说 | 激活 | 产出 |
|------|------|------|
| 今天写什么 / 找几个选题 | `wewrite-topic` | 10 个评分排序的选题 |
| 就这个选题写一篇 | `wewrite-write` | 文章任务书 + 主张与来源清单 + 初稿 |
| 检查一下 / 这篇怎么样 | `wewrite-review` | 事实核对 + 必要改稿 + 通过后生成成稿与编辑报告 |
| 给这篇配个封面 | `wewrite-visual` | 一张封面图；不改原始正文 |
| 给这篇完整配图 | `wewrite-visual` | 封面 + 必要内文图 + 带图副本 |
| 推到草稿箱 / 换个主题 | `wewrite-publish` | 条件满足时生成微信草稿，否则保留本地 HTML |
| 改写成小红书 / 抖音版 | `wewrite-rewrite` | 内容级真改的平台版本 |
| 学习我的修改 / 导入范文 | `wewrite-learn` | playbook 规则 / 风格库 |
| 看看文章数据 | `wewrite-stats` | 阅读数据回填 + 选题建议 |
| 重新设置风格 | `wewrite-style` | style.yaml |

## 🏗 架构：三层解耦

设计原则一句话：**prompt 负责判断，Python 负责确定性**。

| 层 | 位置 | 内容 |
|----|------|------|
| Prompt | `skills/`（10 个自包含 skill） | 选题、事实、观点、实用性和表达判断，每个 skill 自带 references/ |
| Runtime | `wewrite` CLI（pip 包） | 打分、转 HTML、调微信 API、生图、成本路由——确定性操作 |
| State | `~/.wewrite/`（`WEWRITE_HOME` 可覆盖） | 凭证、风格、历史、学习产物、输出文件——全部在仓库外 |

skill 目录复制到哪都能用；CLI 与 skill 独立安装升级；换机器只需带走 `~/.wewrite/`。

## 🔩 核心能力

| 能力 | 说明 | 所在 |
|------|------|------|
| 热点抓取 | 微博 + 头条 + 百度实时热搜 | `wewrite hotspots` |
| 高频需求 | 搜狗微信搜索垂类近期文章，用同题密度观察内容需求，不虚构阅读量 | `wewrite search-articles` |
| SEO 评分 | 百度 + 360 搜索量化评分 | `wewrite seo` |
| 选题生成 | 10 选题 × 3 维度评分 + 历史去重 | wewrite-topic |
| 素材采集 | WebSearch 核对数据/引述/案例，并为每篇文章保存来源账本 | wewrite-write / `wewrite sources` |
| 框架生成 | 7 套写作骨架（痛点/故事/清单/对比/热点解读/纯观点/复盘） | wewrite-write |
| 文章任务书 | 写前明确目标读者、问题、交付、核心判断、反方和边界 | wewrite-write |
| 主张与证据 | 区分事实、推断、意见与用户经历，逐项关联来源 | wewrite-write / `wewrite sources` |
| 内容增强 | 按框架补足可支持的新角度、行动条件、真实细节或决策标准 | wewrite-write |
| 编辑成稿 | 准确、观点、有用、合声、好读五项判断；不通过就直接改稿并复审 | wewrite-review / `wewrite content-eval` |
| 风险提示 | 11 项机械检查，定位套话、碎句、重复节奏等；不判断作者身份 | `wewrite score` |
| SEO 优化 | 标题策略 / 摘要 / 关键词 / 标签 | wewrite-review |
| 视觉 AI | 按任务设置生成封面/必要配图，生成前检查数量和预估费用 | `wewrite image-gen` |
| 排版发布 | 18+ 主题 + 微信兼容修复 + 暗黑模式 | `wewrite preview/publish` |
| 多平台改写 | 一稿 → 小红书/抖音，内容级真改 + 原创度门 | wewrite-rewrite |
| 效果复盘 | 微信数据分析 API 回填阅读数据，反哺选题 | `wewrite stats` |
| 范文风格库 | 从文章提取结构与节奏；第三方内容不提供观点和个人经历 | `wewrite exemplar` |
| 风格飞轮 | 单次修改只参考，重复出现或明确确认后才成为同范围稳定规则 | `wewrite learn-edits` |
| 排版学习 | 从任意公众号文章 URL 提取排版主题 | `wewrite learn-theme` |
| 文章采集 | 从公众号 URL 提取正文为 Markdown，可导入范文库 | `wewrite fetch-article` |

## ✍️ 写作人格

像选排版主题一样选写作风格。在 `~/.wewrite/style.yaml` 里一行配置：

```yaml
writing_persona: "midnight-friend"
```

| 人格 | 适合 | 风格特点 |
|------|------|---------|
| `midnight-friend` | 个人号/自媒体 | 口语化、保留自我质疑；无个人材料时不用虚构故事开场 |
| `warm-editor` | 生活/文化/情感 | 温暖叙事、故事嵌套数据、柔和情绪弧 |
| `industry-observer` | 行业媒体/分析 | 中性分析、数据先行、稳中带刺 |
| `sharp-journalist` | 新闻/评论 | 犀利简洁、数据驱动、强观点 |
| `cold-analyst` | 财经/投研 | 冷静克制、逻辑链条、风险意识强 |
| `humor-storyteller` | 泛科技娱乐/热点辣评 | 包袱密集、荒诞解构、笑完有余味 |
| `tech-coder` | 技术教程/开发者社区 | 代码先行、注释式行文、版本敏感 |

每个人格定义语气、数据呈现和节奏偏好，但不能覆盖事实和个人材料边界。只有用户在当前任务
明确提供的经历才能写成作者亲历。详见 `skills/wewrite-write/personas/`；自定义人格放
`~/.wewrite/personas/`。

## 📝 内容质量

WeWrite 的目标是**写出准确、有观点、对读者有用的文章**。核心机制：

1. **先定义再写**：任务书明确目标读者、真正问题、核心判断、新增价值、反方和适用边界
2. **主张对证据**：事实、推断、意见和用户经历分别记录；无法支持的具体主张不进入初稿
3. **安全增强**：热点文找有证据的新角度，干货文补行动条件，故事文只用真实材料，对比文给决策条件
4. **编辑门槛**：按准确、观点、有用、合声、好读判断；未通过就直接修改并复审，只有通过才生成成稿
5. **谨慎学习**：范文只校准结构与节奏；单次人工修改不自动升级为所有文章的硬规则

每篇任务保留 `brief.yaml`、`claims.yaml`、`draft.md`、`article.md` 和
`review-report.json`，方便追溯“为什么这样写”和初稿到成稿改了多少。完整标准见
[`docs/content-quality-rubric.md`](https://github.com/imraywang/wewrite/blob/main/docs/content-quality-rubric.md)。

## 🎨 排版引擎

```bash
wewrite gallery    # 浏览器内预览所有主题（并排对比 + 一键复制）
wewrite themes     # 列出主题名称
```

| 类别 | 主题 |
|------|------|
| 通用 | `professional-clean`（默认）、`minimal`、`newspaper` |
| 科技 | `tech-modern`、`bytedance`、`github` |
| 文艺 | `warm-editorial`、`sspai`、`ink`、`elegant-rose` |
| 商务 | `bold-navy`、`minimal-gold`、`bold-green` |
| 风格 | `bauhaus`、`focus-red`、`midnight` |
| 专属 | `impeccable`、`lobster-notes` |

所有主题均支持微信暗黑模式。`wewrite learn-theme <url>` 学到的新主题存在 `~/.wewrite/themes/`，加载时优先于内置主题。

另有四个排版细节自动处理：**产物合规校验**（`wewrite validate`，preview/publish 自动跑，拦截会被微信过滤的写法）、**粘贴加固**（preview 产物自动做 `<span leaf>` 包裹，复制进编辑器不掉样式；API 发布路径无需）、**GIF 角标**（动图自动加右上角标签）、**H2 章节编号**（主题 YAML 设 `section_numbering: true` 启用）。

<details>
<summary><b>微信兼容性自动修复</b>（converter 内置兜底）</summary>

| 问题 | 自动修复 |
|------|---------|
| 外链被屏蔽 | 转为上标编号脚注 + 文末参考链接 |
| 中英混排无间距 | CJK-Latin 自动加空格 |
| 加粗标点渲染异常 | 标点移到 `</strong>` 外 |
| 原生列表不稳定 | `<ul>/<ol>` 转样式化 `<section>` |
| 暗黑模式颜色反转 | 注入 `data-darkmode-*` 属性 |
| `<style>` 被剥离 | 所有 CSS 内联注入 |

</details>

<details>
<summary><b>容器语法</b>（Markdown 里直接写的富组件）</summary>

````markdown
:::dialogue
你好，请问这个功能怎么用？
> 很简单，直接在 Markdown 里写就行。
:::

:::timeline
**2024 Q1** 立项启动
**2024 Q3** MVP 上线
:::

:::callout tip
提示框，支持 tip / warning / info / danger。
:::

:::quote
好的排版不是让读者注意到设计，而是让读者忘记设计。
:::
````

另有 `:::pullquote`（金句居中）、`:::label` / `:::label pill`（小标签标题：竖条/药丸）、`:::steps`（编号步骤卡）、`:::highlight`（琥珀高亮框）、`:::summary`（青色总结框）。

</details>

## 🔧 CLI 独立使用

`wewrite` CLI 不依赖任何 Agent，可以单独当排版/发布/评分工具用：

```bash
wewrite preview article.md --theme sspai            # Markdown → 微信 HTML 预览
wewrite publish article.md --cover cover.png --title "标题"   # 推送草稿箱
wewrite image-post p1.jpg p2.jpg -t "周末探店"       # 小绿书/图片帖（横滑轮播）
wewrite score article.md --verbose                  # 写作质量评分（11 项检测）
wewrite content-eval --draft draft.md --final article.md --assessment assessment.yaml --json # 编辑结果
wewrite hotspots --limit 20                         # 抓热点
wewrite search-articles "AI编程" -n 15 -t 2         # 搜公众号文章（-t 时间过滤，-r 解析直链）
wewrite seo --json "AI大模型" "科技股"               # SEO 分析
wewrite exemplar article.md / --list                # 范文风格库
wewrite fetch-article <url> -o out.md               # 公众号文章 → Markdown
wewrite learn-theme <url> --name my-style           # 学排版主题
wewrite validate article.html                       # 微信兼容性校验
wewrite diagnose                                    # 环境 + 配置自检
wewrite run start/list/resume/show/finish/permission # 独立文章任务、恢复与发布授权
wewrite sources add/list                            # 保存和查看事实来源
wewrite home                                        # 查看状态目录
wewrite migrate --from <旧仓库路径>                  # 从 v2.1 及更早版本迁移状态
```

## 🔄 工作流程

```
Step 1  环境检查 + 加载风格（不存在则 Onboard）        ← 主入口 wewrite
  ↓
Step 2  热点 + 高频需求 → 历史去重 + 搜索需求 → 选题    ← wewrite-topic
  ↓
Step 3  文章任务书 → 主张与来源 → 安全内容增强         ┐
  ↓                                                    ├ wewrite-write
Step 4  用户风格与有效学习规则 → 初稿                  ┘
  ↓
Step 5  编辑判断 → 必要时改稿并复审 → 成稿与编辑报告    ← wewrite-review
  ↓
Step 6  封存原始正文 → 写入历史                         ← 主入口 wewrite

正文完成后，可独立执行：
  ├─ 配封面 / 完整配图                                 ← wewrite-visual
  ├─ 微信排版与本地预览                                ← wewrite-publish
  └─ 明确授权后推送草稿箱                              ← wewrite-publish
```

默认连续完成正文，但“写一篇”只交付本地成稿。“完整制作”是正文、配图和本地预览三个独立
动作的组合快捷方式；“推到草稿箱”才授予发布权限，而且不会自动生图。已完成文章可以继续
配图、排版或发布，原始正文不被覆盖。每篇文章使用独立任务目录并可恢复（契约见
[`skills/wewrite/references/pipeline-state.md`](https://github.com/imraywang/wewrite/blob/main/skills/wewrite/references/pipeline-state.md)）。

<details>
<summary><b>📁 目录结构</b></summary>

```
wewrite/
├── skills/                   # Prompt 层：10 个自包含 skill（复制即用）
│   ├── wewrite/                # 主入口：内容流程编排 + 配图/排版/发布可选路由
│   ├── wewrite-style/          # 风格设置 / Onboard（onboard.md、style-template.md、style.example.yaml）
│   ├── wewrite-topic/          # 选题（topic-selection.md）
│   ├── wewrite-write/          # 任务书 + 主张证据 + 安全增强 + 初稿（personas/ 7 人格…）
│   ├── wewrite-review/         # 事实核对 + 改稿复审 + 标题摘要 + 编辑报告
│   ├── wewrite-visual/         # 封面 + 必要配图（数量与费用上限）
│   ├── wewrite-publish/        # 排版 + 发布 + 主题画廊 + 小绿书（wechat-constraints.md）
│   ├── wewrite-learn/          # 学习修改 / 导入范文 / 学排版（learn-edits.md）
│   ├── wewrite-stats/          # 文章数据复盘（effect-review.md）
│   └── wewrite-rewrite/        # 一源多平台改写（multiplatform-rewrite.md + platforms/ 平台定义）
│
├── src/wewrite/              # Runtime 层：`wewrite` CLI（pip 包）
│   ├── cli.py                  # 子命令调度器
│   ├── paths.py                # 状态目录解析（$WEWRITE_HOME → ~/.wewrite）
│   ├── migrate.py              # 旧状态一次性迁移
│   ├── commands/               # run / sources / diagnose / score / content-eval / hotspots / search-articles / seo / stats / learn-* / exemplar / fetch-article / llm-write / similarity / build-playbook
│   └── toolkit/                # converter / theme / publisher / wechat_api / image_gen + 18 个内置主题
│
├── pyproject.toml            # CLI 打包定义
├── config.example.yaml       # API 配置模板
├── writing-config.example.yaml # 写作参数模板
├── scripts/                  # 仅开发工具（context_budget 预算门 / gen_star_history 图表）
└── tests/                    # 排版、任务流程、skill/README 契约与上下文预算测试
```

State 层（全部在 `~/.wewrite/`，不在仓库）：`config.yaml`、`style.yaml`、`history.yaml`、`playbook.md`、`writing-config.yaml`、`current_run`、`runs/`、`exemplars/`、`corpus/`、`lessons/`、`output/`、`themes/`、`personas/`。

</details>

## ⬆️ 升级

对 Agent 说「更新」，或手动：

```bash
cd <仓库路径> && git pull && bash install.sh
```

从 v2.1 及更早版本升级时，install.sh 会自动把仓库里的旧用户状态迁到 `~/.wewrite/`。

## ⭐ Star History

[![Star History](https://raw.githubusercontent.com/imraywang/wewrite/main/docs/star-history.svg)](https://star-history.com/#imraywang/wewrite&Date)

<sub>图表自托管：GitHub 新的 API 限制下，star-history.com 需自备 fine-grained PAT，而 README 嵌入无法安全携带 token——本图由 [CI](.github/workflows/star-history.yml) 用仓库自身 token 每周刷新；点击可看交互版。</sub>

## 🤝 贡献

Issue / PR 欢迎。跑 `python3 -m pytest tests/ -q` 与 `python3 scripts/context_budget.py --budget-tokens 15500` 保持绿灯（CI 同款检查）。

## 📄 License

MIT
