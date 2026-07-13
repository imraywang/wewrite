---
name: wewrite-publish
description: |
  WeWrite 排版发布模块：Markdown → 微信 HTML 排版（16 主题 + 容器语法），metadata
  预检后推送公众号草稿箱或本地预览；含主题画廊、小绿书（图片帖）。
  触发关键词：推到草稿箱、发布公众号、微信排版、markdown 转微信格式、排版预览、
  主题画廊、看看有什么主题、换成XX主题、小绿书、图片帖。
  不应被"发布网站"、"发推特"触发——只管微信公众号。
allowed-tools:
  - Bash
  - Read
  - Write
  - Edit
  - Glob
---

# wewrite-publish — 排版 + 发布

<!-- wewrite:standalone-start -->
## 运行约定

- **CLI**：确定性操作走 `wewrite` 命令（需在 PATH；缺失则引导 `uv tool install git+https://github.com/oaker-io/wewrite.git`，或在仓库里 `bash install.sh`）。
- **{home}**：用户状态目录 = `$WEWRITE_HOME` 或 `~/.wewrite`（`wewrite home` 可查）。config/style/history/playbook/output/exemplars 全在 {home}，不在仓库；references 文档中的状态路径同此约定。
- **`读取: <路径>`** = 用文件读取工具真实读完该文件再继续，不是注释。
- **references/**：本 skill 自带 `{skill_dir}/references/`；references 文档内的 `{skill_dir}` 即本 skill 目录。
- **管道状态**：`{home}/output/_state.yaml`（契约见主入口 wewrite 的 `references/pipeline-state.md`）。

## 前置（发布/预览时；主题画廊、小绿书不需要）

1. **文章**：用户指定的文件 > `_state.yaml` 的 `article` > `{home}/output/article.md`。
2. **标题/摘要**：`_state.yaml` 的 `seo.title` / `seo.digest`；缺失 → 用文章 H1 当标题、
   converter 自动生成摘要（或建议先跑 wewrite-review 出 SEO）。
3. **封面**：`_state.yaml` 的 `images.cover`；没有 → 见 7.1 预检的封面行。
4. **主题**：style.yaml 的 `theme`，默认 professional-clean。
5. **降级标记**：读 `_state.yaml` 的 `flags.skip_publish`；缺失或 `diagnosed_at`
   非当天 → `wewrite diagnose --json` 重取并写回。
<!-- wewrite:standalone-end -->

## 发布主流程

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

## 辅助功能

| 用户说 | 动作 |
|--------|------|
| 看看有什么主题 / 主题画廊 | `wewrite gallery`（浏览器内预览全部 16 个主题） |
| 换成 XX 主题 | 用该主题重新 preview/publish；用户满意可提示写入 style.yaml 的 theme 字段 |
| 做一个小绿书 / 图片帖 | `wewrite image-post img1.jpg img2.jpg -t "标题"` |
| 只排版不发布 / 预览 | 走 preview 命令，输出本地 HTML 路径 |
