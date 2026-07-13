---
name: wewrite-write
description: |
  WeWrite 写作模块（管道半内部）：在选题已确定的前提下完成「框架选择 → 素材采集/
  内容增强 → 反 AI 正文写作」，产出 output/article.md。
  仅在两种情况触发：主入口 wewrite 管道调度；或用户已有明确选题且只要正文
  （"就这个选题写一篇""按框架 X 重写正文"）。
  "写一篇公众号（文章）"等完整需求一律触发主入口 wewrite（含选题/配图/发布），
  不是本模块；通用"写文章"、blog、短视频文案也不触发。
allowed-tools:
  - Bash
  - Read
  - Write
  - Edit
  - Glob
  - WebSearch
  - WebFetch
---

# wewrite-write — 框架 + 素材 + 写作

<!-- wewrite:standalone-start -->
## 运行约定

- **{root}** = `{skill_dir}/root`（本目录内指向 WeWrite 仓库根的符号链接）。
- **Python**：优先 venv——`PY="{root}/.venv/bin/python3"; [ -x "$PY" ] || PY="python3"`；下文 `python3` 均指 `$PY`。
- **`读取: <路径>`** = 用文件读取工具真实读完该文件再继续，不是注释。
- **references/ 文档中的 `{skill_dir}`** 一律指 `{root}`（历史约定，指仓库根）。
- **管道状态**：`{root}/output/_state.yaml`（契约见 `{root}/references/pipeline-state.md`）。

## 前置

1. **选题**：取 `output/_state.yaml` 的 `topic`；没有则用用户本轮给的选题（写入
   `topic`，`source: "用户指定"`）；都没有 → 问用户要写什么，或建议先跑 **wewrite-topic**。
2. **风格**：`{root}/style.yaml` 存在 → 提取 `name`、`topics`、`tone`、`voice`、
   `blacklist`、`writing_persona`、`content_style`。不存在 → 先激活 **wewrite-style**（onboard）。
3. **写作模式标记**：读 `_state.yaml` 的 `flags.use_writer_model`；缺失或
   `diagnosed_at` 非当天 → `python3 {root}/scripts/diagnose.py --json` 重取并写回。
<!-- wewrite:standalone-end -->

## Step 3: 框架 + 素材

**3.1 框架选择**：

```
读取: {root}/references/frameworks.md
```

7 套框架（痛点/故事/清单/对比/热点解读/纯观点/复盘），自动选推荐指数最高的
（`topic.framework_hint` 与 history 表现加权参与推荐）。

**3.2 素材采集 + 内容增强**（合并执行，共用搜索结果）：

```
读取: {root}/references/content-enhance.md
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

**降级**：WebSearch 不可用 → 用 LLM 训练数据中可验证的公开信息。但需告知用户："素材采集未能使用 WebSearch，建议在编辑锚点处多加入你自己的内容。"密度强化不依赖搜索，始终执行。

## Step 4: 写作

> **🔴 写作模式取决于前置的 `flags.use_writer_model`（详见 4.4），别两种都做**：
> - **`false`（默认 · 编排器自写）** → 你直接按"写作规范"写正文。**不要调用 `llm_write.py`**（没配写作模型，调了必然 exit 3、白费一轮）。
> - **`true`（混合路由 · 配了写作模型）** → 你只编排，正文交 `scripts/llm_write.py` 出稿。
>
> 下面 4.1-4.3 读取的文件两种模式都要（自写时是写作依据；委托时是 brief 备料）。

```
读取: {root}/references/anti-ai-writing-system.md
读取: {root}/references/writing-guide.md
读取: {root}/playbook.md（如果存在，按 confidence 分级执行）
读取: {root}/history.yaml（最近 3 篇的 dimensions + closing_type 字段）
读取: {root}/references/exemplars/index.yaml（如果存在）
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
读取: {root}/personas/{选定人格}.yaml
```

人格的选定规则（参见 `{root}/references/persona-selection.md`）：

- **style.yaml 有 `writing_persona`** → 直接加载该人格。用户已固定账号声音，尊重配置（persona-selection 的「用户明确指定」优先级最高）。
- **没有 `writing_persona`**（或用户本轮明确要求换风格）→ 读取 `references/persona-selection.md`，按选定选题的特征匹配 top 2 人格；用 history.yaml 最近 3 篇的写作人格降权（保证风格多样化），向用户展示推荐理由让其二选一；匹配不明确时默认 midnight-friend。

人格文件定义了：语气浓度、数据呈现方式、情绪弧线、段落节奏、不确定性表达模板等。作为写作的硬性约束执行。

**优先级**：playbook.md（confidence ≥ 5 的规则）> persona > 范文风格 > writing-guide.md。writing-guide 是底线（基础写作规范），范文提供风格示范（句长节奏、情绪表达方式），persona 在此基础上特化风格参数（语气浓度、数据呈现），playbook 中高置信度规则是用户个性化的最终覆盖。playbook 中 confidence < 5 的规则作为软性参考。

**4.3 范文风格注入**（有 `references/exemplars/index.yaml` 时执行）：

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

**Fallback（范文库为空时）**：读取 `{root}/references/exemplar-seeds.yaml`，从每个段落类型中随机选 1 个注入 prompt。种子段落只示范人类写作的结构模式（句长方差、情绪锐度、自我纠正、非总结式收尾），不携带特定风格。注入时使用：

> 以下是人类写作的结构模式示例，注意模仿其句长节奏和情绪表达方式（不要模仿具体内容或风格）：
>
> 【开头模式】{seeds.opening_hooks 随机 1 个}
>
> 【情绪段模式】{seeds.emotional_peaks 随机 1 个}
>
> 【转折模式】{seeds.transitions 随机 1 个}
>
> 【收尾模式】{seeds.closings 随机 1 个}

建库命令：`python3 {root}/scripts/extract_exemplar.py article.md`

**4.4 写文章** —— 本步只产出 `output/article.md`。按前置的 `flags.use_writer_model` **二选一**，别两种都走：

**A. 自写模式（`use_writer_model = false`，默认 · 全 DeepSeek）**：按下面"写作规范"直接把正文写进 `output/article.md`，写完执行 4.5。**不要调用 `llm_write.py`**——没配写作模型，调它只会 exit 3、白白多耗一轮。

**B. 委托模式（`use_writer_model = true`，混合路由 · 配了写作模型）**：你只编排，正文交给写作模型：
1. 把【Step 3 框架大纲 + **Step 3.2 的真实素材锚点（具体数字/工具名/价格/案例——逐条写进去；写作模型只在给定事实上组织语言，严禁编造）** + 4.1 维度 + 4.2 人格要点 + 4.3 范文风格片段 + 下面"写作规范"全部要求 + 目标字数 + 可用容器语法 + 编辑锚点要求】组装成 brief，写到 `output/_brief.md`。
2. 调：`python3 {root}/scripts/llm_write.py --brief output/_brief.md --output output/article.md`
3. 按退出码：**exit 0**（stdout 是摘要）→ 正文已写入，**不要 cat / 读全文**（靠评分驱动改写——省钱命门；只有 wewrite-review 的整体自评读一次全文），**跳过 4.5** 直接进验证。**exit 3 / 4**（没配/失败）→ 退回 A 自写。

**写作规范**（自己写时直接执行；委托写作模型时这些就是 brief 的内容要求）：
- **🔴 出稿契约**：严格按 `references/anti-ai-writing-system.md` 的反 AI 写作铁律**逐条满足**（句长强烈交替 / 段落长短交替 / 杜绝 AI 腔词 / 事实零编造 / 情绪有起伏 / 少副词 / 口语化自我修正 / 不堆整齐小标题），违反任一条直接重写。这是把 composite 压到 <30 的关键，下面的细则与之一致。
- H1 标题（20-28 字） + H2 结构，1500-2500 字
- **素材 + 增强约束**：Step 3.2 的素材和增强材料分散嵌入各 H2 段落。增强策略的核心输出（角度/密度要点/细节/用户声音）必须贯穿全文，不只装饰性出现一次
- **写作人格**：按 4.2 加载的人格参数写作（数据呈现方式、个人声音浓度、不确定性表达等）
- **收尾方式**：persona 的 `closing_tendency` 仅作为倾向参考。根据文章内容和情绪弧线自行判断最自然的收尾方式。如果 history.yaml 中最近 3 篇有 `closing_type` 字段，避免使用相同的收尾类型
- **写作规范**：writing-guide.md 中的基础规则（禁用词、句长方差、词汇混用等）在初稿阶段生效
- **分段实时自检**：读取 `{root}/references/realtime-check.md`，每写完约 500 字（或每个 H2）就地执行 5 项快速检查（句长交替 / 情绪锚定 / 词汇温度 / 素材锚定 / 句法变形），问题当场掐掉不累积到全文。按 500 字/H2 粒度查，不要写一句修一句；也不要为凑检查项刻意制造大量单句段落（会触发过度优化检测）
- 2-3 个编辑锚点：`<!-- ✏️ 编辑建议：在这里加一句你自己的经历/看法 -->`
- 可选容器语法：`:::dialogue`、`:::timeline`、`:::callout`、`:::quote`、`:::highlight`（琥珀高亮框）、`:::summary`（青色总结框）

保存到 `{root}/output/article.md`（全流程统一用这个工作文件名；委托写作模型与自己写都写这里）

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

## 完成

写回 `output/_state.yaml`：`article: "output/article.md"`、`framework`、
`enhance_strategy`、`persona`、`dimensions`、`closing_type`、`word_count`，
`steps_done` 追加 `write`。单独激活时提示："初稿完成，建议接着跑质量验证
（wewrite-review）再配图发布。"
