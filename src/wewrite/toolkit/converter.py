"""
Markdown to WeChat-compatible HTML converter.

Forked from wechat_article_skills/scripts/markdown_to_html.py,
adapted for YAML-driven themes and agent integration.
"""

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import markdown
from bs4 import BeautifulSoup

from .theme import Theme, load_theme, get_inline_css_rules


@dataclass
class ConvertResult:
    """Result of a Markdown → WeChat HTML conversion."""

    html: str  # WeChat-compatible inline-style HTML (body content only)
    title: str  # Extracted H1 title
    digest: str  # Auto-generated summary (first 120 chars)
    images: list[str] = field(default_factory=list)  # Image references found


class WeChatConverter:
    """Convert Markdown to WeChat-compatible inline-style HTML."""

    def __init__(self, theme: Optional[Theme] = None, theme_name: str = "professional-clean"):
        if theme is not None:
            self._theme = theme
        else:
            self._theme = load_theme(theme_name)
        self._css_rules = get_inline_css_rules(self._theme)

    def convert(self, markdown_text: str) -> ConvertResult:
        """
        Convert Markdown text to WeChat-compatible HTML.

        Returns ConvertResult with:
          - html: inline-style HTML (body content only, no <html>/<head> wrapper)
          - title: extracted H1 title (or empty string)
          - digest: first 120 characters of plain text
          - images: list of image src references
        """
        title = self._extract_title(markdown_text)
        markdown_text = self._strip_h1(markdown_text)

        # Pre-process container blocks (:::dialogue, :::timeline, etc.)
        markdown_text = self._preprocess_containers(markdown_text)

        # CJK fix: auto-space between CJK and Latin characters
        markdown_text = self._fix_cjk_spacing(markdown_text)

        # Parse Markdown → HTML
        html = self._markdown_to_html(markdown_text)

        # Enhance code blocks (add data-lang attribute)
        html = self._enhance_code_blocks(html)

        # H2 章节编号（主题 section_numbering: true 时启用）
        html = self._number_sections(html)

        # Process images (ensure responsive styling)
        html, images = self._process_images(html)

        # CJK fix: move punctuation outside bold tags
        html = self._fix_cjk_bold_punctuation(html)

        # CJK fix: convert ul/ol to section-based lists (WeChat renders native lists unreliably)
        html = self._convert_lists_to_sections(html)

        # Convert external links to footnotes (WeChat blocks external links)
        html = self._convert_links_to_footnotes(html)

        # Apply inline CSS from theme
        html = self._apply_inline_styles(html)

        # Apply WeChat compatibility fixes
        html = self._apply_wechat_fixes(html)

        # 净化不兼容标签/属性（codehilite 等库会残留 div/class）
        html = self._sanitize_for_wechat(html)

        # Inject dark mode attributes
        html = self._inject_darkmode(html)

        # Append AIGC declaration footer by default（合规：AI 生成/辅助内容需标识；
        # 主题或配置显式设 aigc_footer: false 才关闭）。
        raw = getattr(self._theme, '_raw_data', {}) or {}
        aigc = raw.get('aigc_footer', self._theme.colors.get('aigc_footer', True))
        if aigc:
            html = self._append_aigc_footer(html)

        # Generate digest from plain text
        digest = self._generate_digest(html)

        return ConvertResult(html=html, title=title, digest=digest, images=images)

    def convert_file(self, input_path: str) -> ConvertResult:
        """Convert a Markdown file."""
        path = Path(input_path)
        if not path.exists():
            raise FileNotFoundError(f"Input file not found: {input_path}")

        text = path.read_text(encoding="utf-8")
        return self.convert(text)

    # -- internal methods --

    def _extract_title(self, text: str) -> str:
        """Extract the first H1 title from Markdown text."""
        for line in text.split("\n"):
            stripped = line.strip()
            if stripped.startswith("# ") and not stripped.startswith("## "):
                return stripped[2:].strip()
        return ""

    def _strip_h1(self, text: str) -> str:
        """Remove H1 lines — WeChat has a separate title field."""
        lines = []
        for line in text.split("\n"):
            stripped = line.strip()
            if stripped.startswith("# ") and not stripped.startswith("## "):
                continue
            lines.append(line)
        return "\n".join(lines)

    def _markdown_to_html(self, text: str) -> str:
        """Parse Markdown to HTML using python-markdown with extensions."""
        extensions = [
            "markdown.extensions.fenced_code",
            "markdown.extensions.tables",
            "markdown.extensions.nl2br",
            "markdown.extensions.sane_lists",
            "markdown.extensions.codehilite",
        ]
        extension_configs = {
            "codehilite": {
                "linenums": False,
                "guess_lang": True,
                "noclasses": True,  # Inline syntax highlight styles
            }
        }
        md = markdown.Markdown(extensions=extensions, extension_configs=extension_configs)
        return md.convert(text)

    def _enhance_code_blocks(self, html: str) -> str:
        """Add data-lang attribute to <pre> elements for language labeling."""
        soup = BeautifulSoup(html, "html.parser")
        for pre in soup.find_all("pre"):
            code = pre.find("code")
            if code:
                for cls in code.get("class", []):
                    if cls.startswith("language-"):
                        pre["data-lang"] = cls.replace("language-", "")
                        break
        return str(soup)

    def _process_images(self, html: str) -> tuple[str, list[str]]:
        """Extract image references and ensure responsive styling."""
        soup = BeautifulSoup(html, "html.parser")
        images = []
        for img in soup.find_all("img"):
            src = img.get("src", "")
            if src:
                images.append(src)
            # GIF 角标：动图上方右对齐小标签（不用 absolute 定位——微信不支持）
            is_gif = src.lower().split("?")[0].endswith(".gif")
            if is_gif:
                badge = soup.new_tag("section")
                badge["style"] = "display: flex; justify-content: flex-end; margin: 24px 0 4px"
                tag = soup.new_tag("span")
                tag["style"] = ("background: rgba(0,0,0,0.55); color: #ffffff; font-size: 11px; "
                                "padding: 2px 8px; border-radius: 4px; letter-spacing: 1px")
                tag.string = "GIF"
                badge.append(tag)
                img.insert_before(badge)
            # Ensure responsive image styles
            existing = img.get("style", "")
            if "max-width" not in existing:
                margin = "margin: 4px auto 24px" if is_gif else "margin: 24px auto"
                additions = f"max-width: 100%; height: auto; display: block; {margin}"
                img["style"] = f"{existing}; {additions}" if existing else additions
        return str(soup), images

    def _apply_inline_styles(self, html: str) -> str:
        """Apply theme CSS rules as inline styles on matching elements."""
        soup = BeautifulSoup(html, "html.parser")

        for selector, styles in self._css_rules.items():
            # Skip body — we don't wrap in body tag
            if selector.strip() == "body":
                continue

            try:
                elements = soup.select(selector)
            except Exception:
                continue

            for elem in elements:
                existing = elem.get("style", "")
                style_dict = {}

                # Parse existing inline styles
                if existing:
                    for item in existing.split(";"):
                        if ":" in item:
                            key, val = item.split(":", 1)
                            style_dict[key.strip()] = val.strip()

                # Add theme styles (existing styles take precedence)
                for prop, val in styles.items():
                    if prop not in style_dict:
                        style_dict[prop] = val

                elem["style"] = "; ".join(f"{k}: {v}" for k, v in style_dict.items())

        return str(soup)

    def _apply_wechat_fixes(self, html: str) -> str:
        """
        Apply WeChat-specific compatibility fixes:
        1. Force explicit color on every <p> tag
        2. Ensure code blocks preserve whitespace
        """
        soup = BeautifulSoup(html, "html.parser")
        text_color = self._theme.colors.get("text", "#333333")

        # Fix 1: Ensure all <p> tags have explicit color
        for p in soup.find_all("p"):
            style = p.get("style", "")
            if "color" not in style:
                p["style"] = f"{style}; color: {text_color}" if style else f"color: {text_color}"

        # Fix 2: Ensure <pre> has whitespace preservation
        for pre in soup.find_all("pre"):
            style = pre.get("style", "")
            if "white-space" not in style:
                pre["style"] = f"{style}; white-space: pre-wrap; word-wrap: break-word" if style else "white-space: pre-wrap; word-wrap: break-word"

        return str(soup)

    # -- CJK compatibility fixes --

    def _fix_cjk_spacing(self, text: str) -> str:
        """Auto-insert a space between CJK and Latin/digit characters.

        WeChat renders CJK-Latin without spacing, making mixed text hard to read.
        This inserts a space at CJK<->Latin boundaries.

        [local fix 2026-09-28] 只处理可见正文：Markdown 链接/图片目标、行内代码、
        裸 URL 和 HTML 属性值先被占位保护（逐行处理，围栏代码块整块跳过）。
        旧实现会把图片路径 `05-第1问.png` 改成 `05-第 1 问.png`，导致发布阶段
        静默找不到图。
        """
        cjk = r'[\u4e00-\u9fff\u3400-\u4dbf\u3000-\u303f\uff00-\uffef]'
        latin = r'[A-Za-z0-9]'

        out = []
        in_code_block = False
        for line in text.split("\n"):
            if line.strip().startswith("```"):
                in_code_block = not in_code_block
                out.append(line)
                continue
            if in_code_block:
                out.append(line)
                continue

            stash = []

            def _stash(m):
                stash.append(m.group(0))
                return "\x00%d\x00" % (len(stash) - 1)

            line = re.sub(r"`[^`\n]*`", _stash, line)          # 行内代码
            line = re.sub(r"\]\([^)\n]*\)", _stash, line)       # 链接/图片目标
            line = re.sub(r"<https?://[^>\s]+>", _stash, line)  # 自动链接
            line = re.sub(r"https?://[^\s)\]]+", _stash, line)  # 裸 URL
            line = re.sub(r'(?<==)"[^"\n]*"', _stash, line)     # HTML 属性值

            line = re.sub("(%s)(%s)" % (cjk, latin), r"\1 \2", line)
            line = re.sub("(%s)(%s)" % (latin, cjk), r"\1 \2", line)

            def _restore(m):
                i = int(m.group(1))
                return stash[i] if 0 <= i < len(stash) else m.group(0)

            line = re.sub(r"\x00(\d+)\x00", _restore, line)
            out.append(line)

        return "\n".join(out)

    def _fix_cjk_bold_punctuation(self, html: str) -> str:
        """Move Chinese punctuation outside bold/strong tags.

        WeChat renders bold CJK punctuation with ugly spacing.
        Move trailing punctuation (，。！？；：、) outside </strong>.
        """
        # Match: <strong>内容+中文标点</strong> → <strong>内容</strong>标点
        pattern = r'(<strong>)(.*?)([，。！？；：、]+)(</strong>)'
        return re.sub(pattern, r'\1\2\4\3', html)

    def _convert_lists_to_sections(self, html: str) -> str:
        """Convert <ul>/<ol> to styled <section> elements.

        WeChat's native list rendering is unreliable (inconsistent bullet
        style, broken indentation on some devices). Using section+span
        for bullets/numbers gives full control over appearance.
        """
        soup = BeautifulSoup(html, "html.parser")
        text_color = self._theme.colors.get("text", "#333333")
        primary = self._theme.colors.get("primary", "#2563eb")

        for ul in soup.find_all("ul"):
            section = soup.new_tag("section")
            for li in ul.find_all("li", recursive=False):
                item = soup.new_tag("section", style=f"display: flex; align-items: flex-start; margin-bottom: 8px; color: {text_color}")
                bullet = soup.new_tag("span", style=f"color: {primary}; margin-right: 8px; flex-shrink: 0; font-size: 18px; line-height: 1.6")
                bullet.string = "•"
                content = soup.new_tag("span", style="flex: 1")
                for child in list(li.children):
                    content.append(child.extract() if hasattr(child, 'extract') else child)
                item.append(bullet)
                item.append(content)
                section.append(item)
            ul.replace_with(section)

        for idx, ol in enumerate(soup.find_all("ol")):
            section = soup.new_tag("section")
            for num, li in enumerate(ol.find_all("li", recursive=False), 1):
                item = soup.new_tag("section", style=f"display: flex; align-items: flex-start; margin-bottom: 8px; color: {text_color}")
                number = soup.new_tag("span", style=f"color: {primary}; margin-right: 8px; flex-shrink: 0; font-weight: 700; line-height: 1.8")
                number.string = f"{num}."
                content = soup.new_tag("span", style="flex: 1")
                for child in list(li.children):
                    content.append(child.extract() if hasattr(child, 'extract') else child)
                item.append(number)
                item.append(content)
                section.append(item)
            ol.replace_with(section)

        return str(soup)

    # -- External link → footnote conversion --

    def _convert_links_to_footnotes(self, html: str) -> str:
        """Convert external <a> links to superscript footnote numbers.

        WeChat blocks external links — readers see dead text. This converts
        each external link to a superscript number with the URL collected
        into a reference list appended at the end.
        """
        soup = BeautifulSoup(html, "html.parser")
        footnotes = []
        counter = 0
        primary = self._theme.colors.get("primary", "#2563eb")

        for a in soup.find_all("a"):
            href = a.get("href", "")
            if not href or href.startswith("#"):
                continue  # skip anchors

            counter += 1
            text = a.get_text()
            footnotes.append((counter, text, href))

            # Replace <a> with text + superscript number
            sup = soup.new_tag("sup")
            sup_link = soup.new_tag("span", style=f"color: {primary}; font-size: 12px")
            sup_link.string = f"[{counter}]"
            sup.append(sup_link)
            a.replace_with(text, sup)

        if footnotes:
            # Append reference section
            hr = soup.new_tag("hr", style="border: none; border-top: 1px solid #e5e5e5; margin: 32px 0 16px")
            soup.append(hr)
            ref_title = soup.new_tag("p", style="font-size: 13px; color: #999999; margin-bottom: 8px; font-weight: 700")
            ref_title.string = "参考链接"
            soup.append(ref_title)
            for num, text, href in footnotes:
                ref = soup.new_tag("p", style="font-size: 12px; color: #999999; margin: 2px 0; word-break: break-all")
                ref.string = f"[{num}] {text}: {href}"
                soup.append(ref)

        return str(soup)

    # -- Dark mode --

    def _inject_darkmode(self, html: str) -> str:
        """Inject data-darkmode-* attributes for WeChat dark mode.

        WeChat auto-inverts colors in dark mode, which often breaks
        designed color schemes. Explicit darkmode attributes tell WeChat
        exactly what colors to use instead of guessing.
        """
        darkmode = self._theme.colors.get("darkmode", {})
        if not darkmode:
            return html

        soup = BeautifulSoup(html, "html.parser")
        dm_text = darkmode.get("text", "#c8c8c8")
        dm_bg = darkmode.get("background", "#1e1e1e")
        dm_primary = darkmode.get("primary", "#6aadff")

        # Body-level elements (p, li, section, span)
        for tag_name in ("p", "span", "section"):
            for elem in soup.find_all(tag_name):
                style = elem.get("style", "")
                # Only set if element has a color
                if "color" in style:
                    elem["data-darkmode-color"] = dm_text
                    elem["data-darkmode-bgcolor"] = "transparent"

        # Headings
        dm_heading = darkmode.get("text", "#e0e0e0")
        for tag_name in ("h1", "h2", "h3", "h4"):
            for elem in soup.find_all(tag_name):
                elem["data-darkmode-color"] = dm_heading
                elem["data-darkmode-bgcolor"] = "transparent"

        # Code blocks
        dm_code_bg = darkmode.get("code_bg", "#2d2d2d")
        dm_code_color = darkmode.get("code_color", "#d4d4d4")
        for pre in soup.find_all("pre"):
            pre["data-darkmode-bgcolor"] = dm_code_bg
            pre["data-darkmode-color"] = dm_code_color
        for code in soup.find_all("code"):
            code["data-darkmode-color"] = dm_code_color

        # Blockquotes
        dm_quote_bg = darkmode.get("quote_bg", "#2a2a2a")
        for bq in soup.find_all("blockquote"):
            bq["data-darkmode-bgcolor"] = dm_quote_bg
            bq["data-darkmode-color"] = dm_text

        # Strong/em with primary color
        for strong in soup.find_all("strong"):
            strong["data-darkmode-color"] = dm_primary

        return str(soup)

    def _sanitize_for_wechat(self, html: str) -> str:
        """微信会改写 <div>、剥离 class/id —— 统一转 section 并清属性。

        主要来源：markdown 库的 codehilite 包装（noclasses 只内联高亮色，
        外层仍是 <div class="codehilite">）、fenced_code 的 language-* class。
        """
        soup = BeautifulSoup(html, "html.parser")
        for div in soup.find_all("div"):
            div.name = "section"
        for el in soup.find_all(attrs={"class": True}):
            del el["class"]
        for el in soup.find_all(attrs={"id": True}):
            del el["id"]
        return str(soup)

    # -- Container block syntax --

    _INLINE_CODE_RE = re.compile(r"`([^`\n]+?)`")
    _INLINE_BOLD_RE = re.compile(r"\*\*(.+?)\*\*")
    _INLINE_EM_RE = re.compile(r"(?<!\*)\*([^*\n]+?)\*(?!\*)")

    def _inline_md(self, text: str) -> str:
        """Render inline Markdown (code/bold/em) inside container content.

        Containers are pre-rendered to raw HTML before the Markdown pass, and
        python-markdown skips inline syntax inside HTML blocks — so `**bold**`
        etc. would otherwise appear literally in the output.
        """
        text = self._INLINE_CODE_RE.sub(
            r'<code style="background: rgba(0,0,0,0.06); padding: 2px 5px; '
            r'border-radius: 3px; font-size: 0.9em">\1</code>', text)
        text = self._INLINE_BOLD_RE.sub(r"<strong>\1</strong>", text)
        text = self._INLINE_EM_RE.sub(r"<em>\1</em>", text)
        return text

    def _preprocess_containers(self, text: str) -> str:
        """Pre-process :::container blocks into styled HTML before Markdown parsing.

        Supports:
          :::dialogue   — chat bubble layout
          :::timeline   — vertical timeline with dots
          :::callout    — Obsidian-style callout (tip/warning/info/danger)
          :::quote      — styled pull quote
        """
        text = self._process_dialogue(text)
        text = self._process_timeline(text)
        text = self._process_callout(text)
        text = self._process_quote_block(text)
        text = self._process_pullquote(text)
        text = self._process_label(text)
        text = self._process_steps(text)
        text = self._process_highlight(text)
        text = self._process_summary(text)
        return text

    def _process_dialogue(self, text: str) -> str:
        """Convert :::dialogue blocks to chat bubble HTML."""
        primary = self._theme.colors.get("primary", "#2563eb")

        def replace_dialogue(match):
            content = match.group(1).strip()
            bubbles = []
            for line in content.split('\n'):
                line = line.strip()
                if not line:
                    continue
                if line.startswith('> '):
                    # Right-aligned (reply) bubble
                    msg = line[2:].strip()
                    bubbles.append(f'<section style="display: flex; justify-content: flex-end; margin-bottom: 12px">'
                                   f'<section style="background: {primary}; color: white; padding: 10px 14px; border-radius: 12px 12px 2px 12px; max-width: 80%; font-size: 15px; line-height: 1.6">{self._inline_md(msg)}</section></section>')
                else:
                    # Left-aligned bubble
                    bubbles.append(f'<section style="display: flex; justify-content: flex-start; margin-bottom: 12px">'
                                   f'<section style="background: #f3f4f6; color: #333; padding: 10px 14px; border-radius: 12px 12px 12px 2px; max-width: 80%; font-size: 15px; line-height: 1.6">{self._inline_md(line)}</section></section>')
            return '\n'.join(bubbles)

        return re.sub(r':::dialogue\n(.*?)\n:::', replace_dialogue, text, flags=re.DOTALL)

    def _process_timeline(self, text: str) -> str:
        """Convert :::timeline blocks to vertical timeline HTML."""
        primary = self._theme.colors.get("primary", "#2563eb")

        def replace_timeline(match):
            content = match.group(1).strip()
            items = []
            for line in content.split('\n'):
                line = line.strip()
                if not line:
                    continue
                # Format: "**title** description" or just "description"
                items.append(
                    f'<section style="display: flex; margin-bottom: 16px">'
                    f'<section style="flex-shrink: 0; width: 12px; display: flex; flex-direction: column; align-items: center">'
                    f'<section style="width: 10px; height: 10px; border-radius: 50%; background: {primary}; margin-top: 6px"></section>'
                    f'<section style="width: 2px; flex: 1; background: #e5e7eb; margin-top: 4px"></section>'
                    f'</section>'
                    f'<section style="flex: 1; padding-left: 12px; padding-bottom: 8px; font-size: 15px; line-height: 1.7">{self._inline_md(line)}</section>'
                    f'</section>'
                )
            return '\n'.join(items)

        return re.sub(r':::timeline\n(.*?)\n:::', replace_timeline, text, flags=re.DOTALL)

    def _process_callout(self, text: str) -> str:
        """Convert :::callout blocks to styled callout boxes.

        Syntax: :::callout tip/warning/info/danger
        """
        colors_map = {
            "tip": ("#059669", "#ecfdf5", "💡"),
            "warning": ("#d97706", "#fffbeb", "⚠️"),
            "info": ("#2563eb", "#eff6ff", "ℹ️"),
            "danger": ("#dc2626", "#fef2f2", "🚨"),
        }

        def replace_callout(match):
            ctype = match.group(1).strip().lower()
            content = match.group(2).strip()
            color, bg, icon = colors_map.get(ctype, colors_map["info"])
            return (f'<section style="background: {bg}; border-left: 4px solid {color}; '
                    f'padding: 14px 16px; border-radius: 4px; margin: 16px 0; font-size: 15px; line-height: 1.7">'
                    f'<section style="font-weight: 700; color: {color}; margin-bottom: 6px">{icon} {ctype.upper()}</section>'
                    f'{self._inline_md(content)}</section>')

        return re.sub(r':::callout\s+(\w+)\n(.*?)\n:::', replace_callout, text, flags=re.DOTALL)

    def _process_quote_block(self, text: str) -> str:
        """Convert :::quote blocks to styled pull quotes."""
        primary = self._theme.colors.get("primary", "#2563eb")

        def replace_quote(match):
            content = match.group(1).strip()
            return (f'<section style="margin: 24px 0; padding: 20px 24px; border-left: 4px solid {primary}; '
                    f'background: linear-gradient(135deg, #f8f9fa 0%, #ffffff 100%); border-radius: 0 8px 8px 0">'
                    f'<section style="font-size: 18px; line-height: 1.8; color: #333; font-style: italic">'
                    f'"{self._inline_md(content)}"</section></section>')

        return re.sub(r':::quote\n(.*?)\n:::', replace_quote, text, flags=re.DOTALL)

    def _process_pullquote(self, text: str) -> str:
        """Convert :::pullquote blocks to centered stand-alone pull quotes（金句居中）."""
        primary = self._theme.colors.get("primary", "#2563eb")

        def replace_pullquote(match):
            content = self._inline_md(match.group(1).strip().replace('\n', '<br>'))
            return (
                f'<section style="margin: 36px 0; padding: 0 24px; text-align: center">'
                f'<section style="font-size: 30px; line-height: 1; color: {primary}; font-weight: 700; margin-bottom: 10px">“</section>'
                f'<section style="font-size: 18px; font-weight: 600; line-height: 1.9; color: #333333">{content}</section>'
                # 装饰短横内置占位，防止微信剥空元素样式
                f'<section style="width: 36px; height: 2px; background: {primary}; margin: 16px auto 0"><span leaf=""><br></span></section>'
                f'</section>')

        return re.sub(r':::pullquote\n(.*?)\n:::', replace_pullquote, text, flags=re.DOTALL)

    def _process_label(self, text: str) -> str:
        """Convert :::label blocks to mini section labels（小标签标题）.

        语法：:::label\n文字\n:::（左竖条式，默认）
              :::label pill\n文字\n:::（实色药丸式）
        """
        primary = self._theme.colors.get("primary", "#2563eb")

        def replace_label(match):
            variant = (match.group(1) or "").strip().lower()
            content = self._inline_md(match.group(2).strip())
            if variant == "pill":
                return (
                    f'<section style="margin: 28px 0 14px">'
                    f'<span style="display: inline-block; background: {primary}; color: #ffffff; '
                    f'font-size: 13px; font-weight: 700; padding: 4px 14px; border-radius: 999px; '
                    f'letter-spacing: 1px">{content}</span></section>')
            return (
                f'<section style="display: flex; align-items: center; margin: 28px 0 14px">'
                # 竖条装饰内置占位，防微信剥空元素样式
                f'<section style="flex-shrink: 0; width: 4px; height: 16px; background: {primary}; '
                f'border-radius: 2px; margin-right: 8px"><span leaf=""><br></span></section>'
                f'<section style="font-size: 16px; font-weight: 700; color: #1a1a1a">{content}</section>'
                f'</section>')

        return re.sub(r':::label[ \t]*(\w*)\n(.*?)\n:::', replace_label, text, flags=re.DOTALL)

    def _process_steps(self, text: str) -> str:
        """Convert :::steps blocks to numbered step cards（步骤卡）.

        每行一个步骤，支持行内 Markdown（如 **标题** 描述）。
        编号圆点用 line-height 垂直居中——微信对 flex 居中支持有限。
        """
        primary = self._theme.colors.get("primary", "#2563eb")

        def replace_steps(match):
            items = []
            n = 0
            for line in match.group(1).strip().split('\n'):
                line = line.strip().lstrip('-').strip()
                if not line:
                    continue
                n += 1
                items.append(
                    f'<section style="display: flex; margin-bottom: 14px">'
                    f'<section style="flex-shrink: 0; width: 22px; height: 22px; border-radius: 50%; '
                    f'background: {primary}; color: #ffffff; font-size: 13px; font-weight: 700; '
                    f'text-align: center; line-height: 22px; margin-right: 10px">{n}</section>'
                    f'<section style="flex: 1; font-size: 15px; line-height: 1.7; padding-top: 1px">'
                    f'{self._inline_md(line)}</section>'
                    f'</section>')
            return '<section style="margin: 20px 0">' + '\n'.join(items) + '</section>'

        return re.sub(r':::steps\n(.*?)\n:::', replace_steps, text, flags=re.DOTALL)

    def _number_sections(self, html: str) -> str:
        """给 H2 加两位数章节编号（01/02/…）。主题 YAML 顶层 section_numbering: true 启用。"""
        raw = getattr(self._theme, '_raw_data', {}) or {}
        if not raw.get('section_numbering'):
            return html
        primary = self._theme.colors.get("primary", "#2563eb")
        soup = BeautifulSoup(html, "html.parser")
        for i, h2 in enumerate(soup.find_all("h2"), 1):
            num = soup.new_tag("span")
            num["style"] = f"color: {primary}; font-weight: 800; margin-right: 10px; letter-spacing: 1px"
            num.string = f"{i:02d}"
            h2.insert(0, num)
        return str(soup)

    # -- AIGC footer --

    def _append_aigc_footer(self, html: str) -> str:
        """Append AIGC declaration footer as required by WeChat platform rules."""
        footer = ('<p style="text-align: center; font-size: 13px; color: #9ca3af; '
                  'margin-top: 48px; padding-top: 24px; border-top: 1px solid #e5e7eb;">'
                  '本文由 AI 辅助创作，作者进行了实测验证和编辑修改。</p>')
        return html + '\n' + footer

    def _process_highlight(self, text: str) -> str:
        """Convert :::highlight blocks to amber highlight info boxes (Impeccable style)."""
        secondary = self._theme.colors.get("secondary", "#c4820e")
        highlight_bg = self._theme.colors.get("highlight_bg", "#fef7e8")
        highlight_border = self._theme.colors.get("highlight_border", "rgba(196,130,14,0.2)")

        def replace_highlight(match):
            content = match.group(1).strip()
            lines = content.split('\n', 1)
            title = lines[0].strip() if lines else ""
            body = lines[1].strip() if len(lines) > 1 else ""
            html = (f'<section style="margin: 24px 0; padding: 20px 24px; background: {highlight_bg}; '
                    f'border: 1px solid {highlight_border}; border-radius: 6px;">')
            if title:
                html += f'<p style="margin: 0;"><strong style="color: {secondary};">{self._inline_md(title)}</strong></p>'
            if body:
                html += f'<p style="margin: 8px 0 0 0;">{self._inline_md(body)}</p>'
            html += '</section>'
            return html

        return re.sub(r':::highlight\n(.*?)\n:::', replace_highlight, text, flags=re.DOTALL)

    def _process_summary(self, text: str) -> str:
        """Convert :::summary blocks to teal summary boxes (Impeccable style)."""
        primary = self._theme.colors.get("primary", "#1a6b5a")
        summary_bg = self._theme.colors.get("summary_bg", "#e8f5f0")
        summary_border = self._theme.colors.get("summary_border", "rgba(26,107,90,0.15)")

        def replace_summary(match):
            content = match.group(1).strip()
            lines = content.split('\n', 1)
            title = lines[0].strip() if lines else "总结"
            body = lines[1].strip() if len(lines) > 1 else ""
            html = (f'<section style="margin: 24px 0; padding: 20px 24px; background: {summary_bg}; '
                    f'border: 1px solid {summary_border}; border-radius: 6px;">')
            html += f'<p style="margin: 0;"><strong style="color: {primary};">{self._inline_md(title)}</strong></p>'
            if body:
                html += f'<p style="margin: 8px 0 0 0;">{self._inline_md(body)}</p>'
            html += '</section>'
            return html

        return re.sub(r':::summary\n(.*?)\n:::', replace_summary, text, flags=re.DOTALL)

    # -- Digest generation --

    def _generate_digest(self, html: str, max_bytes: int = 120) -> str:
        """Generate a digest that fits within WeChat's byte limit (120 bytes UTF-8).

        [local fix 2026-09-28] 旧实现取全篇第一段文字，正文以图注开篇时摘要就变成
        「图注：...」。改为挑第一个实质段落：跳过图注/图片说明、纯图片块、
        标题和文末声明。
        """
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup.find_all(["script", "style"]):
            tag.decompose()

        blocks = []
        for el in soup.find_all(["p", "li", "h2", "h3", "h4", "blockquote"]):
            if el.find_parent(["p", "li", "blockquote"]) is not None:
                continue
            txt = re.sub(r"\s+", " ", el.get_text(" ", strip=True)).strip()
            if txt and txt not in blocks:
                blocks.append(txt)
        if not blocks:
            blocks = [re.sub(r"\s+", " ", soup.get_text(" ", strip=True)).strip()]

        caption_prefixes = ("图注", "插图", "题图", "图片：", "图片:", "图片来源",
                            "来源：", "数据来源", "本文数据核对", "封面图")
        def _is_caption(t):
            return t.startswith(caption_prefixes) or t.startswith("（图源")

        def _is_noise(t):
            return len(t) < 20 or _is_caption(t)

        body = [b for b in blocks if not _is_noise(b)]
        if not body:
            body = [b for b in blocks if not _is_caption(b)] or blocks

        text = body[0]
        for extra in body[1:]:
            if len(text.encode("utf-8")) >= max_bytes // 2:
                break
            text = (text + " " + extra).strip()

        ellipsis = "..."
        if len(text.encode("utf-8")) <= max_bytes:
            return text
        target_bytes = max_bytes - len(ellipsis.encode("utf-8"))
        truncated = text.encode("utf-8")[:target_bytes].decode("utf-8", errors="ignore").rstrip()
        return truncated + ellipsis

def make_paste_safe(html: str) -> str:
    """粘贴路径加固：文本节点包 <span leaf="">，空装饰元素补 <br> 占位。

    微信编辑器在粘贴时会重排不在 leaf span 内的文本、剥掉空元素的样式；
    API 发布草稿箱不经编辑器改写，无需本处理——本函数只用于 preview
    （复制粘贴进编辑器）路径。
    """
    soup = BeautifulSoup(html, "html.parser")

    # 1) 非空文本节点包 leaf（代码区跳过，已在 leaf span 内的跳过）
    for node in list(soup.find_all(string=True)):
        if not str(node).strip():
            continue
        if node.find_parent(["pre", "code"]) is not None:
            continue
        parent = node.parent
        if parent is None or (parent.name == "span" and parent.has_attr("leaf")):
            continue
        wrapper = soup.new_tag("span")
        wrapper["leaf"] = ""
        node.wrap(wrapper)

    # 2) 空装饰元素（分隔线、圆点等）补占位，防样式被剥
    for el in soup.find_all(["section", "span"]):
        if el.get_text(strip=True):
            continue
        if el.find(["img", "br"]) is not None:
            continue
        if el.name == "span" and el.has_attr("leaf"):
            continue
        ph = soup.new_tag("span")
        ph["leaf"] = ""
        ph.append(soup.new_tag("br"))
        el.append(ph)

    return str(soup)


def preview_html(body_html: str, theme: Theme) -> str:
    """
    Wrap body content in a full HTML document for browser preview.
    This is only for local preview — NOT for WeChat publishing.
    """
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Preview</title>
    <style>
{theme.base_css}
    </style>
</head>
<body>
    {body_html}
</body>
</html>"""
