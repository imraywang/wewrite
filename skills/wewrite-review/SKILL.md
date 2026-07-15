---
name: wewrite-review
description: |
  WeWrite 编辑审稿模块：核对任务、事实来源、观点和实用性，必要时直接改稿，只有通过编辑门槛
  才生成公众号成稿。也响应“检查这篇文章”。通用代码 review 和网站 SEO 不触发。
allowed-tools:
  - Bash
  - Read
  - Write
  - Edit
---

# wewrite-review — 编辑、改稿与成稿

## 前置

用户指定文章时检查该文件；否则运行 `wewrite run show`，优先读取 `artifacts.draft`，并读取
`artifacts.brief`、`artifacts.claims` 和 `artifacts.sources`。旧任务没有初稿产物时才回退
`artifacts.article`。管道内先运行 `wewrite run step review in_progress`。

完整读取：

```text
读取: {skill_dir}/../wewrite-write/references/article-brief.md
读取: {skill_dir}/../wewrite-write/references/editorial-quality.md
读取: {skill_dir}/references/seo-rules.md
```

用户只说“检查一下”且给了外部文件时，只给报告；主流程、任务内初稿或用户明确说“优化”时，
必须直接完成必要修改。

## 审稿与改稿

### 1. 对齐任务

检查文章是否真的回答 `audience.question`，核心判断是否与 `thesis` 一致，每节是否推动指定
claim，结尾是否交付 `goal.takeaway/action`。无关段落删除，不用漂亮结构掩盖答非所问。

### 2. 核对事实与个人材料

运行 `wewrite sources list --json`，把正文中的具体数字、日期、引述、研究结论和时效性事实
逐项对到 `claims.yaml` 与原始来源。来源不支持时优先补查；查不到就删除、缩小或改成明确的
推断。不能用模型记忆补洞。

检查所有第一人称事件、朋友同事、采访、对话、时间地点和感官细节。它们必须来自本次任务
明确记录的用户材料；否则属于阻断问题，直接删除或改成非亲历论述。

### 3. 五项编辑判断

按“准确、观点、有用、合声、好读”各评 1-5 分，并列出阻断问题和最多 5 个主要问题：

- `pass`：平均分至少 4、单项不低于 3、没有阻断问题。
- `revise`：能在现有材料内修正。直接修改后重新执行 1-3，不得只写建议。
- `needs_input`：仅限用户明确要求个人故事而材料不足且无法安全换框架。

最多两轮。第二轮仍有问题时，删掉不可靠内容、缩小承诺，生成能通过的可靠版本；不得给未
通过的文章贴上“可交付”。通过后把最终正文写入 `artifacts.article`。

### 4. 标题、摘要与工具提示

生成一个主标题、两个准确的备选标题、40 字内摘要和 3-5 个标签。关键词自然出现，不按密度
硬塞，也不为打开率虚构数字或承诺。审稿不调用配图。

运行 `wewrite score {article_path} --json`。该分数只帮助定位套话、句式过齐和段落节奏风险，
不设机械及格线，也不为提分反复重写。

## 保存编辑报告

先把编辑判断写为任务目录内临时 `assessment.yaml`：

```yaml
decision: pass
pass_number: 1
dimensions:
  accuracy: 4
  viewpoint: 4
  usefulness: 4
  voice: 4
  readability: 4
blockers: []
major_issues: []
notes: ""
```

再生成 `artifacts.review_report`：

```bash
wewrite content-eval --draft {draft_path} --final {article_path} \
  --assessment {assessment_path} --output {review_report_path} --json
```

只有报告里的 `publishable=true` 才能完成审稿。更新任务并标记完成：

```bash
wewrite run update --patch '{"editorial":{"decision":"pass","pass_number":1,"publishable":true},"seo":{"title":"...","alt_titles":[],"digest":"...","tags":[],"quality_score":0},"provenance":{"verified_sources":0,"unverified_sources":0}}'
wewrite run step review completed
```

自检报告用自然语言，最多列 5 个按影响排序的问题，并说明已经怎样修正。没有硬伤就直说正文
可以交付；如有需要可再单独配图或排版，不输出大段分数表。
