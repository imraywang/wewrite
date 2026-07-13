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
allowed-tools:
  - Bash
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - WebSearch
  - WebFetch
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

**路径约定**：本文档中 `{skill_dir}` 指本 skill 目录（自带 `references/`）；兄弟模块经 `{skill_dir}/../wewrite-<模块>/` 访问（安装目录里各 skill 互为同级链接，路径经符号链接解析仍指回仓库）。**{repo}** = 仓库根，需要时用 `REPO="$(cd "$(dirname "$(realpath "{skill_dir}/SKILL.md")")/../.." && pwd)"` 定位。

**读取/检查约定**：本文档中 `读取: <路径>` / `检查: <路径>` = **用你环境的文件读取工具真实打开该文件、读完其全部内容，然后再继续本步**。这不是描述性注释——未读取前不得执行依赖该文件的步骤；不同 harness 的文件读取工具名不同，按你环境的对应工具执行。

**CLI 约定**：确定性操作（自检/抓热点/评分/生图/排版/发布…）一律走 `wewrite` 命令，需在 PATH（缺失 → `bash {repo}/install.sh` 或 `uv tool install git+https://github.com/oaker-io/wewrite.git`）。**{home}** = 用户状态目录 `$WEWRITE_HOME` 或 `~/.wewrite`（`wewrite home` 可查）——config/style/history/playbook/output/exemplars 全在 {home}，不在仓库；references 文档中的状态路径同此约定。

**管道状态**：跨模块状态统一落盘 `{home}/output/_state.yaml`，契约见 `{skill_dir}/references/pipeline-state.md`。主管道开新一篇文章时重置该文件（保留当天有效的 `flags`）。

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

<!-- wewrite:modular-start -->
**模块激活方式**：环境有 Skill 工具 → 直接激活同名 skill；没有 →
`读取: {skill_dir}/../<模块名>/SKILL.md`，跳过其「运行约定」小节，按主体执行。
<!-- wewrite:modular-end -->

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

<!-- wewrite:modular-start -->
### Step 2-7: 按序激活管道模块

| 进度 | 模块 | 核心产出 |
|------|------|---------|
| [2/8] 选题 | `wewrite-topic` | `_state.topic` |
| [3/8]+[4/8] 框架+素材 / 写作 | `wewrite-write` | `{home}/output/article.md` |
| [5/8] SEO+验证 | `wewrite-review` | `_state.seo` |
| [6/8] 视觉 AI | `wewrite-visual` | `_state.images`（.png 文件） |
| [7/8] 排版+发布 | `wewrite-publish` | `_state.publish` |

激活方式同上方「模块激活方式」。每个模块完成即更新进度，直接进下一个。
<!-- wewrite:modular-end -->
<!-- wewrite:inline-pipeline -->

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
| 热点抓取 | WebSearch 替代 |
| 选题为空 | 请用户手动给选题 |
| SEO 脚本 | LLM 判断 |
| 素材采集（WebSearch） | LLM 训练数据中可验证的公开信息 |
| 维度随机化 | history 空时跳过去重 |
| Persona 文件不存在 | 回退到 midnight-friend（默认） |
| 范文库为空 | Fallback 到 exemplar-seeds.yaml（通用模式） |
| 质量验证 | 评分仅作参考；读着顺、无硬伤即继续，修不动的小问题留给作者 |
| 生图失败 | 输出提示词 |
| 推送失败 | 本地 HTML |
| 历史写入 | 警告不阻断 |
| 效果数据 | 告知等 24h |
| Playbook 不存在 | 用 writing-guide.md |
<!-- wewrite:modular-start -->
| 模块 skill 未安装（Skill 工具不可见） | `读取: {skill_dir}/../<模块名>/SKILL.md` 按主体执行 |
<!-- wewrite:modular-end -->

<!-- wewrite:inline-aux -->
