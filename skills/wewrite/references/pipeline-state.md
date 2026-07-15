# 任务状态契约

每篇文章使用 `{home}/runs/<run_id>/state.yaml`，通过 `wewrite run` 读写。不要直接修改
`state.yaml`，也不要再使用共享的 `output/_state.yaml`。

## 生命周期

1. `wewrite run start` 创建独立目录、文章路径、来源账本和权限。
2. `wewrite run update` 合并模块产出，`wewrite run step` 记录步骤状态。
3. `wewrite run resume` 恢复失败或未完成任务。
4. `wewrite run finish` 封存正文、来源和写作结果并写入统一历史。
5. 已完成任务仍可追加 `visual/images/publish` 结果，但原始正文、来源和写作字段不可修改。
6. 用户明确要求或撤回发布时，用 `wewrite run permission publish allow/deny` 单独记录权限。

## 关键字段

```yaml
version: 4
run_id: "20260715-120000-a1b2c3"
status: active                 # active / failed / completed
mode: draft                    # draft / complete / publish
permissions:
  publish: false               # 只有用户明确要求发布才为 true
visual:
  mode: none                   # none / prompts / cover / full
  max_images: 4
  max_cost: null
flags:
  skip_publish: false
  skip_image_gen: false
  use_writer_model: false
  needs_onboard: false
  diagnosed_at: "2026-07-15"
topic:
  title: ""
  keywords: []
  source: "用户指定"
artifacts:
  brief: "runs/<run_id>/brief.yaml"
  claims: "runs/<run_id>/claims.yaml"
  draft: "runs/<run_id>/draft.md"
  article: "runs/<run_id>/article.md"
  illustrated_article: "runs/<run_id>/article-illustrated.md"
  image_prompts: "runs/<run_id>/image-prompts.md"
  images_manifest: "runs/<run_id>/images.json"
  review_report: "runs/<run_id>/review-report.json"
  sources: "runs/<run_id>/sources.yaml"
  preview: "runs/<run_id>/preview.html"
seo:
  title: ""
  alt_titles: []
  digest: ""
  tags: []
  quality_score: null
editorial:
  decision: null             # pass / revise / needs_input
  pass_number: null
  publishable: false
provenance:
  verified_sources: 0
  unverified_sources: 0
  exemplars: []
  playbook_rules: []
images:
  cover: ""
  figures: []
publish:
  media_id: null
  preview_html: ""
steps: {}
last_error: null
```

所有产物路径都相对 `{home}`。下游模块只读当前任务里的路径，不能回退到共享的
`output/article.md`，避免并行文章互相覆盖。写作模块生成任务书、主张清单和初稿；审稿通过
后才生成 `article.md` 和编辑报告。视觉模块只能写图片和
`illustrated_article`，发布模块优先使用非空的带图副本，否则使用原始正文。读取 v2 任务时
CLI 会自动补齐新增产物路径，不需要手工迁移。
