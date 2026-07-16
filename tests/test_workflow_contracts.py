import io
import yaml
import pytest
from PIL import Image

from wewrite.commands import content_eval, diagnose, fetch_stats, humanness_score, learn_edits
from wewrite.history import append_article, load_history, save_history, upsert_article
from wewrite.runs import (
    create_run,
    finish_run,
    load_run,
    mark_step,
    resume_run,
    set_publish_permission,
    update_run,
)
from wewrite.sources import add_source, load_sources
from wewrite.toolkit import image_gen, publisher


def test_history_normalizes_legacy_list_and_saves_canonical(tmp_path):
    path = tmp_path / "history.yaml"
    path.write_text("- title: 旧文章\n  media_id: old\n", encoding="utf-8")

    data = load_history(path)
    assert data["version"] == 1
    assert data["articles"][0]["title"] == "旧文章"

    save_history(data, path)
    saved = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert saved == {"version": 1, "articles": [{"title": "旧文章", "media_id": "old"}]}


def test_append_article_preserves_existing_history(tmp_path):
    path = tmp_path / "history.yaml"
    append_article({"title": "第一篇"}, path)
    append_article({"title": "第二篇"}, path)
    assert [a["title"] for a in load_history(path)["articles"]] == ["第一篇", "第二篇"]


def test_upsert_article_refreshes_run_without_losing_stats(tmp_path):
    path = tmp_path / "history.yaml"
    upsert_article({"run_id": "r1", "title": "初稿", "stats": {"read_count": 10}}, path)
    upsert_article({"run_id": "r1", "title": "已发布", "media_id": "m1", "stats": None}, path)
    articles = load_history(path)["articles"]
    assert articles == [{
        "run_id": "r1",
        "title": "已发布",
        "media_id": "m1",
        "stats": {"read_count": 10},
    }]


def test_stats_updates_legacy_history_list(tmp_path, monkeypatch):
    path = tmp_path / "history.yaml"
    path.write_text("- title: 测试\n  media_id: m1\n", encoding="utf-8")
    monkeypatch.setattr(fetch_stats, "history_path", lambda: path)

    fetch_stats.update_history([{"title": "测试", "media_id": "m1", "int_page_read_count": 10}])

    article = load_history(path)["articles"][0]
    assert article["stats"]["read_count"] == 10


def test_diagnose_accepts_multi_provider_image_config(tmp_path, monkeypatch):
    path = tmp_path / "config.yaml"
    path.write_text(
        yaml.safe_dump({"image": {"providers": [{"provider": "doubao", "api_key": "key"}]}}),
        encoding="utf-8",
    )
    monkeypatch.setattr(diagnose.paths, "config_path", lambda: path)
    checks = diagnose.check_config()
    image_check = next(c for c in checks if c["name"] == "image_api_key")
    assert image_check["status"] == "pass"
    assert diagnose.runtime_flags(checks)["skip_image_gen"] is False


def test_missing_style_requires_onboard_without_failure(tmp_path, monkeypatch):
    monkeypatch.setattr(diagnose.paths, "style_path", lambda: tmp_path / "missing.yaml")
    checks = diagnose.check_style()
    assert checks == [{
        "group": "style",
        "name": "style_file",
        "status": "warn",
        "detail": "not found → first-run onboard required",
    }]
    assert diagnose.runtime_flags(checks)["needs_onboard"] is True


def test_quality_score_is_high_good_and_composite_is_compatible():
    result = humanness_score.score_article("这是一个测试。短句。再写一个更长一点的测试句子。")
    assert result["quality_score"] == round(100 - result["composite_score"], 2)
    assert result["tier1"]["emotional_balance"]["score"] == 1.0


def test_style_score_does_not_reward_forced_fragments():
    clean = "这是一个完整句子。这里继续把意思说清楚。最后给出明确结论。"
    forced = "嗯。\n\n然后。\n\n不对，\n\n算了。\n\n这个——"
    clean_score = humanness_score.score_sentence_integrity(clean)["score"]
    forced_score = humanness_score.score_sentence_integrity(forced)["score"]
    assert clean_score > forced_score


def test_learn_edits_uses_packaged_exemplar_module():
    from wewrite.commands import extract_exemplar

    assert extract_exemplar.extract_exemplar is not None
    assert learn_edits.__package__ == "wewrite.commands"


def test_exemplar_uses_high_is_good_quality_score(tmp_path, monkeypatch):
    from wewrite.commands import extract_exemplar
    monkeypatch.setattr(extract_exemplar, "EXEMPLARS_DIR", tmp_path)
    monkeypatch.setattr(extract_exemplar, "INDEX_FILE", tmp_path / "index.yaml")
    article = "# 标题\n\n这是开头。这里有一个更具体、更完整的说明。\n\n## 正文\n\n短句。再补一段内容。"
    exemplar = extract_exemplar.extract_exemplar(article, source="测试")
    path = extract_exemplar.save_exemplar(exemplar)
    saved = yaml.safe_load(path.read_text(encoding="utf-8").split("---\n")[1])
    index = yaml.safe_load((tmp_path / "index.yaml").read_text(encoding="utf-8"))
    assert saved["quality_score"] == exemplar["quality_score"]
    assert index[0]["quality_score"] == exemplar["quality_score"]
    assert saved["ownership"] == "unknown"
    assert saved["allowed_uses"] == ["style", "structure"]
    assert saved["personal_materials_reusable"] is False


def test_content_eval_requires_editorial_quality_and_measures_rewrite():
    draft = "# 标题\n\n## 旧结构\n\n一个含糊的判断。"
    final = "# 更准确的标题\n\n## 清楚的结论\n\n这个判断说明了适用条件。"
    report = content_eval.build_report(draft, final, {
        "decision": "pass",
        "pass_number": 2,
        "dimensions": {
            "accuracy": 4,
            "viewpoint": 4,
            "usefulness": 5,
            "voice": 4,
            "readability": 4,
        },
        "blockers": [],
        "major_issues": [],
    })
    assert report["publishable"] is True
    assert report["structure_changed"] is True
    assert report["edit_ratio"] > 0


def test_content_eval_blocks_false_pass_and_bad_scores():
    assessment = {
        "decision": "pass",
        "dimensions": {name: 4 for name in content_eval.DIMENSIONS},
        "blockers": ["存在虚构经历"],
        "major_issues": [],
    }
    assert content_eval.build_report("初稿", "终稿", assessment)["publishable"] is False
    assessment["blockers"] = []
    assessment["dimensions"]["accuracy"] = 2
    assert content_eval.build_report("初稿", "终稿", assessment)["publishable"] is False
    with pytest.raises(ValueError, match="non-empty"):
        content_eval.build_report("", "终稿", assessment)


def test_edit_learning_keeps_one_off_soft_and_scopes_patterns():
    now = learn_edits.datetime.now().isoformat()
    lessons = [{
        "timestamp": now,
        "patterns": [{
            "key": "shorter_paragraphs", "rule": "拆短", "scope": "framework",
            "scope_value": "清单", "confirmed": False,
        }],
    }]
    one = learn_edits.aggregate_patterns(lessons)[0]
    assert one["confidence"] < 5
    assert one["hard"] is False

    lessons.append({
        "timestamp": now,
        "patterns": [{
            "key": "shorter_paragraphs", "rule": "拆短", "scope": "framework",
            "scope_value": "清单", "confirmed": False,
        }, {
            "key": "shorter_paragraphs", "rule": "保留长段", "scope": "framework",
            "scope_value": "观点", "confirmed": False,
        }],
    })
    patterns = learn_edits.aggregate_patterns(lessons)
    by_scope = {p["scope_value"]: p for p in patterns}
    assert by_scope["清单"]["hard"] is True
    assert by_scope["观点"]["hard"] is False


def test_edit_learning_confirmation_can_make_single_rule_hard():
    now = learn_edits.datetime.now().isoformat()
    result = learn_edits.aggregate_patterns([{
        "timestamp": now,
        "patterns": [{"key": "tone", "confirmed": True}],
    }])[0]
    assert result["confidence"] < 5
    assert result["hard"] is True


def test_empty_learning_summary_is_valid_json(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("WEWRITE_HOME", str(tmp_path))
    learn_edits.summarize_lessons(as_json=True)
    assert yaml.safe_load(capsys.readouterr().out) == {
        "total_lessons": 0,
        "total_patterns": 0,
        "patterns": [],
    }


def test_runs_are_isolated_resumable_and_finish_once(tmp_path, monkeypatch):
    monkeypatch.setenv("WEWRITE_HOME", str(tmp_path))
    first = create_run(topic="第一篇")
    article = tmp_path / first["artifacts"]["article"]
    article.write_text("第一篇正文", encoding="utf-8")
    mark_step("write", "failed", first["run_id"], "network")
    resumed = resume_run(first["run_id"])
    assert resumed["status"] == "active"
    assert article.read_text(encoding="utf-8") == "第一篇正文"

    second = create_run(topic="第二篇")
    assert second["artifacts"]["article"] != first["artifacts"]["article"]
    assert article.read_text(encoding="utf-8") == "第一篇正文"
    (tmp_path / second["artifacts"]["article"]).write_text("第二篇正文", encoding="utf-8")

    finish_run({"seo": {"title": "第二篇"}}, second["run_id"])
    finish_run(run_id=second["run_id"])
    assert len(load_history(tmp_path / "history.yaml")["articles"]) == 1
    with pytest.raises(ValueError, match="immutable"):
        resume_run(second["run_id"])
    with pytest.raises(ValueError, match="start a new run"):
        update_run({"word_count": 9}, second["run_id"])


def test_images_and_publish_can_follow_a_completed_article(tmp_path, monkeypatch):
    monkeypatch.setenv("WEWRITE_HOME", str(tmp_path))
    run = create_run(topic="先写后配图", mode="complete")
    assert run["visual"]["mode"] == "none"
    assert run["artifacts"]["illustrated_article"].endswith("article-illustrated.md")
    (tmp_path / run["artifacts"]["article"]).write_text("已经完成的正文", encoding="utf-8")
    finish_run(run_id=run["run_id"])

    # The completed task remains the current article for independent follow-up actions.
    assert load_run()["run_id"] == run["run_id"]
    mark_step("visual", "in_progress")
    update_run({"visual": {"mode": "cover"}, "images": {"cover": "cover.png"}})
    mark_step("visual", "completed")
    mark_step("publish", "in_progress")
    update_run({"publish": {"preview_html": "preview.html", "media_id": "m1"}})
    mark_step("publish", "completed")

    finished = load_run(run["run_id"])
    assert finished["status"] == "completed"
    assert finished["steps"]["visual"]["status"] == "completed"
    assert finished["steps"]["publish"]["status"] == "completed"
    assert finished["images"]["cover"] == "cover.png"
    articles = load_history(tmp_path / "history.yaml")["articles"]
    assert len(articles) == 1
    assert articles[0]["media_id"] == "m1"

    with pytest.raises(ValueError, match="visual or publish"):
        mark_step("review", "in_progress", run["run_id"])
    with pytest.raises(ValueError, match="start a new run"):
        update_run({"seo": {"title": "改正文"}}, run["run_id"])


def test_all_run_modes_default_to_no_images(tmp_path, monkeypatch):
    monkeypatch.setenv("WEWRITE_HOME", str(tmp_path))
    for mode in ("draft", "complete", "publish"):
        run = create_run(mode=mode)
        assert run["visual"]["mode"] == "none"


def test_v2_run_is_upgraded_for_current_artifacts(tmp_path, monkeypatch):
    monkeypatch.setenv("WEWRITE_HOME", str(tmp_path))
    run = create_run(topic="旧任务")
    state_path = tmp_path / "runs" / run["run_id"] / "state.yaml"
    legacy = yaml.safe_load(state_path.read_text(encoding="utf-8"))
    legacy["version"] = 2
    for key in (
        "brief", "claims", "draft", "review_report",
        "illustrated_article", "image_prompts", "images_manifest",
    ):
        legacy["artifacts"].pop(key)
    state_path.write_text(yaml.safe_dump(legacy, allow_unicode=True), encoding="utf-8")

    upgraded = load_run(run["run_id"])
    assert upgraded["version"] == 4
    assert upgraded["artifacts"]["brief"].endswith("brief.yaml")
    assert upgraded["artifacts"]["claims"].endswith("claims.yaml")
    assert upgraded["artifacts"]["draft"].endswith("draft.md")
    assert upgraded["artifacts"]["review_report"].endswith("review-report.json")
    assert upgraded["artifacts"]["illustrated_article"].endswith("article-illustrated.md")
    assert upgraded["artifacts"]["image_prompts"].endswith("image-prompts.md")
    assert upgraded["artifacts"]["images_manifest"].endswith("images.json")


def test_source_ledger_is_per_run_and_deduplicates(tmp_path, monkeypatch):
    monkeypatch.setenv("WEWRITE_HOME", str(tmp_path))
    run = create_run(topic="来源测试")
    kwargs = {
        "run_id": run["run_id"],
        "url": "https://example.com/report",
        "title": "公开报告",
        "claim": "报告给出一项可核对的数据",
        "publisher": "Example",
    }
    add_source(**kwargs)
    add_source(**kwargs)
    sources = load_sources(run["run_id"])["sources"]
    assert len(sources) == 1
    assert sources[0]["status"] == "verified"
    (tmp_path / run["artifacts"]["article"]).write_text("来源测试正文", encoding="utf-8")
    finished = finish_run(run_id=run["run_id"])
    assert finished["provenance"]["verified_sources"] == 1


def test_user_provided_source_does_not_require_fake_web_url(tmp_path, monkeypatch):
    monkeypatch.setenv("WEWRITE_HOME", str(tmp_path))
    run = create_run(topic="用户资料")
    entry = add_source(
        run_id=run["run_id"], title="用户提供的访谈记录",
        claim="用户确认这是自己的经历", status="user_provided", url="",
    )
    assert entry["url"] == "user-provided://material"


def test_publish_run_requires_explicit_mode(tmp_path, monkeypatch):
    monkeypatch.setenv("WEWRITE_HOME", str(tmp_path))
    draft = create_run(mode="draft")
    publish_run = create_run(mode="publish")
    assert load_run(draft["run_id"])["permissions"]["publish"] is False
    assert load_run(publish_run["run_id"])["permissions"]["publish"] is True
    with pytest.raises(ValueError, match="Protected run fields"):
        update_run({"permissions": {"publish": True}}, draft["run_id"])
    with pytest.raises(ValueError, match="artifact paths"):
        update_run({"artifacts": {"article": "other.md"}}, draft["run_id"])


def test_publish_permission_can_be_granted_after_article_completion(tmp_path, monkeypatch):
    monkeypatch.setenv("WEWRITE_HOME", str(tmp_path))
    run = create_run(mode="draft")
    (tmp_path / run["artifacts"]["article"]).write_text("稍后再发布", encoding="utf-8")
    finish_run(run_id=run["run_id"])
    assert load_run(run["run_id"])["permissions"]["publish"] is False
    assert set_publish_permission(True, run["run_id"])["permissions"]["publish"] is True
    assert set_publish_permission(False, run["run_id"])["permissions"]["publish"] is False
    assert len(load_history(tmp_path / "history.yaml")["articles"]) == 1


def test_run_cannot_finish_without_article(tmp_path, monkeypatch):
    monkeypatch.setenv("WEWRITE_HOME", str(tmp_path))
    run = create_run(topic="空任务")
    with pytest.raises(ValueError, match="non-empty article"):
        finish_run(run_id=run["run_id"])


def test_drafted_run_cannot_finish_before_editorial_pass(tmp_path, monkeypatch):
    monkeypatch.setenv("WEWRITE_HOME", str(tmp_path))
    run = create_run(topic="需要审稿")
    (tmp_path / run["artifacts"]["draft"]).write_text("初稿", encoding="utf-8")
    (tmp_path / run["artifacts"]["article"]).write_text("成稿", encoding="utf-8")
    with pytest.raises(ValueError, match="editorial review passes"):
        finish_run(run_id=run["run_id"])
    (tmp_path / run["artifacts"]["review_report"]).write_text(
        '{"decision":"pass","publishable":true}', encoding="utf-8"
    )
    finished = finish_run({"editorial": {"decision": "pass", "publishable": True}}, run["run_id"])
    assert finished["status"] == "completed"


def _png_bytes(color="red"):
    buf = io.BytesIO()
    Image.new("RGB", (8, 8), color).save(buf, "PNG")
    return buf.getvalue()


def test_image_batch_enforces_count_and_cost_before_generation():
    cfg = {"image": {"estimated_cost_per_image": 0.5}}
    items = [{"prompt": "x", "output": "x.png"}] * 3
    with pytest.raises(ValueError, match="exceeds limit"):
        image_gen.generate_batch(items, cfg, max_images=2)
    with pytest.raises(ValueError, match="Estimated image cost"):
        image_gen.generate_batch(items, cfg, max_cost=1.0)


def test_provider_override_filters_multi_provider_config():
    cfg = {"image": {"providers": [
        {"provider": "doubao", "api_key": "one"},
        {"provider": "openai", "api_key": "two"},
    ]}}
    selected = image_gen._apply_provider_override(cfg, "openai")
    assert selected["image"]["providers"] == [{"provider": "openai", "api_key": "two"}]
    assert len(cfg["image"]["providers"]) == 2


def test_generated_image_is_valid_and_matches_extension(tmp_path, monkeypatch):
    class FakeProvider:
        provider_key = "fake"
        def resolve_size(self, size):
            return size
        def generate(self, prompt, size):
            return _png_bytes()

    monkeypatch.setattr(image_gen, "_build_provider_chain", lambda config: [FakeProvider()])
    output = tmp_path / "image.jpg"
    image_gen.generate_image("test", str(output), config={})
    with Image.open(output) as image:
        assert image.format == "JPEG"


def test_wechat_draft_requires_cover_and_uses_timeout(monkeypatch):
    with pytest.raises(ValueError, match="cover image"):
        publisher.create_draft("token", "title", "<p>x</p>", "digest")

    captured = {}
    class Response:
        def json(self):
            return {"media_id": "m1"}
    def fake_post(*args, **kwargs):
        captured.update(kwargs)
        return Response()
    monkeypatch.setattr(publisher.requests, "post", fake_post)
    publisher.create_draft("token", "title", "<p>x</p>", "digest", "cover")
    assert captured["timeout"] == 30
