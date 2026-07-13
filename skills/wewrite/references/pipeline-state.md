# 管道状态契约（{home}/output/_state.yaml）

WeWrite 拆分为「主入口 wewrite + wewrite-* 模块 skill」后，跨模块的管道状态统一落盘在
`{home}/output/_state.yaml`。这是模块之间唯一的握手文件——模块可以在同一会话被主入口
按序激活，也可以在全新会话被用户单独激活，两种情况都靠它接上上下文。

## 读写规则

1. **进入模块时读取**。文件不存在 → 视为空状态，按各模块 SKILL.md 的「前置」小节补齐或降级。
2. **完成模块时合并写回**：只更新本模块产出的字段 + `updated` + 向 `steps_done` 追加自己的名字；其余字段原样保留。
3. **主入口开新一篇文章时重置**：清空除 `flags` 外的全部字段（flags 当天有效可复用）。
4. **flags 时效**：`flags.diagnosed_at` 非当天 → 视为过期，需要 flags 的模块自己重跑
   `diagnose.py --json` 并写回。
5. Step 8 收尾时，主入口以本文件为唯一事实源写 `history.yaml`。

## 字段定义

```yaml
updated: "2026-07-12 14:30"        # 每次写回时更新
flags:                              # diagnose.py 产出（谁先跑谁写入）
  skip_publish: false
  skip_image_gen: false
  use_writer_model: false
  diagnosed_at: "2026-07-12"
topic:                              # wewrite-topic 产出；用户直接给选题时由主入口记录
  title: ""
  keywords: []
  source: "热点抓取"                # 或 "用户指定"
  framework_hint: ""                # 选题阶段的推荐框架
article: "output/article.md"        # wewrite-write 产出（相对 {home}；全流程统一文件名）
framework: ""                       # wewrite-write 选定（7 套框架之一）
enhance_strategy: ""                # angle_discovery/density_boost/detail_anchoring/real_feel
persona: ""                         # wewrite-write 加载的写作人格
dimensions: []                      # 维度随机化组合，如 "叙事视角: 对话体"
closing_type: ""                    # trailing_off/unanswered/scene_revert/abrupt_stop/anti_conclusion/image
word_count: 0
seo:                                # wewrite-review 产出
  title: ""
  alt_titles: []
  digest: ""
  tags: []
  composite_score: null             # humanness_score 的 composite（0=好,100=差，仅参考）
images:                             # wewrite-visual 产出
  cover: ""                         # 如 output/{slug}-cover.png
  figures: []
publish:                            # wewrite-publish 产出
  media_id: null                    # 降级（本地预览）时为 null
  preview_html: ""
steps_done: []                      # 累加: topic / write / review / visual / publish
```

## 为什么需要它

单体版 8 步靠同一会话的上下文驻留隐式传递状态（选题、素材、降级标记、persona）。
模块化后每个 skill 必须能独立进入，隐式状态必须显式化——否则单独激活 wewrite-visual
时它不知道文章在哪、封面风格锚点是什么。改动模块时先想清楚：新状态要不要进契约？
只有「会被下游模块消费」的才进；模块内部的中间量（如素材锚点在 write 内部）不进。
