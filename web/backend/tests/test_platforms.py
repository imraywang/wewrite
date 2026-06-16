import textwrap
from pathlib import Path
from app.platforms import load_profile, PlatformProfile

def test_load_profile_parses_fields(tmp_path: Path):
    f = tmp_path / "xhs.yaml"
    f.write_text(textwrap.dedent("""
        id: xiaohongshu
        label: 小红书
        output_kind: graphic_text
        output_filename: xiaohongshu.md
        min_chars: 600
        max_chars: 1000
        needs_images: true
        tag_count: [3, 6]
        rewrite_brief: |
          小红书种草体。
    """), encoding="utf-8")
    p = load_profile(f)
    assert isinstance(p, PlatformProfile)
    assert p.id == "xiaohongshu"
    assert p.output_kind == "graphic_text"
    assert p.output_filename == "xiaohongshu.md"
    assert p.needs_images is True
    assert p.tag_count == (3, 6)
    assert "种草体" in p.rewrite_brief

def test_load_profile_defaults(tmp_path: Path):
    f = tmp_path / "min.yaml"
    f.write_text("id: douyin\n", encoding="utf-8")
    p = load_profile(f)
    assert p.label == "douyin"
    assert p.output_filename == "douyin.md"
    assert p.needs_images is False
    assert p.tag_count == (0, 0)
