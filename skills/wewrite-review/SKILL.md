---
name: wewrite-review
description: |
  WeWrite 质量验证模块：SEO（标题/摘要/标签）+ 编辑视角整体自评 + 反 AI 评分，
  也承接「检查一下 / 自检 / 这篇文章怎么样 / 有没有 AI 味」的自检报告。
  触发关键词：检查一下、自检、这篇文章怎么样、AI 味检测、反AI评分、公众号 SEO 优化。
  需要公众号/WeWrite 上下文；不应被通用的"代码 review"、网站 SEO 触发。
allowed-tools:
  - Bash
  - Read
  - Write
  - Edit
---

# wewrite-review — SEO + 质量验证

<!-- wewrite:standalone-start -->
## 运行约定

- **CLI**：确定性操作走 `wewrite` 命令（需在 PATH；缺失则引导 `uv tool install git+https://github.com/oaker-io/wewrite.git`，或在仓库里 `bash install.sh`）。
- **{home}**：用户状态目录 = `$WEWRITE_HOME` 或 `~/.wewrite`（`wewrite home` 可查）。config/style/history/playbook/output/exemplars 全在 {home}，不在仓库；references 文档中的状态路径同此约定。
- **`读取: <路径>`** = 用文件读取工具真实读完该文件再继续，不是注释。
- **references/**：本 skill 自带 `{skill_dir}/references/`；references 文档内的 `{skill_dir}` 即本 skill 目录。
- **管道状态**：`{home}/output/_state.yaml`（契约见主入口 wewrite 的 `references/pipeline-state.md`）。

## 前置

1. **文章**：用户指定的文件 > `_state.yaml` 的 `article` > `{home}/output/article.md`。
   都没有 → 问用户"要检查哪篇？"
2. 本会话若未读过 writing-guide.md → `读取: {skill_dir}/../wewrite-write/references/writing-guide.md`
   （5.2 校验按其编号规则 1.1-3.2 检查；管道模式下 wewrite-write 已读，保持驻留不要重读；
   读不到该文件就按本文件内建检查项执行）。
3. **模式判断**：管道内（或用户要"优化这篇"）→ 走「管道验证」；用户只要报告
   （"检查一下/怎么样"）→ 走「自检报告」，只诊断不改稿。
<!-- wewrite:standalone-end -->

## 管道验证

```
读取: {skill_dir}/references/seo-rules.md
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

## 自检报告（"检查一下 / 自检 / 这篇怎么样"）

对最近一篇生成的文章（或用户指定的文章）执行，输出生成报告：

**第一部分：生成档案**（这篇是怎么来的）
1. 读取 `{home}/history.yaml` 最近一条记录，提取：使用的框架类型 + 写作人格、激活的维度随机化组合、素材采集来源（WebSearch 还是降级到 LLM）、内容增强策略、范文库是否命中（用了哪几篇 exemplar 还是 fallback 到种子）、playbook 中生效的规则条数。
2. 若 history.yaml 无记录或用户指定了外部文章 → 跳过此部分，提示"这篇文章不是 WeWrite 生成的，只做质量检查"。

**第二部分：质量检查**（哪里还能改）
1. `wewrite score {article_path} --json`
2. Agent 解读 JSON 各项得分，翻译成可操作建议：每条定位到具体段落/句子、给出具体改法、按影响度排序最多 5 条。
3. 若各项得分都不错 → "这篇文章质量不错，建议在编辑锚点处加入你的个人内容就可以发了。"

**输出格式**：自然语言报告，不输出 JSON 或分数。
