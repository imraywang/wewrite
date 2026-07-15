---
name: wewrite-review
description: |
  WeWrite 编辑审稿模块：核对事实来源、评价观点与实用性、优化标题摘要，并给出可交付的
  公众号成稿。也响应“检查这篇文章”。通用代码 review 和网站 SEO 不触发。
allowed-tools:
  - Bash
  - Read
  - Write
  - Edit
---

# wewrite-review — 编辑审稿

## 前置

用户指定文章时检查该文件；否则 `wewrite run show` 并读取 `artifacts.article`。管道内先：

```bash
wewrite run step review in_progress
```

完整读取：

```text
读取: {skill_dir}/../wewrite-write/references/editorial-quality.md
读取: {skill_dir}/references/seo-rules.md
```

用户只说“检查一下”时只给报告，不改文章；主流程或用户明确说“优化”时可以定点修改。

## 审稿顺序

### 1. 事实与来源

运行 `wewrite sources list --json`，逐项确认来源页面确实支持正文中的说法。检查：

- 具体数字、日期、引述、研究结论和时效性事实是否都有来源。
- 正文是否把推断写成事实，或把用户提供的信息伪装成公开核实结果。
- 链接是否指向原始页面，而不是搜索结果页。

缺证据时优先补查；查不到就删掉或改成有边界的判断，不能用模型记忆补洞。

### 2. 编辑质量

按“准确、观点、有用、合声、好读”五项通读全文。重点修：核心判断含糊、证据与结论脱节、
没有读者收益、虚构个人经验、结构跳跃和重复。每次只改真正影响交付的地方，不为了制造
所谓人味加入错句、情绪波动或无关岔路。

### 3. 标题、摘要与检索

生成一个主标题、两个备选标题、40 字内摘要和 5 个标签。标题必须准确，不承诺正文没有
交付的结果；关键词自然出现即可，不按密度硬塞。

### 4. 工具提示

```bash
wewrite score {article_path} --json
```

`quality_score` 为 0-100，越高代表检测到的语言风险越少。只查看禁用词、句式过齐、段落
节奏等提示；它不能判断事实、洞察或作者声音，不设机械及格线，也不为提分反复重写。

## 完成

管道内写入标题、摘要、标签、工具提示分和来源统计，再标记完成：

```bash
wewrite run update --patch '{"seo":{"title":"...","alt_titles":[],"digest":"...","tags":[],"quality_score":0},"provenance":{"verified_sources":0,"unverified_sources":0}}'
wewrite run step review completed
```

自检报告用自然语言，最多列 5 个按影响排序的问题，并指出具体位置和改法；没有硬伤就直说
正文可以交付，如有需要可再单独配图或排版，不输出大段分数表。
