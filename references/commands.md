# WeWrite 命令分发（非管道）

> SKILL.md 检测到"选题→发布"主流程之外的命令时加载本文件，按下表执行。
> 主管道内的步骤不需要本文件。

## 触发词 → 动作

| 用户说 | 动作 |
|--------|------|
| 重新设置风格 | `读取: {skill_dir}/references/onboard.md` |
| 学习我的修改 | `读取: {skill_dir}/references/learn-edits.md`。支持本地 markdown 修改与微信草稿箱同步（`python3 {skill_dir}/scripts/learn_edits.py --from-wechat`） |
| 学习排版 / 学排版 | `python3 {skill_dir}/scripts/learn_theme.py <url> --name <name>`，提取后提示用户设置 style.yaml 的 theme 字段 |
| 学习这篇文章 / 导入范文 + URL | `python3 {skill_dir}/scripts/fetch_article.py <url> -o /tmp/article.md && python3 {skill_dir}/scripts/extract_exemplar.py /tmp/article.md -s <账号名>` |
| 查看范文库 | `python3 {skill_dir}/scripts/extract_exemplar.py --list` |
| 看看文章数据 | `读取: {skill_dir}/references/effect-review.md` |
| 看看有什么主题 / 主题画廊 | `python3 {skill_dir}/toolkit/cli.py gallery` |
| 做一个小绿书 / 图片帖 | `python3 {skill_dir}/toolkit/cli.py image-post img1.jpg img2.jpg -t "标题"` |
| 更新 / 更新 WeWrite / 升级 | 在 {skill_dir} 执行 `git pull origin main`，完成后告知版本变化 |
| 检查一下 / 自检 / 这篇文章怎么样 | 见下方「自检报告」 |

## 自检报告（"检查一下/自检"）

对最近一篇生成的文章（或用户指定的文章）执行，输出生成报告：

**第一部分：生成档案**（这篇是怎么来的）
1. 读取 `history.yaml` 最近一条记录，提取：使用的框架类型 + 写作人格、激活的维度随机化组合、素材采集来源（WebSearch 还是降级到 LLM）、内容增强策略、范文库是否命中（用了哪几篇 exemplar 还是 fallback 到种子）、playbook 中生效的规则条数。
2. 若 history.yaml 无记录或用户指定了外部文章 → 跳过此部分，提示"这篇文章不是 WeWrite 生成的，只做质量检查"。

**第二部分：质量检查**（哪里还能改）
1. `python3 {skill_dir}/scripts/humanness_score.py {article_path} --json`
2. Agent 解读 JSON 各项得分，翻译成可操作建议：每条定位到具体段落/句子、给出具体改法、按影响度排序最多 5 条。
3. 若各项得分都不错 → "这篇文章质量不错，建议在编辑锚点处加入你的个人内容就可以发了。"

**输出格式**：自然语言报告，不输出 JSON 或分数。
