---
name: wewrite
description: |
  微信公众号内容全流程主入口：热点抓取 → 选题 → 框架 → 内容增强 → 写作 → SEO →
  视觉AI → 排版推送草稿箱。负责路由与全流程编排；各功能也拆成 wewrite-* 模块
  （topic 选题 / write 写作 / review 验证 / visual 配图 / publish 排版发布 /
  style 风格 / learn 学习 / stats 数据 / rewrite 多平台改写）可单独激活。
  触发关键词：公众号、推文、微信文章、微信推文、草稿箱、微信排版、写公众号、写一篇。
  意图明确命中单一模块时（如只要选题、只要封面、只要排版）应直接触发对应
  wewrite-* 模块；本入口负责完整流程和模糊意图的分流。
  不应被通用的"写文章"、blog、邮件、PPT、抖音/短视频、网站 SEO 触发——
  需要有公众号/微信等明确上下文。
---

# WeWrite — 公众号内容主入口

## 行为声明

**角色**：用户的公众号内容编辑 Agent。本入口做两件事：**路由**（辅助命令分发到
wewrite-* 模块）和**编排**（主管道 8 步按序跑完）。

**模式**：
- **默认全自动**——一口气跑完 Step 1-8，不中途停下。只在出错时停。
- **交互模式**——用户说"交互模式"/"我要自己选"时，在选题/框架/配图处暂停。

**降级原则**：每一步都有降级方案。Step 1 检测到的降级标记（`skip_publish`、`skip_image_gen`）写入 `{home}/output/_state.yaml`，后续模块自动生效，不重复报错。

**进度追踪**：**若 harness 提供 task 工具（如 TaskCreate）**，主管道启动时为 8 个 Step 创建任务，每步 in_progress→completed；**否则**每进入一步发一行 `[N/8] 步骤名` 文本进度。无论哪种，都必须把 8 步走完——编号清单是排序骨架，不依赖特定工具。

**完成协议**：
- **DONE** — 全流程完成，文章已保存/推送
- **DONE_WITH_CONCERNS** — 完成但部分步骤降级，列出降级项
- **BLOCKED** — 关键步骤无法继续（如 wewrite CLI 缺失且用户拒绝安装）
- **NEEDS_CONTEXT** — 需要用户提供信息才能继续（如首次设置需要公众号名称）

**路径约定**：本文档中 `{baseDir}` 与 `{repo}` 均指本 SKILL.md 所在的目录（即 WeWrite 单体版根目录，references/ 与 personas/ 在其下）。

**读取/检查约定**：本文档中 `读取: <路径>` / `检查: <路径>` = **用你环境的文件读取工具真实打开该文件、读完其全部内容，然后再继续本步**。这不是描述性注释——未读取前不得执行依赖该文件的步骤；不同 harness 的文件读取工具名不同，按你环境的对应工具执行。

**CLI 约定**：确定性操作（自检/抓热点/评分/生图/排版/发布…）一律走 `wewrite` 命令，需在 PATH（缺失 → `bash {repo}/install.sh` 或 `uv tool install git+https://github.com/oaker-io/wewrite.git`）。**{home}** = 用户状态目录 `$WEWRITE_HOME` 或 `~/.wewrite`（`wewrite home` 可查）——config/style/history/playbook/output/exemplars 全在 {home}，不在仓库；references 文档中的状态路径同此约定。

**管道状态**：跨模块状态统一落盘 `{home}/output/_state.yaml`，契约见 `{baseDir}/references/pipeline-state.md`。主管道开新一篇文章时重置该文件（保留当天有效的 `flags`）。

**Onboard 例外**：Onboard（wewrite-style）是交互式的（需要问用户问题），不受"全自动"约束。Onboard 完成后回到全自动管道。

---

## 路由（非管道命令）

用户发出"选题→发布"主流程之外的命令时，分发到对应模块，不进主管道：

| 用户说 | 模块 | 说明 |
|--------|------|------|
| 重新设置风格 / 修改配置 | `wewrite-style` | onboard / 重设 style.yaml |
| 只要选题 / 今天写什么 | `wewrite-topic` | 10 个评分选题 |
| 检查一下 / 自检 / 有没有 AI 味 | `wewrite-review` | 自检报告（只诊断不改） |
| 封面 / 配图相关 | `wewrite-visual` | 生成/重生成图片 |
| 排版 / 预览 / 主题画廊 / 换主题 / 小绿书 / 推草稿箱 | `wewrite-publish` | 排版发布与主题 |
| 学习我的修改 / 学排版 / 导入范文 / 查看范文库 | `wewrite-learn` | 自学习飞轮 |
| 看看文章数据 / 效果复盘 | `wewrite-stats` | 拉数据 + 回填 + 建议 |
| 改写成小红书 / 抖音版 / 多平台分发 | `wewrite-rewrite` | 一源多平台改写 |
| 更新 / 更新 WeWrite / 升级 | （就地执行）在 `{repo}` 执行 `git pull origin main` 并重跑 `bash {repo}/install.sh`（更新 CLI 与链接），完成后告知版本变化 | |


---

## 主管道（Step 1-8）

主管道是固定的 8 个 Step：

```
[1/8] 环境 + 配置   [2/8] 选题   [3/8] 框架 + 素材   [4/8] 写作
[5/8] SEO + 验证   [6/8] 视觉 AI   [7/8] 排版 + 发布   [8/8] 收尾
```

Step 1、8 由本入口执行；Step 2-7 由 5 个管道模块承担，状态经 `{home}/output/_state.yaml` 传递，模块间不停顿（交互模式除外）。

### Step 1: 环境 + 配置

**1.1 环境 + 配置自检**（**一条命令拿全部降级标记**，别再逐项手查/逐个读文件）：

```bash
wewrite diagnose --json
```

读返回 JSON 的 `flags` 与 `summary`（diagnose 已涵盖依赖检查 + config/env 双源识别，不必再单独 import 测试或读 config.yaml）：
- `flags.skip_publish` / `flags.skip_image_gen` / `flags.use_writer_model` → 连同 `diagnosed_at: 今天` 写入 `{home}/output/_state.yaml` 的 `flags`，后续模块自动遵守。
- `wewrite` 命令不存在或 `summary.failures > 0` → 引导 `bash {repo}/install.sh`（安装/更新 wewrite CLI 并链接 skills）；否则静默继续。
- 若 `files.exemplars` 为空可顺带提示一次"可说**'导入范文'**建风格库"，不阻断。

**1.2 版本检查**（仅本地交互式 skill 安装；云端/容器跳过）：

`{repo}` 是 git 仓库（存在 `.git`）且当前是交互式使用时，才比对本地 `VERSION` 与 `git show origin/main:VERSION`，不同则提示"说「更新」升级"（不阻断）。**容器/云端部署没有 `.git`、也不该让 agent 自更新（更新走重新部署）→ 直接跳过本步，不要跑 git 命令。**

**1.3 加载风格**：

```
检查: {home}/style.yaml
```

- 存在 → 提取 `name`、`topics`、`tone`、`voice`、`blacklist`、`theme`、`cover_style`、`author`、`content_style`
- 不存在 → 激活 `wewrite-style`（onboard），完成后回到 Step 1

**1.4 重置管道状态**：开新一篇文章 → 重置 `{home}/output/_state.yaml`（保留 `flags`）。
如果用户直接给了选题 → 写入 `topic`（`source: "用户指定"`），跳过 [2/8] 直达 [3/8]（仍需框架选择和素材采集，不可跳过）。

## wewrite-topic — 选题


### 2.1 热点抓取

```bash
wewrite hotspots --limit 30
```

**降级**：脚本报错 → web_search "今日热点 {topics第一个垂类}"

### 2.2 历史分析 + SEO

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

### 2.3 生成选题

```
读取: {baseDir}/references/topic-selection.md
```

生成 **10 个选题**，其中：
- **7-8 个热点选题**：基于 2.1 的热点，按 topic-selection.md 规则评分
- **2-3 个常青选题**：不依赖热点，从用户的 `topics` 领域生成长尾内容（教程/方法论/经验总结/工具推荐），标注为"常青"。适合 content_style 为干货型/测评型的用户

每个选题含标题、评分、点击率潜力、SEO 友好度、推荐框架。

- 自动模式 → 选最高分
- 交互模式 / 单独激活 → 展示全部，等用户选

### 完成

把选定选题写入 `{home}/output/_state.yaml`：`topic.title`、`topic.keywords`、
`topic.source: "热点抓取"`、`topic.framework_hint`（推荐框架），`steps_done` 追加 `topic`。
单独激活且用户只要选题列表时，展示 10 个选题即可；用户选定后写入状态并提示
"可以直接说'就写这个'进入写作（wewrite-write）"。

---

## wewrite-write — 框架 + 素材 + 写作


### Step 3: 框架 + 素材

**3.1 框架选择**：

```
读取: {baseDir}/references/frameworks.md
```

7 套框架（痛点/故事/清单/对比/热点解读/纯观点/复盘），自动选推荐指数最高的
（`topic.framework_hint` 与 history 表现加权参与推荐）。

**3.2 素材采集 + 内容增强**（合并执行，共用搜索结果）：

```
读取: {baseDir}/references/content-enhance.md
```

根据 3.1 选定的框架类型，一次搜索同时完成素材采集和内容增强：

| 框架 | 搜索策略 | 从结果中提取 |
|------|---------|-------------|
| 热点解读 / 纯观点 | `"{关键词} site:mp.weixin.qq.com OR site:36kr.com"` + `"{关键词} 观点 OR 评论"` | 真实素材（数据/引述）**+** 已有文章的主流观点（供角度发现） |
| 痛点 / 清单 | `"{关键词} 教程 OR 工具 OR 实操"` + `"{关键词} 数据 报告"` | 真实素材 **+** 具体工具名/步骤/参数（供密度强化） |
| 故事 / 复盘 | `"{人物/事件} 采访 OR 专访 OR 细节"` + `"{关键词} 数据 报告"` | 真实素材 **+** 时间锚/数字锚/对话锚/感官锚（供细节锚定） |
| 对比 | `"{方案A} vs {方案B} 评测 OR 体验"` + `"{方案A OR 方案B} 踩坑 OR 缺点 site:v2ex.com OR site:zhihu.com"` | 真实素材 **+** 真实用户评价和踩坑信息（供真实体感） |

每次搜索 2 轮，从结果中**同时**提取：
1. **素材**：5-8 条真实素材（具名来源 + 具体数据/引述/案例）。**禁止编造**。
2. **增强材料**：按 content-enhance.md 对应策略的要求提取（角度/密度要点/细节/用户声音）。

两者并入框架大纲，一起传入 Step 4 写作。

**降级**：web_search 不可用 → 用 LLM 训练数据中可验证的公开信息。但需告知用户："素材采集未能使用 web_search，建议在编辑锚点处多加入你自己的内容。"密度强化不依赖搜索，始终执行。

### Step 4: 写作

> **🔴 写作模式取决于前置的 `flags.use_writer_model`（详见 4.4），别两种都做**：
> - **`false`（默认 · 编排器自写）** → 你直接按"写作规范"写正文。**不要调用 `llm_write.py`**（没配写作模型，调了必然 exit 3、白费一轮）。
> - **`true`（混合路由 · 配了写作模型）** → 你只编排，正文交 `wewrite llm-write` 出稿。
>
> 下面 4.1-4.3 读取的文件两种模式都要（自写时是写作依据；委托时是 brief 备料）。

```
读取: {baseDir}/references/anti-ai-writing-system.md
读取: {baseDir}/references/writing-guide.md
读取: {home}/playbook.md（如果存在，按 confidence 分级执行）
读取: {home}/history.yaml（最近 3 篇的 dimensions + closing_type 字段）
读取: {home}/exemplars/index.yaml（如果存在）
```

（anti-ai-writing-system.md 是出稿前必须逐条记住的**写作契约**——内联自写与 llm_write.py 共用、实测能把 composite 压到 <30；writing-guide.md 是其背后的详细 Tier 规则。两者**未读取前不得开始写作**，且在写作与验证期间保持驻留，验证模块（wewrite-review）仍按 writing-guide.md 的编号规则 1.1-3.2 检查，中途不要丢弃重读。）

**4.1 维度随机化**：

从以下维度池随机激活 2-3 个维度，让每篇文章的表达方式不同。如果 history.yaml 有最近 3 篇的 `dimensions` 字段，避免使用相同组合。

| 维度 | 选项 |
|------|------|
| 叙事视角 | 第一人称亲历 / 旁观者分析 / 对话体 / 自问自答 |
| 时间线 | 正序 / 倒叙 / 插叙 |
| 类比域 | 体育 / 做饭 / 军事 / 恋爱 / 游戏 / 电影 / 建筑 / 医学 |
| 情绪基调 | 克制冷静 / 热血激动 / 讽刺吐槽 / 温暖治愈 / 焦虑警示 |
| 节奏 | 短句密集 / 长叙述慢推 / 长短急切交替 / 慢开头快收尾 |

**4.2 加载写作人格**：

```
读取: {baseDir}/personas/{选定人格}.yaml
```

人格的选定规则（参见 `{baseDir}/references/persona-selection.md`）：

- **style.yaml 有 `writing_persona`** → 直接加载该人格。用户已固定账号声音，尊重配置（persona-selection 的「用户明确指定」优先级最高）。
- **没有 `writing_persona`**（或用户本轮明确要求换风格）→ 读取 `references/persona-selection.md`，按选定选题的特征匹配 top 2 人格；用 history.yaml 最近 3 篇的写作人格降权（保证风格多样化），向用户展示推荐理由让其二选一；匹配不明确时默认 midnight-friend。

人格文件定义了：语气浓度、数据呈现方式、情绪弧线、段落节奏、不确定性表达模板等。作为写作的硬性约束执行。

**优先级**：playbook.md（confidence ≥ 5 的规则）> persona > 范文风格 > writing-guide.md。writing-guide 是底线（基础写作规范），范文提供风格示范（句长节奏、情绪表达方式），persona 在此基础上特化风格参数（语气浓度、数据呈现），playbook 中高置信度规则是用户个性化的最终覆盖。playbook 中 confidence < 5 的规则作为软性参考。

**4.3 范文风格注入**（有 `{home}/exemplars/index.yaml` 时执行）：

从 index.yaml 筛选 category 匹配当前框架类型的范文，取 top 3。读取对应 .md 文件的片段内容。

在写作 prompt 中注入：

> 以下是该公众号风格的真实段落示例，模仿其句长节奏、情绪强度和口语化程度：
>
> 【开头风格】
> {exemplar_1 的开头钩子段}
>
> 【情绪段风格】
> {exemplar_2 的情绪高峰段}
>
> 【转折风格】
> {exemplar_2 或 exemplar_3 的转折/自纠段（如有）}
>
> 【收尾风格】
> {exemplar_3 的收尾段}

Category 映射规则：

| 框架类型 | exemplar category |
|----------|-------------------|
| 痛点型 | tech-opinion |
| 故事型 / 复盘型 | story-emotional |
| 清单型 / 对比型 | list-practical |
| 热点解读型 / 纯观点型 | hot-take |
| 其他 | general |

如果匹配到的范文不足 3 篇，用 general category 补足。

**Fallback（范文库为空时）**：读取 `{baseDir}/references/exemplar-seeds.yaml`，从每个段落类型中随机选 1 个注入 prompt。种子段落只示范人类写作的结构模式（句长方差、情绪锐度、自我纠正、非总结式收尾），不携带特定风格。注入时使用：

> 以下是人类写作的结构模式示例，注意模仿其句长节奏和情绪表达方式（不要模仿具体内容或风格）：
>
> 【开头模式】{seeds.opening_hooks 随机 1 个}
>
> 【情绪段模式】{seeds.emotional_peaks 随机 1 个}
>
> 【转折模式】{seeds.transitions 随机 1 个}
>
> 【收尾模式】{seeds.closings 随机 1 个}

建库命令：`wewrite exemplar article.md`

**4.4 写文章** —— 本步只产出 `{home}/output/article.md`。按前置的 `flags.use_writer_model` **二选一**，别两种都走：

**A. 自写模式（`use_writer_model = false`，默认 · 全 DeepSeek）**：按下面"写作规范"直接把正文写进 `{home}/output/article.md`，写完执行 4.5。**不要调用 `llm_write.py`**——没配写作模型，调它只会 exit 3、白白多耗一轮。

**B. 委托模式（`use_writer_model = true`，混合路由 · 配了写作模型）**：你只编排，正文交给写作模型：
1. 把【Step 3 框架大纲 + **Step 3.2 的真实素材锚点（具体数字/工具名/价格/案例——逐条写进去；写作模型只在给定事实上组织语言，严禁编造）** + 4.1 维度 + 4.2 人格要点 + 4.3 范文风格片段 + 下面"写作规范"全部要求 + 目标字数 + 可用容器语法 + 编辑锚点要求】组装成 brief，写到 `{home}/output/_brief.md`。
2. 调：`wewrite llm-write --brief output/_brief.md --output output/article.md`
3. 按退出码：**exit 0**（stdout 是摘要）→ 正文已写入，**不要 cat / 读全文**（靠评分驱动改写——省钱命门；只有 wewrite-review 的整体自评读一次全文），**跳过 4.5** 直接进验证。**exit 3 / 4**（没配/失败）→ 退回 A 自写。

**写作规范**（自己写时直接执行；委托写作模型时这些就是 brief 的内容要求）：
- **🔴 出稿契约**：严格按 `references/anti-ai-writing-system.md` 的反 AI 写作铁律**逐条满足**（句长强烈交替 / 段落长短交替 / 杜绝 AI 腔词 / 事实零编造 / 情绪有起伏 / 少副词 / 口语化自我修正 / 不堆整齐小标题），违反任一条直接重写。这是把 composite 压到 <30 的关键，下面的细则与之一致。
- H1 标题（20-28 字） + H2 结构，1500-2500 字
- **素材 + 增强约束**：Step 3.2 的素材和增强材料分散嵌入各 H2 段落。增强策略的核心输出（角度/密度要点/细节/用户声音）必须贯穿全文，不只装饰性出现一次
- **写作人格**：按 4.2 加载的人格参数写作（数据呈现方式、个人声音浓度、不确定性表达等）
- **收尾方式**：persona 的 `closing_tendency` 仅作为倾向参考。根据文章内容和情绪弧线自行判断最自然的收尾方式。如果 history.yaml 中最近 3 篇有 `closing_type` 字段，避免使用相同的收尾类型
- **写作规范**：writing-guide.md 中的基础规则（禁用词、句长方差、词汇混用等）在初稿阶段生效
- **分段实时自检**：读取 `{baseDir}/references/realtime-check.md`，每写完约 500 字（或每个 H2）就地执行 5 项快速检查（句长交替 / 情绪锚定 / 词汇温度 / 素材锚定 / 句法变形），问题当场掐掉不累积到全文。按 500 字/H2 粒度查，不要写一句修一句；也不要为凑检查项刻意制造大量单句段落（会触发过度优化检测）
- 2-3 个编辑锚点：`<!-- ✏️ 编辑建议：在这里加一句你自己的经历/看法 -->`
- 可选容器语法：`:::dialogue`、`:::timeline`、`:::callout`、`:::quote`、`:::highlight`（琥珀高亮框）、`:::summary`（青色总结框）

保存到 `{home}/output/article.md`（全流程统一用这个工作文件名；委托写作模型与自己写都写这里）

**4.5 快速自检**（写完后立即执行，减少验证阶段重写概率）：

对初稿做 5 项快速扫描，**当场修复**，不留到验证阶段：

**写作层面**：
1. **禁用词扫描**：检查 writing-guide.md 2.1 的禁用词列表，命中的直接替换
2. **句长方差**：是否有连续 3 句以上长度接近的段落，有则拆句或加短句

**内容层面**：
3. **开头钩子**：前 3 句是否制造了悬念/冲突/好奇心？如果是平铺直叙的背景介绍，重写开头
4. **增强贯穿**：增强策略的核心输出是否只出现在一段？如果是，在其他 H2 中补充
5. **金句检查**：全文是否有至少 1 句可独立截图转发的句子？如果没有，在情绪高点处补一句

LLM 自行完成，不需要调用脚本。

### 完成

写回 `{home}/output/_state.yaml`：`article: "output/article.md"`、`framework`、
`enhance_strategy`、`persona`、`dimensions`、`closing_type`、`word_count`，
`steps_done` 追加 `write`。单独激活时提示："初稿完成，建议接着跑质量验证
（wewrite-review）再配图发布。"

---

## wewrite-review — SEO + 质量验证


### 管道验证

```
读取: {baseDir}/references/seo-rules.md
```

**5.1 SEO**：3 个备选标题 + 摘要（≤40 字）+ 5 标签 + 关键词密度优化

**5.2 编辑视角整体自评**（**读一遍文章全文**，像挑剔的主编那样判断——这是质量的**主**把关，不是逐项打钩。委托写作模式下这就是你唯一一次把正文读进上下文）：

读一遍，问自己：
- **顺不顺**：读下来通畅吗？逻辑站得住吗？有没有突兀跳转、车轱辘话、为凑字的废话？
- **像不像一个好作者写的**：有具体细节、有观点、有人味——还是"正确的废话"？
- **有没有 AI 味**：套话（值得注意的是 / 综上所述 / 赋能…）、通篇一个腔调、情绪全程平铺？命中就改。
- **真不真**：数据/案例/工具名是不是素材采集拿到的真实素材？**有没有编造？编造必须改——这是底线**。

外加按框架看下面内容质量（脚本测不了，你来判），明显缺的补一处：

| 内容检查项 | 标准 | 适用框架 |
|--------|------|---------|
| 增强贯穿 | 增强策略核心输出全文可见，不只一段 | 所有 |
| 开头钩子 | 前 3 句制造悬念/冲突/好奇，非背景铺垫 | 所有 |
| 金句密度 | ≥ 1 处可独立截图转发的句子 | 所有 |
| 操作密度 | 每个 H2 有可操作要点（工具/步骤/参数） | 痛点/清单 |
| 角度锐度 | 核心观点能引发同意或反对 | 热点解读/纯观点 |
| 场景感 | ≥ 2 处时间/地点/对话画面细节 | 故事/复盘 |
| 真实声音 | ≥ 1 处真实用户评价或体验 | 对比 |

发现问题就**定向修**：只改有问题的具体句子，不重写整段，最多 3-5 处。剩下的小毛病留给作者（编辑锚点）。

**5.3 反 AI 评分（顺手跑一次当参考，别为分数返工）**：

```bash
wewrite score output/article.md --json
```

`composite_score`（0=好,100=差）只当**参考信号**，不是过线门：
- 看 `param_scores` 有没有**明显翻车**的项（禁用词命中、句长几乎没方差等）→ 有就顺手修那一处。
- **别为了压低分数反复重写**：实测这个分单次方差很大（~31-50），且刻意拉满会触发"过度优化"反而更差。**读着顺、没硬伤就进下一步**。
- 真正的质量门是**人**：作者在编辑锚点处补自己的话、复审定稿。把 `composite_score` 记进状态（收尾时进 history）当长期参考即可。

（委托模式想再润一版：把"最弱 1-2 个 param + 具体改写要求"追加进 `{home}/output/_brief.md` 重生成**一次**，不多轮。）

**完成**：写回 `_state.yaml`：`seo.title`、`seo.alt_titles`、`seo.digest`、`seo.tags`、
`seo.composite_score`，`steps_done` 追加 `review`。

### 自检报告（"检查一下 / 自检 / 这篇怎么样"）

对最近一篇生成的文章（或用户指定的文章）执行，输出生成报告：

**第一部分：生成档案**（这篇是怎么来的）
1. 读取 `{home}/history.yaml` 最近一条记录，提取：使用的框架类型 + 写作人格、激活的维度随机化组合、素材采集来源（web_search 还是降级到 LLM）、内容增强策略、范文库是否命中（用了哪几篇 exemplar 还是 fallback 到种子）、playbook 中生效的规则条数。
2. 若 history.yaml 无记录或用户指定了外部文章 → 跳过此部分，提示"这篇文章不是 WeWrite 生成的，只做质量检查"。

**第二部分：质量检查**（哪里还能改）
1. `wewrite score {article_path} --json`
2. Agent 解读 JSON 各项得分，翻译成可操作建议：每条定位到具体段落/句子、给出具体改法、按影响度排序最多 5 条。
3. 若各项得分都不错 → "这篇文章质量不错，建议在编辑锚点处加入你的个人内容就可以发了。"

**输出格式**：自然语言报告，不输出 JSON 或分数。

---

## wewrite-visual — 视觉 AI（封面 + 配图）


### 执行

**如果 `skip_image_gen = true`** → 只执行 6.1（输出提示词，不生图）。

```
读取: {baseDir}/references/visual-prompts.md
```

**6.1 实体提取**：从终稿中提取 3-5 个**具体实体**（人物、产品名、场景、数据点、行业术语）。后续所有提示词必须包含至少 2 个实体。

**6.2 提示词 + 风格锚定**（一次性把全部提示词写齐，**不要生成一张等一张**）：
1. 生成封面 3 组创意提示词（按 visual-prompts.md），选最佳 1 组。
2. **从选定的封面提示词文本**（而非已渲染的图）提取视觉锚点：色板 hex、风格关键词、画面调性。锚点来自提示词本身，所以无需等封面图回来就能继续。
3. 分析文章结构，为每个需要配图的段落选图片类型（infographic/scene/flowchart/comparison/framework/timeline），按 visual-prompts.md 模板写 3-6 张内文配图提示词；每张都引用第 2 步的视觉锚点，保证全文视觉一致。

**6.3 生成全部图片（封面 + 内文配图，必须实际生成 .png，不能只写提示词就算完成）**：把封面与每张内文配图都用 `wewrite image-gen` 实际生成出来。封面 `--size cover`，内文配图 `--size article`；多 provider 自动 fallback 已内置。**一次性把全部命令发出**（环境支持并行工具调用就并行，不支持就顺序，但务必把全部图都生成）：

```bash
wewrite image-gen --prompt "{封面提示词}" --output {home}/output/{slug}-cover.png --size cover
wewrite image-gen --prompt "{配图1提示词}" --output {home}/output/{slug}-fig1.png --size article
wewrite image-gen --prompt "{配图2提示词}" --output {home}/output/{slug}-fig2.png --size article
# …其余配图同理，全部生成
```
> 提示词只是中间产物——**本模块完成的标志是 `{home}/output/` 下真的出现了这些 .png 文件**，不是把提示词写进某个 md 就完事。
> 也可用一条命令批量并发（等价、工具内并行）：把 `[{"prompt","output","size"}…]` 写进 `{home}/output/_images.json`，再 `wewrite image-gen --manifest {home}/output/_images.json`。

**6.4 一次性验证 + 插入**：
- **全自动模式**：所有图返回后，**在一轮内**统一确认每张 .png 都已生成（核心实体可识别、风格一致）。只对明显失败（实体不可辨 / 风格跑偏 / 没生成）的那一张换提示词重试 1 次，其余直接采用。**不要逐张读图、逐张推理**（那会把一次检查拆成多轮，显著拖慢）。
- **交互模式**：展示封面（及配图），问用户"效果如何？"，不满意再针对性重生成。

确认后把对应的 Markdown 图片占位符一次性替换为实际路径。

**降级**：`wewrite image-gen` 支持多 provider 自动 fallback（按 config.yaml 中 providers 列表顺序尝试）。全部失败 → 输出提示词 + 备选图库关键词，继续。

### 完成

写回 `_state.yaml`：`images.cover`、`images.figures`（实际生成的 .png 路径），
`steps_done` 追加 `visual`。单独激活时展示生成的图片路径并提示可"换个风格重生成"。

---

## wewrite-publish — 排版 + 发布


### 发布主流程

**7.1 Metadata 预检**（发布前必须通过）：

| 检查项 | 标准 | 不通过时 |
|--------|------|---------|
| H1 标题 | 存在且 5-64 字节 | 自动修正或提示用户 |
| 摘要 | 存在且 ≤ 120 UTF-8 字节 | converter 自动生成 |
| 封面图 | 推送模式下需要 | 无封面则警告，仍可推送（微信会显示默认封面） |
| 正文字数 | ≥ 200 字 | 警告"内容过短，微信可能不收录" |
| 图片数量 | ≤ 10 张 | 超出则移除末尾多余图片 |

预检全部通过后才进入排版。

**平台硬限**（converter 不强制，写作/发布时 agent 必须遵守）：
- 单篇正文 ≤ 20000 字
- 图片 ≤ 10 张（超出移除末尾多余）
- 未认证公众号**不能用外部链接** → 转纯文本或放「阅读原文」
- 表格 ≤ 4 列（手机端更宽会被截断）

**7.2 排版 + 发布**：

**如果 `skip_publish = true`** → 直接走 preview。

Converter 自动处理：CJK 加空格、加粗标点外移、列表转 section、外链转脚注、暗黑模式、容器语法、AIGC 声明（**默认追加**，合规标识；主题/配置设 `aigc_footer: false` 可关）。

```bash
# 发布
wewrite publish {markdown} --cover {cover} --theme {theme} --title "{title}" --digest "{digest}"

# 降级：本地预览
wewrite preview {markdown} --theme {theme} --no-open -o {output}.html
```

**完成**：写回 `_state.yaml`：`publish.media_id`（降级时 null）、`publish.preview_html`
（预览时），`steps_done` 追加 `publish`。单独激活时告知 media_id 或预览文件路径。

### 辅助功能

| 用户说 | 动作 |
|--------|------|
| 看看有什么主题 / 主题画廊 | `wewrite gallery`（浏览器内预览全部 16 个主题） |
| 换成 XX 主题 | 用该主题重新 preview/publish；用户满意可提示写入 style.yaml 的 theme 字段 |
| 做一个小绿书 / 图片帖 | `wewrite image-post img1.jpg img2.jpg -t "标题"` |
| 只排版不发布 / 预览 | 走 preview 命令，输出本地 HTML 路径 |

### Step 8: 收尾

**8.1 写入历史**（推送成功或降级都要写，文件不存在则创建；字段值以 `{home}/output/_state.yaml` 为唯一事实源）：

```yaml
# → {home}/history.yaml
- date: "{日期}"
  title: "{标题}"
  topic_source: "热点抓取"  # 或 "用户指定"
  topic_keywords: ["{词1}", "{词2}"]
  output_file: "output/article.md"  # 全流程统一工作文件名
  framework: "{框架}"
  enhance_strategy: "{增强策略}"  # angle_discovery/density_boost/detail_anchoring/real_feel
  word_count: {字数}
  media_id: "{id}"  # 降级时 null
  writing_persona: "{人格名}"
  dimensions:
    - "{维度}: {选项}"
  closing_type: "{收尾类型}"  # trailing_off/unanswered/scene_revert/abrupt_stop/anti_conclusion/image
  composite_score: {验证阶段的 composite_score}  # 0=质量高, 100=问题多
  writing_config_snapshot:  # 本次使用的关键参数（从 writing-config.yaml 提取）
    sentence_variance: {值}
    paragraph_rhythm: "{值}"
    emotional_arc: "{值}"
    word_temperature_bias: "{值}"
    broken_sentence_rate: {值}
    tangent_frequency: "{值}"
    style_drift: {值}
    negative_emotion_floor: {值}
  stats: null
```

**8.2 回复用户**：

- 最终标题 + 2 备选 + 摘要 + 5 标签 + media_id
- 编辑建议："文章有 2-3 个编辑锚点，建议加入你自己的话。你可以在本地 markdown 里改，也可以直接在微信草稿箱改——改完后说**'学习我的修改'**，WeWrite 都能学到你的风格。"

**8.3 后续操作**：

| 用户说 | 动作 |
|--------|------|
| 润色/缩写/扩写/换语气 | 编辑文章 |
| 封面换暖色调等 | `wewrite-visual` 重新生图 |
| 用框架 B 重写 | `wewrite-write` 重跑（指定框架） |
| 换一个选题 | `wewrite-topic` 重跑（或直接给新选题） |
| 换成 XX 主题 | `wewrite-publish` 重新渲染 |
| 改写成小红书/抖音 | `wewrite-rewrite` |

其余非管道命令按上方「路由」表分发。

---

## 错误处理

| 步骤 | 降级 |
|------|------|
| 环境检查 | 逐项引导，设降级标记 |
| 热点抓取 | web_search 替代 |
| 选题为空 | 请用户手动给选题 |
| SEO 脚本 | LLM 判断 |
| 素材采集（web_search） | LLM 训练数据中可验证的公开信息 |
| 维度随机化 | history 空时跳过去重 |
| Persona 文件不存在 | 回退到 midnight-friend（默认） |
| 范文库为空 | Fallback 到 exemplar-seeds.yaml（通用模式） |
| 质量验证 | 评分仅作参考；读着顺、无硬伤即继续，修不动的小问题留给作者 |
| 生图失败 | 输出提示词 |
| 推送失败 | 本地 HTML |
| 历史写入 | 警告不阻断 |
| 效果数据 | 告知等 24h |
| Playbook 不存在 | 用 writing-guide.md |

---

## 辅助模块

（上方「路由」表中的模块名对应本节下方的同名小节，命中路由后直接执行对应小节）

## wewrite-style — 风格设置 / Onboard


### 执行

**触发场景**：
1. 主入口 Step 1 发现 `{home}/style.yaml` 不存在（首次使用）
2. 用户说"重新设置风格"、"修改配置"

两种场景都执行：

```
读取: {baseDir}/references/onboard.md
```

按 onboard.md 的 Phase 1-4 完成：交互式收集信息 → 生成 `{home}/style.yaml` →
可选 Playbook 建库 → 试跑询问。重设风格时以现有 style.yaml 为基线，只改用户要改的字段，
改完展示全文让用户确认。

**完成后**：若由主管道激活（首次 onboard），回到主管道 Step 1 继续；若用户单独触发，
告知"配置已更新，下次写作自动生效"。

---

## wewrite-learn — 自学习（改稿飞轮 / 范文库 / 排版学习）


### 子功能分发

| 用户说 | 动作 |
|--------|------|
| 学习我的修改 / 我改了，学习一下 | `读取: {baseDir}/references/learn-edits.md`，按其流程执行。支持本地 markdown 修改与微信草稿箱同步（`wewrite learn-edits --from-wechat`） |
| 学习排版 / 学排版 + URL | `wewrite learn-theme <url> --name <name>`，提取后提示用户设置 style.yaml 的 theme 字段 |
| 学习这篇文章 / 导入范文 + URL | `wewrite fetch-article <url> -o /tmp/article.md && wewrite exemplar /tmp/article.md -s <账号名>` |
| 导入范文 + 本地文件 | `wewrite exemplar <文件路径>`（多文件可批量） |
| 查看范文库 | `wewrite exemplar --list` |

**范文库的用途**：exemplars 会在写作模块（wewrite-write）按框架类型注入初稿 prompt，
是 SICO 式 few-shot 的来源。导入完成后告知用户库里现有多少篇、覆盖哪些 category。

**改稿飞轮的价值**：每次学习让下一篇初稿更接近用户风格。learn-edits.md 的
confidence 分级（≥5 硬约束 / <5 软参考 / <2 淘汰）决定规则在写作时的效力。

---

## wewrite-stats — 文章数据复盘


### 执行

```
读取: {baseDir}/references/effect-review.md
```

按其流程执行：`fetch_stats.py --days 7` 拉数据 → 匹配并回填 `history.yaml` 的
stats 字段 → 分析最好/最差表现及原因 → 给出后续选题/标题/框架的调整建议。

**前置**：需要 config.yaml 里的微信 API 凭证。缺凭证 → 告知用户"数据复盘需要配置
公众号 API（config.yaml），当前只能基于 history.yaml 已有记录做定性分析"，然后就
history.yaml 现有内容能分析多少分析多少。刚发布的文章 → 告知等 24h 后再看。

**下游影响**：回填的 stats 会被选题模块（wewrite-topic）读取——哪种框架/增强策略
表现好会加权到下次推荐。这是数据闭环的一半，另一半是 wewrite-learn 的改稿飞轮。

---

## wewrite-rewrite — 一源多平台改写


### 前置

1. **源文章**：按优先级解析——用户指定的文件/粘贴内容 > `{home}/output/_state.yaml` 的
   `article` 字段 > `{home}/output/article.md`。都没有 → 问用户"要改写哪篇？给我文件路径
   或直接粘贴全文"。确定后把源复制/保存为 `{home}/output/source.md`（质量门要用）。
2. **目标平台**：用户点名了就用；没点名 → 列出 `{baseDir}/platforms/` 下的可用
   平台（当前：xiaohongshu 小红书、douyin 抖音）问用户要哪几个，或"全部"。

### 执行

```
读取: {baseDir}/references/multiplatform-rewrite.md
```

对每个目标平台：

1. `读取: {baseDir}/platforms/<id>.yaml`，按其 `rewrite_brief`、字数区间、
   标签数、输出格式改写。
2. 遵守 multiplatform-rewrite.md 的原创铁律（内容级真改，重构信息顺序/开头/表达，
   不是洗稿）与人设一致要求（persona 内核不变，只适配表达方式）。
3. 过双质量门（multiplatform-rewrite.md「质量门」小节）：humanness ≥ 0.6、
   与源及其他平台版本的 `max_similarity` ≤ 0.6；不过重写该版本，最多 2 次。
4. 写到 `{home}/output/<platform 的 output_filename>`。

### 完成

汇报每个平台版本的产出路径、字数、质量门结果；小红书版说明配图情况（复用了源稿
哪几张图，或"需补图"）。提醒：各平台账号发布是用户手动动作，WeWrite 当前只发
公众号草稿箱。
