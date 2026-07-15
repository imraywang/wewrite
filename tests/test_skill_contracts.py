from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def _read(relative):
    return (ROOT / relative).read_text(encoding="utf-8")


def test_pipeline_uses_run_scoped_state_and_explicit_publish_permission():
    main = _read("skills/wewrite/SKILL.md")
    publish = _read("skills/wewrite-publish/SKILL.md")
    assert "wewrite run start" in main
    assert "permissions.publish=true" in publish
    assert "“写一篇”默认只交付审过的本地稿" in main
    assert "output/_state.yaml" not in main
    assert "output/article.md" not in main


def test_visual_is_an_optional_post_completion_action():
    main = _read("skills/wewrite/SKILL.md")
    visual = _read("skills/wewrite-visual/SKILL.md")
    publish = _read("skills/wewrite-publish/SKILL.md")
    assert "--mode complete --visual-mode none" in main
    assert "--mode publish --visual-mode none" in main
    assert main.index("wewrite run finish") < main.index("## 可选后续动作")
    assert "已完成的文章也可以直接配图" in visual
    assert "artifacts.illustrated_article" in visual
    assert "任何模式都不得覆盖原始正文" in visual
    assert "artifacts.illustrated_article" in publish
    assert "排版和发布不得自动调用 `wewrite-visual`" in publish
    assert "wewrite run permission publish allow" in publish


def test_writing_and_review_require_source_ledger_and_editorial_quality():
    write = _read("skills/wewrite-write/SKILL.md")
    review = _read("skills/wewrite-review/SKILL.md")
    assert "wewrite sources add" in write
    assert "不得把模型记忆标为 `verified`" in write
    assert "准确、观点、有用、合声、好读" in review
    editorial = _read("skills/wewrite-write/references/editorial-quality.md")
    assert "情绪配额" in editorial


def test_visual_contract_enforces_count_and_cost_limits():
    visual = _read("skills/wewrite-visual/SKILL.md")
    assert "--max-images" in visual
    assert "--max-cost" in visual
    assert "不能绕过上限" in visual
