---
name: wewrite-publish
description: |
  WeWrite 排版发布模块：把 Markdown 做成微信预览，或在用户明确授权后推入公众号草稿箱；
  也支持主题画廊和图片帖。只处理微信公众号。
allowed-tools:
  - Bash
  - Read
  - Write
  - Edit
  - Glob
---

# wewrite-publish — 排版、预览、草稿箱

## 前置

用户指定文章时使用该文件；否则 `wewrite run show`。如果
`artifacts.illustrated_article` 存在且非空就使用它，否则使用 `artifacts.article`；读取标题、
摘要、封面、预览路径、发布权限和降级标记。已完成文章可以直接排版或发布，不要恢复写作
任务。主题取 style.yaml 的 `theme`，默认 `professional-clean`。

排版和发布不得自动调用 `wewrite-visual`。没有封面时照常生成本地预览；只有用户另行要求
配图时才进入视觉模块。

用户本轮明确要求“推到草稿箱/发布”时，有任务先运行
`wewrite run permission publish allow`；用户撤回时运行 `wewrite run permission publish deny`。
只排版、预览或“完整制作”都不能授予发布权限。

有任务时进入：

```bash
wewrite run step publish in_progress
```

## 预检

- 标题存在且符合微信限制；摘要不超过 120 字节；正文 200-20000 字。
- 正文图片不超过 10 张且实际可读；表格不超过 4 列。
- 发布草稿必须有封面。没有封面不能假设微信会补默认图，改走本地预览。
- 发布必须同时满足：`permissions.publish=true`、`flags.skip_publish=false`、用户本轮没有撤回。

## 动作

始终先生成本地预览，有任务时保存到 `artifacts.preview`；任务外文章保存到原文件旁：

```bash
wewrite preview {article} --theme {theme} --no-open -o {preview}
```

确认预览产物存在且通过兼容性校验。若没有明确发布权限，流程到此结束；“写一篇”“完整制作”
都不等于允许发布。

只有用户明确要求草稿箱且预检全部通过时执行：

```bash
wewrite publish {article} --cover {cover} --theme {theme} --title "{title}" --digest "{digest}"
```

发布失败时保留预览，不自动重试产生外部动作。有任务时更新 `publish.preview_html`；成功时再写
`publish.media_id`，随后：

```bash
wewrite run step publish completed
```

## 辅助功能

| 用户说 | 动作 |
|---|---|
| 看主题 | `wewrite gallery` |
| 换主题 | 重新 preview；只有再次明确要求才重新 publish |
| 做图片帖 | 先确认用户确实要推草稿箱，再执行 `wewrite image-post` |
| 只排版 | 只 preview |
