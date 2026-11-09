"""
Comprehensive test suite for toolkit/converter.py — WeChatConverter.

Covers: container syntax, CJK fixes, list conversion, link-to-footnote,
dark mode injection, AIGC footer, CSS randomization, image processing,
title/digest extraction, and theme integration.
"""

import sys
from pathlib import Path

# Ensure src/ is importable (package layout since v2.2)
SRC_DIR = str(Path(__file__).resolve().parent.parent / "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

import re

import pytest
from bs4 import BeautifulSoup

from wewrite.toolkit.converter import ConvertResult, WeChatConverter, make_paste_safe, preview_html
from wewrite.toolkit.theme import Theme, load_theme


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

THEMES_DIR = str(Path(__file__).resolve().parent.parent / "src" / "wewrite" / "toolkit" / "themes")


@pytest.fixture
def pro_theme():
    """Load the professional-clean theme (basic tests)."""
    return load_theme("professional-clean", themes_dir=THEMES_DIR)


@pytest.fixture
def imp_theme():
    """Load the impeccable theme (AIGC / randomize tests)."""
    return load_theme("impeccable", themes_dir=THEMES_DIR)


@pytest.fixture
def converter(pro_theme):
    return WeChatConverter(theme=pro_theme)


@pytest.fixture
def imp_converter(imp_theme):
    return WeChatConverter(theme=imp_theme)


# ===================================================================
# 1. Container syntax
# ===================================================================

class TestDialogueContainer:
    def test_left_and_right_bubbles(self, converter):
        md = ":::dialogue\n你好\n> 你好呀\n:::"
        result = converter.convert(md)
        soup = BeautifulSoup(result.html, "html.parser")
        sections = soup.find_all("section")
        # At least two bubble wrappers
        assert len(sections) >= 2
        # Right bubble uses primary color background
        right = [s for s in sections if "flex-end" in s.get("style", "")]
        left = [s for s in sections if "flex-start" in s.get("style", "")]
        assert len(right) >= 1
        assert len(left) >= 1

    def test_empty_dialogue(self, converter):
        md = ":::dialogue\n\n:::"
        result = converter.convert(md)
        # Should not crash; no bubbles expected
        assert isinstance(result.html, str)


class TestTimelineContainer:
    def test_timeline_dots(self, converter):
        md = ":::timeline\n第一步\n第二步\n:::"
        result = converter.convert(md)
        soup = BeautifulSoup(result.html, "html.parser")
        # Each timeline item has a dot (border-radius: 50%)
        dots = [s for s in soup.find_all("section") if "border-radius: 50%" in s.get("style", "")]
        assert len(dots) == 2


class TestCalloutContainer:
    @pytest.mark.parametrize("kind,icon", [
        ("tip", "💡"),
        ("warning", "⚠️"),
        ("info", "ℹ️"),
        ("danger", "🚨"),
    ])
    def test_callout_types(self, converter, kind, icon):
        md = f":::callout {kind}\n内容文本\n:::"
        result = converter.convert(md)
        assert icon in result.html
        assert kind.upper() in result.html
        assert "内容文本" in result.html

    def test_unknown_callout_defaults_to_info(self, converter):
        md = ":::callout unknown\n内容\n:::"
        result = converter.convert(md)
        # Falls back to info colors (#2563eb)
        assert "#2563eb" in result.html


class TestQuoteContainer:
    def test_pull_quote_styling(self, converter):
        md = ":::quote\n人生苦短\n:::"
        result = converter.convert(md)
        assert "人生苦短" in result.html
        # Styled pull quote wraps content in quotes
        assert "&quot;" in result.html or '"' in result.html or "\u201c" in result.html


class TestHighlightContainer:
    def test_highlight_box(self, imp_converter):
        md = ":::highlight\n重点标题\n详情内容\n:::"
        result = imp_converter.convert(md)
        assert "重点标题" in result.html
        assert "详情内容" in result.html
        # Uses impeccable secondary color
        assert "#c4820e" in result.html


class TestSummaryContainer:
    def test_summary_box(self, imp_converter):
        md = ":::summary\n总结标题\n总结正文\n:::"
        result = imp_converter.convert(md)
        assert "总结标题" in result.html
        assert "总结正文" in result.html
        # Uses impeccable primary color
        assert "#1a6b5a" in result.html


# ===================================================================
# 2. CJK fixes
# ===================================================================

class TestCJKSpacing:
    def test_cjk_latin_space_inserted(self, converter):
        md = "# Title\n\n中文abc中文"
        result = converter.convert(md)
        plain = BeautifulSoup(result.html, "html.parser").get_text()
        # Space should exist between 中文 and abc, and between abc and 中文
        assert "中文 abc" in plain or "中文 abc" in plain
        assert "abc 中文" in plain or "abc 中文" in plain

    def test_cjk_digit_space(self, converter):
        md = "# T\n\n共有100个"
        result = converter.convert(md)
        plain = BeautifulSoup(result.html, "html.parser").get_text()
        assert "有 100" in plain or "有 100" in plain

    def test_code_block_not_affected(self, converter):
        md = "# T\n\n```\n中文abc\n```"
        result = converter.convert(md)
        # Inside code blocks the text should NOT get extra spacing
        assert "中文abc" in result.html


class TestBoldPunctuationRelocation:
    def test_chinese_punct_moved_outside_strong(self, converter):
        md = "# T\n\n**重点，**"
        result = converter.convert(md)
        # The comma should be AFTER </strong>, not inside
        # Pattern: </strong>，  (not <strong>...，</strong>)
        assert re.search(r"</strong>[，。！？；：、]", result.html)

    def test_no_punct_no_change(self, converter):
        md = "# T\n\n**重点**"
        result = converter.convert(md)
        soup = BeautifulSoup(result.html, "html.parser")
        assert soup.find("strong") is not None


# ===================================================================
# 3. List conversion
# ===================================================================

class TestListConversion:
    def test_ul_becomes_sections_with_bullets(self, converter):
        md = "# T\n\n- 项目一\n- 项目二"
        result = converter.convert(md)
        soup = BeautifulSoup(result.html, "html.parser")
        # No <ul> or <li> should remain
        assert soup.find("ul") is None
        assert soup.find("li") is None
        # Bullet character present
        assert "•" in result.html

    def test_ol_becomes_sections_with_numbers(self, converter):
        md = "# T\n\n1. 第一\n2. 第二\n3. 第三"
        result = converter.convert(md)
        soup = BeautifulSoup(result.html, "html.parser")
        assert soup.find("ol") is None
        assert soup.find("li") is None
        assert "1." in result.html
        assert "2." in result.html
        assert "3." in result.html

    def test_list_uses_theme_primary_color(self, converter, pro_theme):
        md = "# T\n\n- item"
        result = converter.convert(md)
        primary = pro_theme.colors["primary"]
        assert primary in result.html


# ===================================================================
# 4. Link to footnote
# ===================================================================

class TestLinkToFootnote:
    def test_external_link_becomes_footnote(self, converter):
        md = "# T\n\n访问[百度](https://www.baidu.com)"
        result = converter.convert(md)
        # Should have superscript [1]
        assert "[1]" in result.html
        # Reference section at bottom
        assert "参考链接" in result.html
        assert "https://www.baidu.com" in result.html

    def test_multiple_links_numbered_sequentially(self, converter):
        md = "# T\n\n[A](https://a.com) and [B](https://b.com)"
        result = converter.convert(md)
        assert "[1]" in result.html
        assert "[2]" in result.html

    def test_anchor_links_not_converted(self, converter):
        md = "# T\n\n[跳转](#section)"
        result = converter.convert(md)
        assert "参考链接" not in result.html

    def test_no_links_no_reference_section(self, converter):
        md = "# T\n\n纯文本段落"
        result = converter.convert(md)
        assert "参考链接" not in result.html


# ===================================================================
# 5. Dark mode injection
# ===================================================================

class TestDarkModeInjection:
    def test_darkmode_attributes_on_paragraphs(self, converter):
        md = "# T\n\n这是段落"
        result = converter.convert(md)
        soup = BeautifulSoup(result.html, "html.parser")
        p_tags = soup.find_all("p")
        # At least one p should have darkmode attrs
        has_dm = any(p.get("data-darkmode-color") for p in p_tags)
        assert has_dm

    def test_darkmode_on_headings(self, converter):
        md = "# T\n\n## 标题二"
        result = converter.convert(md)
        soup = BeautifulSoup(result.html, "html.parser")
        h2 = soup.find("h2")
        assert h2 is not None
        assert h2.get("data-darkmode-color") is not None

    def test_darkmode_on_strong(self, converter):
        md = "# T\n\n**加粗**"
        result = converter.convert(md)
        soup = BeautifulSoup(result.html, "html.parser")
        strong = soup.find("strong")
        assert strong is not None
        assert strong.get("data-darkmode-color") is not None

    def test_darkmode_on_code_blocks(self, converter):
        md = "# T\n\n```python\nprint('hi')\n```"
        result = converter.convert(md)
        soup = BeautifulSoup(result.html, "html.parser")
        pre = soup.find("pre")
        assert pre is not None
        assert pre.get("data-darkmode-bgcolor") is not None

    def test_darkmode_on_blockquote(self, converter):
        md = "# T\n\n> 引用文本"
        result = converter.convert(md)
        soup = BeautifulSoup(result.html, "html.parser")
        bq = soup.find("blockquote")
        assert bq is not None
        assert bq.get("data-darkmode-bgcolor") is not None

    def test_no_darkmode_when_theme_has_none(self):
        theme = Theme(name="no-dm", description="test", base_css="p { color: red; }", colors={})
        c = WeChatConverter(theme=theme)
        result = c.convert("# T\n\ntext")
        assert "data-darkmode" not in result.html


# ===================================================================
# 6. AIGC footer
# ===================================================================

class TestAIGCFooter:
    def test_impeccable_has_aigc_footer(self, imp_converter):
        result = imp_converter.convert("# T\n\n内容")
        assert "AI 辅助创作" in result.html

    def test_default_theme_has_aigc_footer(self, converter):
        """AIGC footer is appended by default (合规标识)，即使主题没显式开启。"""
        result = converter.convert("# T\n\n内容")
        assert "AI 辅助创作" in result.html

    def test_aigc_footer_can_be_disabled(self, pro_theme):
        """aigc_footer: false 显式关闭脚注。"""
        data = dict(getattr(pro_theme, "_raw_data", {}) or {})
        data["aigc_footer"] = False
        pro_theme._raw_data = data
        result = WeChatConverter(theme=pro_theme).convert("# T\n\n内容")
        assert "AI 辅助创作" not in result.html


# ===================================================================
# 7. Deterministic output (CSS fingerprint perturbation removed)
# ===================================================================

class TestDeterministicOutput:
    def test_impeccable_output_deterministic(self, imp_theme):
        """CSS 防指纹随机扰动已移除——同一输入应产出完全一致的 HTML。"""
        md = "# T\n\n段落文本内容。\n\n## 二级标题\n\n更多段落。"
        outputs = {WeChatConverter(theme=imp_theme).convert(md).html for _ in range(5)}
        assert len(outputs) == 1

    def test_professional_clean_no_randomization(self, pro_theme):
        """professional-clean output is deterministic (no perturbation)."""
        md = "# T\n\n段落文本。\n\n## 二级标题"
        outputs = set()
        for _ in range(5):
            c = WeChatConverter(theme=pro_theme)
            result = c.convert(md)
            outputs.add(result.html)
        assert len(outputs) == 1


# ===================================================================
# 8. Image processing
# ===================================================================

class TestImageProcessing:
    def test_image_responsive_style(self, converter):
        md = "# T\n\n![photo](https://example.com/photo.jpg)"
        result = converter.convert(md)
        assert "max-width: 100%" in result.html
        assert "height: auto" in result.html

    def test_image_extraction(self, converter):
        md = "# T\n\n![a](https://example.com/a.png)\n\n![b](https://example.com/b.png)"
        result = converter.convert(md)
        assert len(result.images) == 2
        assert "https://example.com/a.png" in result.images
        assert "https://example.com/b.png" in result.images

    def test_no_images_empty_list(self, converter):
        result = converter.convert("# T\n\n纯文本")
        assert result.images == []


# ===================================================================
# 9. Title / digest extraction
# ===================================================================

class TestTitleExtraction:
    def test_h1_extracted(self, converter):
        result = converter.convert("# 我的标题\n\n正文")
        assert result.title == "我的标题"

    def test_h1_stripped_from_body(self, converter):
        result = converter.convert("# 标题\n\n正文")
        soup = BeautifulSoup(result.html, "html.parser")
        h1 = soup.find("h1")
        assert h1 is None

    def test_no_h1_empty_title(self, converter):
        result = converter.convert("## 只有二级\n\n正文")
        assert result.title == ""

    def test_h2_not_mistaken_for_h1(self, converter):
        result = converter.convert("## 二级标题\n\n正文")
        assert result.title == ""


class TestDigestGeneration:
    def test_digest_within_120_bytes(self, converter):
        long_text = "# T\n\n" + "这是测试文本。" * 50
        result = converter.convert(long_text)
        encoded = result.digest.encode("utf-8")
        assert len(encoded) <= 120

    def test_short_text_no_ellipsis(self, converter):
        result = converter.convert("# T\n\nHello")
        assert "..." not in result.digest

    def test_long_text_has_ellipsis(self, converter):
        long_text = "# T\n\n" + "长文本内容。" * 30
        result = converter.convert(long_text)
        assert result.digest.endswith("...")


# ===================================================================
# 10. Theme integration
# ===================================================================

class TestThemeIntegration:
    def test_impeccable_serif_font_in_theme(self, imp_theme):
        """Impeccable theme base_css declares serif font-family on body."""
        # The converter skips body for inline styles (WeChat has no body wrapper),
        # so we verify the theme definition itself carries the serif stack.
        assert "serif" in imp_theme.base_css
        assert "Noto Serif SC" in imp_theme.base_css

    def test_impeccable_colors_applied(self, imp_converter):
        """Impeccable theme colors (#3d4249 text, #1a6b5a primary) appear in output."""
        result = imp_converter.convert("# T\n\n段落内容\n\n- 列表项")
        # text color from impeccable
        assert "#3d4249" in result.html
        # primary color on bullet/list
        assert "#1a6b5a" in result.html

    def test_professional_clean_sans_serif(self, converter):
        result = converter.convert("# T\n\n段落内容")
        soup = BeautifulSoup(result.html, "html.parser")
        p = soup.find("p")
        style = p.get("style", "")
        # professional-clean uses system sans-serif stack
        assert "sans-serif" in style or "PingFang" in style or "color" in style

    def test_default_theme_name(self):
        """Constructing without explicit theme loads professional-clean."""
        c = WeChatConverter()
        assert c._theme.name == "professional-clean"

    def test_explicit_theme_object(self, pro_theme):
        c = WeChatConverter(theme=pro_theme)
        assert c._theme.name == "professional-clean"


# ===================================================================
# Misc / integration
# ===================================================================

class TestConvertResult:
    def test_result_fields(self, converter):
        result = converter.convert("# Hello\n\nWorld")
        assert isinstance(result, ConvertResult)
        assert result.title == "Hello"
        assert "World" in result.html
        assert isinstance(result.digest, str)
        assert isinstance(result.images, list)


class TestConvertFile:
    def test_file_not_found(self, converter):
        with pytest.raises(FileNotFoundError):
            converter.convert_file("/nonexistent/path.md")

    def test_convert_file_roundtrip(self, converter, tmp_path):
        md_file = tmp_path / "test.md"
        md_file.write_text("# File Title\n\nFile body content.", encoding="utf-8")
        result = converter.convert_file(str(md_file))
        assert result.title == "File Title"
        assert "File body content" in result.html


class TestPreviewHtml:
    def test_preview_wraps_in_full_document(self, pro_theme):
        body = "<p>Hello</p>"
        full = preview_html(body, pro_theme)
        assert "<!DOCTYPE html>" in full
        assert "<body>" in full
        assert body in full


class TestWeChatFixes:
    def test_all_p_tags_have_explicit_color(self, converter):
        md = "# T\n\nparagraph one\n\nparagraph two"
        result = converter.convert(md)
        soup = BeautifulSoup(result.html, "html.parser")
        for p in soup.find_all("p"):
            assert "color" in p.get("style", "")

    def test_pre_has_whitespace_preservation(self, converter):
        md = "# T\n\n```\ncode\n```"
        result = converter.convert(md)
        soup = BeautifulSoup(result.html, "html.parser")
        pre = soup.find("pre")
        assert pre is not None
        assert "white-space" in pre.get("style", "")


class TestCodeBlockEnhancement:
    def test_data_lang_attribute(self, converter):
        md = "# T\n\n```python\nprint('hi')\n```"
        result = converter.convert(md)
        soup = BeautifulSoup(result.html, "html.parser")
        pre = soup.find("pre")
        # codehilite may or may not produce language- classes depending on config
        # but if it does, data-lang should be set
        if pre and pre.find("code"):
            code = pre.find("code")
            classes = code.get("class", [])
            if any(c.startswith("language-") for c in classes):
                assert pre.get("data-lang") is not None


class TestContainerInlineMarkdown:
    """Inline md inside containers must render (pre-rendered HTML skips the md pass)."""

    def test_timeline_bold_renders(self):
        conv = WeChatConverter(theme=load_theme("professional-clean", THEMES_DIR))
        md = ":::timeline\n**第 1 周** 磨合期\n**第 2 周** 上升期\n:::"
        html = conv.convert(md).html
        assert "**" not in html
        # 后续管线会给 strong 注入 darkmode 属性，只断言标签与内容
        assert "<strong" in html and "第 1 周" in html

    def test_callout_and_quote_inline(self):
        conv = WeChatConverter(theme=load_theme("professional-clean", THEMES_DIR))
        md = ":::callout tip\n用 `wewrite score` 查 **质量**\n:::\n\n:::quote\n*慢* 就是 **快**\n:::"
        html = conv.convert(md).html
        assert "**" not in html and "`" not in html
        assert "<strong" in html and "质量" in html
        assert "<em" in html and "慢" in html and "<code" in html


class TestTypographyR1:
    """排版增强 R1：sanitize / validate / paste-safe / pullquote / GIF 角标 / 章节编号。"""

    def _conv(self):
        return WeChatConverter(theme=load_theme("professional-clean", THEMES_DIR))

    def test_codehilite_div_class_sanitized(self):
        html = self._conv().convert("```python\nx = 1\n```").html
        assert "<div" not in html and "class=" not in html

    def test_converter_output_passes_validator(self):
        from wewrite.commands.validate_html import validate_html
        md = "## 标题\n\n正文 **加粗**。\n\n```js\nlet x=1\n```\n\n![g](a.gif)"
        html = self._conv().convert(md).html
        errors = [i for i in validate_html(html) if i["level"] == "ERROR"]
        assert errors == []

    def test_validator_catches_forbidden(self):
        from wewrite.commands.validate_html import validate_html
        bad = '<div class="x" style="position:absolute"><style>a{}</style></div>'
        rules = {i["rule"] for i in validate_html(bad)}
        assert {"div_tag", "class_attr", "position_unsupported", "style_tag"} <= rules

    def test_paste_safe_wraps_text_and_pads_empty(self):
        html = ('<section><p>你好</p>'
                '<section style="width:36px;height:2px;background:#000"></section>'
                '<pre><code>x = 1</code></pre></section>')
        out = make_paste_safe(html)
        assert '<span leaf="">你好</span>' in out
        assert 'background:#000"><span leaf=""><br/></span></section>' in out.replace("'", '"')
        assert "<code><span" not in out  # 代码区不包

    def test_pullquote_renders_centered(self):
        html = self._conv().convert(":::pullquote\n慢就是 **快**\n:::").html
        assert "text-align: center" in html and "慢就是" in html and "<strong" in html
        assert ":::" not in html

    def test_gif_badge(self):
        html = self._conv().convert("![动图](demo.gif)\n\n![静图](p.png)").html
        assert html.count(">GIF</span>") == 1

    def test_section_numbering_theme_flag(self):
        theme = load_theme("professional-clean", THEMES_DIR)
        theme._raw_data = dict(theme._raw_data, section_numbering=True)
        html = WeChatConverter(theme=theme).convert("## 一\n\nx\n\n## 二\n\ny").html
        assert ">01</span>" in html and ">02</span>" in html
        html_off = self._conv().convert("## 一\n\nx").html
        assert ">01</span>" not in html_off


class TestTypographyR2:
    """排版增强 R2：:::label 小标签标题、:::steps 步骤卡。"""

    def _conv(self):
        return WeChatConverter(theme=load_theme("professional-clean", THEMES_DIR))

    def test_label_bar_default(self):
        html = self._conv().convert(":::label\n工具清单\n:::").html
        assert "工具清单" in html and ":::" not in html
        assert "width: 4px" in html  # 左竖条
        assert '<span leaf=""><br/></span>' in html.replace("<br>", "<br/>")  # 占位

    def test_label_pill_variant(self):
        html = self._conv().convert(":::label pill\n步骤一\n:::").html
        assert "border-radius: 999px" in html and "步骤一" in html

    def test_steps_numbered(self):
        md = ":::steps\n安装依赖\n**配置** config.yaml\n推送草稿箱\n:::"
        html = self._conv().convert(md).html
        assert ">1</section>" in html and ">2</section>" in html and ">3</section>" in html
        assert "<strong" in html and "配置" in html and "推送草稿箱" in html
        assert "line-height: 22px" in html  # 圆点不用 flex 居中

    def test_r2_passes_validator(self):
        from wewrite.commands.validate_html import validate_html
        md = ":::label pill\nA\n:::\n\n:::steps\n一\n二\n:::"
        html = self._conv().convert(md).html
        assert [i for i in validate_html(html) if i["level"] == "ERROR"] == []

# ===================================================================
# 10. 回归测试 [local fix 2026-09-28]：CJK 空格化污染图片路径 / 摘要取到图注
#     两个缺陷在上游 4.2.1 均存在
# ===================================================================

class TestCJKSpacingPathProtection:
    def test_image_path_kept_intact(self, converter):
        md = "# T\n\n![\u6210\u54c1\u9875\u7b2c1\u95ee](assets/05-\u6210\u54c1\u9875-\u7b2c1\u95ee.png)\n\n\u6b63\u6587\u4e2d\u6587abc"
        html = converter.convert(md).html
        assert "assets/05-\u6210\u54c1\u9875-\u7b2c1\u95ee.png" in html
        assert "assets/05-\u6210\u54c1\u9875-\u7b2c 1 \u95ee.png" not in html

    def test_link_target_kept_intact(self, converter):
        md = "# T\n\n[\u6587\u6863](https://example.com/a1b/\u7b2c1\u7ae0.md)\n\n\u6b63\u6587"
        html = converter.convert(md).html
        assert "example.com/a1b/\u7b2c1\u7ae0.md" in html

    def test_inline_code_kept_intact(self, converter):
        md = "# T\n\n\u8def\u5f84\u662f `assets/05-\u7b2c1\u95ee.png`\u3002\n\n\u4e2d\u6587abc"
        html = converter.convert(md).html
        assert "assets/05-\u7b2c1\u95ee.png" in html

    def test_visible_text_still_spaced(self, converter):
        md = "# T\n\n\u4e2d\u6587abc\u4e2d\u6587\uff0c\u5171100\u4e2a"
        plain = BeautifulSoup(converter.convert(md).html, "html.parser").get_text()
        assert "\u4e2d\u6587 abc" in plain
        assert "\u5171 100" in plain


class TestDigestSkipsCaptions:
    def test_digest_skips_figure_caption(self, converter):
        md = ("# T\n\n![]\u56fe(a.png)\n\n"
              "**\u56fe\u6ce8\uff1a\u8fd9\u662f\u56fe\u6ce8\uff0c\u4e0d\u8be5\u8fdb\u6458\u8981\u3002**\n\n"
              "\u8fd9\u662f\u6b63\u6587\u7b2c\u4e00\u6bb5\uff0c\u5e94\u8be5\u88ab\u9009\u4e3a\u6458\u8981\u5185\u5bb9\uff0c\u5b83\u8db3\u591f\u957f\u4ee5\u901a\u8fc7\u8fc7\u6ee4\u6761\u4ef6\u3002\n")
        digest = converter.convert(md).digest
        assert digest.startswith("\u8fd9\u662f\u6b63\u6587\u7b2c\u4e00\u6bb5")
        assert "\u56fe\u6ce8" not in digest

    def test_digest_within_limit_with_leading_caption(self, converter):
        md = "# T\n\n**\u56fe\u6ce8\uff1a\u77ed\u56fe\u6ce8**\n\n" + "\u6b63\u6587\u5185\u5bb9\u3002" * 60
        d = converter.convert(md).digest
        assert len(d.encode("utf-8")) <= 120
        assert "\u56fe\u6ce8" not in d


class TestPublishImagePathRepair:
    def test_despace_path(self):
        from wewrite.toolkit.cli import _despace_path
        assert _despace_path("05-\u6210\u54c1\u9875-\u7b2c 1 \u95ee.png") == "05-\u6210\u54c1\u9875-\u7b2c1\u95ee.png"
        assert _despace_path("img 05 \u56fe.png") == "img 05\u56fe.png"
        assert _despace_path("img-01-cover.png") == "img-01-cover.png"

    def test_repair_image_path(self, tmp_path):
        from wewrite.toolkit.cli import _repair_image_path
        real = tmp_path / "05-\u6210\u54c1\u9875-\u7b2c1\u95ee.png"
        real.write_bytes(b"x")
        broken = tmp_path / "05-\u6210\u54c1\u9875-\u7b2c 1 \u95ee.png"
        assert _repair_image_path(broken, tmp_path) == real
        assert _repair_image_path(tmp_path / "nope.png", tmp_path) is None
