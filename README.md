# WeWrite

公众号文章全流程 AI Skill —— 从热点抓取到草稿箱推送，一句话搞定。

兼容 [Claude Code](https://docs.anthropic.com/en/docs/claude-code) 和 [OpenClaw](https://github.com/anthropics/openclaw) 的 skill 格式。安装后说「写一篇公众号文章」即可触发完整流程。

## 它能做什么

```
"写一篇公众号文章"
  → 抓热点 → 选题评分 → 框架选择 → 素材采集 → 内容增强
  → 写作（真实信息锚定 + 风格注入 + 编辑锚点）
  → SEO优化 → AI配图 → 微信排版 → 推送草稿箱
```

首次使用时会引导你设置公众号风格，之后每次只需一句话。生成的文章带有 2-3 个编辑锚点——花 3-5 分钟加入你自己的话，文章就会从"AI 初稿"变成"你的作品"。

## 核心能力

| 能力 | 说明 | 实现 |
|------|------|------|
| 热点抓取 | 微博 + 头条 + 百度实时热搜 | `wewrite hotspots` |
| SEO 评分 | 百度 + 360 搜索量化评分 | `wewrite seo` |
| 选题生成 | 10 选题 × 3 维度评分 + 历史去重 | `references/topic-selection.md` |
| 素材采集 | WebSearch 真实数据/引述/案例 | wewrite-write Step 3.2 |
| 框架生成 | 7 套写作骨架（痛点/故事/清单/对比/热点解读/纯观点/复盘） | `references/frameworks.md` |
| 内容增强 | 按框架类型自动匹配：角度发现/密度强化/细节锚定/真实体感 | `references/content-enhance.md` |
| 文章写作 | 真实信息锚定 + 风格注入 + 编辑锚点 | `references/writing-guide.md` |
| SEO 优化 | 标题策略 / 摘要 / 关键词 / 标签 | `references/seo-rules.md` |
| 视觉 AI | 封面 3 创意 + 内文 3-6 配图 | `wewrite image-gen` |
| 排版发布 | 16+ 主题 + 微信兼容修复 + 暗黑模式 | `wewrite preview/publish` |
| 效果复盘 | 微信数据分析 API 回填阅读数据 | `references/effect-review.md` |
| 范文风格库 | SICO 式 few-shot：从你的文章提取风格指纹，写作时注入 | `wewrite exemplar` |
| 风格飞轮 | 学习你的修改，越用越像你 | `references/learn-edits.md` |
| 排版学习 | 从任意公众号文章 URL 提取排版主题 | `wewrite learn-theme` |
| 文章采集 | 从公众号 URL 提取正文为 Markdown，可导入范文库 | `wewrite fetch-article` |

## 写作人格

像选排版主题一样选写作风格。在 `style.yaml` 里一行配置：

```yaml
writing_persona: "midnight-friend"
```

| 人格 | 适合 | 风格特点 |
|------|------|---------|
| `midnight-friend` | 个人号/自媒体 | 极度口语化、高自我怀疑、每段第一人称 |
| `warm-editor` | 生活/文化/情感 | 温暖叙事、故事嵌套数据、柔和情绪弧 |
| `industry-observer` | 行业媒体/分析 | 中性分析、数据先行、稳中带刺 |
| `sharp-journalist` | 新闻/评论 | 犀利简洁、数据驱动、强观点 |
| `cold-analyst` | 财经/投研 | 冷静克制、逻辑链条、风险意识强 |

每个人格定义了语气浓度、数据呈现方式、情绪弧线、不确定性表达模板等参数。详见 `personas/` 目录。

## 内容质量

WeWrite 的目标不是"骗过 AI 检测"，而是**写出值得读的文章**。核心机制：

1. **内容增强**：根据框架类型自动执行不同策略——热点文找反直觉角度、干货文强化信息密度、故事文锚定真实细节、对比文注入真实用户体感
2. **素材采集**：自动 WebSearch 真实数据/引述/案例，锚定在文章中（不编造）
3. **范文风格库**：导入你已发布的文章，写作时自动注入你的风格指纹（句长节奏、情绪表达、转折方式）
4. **编辑锚点**：在 2-3 个关键位置标记"在这里加一句你自己的话"
5. **学习飞轮**：每次你编辑后说"学习我的修改"，下次初稿更接近你的风格
6. **文章自检**：说"检查一下"，查看生成档案（用了什么框架/人格/策略）+ 质量检查（具体到哪句话该怎么改）

## 排版引擎

### 16 个主题

```bash
# 浏览器内预览所有主题（并排对比 + 一键复制）
wewrite gallery

# 列出主题名称
wewrite themes
```

| 类别 | 主题 |
|------|------|
| 通用 | `professional-clean`（默认）、`minimal`、`newspaper` |
| 科技 | `tech-modern`、`bytedance`、`github` |
| 文艺 | `warm-editorial`、`sspai`、`ink`、`elegant-rose` |
| 商务 | `bold-navy`、`minimal-gold`、`bold-green` |
| 风格 | `bauhaus`、`focus-red`、`midnight` |

所有主题均支持微信暗黑模式。

### 微信兼容性自动修复

| 问题 | 自动修复 |
|------|---------|
| 外链被屏蔽 | 转为上标编号脚注 + 文末参考链接 |
| 中英混排无间距 | CJK-Latin 自动加空格 |
| 加粗标点渲染异常 | 标点移到 `</strong>` 外 |
| 原生列表不稳定 | `<ul>/<ol>` 转样式化 `<section>` |
| 暗黑模式颜色反转 | 注入 `data-darkmode-*` 属性 |
| `<style>` 被剥离 | 所有 CSS 内联注入 |

### 容器语法

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

## 安装

**Claude Code**：

```bash
git clone --depth 1 https://github.com/oaker-io/wewrite.git ~/wewrite
cd ~/wewrite && bash install.sh
```

也可以用 [skills.sh](https://skills.sh) 按需挑模块装（skill 目录复制即用；`wewrite` CLI 仍需按下方方式安装）：

```bash
npx skills add oaker-io/wewrite
```

`install.sh` 做三件事：装 `wewrite` CLI（uv/pipx，无则回退 venv）、把主入口和各
`wewrite-*` 模块符号链接到 `~/.claude/skills/` 与 `~/.agents/skills/`、把旧版留在
仓库里的用户状态迁到 `~/.wewrite/`。仓库可以克隆到任意位置。

**OpenClaw**（单 SKILL.md 形态，用构建好的 `dist/openclaw/`；v2.1 起仓库根不再有 SKILL.md）：

```bash
git clone --depth 1 https://github.com/oaker-io/wewrite.git ~/wewrite
ln -sfn ~/wewrite/dist/openclaw ~/.openclaw/skills/wewrite
bash ~/.openclaw/skills/wewrite/install.sh
```

**Codex**（OpenAI Codex CLI）：

```bash
git clone --depth 1 https://github.com/oaker-io/wewrite.git ~/.codex/skills/wewrite
cd ~/.codex/skills/wewrite && bash install.sh
python3 scripts/build_codex.py --install   # 装自定义 prompt 到 ~/.codex/prompts/
```

之后在 Codex 里用 `/wewrite 写一篇关于 X 的文章` 触发完整流程。Codex 没有 SKILL.md 自动触发机制，所以通过自定义 prompt 承载（构建时把各模块合并回单体）；源 `skills/` 更新后重跑 `build_codex.py --install` 同步。详见 [`dist/codex/README.md`](dist/codex/README.md)。

> OpenClaw / Codex 均为单文件形态：构建脚本把 `skills/` 下的模块按管道顺序合并回一份
> 单体 SKILL.md / prompt，下游使用体验与 v1.x 一致。

运行时是一个 pip 包（`wewrite` CLI）。推荐用 [uv](https://docs.astral.sh/uv/) 或 pipx：

```bash
uv tool install git+https://github.com/oaker-io/wewrite.git   # 或 pipx install
```

用户状态（配置/风格/历史/产出）统一在 `~/.wewrite/`（可用 `WEWRITE_HOME` 覆盖），
`wewrite home` 查看；从 v2.1 及更早版本升级用 `wewrite migrate --from <旧仓库路径>`。

安装后 skill 会在每次运行时自动检查新版本。有更新时说"更新"即可升级。

### 配置（可选）

```bash
cp config.example.yaml ~/.wewrite/config.yaml
```

填入微信公众号 `appid`/`secret`（推送需要）和图片 API key（生图需要）。不配也能用——自动降级为本地 HTML + 输出图片提示词。

## 快速开始

```
你：写一篇公众号文章
你：写一篇关于 AI Agent 的公众号文章
你：交互模式，写一篇关于效率工具的推文
你：帮我润色一下刚才那篇
你：学习我的修改                  → 飞轮学习
你：看看有什么主题                → 主题画廊
你：换成 sspai 主题               → 切换主题
你：看看文章数据怎么样            → 效果复盘
你：做一个小绿书                  → 图片帖（横滑轮播）
你：检查一下                        → 生成报告 + 质量自检
你：导入范文                        → 建立风格库
你：查看范文库                      → 查看已导入的范文
你：学习排版                        → 从公众号文章提取排版主题
```

## 目录结构

```
wewrite/
├── skills/                   # 模块化 skill（主入口 + 9 个模块，各自自带 references/，复制即用）
│   ├── wewrite/                # 主入口：路由 + 全流程编排（Step 1/8 内联，Step 2-7 调模块）
│   ├── wewrite-style/          # 风格设置 / Onboard（含 onboard.md、style-template.md、style.example.yaml）
│   ├── wewrite-topic/          # 选题（topic-selection.md）
│   ├── wewrite-write/          # 框架 + 素材 + 反 AI 写作（writing-guide、frameworks、personas/ 7 人格…）
│   ├── wewrite-review/         # SEO + 编辑自评 + 反 AI 评分 + 自检报告（seo-rules.md）
│   ├── wewrite-visual/         # 封面 + 内文配图（visual-prompts.md、cover-prompts.md）
│   ├── wewrite-publish/        # 排版 + 发布 + 主题画廊 + 小绿书（wechat-constraints.md）
│   ├── wewrite-learn/          # 学习修改 / 导入范文 / 学排版（learn-edits.md）
│   ├── wewrite-stats/          # 文章数据复盘（effect-review.md）
│   └── wewrite-rewrite/        # 一源多平台改写（multiplatform-rewrite.md + platforms/ 平台定义）
├── config.example.yaml       # API 配置模板
├── writing-config.example.yaml # 写作参数模板
├── pyproject.toml            # wewrite CLI 打包定义
│
├── dist/openclaw/            # OpenClaw 兼容版（CI 自动构建，模块合并回单体 SKILL.md）
│
├── src/wewrite/              # `wewrite` CLI（pip 包，确定性工具层）
│   ├── cli.py                  # 子命令调度器
│   ├── paths.py                # 状态目录解析（$WEWRITE_HOME → ~/.wewrite）
│   ├── migrate.py              # 旧状态一次性迁移
│   ├── commands/               # diagnose / score / hotspots / seo / stats / learn-* / exemplar / fetch-article / llm-write / similarity / build-playbook
│   └── toolkit/                # converter / theme / publisher / wechat_api / image_gen + 内置主题与平台定义
│
├── scripts/                  # 仅开发构建工具（build_openclaw / build_codex / context_budget）
│
└── tests/                    # converter + context_budget 测试
```

用户状态（v2.2 起全部在 `~/.wewrite/`，不在仓库）：`config.yaml`、`style.yaml`、
`history.yaml`、`playbook.md`、`writing-config.yaml`、`exemplars/`、`corpus/`、
`lessons/`、`output/`、`themes/`（学到的排版主题）

## 工作流程

```
Step 1  环境检查 + 加载风格（不存在则 Onboard）        ← 主入口 wewrite
  ↓
Step 2  热点抓取 → 历史去重 + SEO → 选题              ← wewrite-topic
  ↓
Step 3  框架选择 → 素材采集（WebSearch 真实数据）      ┐
  ↓                                                    ├ wewrite-write
Step 4  维度随机化 → 范文注入 → 写作 → 快速自检        ┘
  ↓
Step 5  SEO 优化 → 质量验证                            ← wewrite-review
  ↓
Step 6  视觉 AI（封面 + 内文配图）                     ← wewrite-visual
  ↓
Step 7  预检 + 排版 + 发布（16 主题 + 微信兼容修复）   ← wewrite-publish
  ↓
Step 8  写入历史 → 回复用户（含编辑建议 + 飞轮提示）   ← 主入口 wewrite
```

默认全自动，主入口按序编排各模块，状态经 `output/_state.yaml` 传递
（契约见 `references/pipeline-state.md`）。说"交互模式"可在选题/框架/配图处暂停确认。

每个模块也可以单独激活，one step at a time：只要选题说 `/wewrite-topic`、
只要封面说 `/wewrite-visual`、检查一篇文章说 `/wewrite-review`、
一稿多发说 `/wewrite-rewrite`——缺前置时模块会自己补齐或向你要。

## Toolkit 独立使用

```bash
# Markdown → 微信 HTML
wewrite preview article.md --theme sspai

# 主题画廊
wewrite gallery

# 发布草稿箱
wewrite publish article.md --cover cover.png --title "标题"

# 小绿书/图片帖（横滑轮播，3:4 比例，最多 20 张）
wewrite image-post photo1.jpg photo2.jpg photo3.jpg -t "周末探店" -c "在望京发现的宝藏咖啡馆"

# 抓热点
wewrite hotspots --limit 20

# SEO 分析
wewrite seo --json "AI大模型" "科技股"

# 范文风格库
wewrite exemplar article.md              # 导入范文
wewrite exemplar *.md -s "你的公众号"     # 批量导入
wewrite exemplar --list                   # 查看范文库

# 文章质量检查
wewrite score article.md --verbose

# 从公众号文章学习排版主题
wewrite learn-theme https://mp.weixin.qq.com/s/xxxx --name my-style
```

## License

MIT
