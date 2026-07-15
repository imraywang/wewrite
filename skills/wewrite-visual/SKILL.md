---
name: wewrite-visual
description: |
  WeWrite 视觉模块：为公众号文章生成封面 + 内文配图（提示词创作 → 风格锚定 →
  批量 AI 生图 → 验证插入）。
  触发关键词：封面图、生成封面、配图、给文章配图、换封面、封面换个风格。
  需要公众号/WeWrite 上下文；不应被通用的"画个图"、logo 设计触发。
allowed-tools:
  - Bash
  - Read
  - Write
  - Edit
  - Glob
---

# wewrite-visual — 视觉 AI（封面 + 配图）

## 运行约定

- **CLI**：确定性操作走 `wewrite` 命令（需在 PATH；缺失则引导 `uv tool install wewrite`，或在仓库里 `bash install.sh`）。
- **{home}**：用户状态目录 = `$WEWRITE_HOME` 或 `~/.wewrite`（`wewrite home` 可查）。config/style/history/playbook/output/exemplars 全在 {home}，不在仓库；references 文档中的状态路径同此约定。
- **`读取: <路径>`** = 用文件读取工具真实读完该文件再继续，不是注释。
- **references/**：本 skill 自带 `{skill_dir}/references/`；references 文档内的 `{skill_dir}` 即本 skill 目录。
- **管道状态**：`{home}/output/_state.yaml`（契约见主入口 wewrite 的 `references/pipeline-state.md`）。

## 前置

1. **文章**：用户指定的文件 > `_state.yaml` 的 `article` > `{home}/output/article.md`。
   都没有 → 问用户"给哪篇文章配图？"
2. **降级标记**：读 `_state.yaml` 的 `flags.skip_image_gen`；缺失或 `diagnosed_at`
   非当天 → `wewrite diagnose --json` 重取并写回。
3. style.yaml 的 `cover_style` / `cover_template`（有则作为封面风格约束）。

## 执行

**如果 `skip_image_gen = true`** → 只执行 6.1（输出提示词，不生图）。

```
读取: {skill_dir}/references/visual-prompts.md
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

确认后按 6.2 的段落分析，把图片引用（`![描述](实际生成的 .png 路径)`）一次性插入对应段落——正文里没有占位符，插入位置以 6.2 的分析为准。

**降级**：`wewrite image-gen` 支持多 provider 自动 fallback（按 config.yaml 中 providers 列表顺序尝试）。全部失败 → 输出提示词 + 备选图库关键词，继续。

## 完成

写回 `_state.yaml`：`images.cover`、`images.figures`（实际生成的 .png 路径），
`steps_done` 追加 `visual`。单独激活时展示生成的图片路径并提示可"换个风格重生成"。
