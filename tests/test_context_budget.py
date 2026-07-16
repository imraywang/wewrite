import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from context_budget import parse_onpath_refs, measure  # noqa: E402


def test_parse_onpath_excludes_auxiliary():
    sample = (
        "读取: {skill_dir}/references/article-brief.md\n"
        "读取: {root}/references/onboard.md\n"
        "读取: {root}/references/editorial-quality.md\n"
        "读取: {root}/references/pipeline-state.md\n"
    )
    refs = parse_onpath_refs(sample)
    assert "references/article-brief.md" in refs
    assert "references/editorial-quality.md" in refs
    assert "references/onboard.md" not in refs
    assert "references/pipeline-state.md" not in refs


def test_parse_dedupes_and_preserves_order():
    sample = (
        "读取: {skill_dir}/references/seo-rules.md\n"
        "读取: {skill_dir}/references/seo-rules.md\n"
    )
    assert parse_onpath_refs(sample) == ["references/seo-rules.md"]


def test_measure_reports_peak_on_real_repo():
    repo = Path(__file__).resolve().parent.parent
    r = measure(repo)
    assert r["peak_tokens"] > 0
    assert any(e["name"] == "skills/wewrite/SKILL.md" for e in r["entries"])
    assert any(e["name"] == "skills/wewrite-write/SKILL.md" for e in r["entries"])
    assert any(e["name"].endswith("editorial-quality.md") for e in r["entries"])
    assert any(e["name"].endswith("frameworks-quick.md") for e in r["entries"])
    retired = {
        "writing-guide.md",
        "frameworks.md",
        "visual-prompts.md",
        "cover-prompts.md",
        "compliance-seo.md",
    }
    assert not any(Path(e["name"]).name in retired for e in r["entries"])
    assert r["peak_tokens"] < 8000
