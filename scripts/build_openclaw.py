#!/usr/bin/env python3
"""
Build OpenClaw-compatible SKILL.md from Claude Code source.

Since v2.0 the Claude Code source is modular (skills/wewrite + skills/wewrite-*);
OpenClaw is a single-SKILL.md harness, so this build merges the modules back
into one monolithic SKILL.md (main entry with module bodies inlined at the
`<!-- wewrite:inline-* -->` markers, per-module standalone boilerplate stripped).

Usage:
    python3 scripts/build_openclaw.py              # output to dist/openclaw/
    python3 scripts/build_openclaw.py -o /tmp/oc   # custom output dir
"""

import argparse
import re
import shutil
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = REPO_ROOT / "skills"

# Module merge order: pipeline bodies replace the inline-pipeline marker
# (between Step 1 and Step 8), aux bodies replace the inline-aux marker (end).
PIPELINE_MODULES = ["wewrite-topic", "wewrite-write", "wewrite-review",
                    "wewrite-visual", "wewrite-publish"]
AUX_MODULES = ["wewrite-style", "wewrite-learn", "wewrite-stats", "wewrite-rewrite"]

STANDALONE_RE = re.compile(
    r"<!-- wewrite:standalone-start -->.*?<!-- wewrite:standalone-end -->\n?", re.S)
MODULAR_RE = re.compile(
    r"<!-- wewrite:modular-start -->.*?<!-- wewrite:modular-end -->\n?", re.S)

# The modular main entry resolves {root} via a per-skill symlink; the merged
# monolith is one file at the repo root, so restore the classic convention.
PATH_NOTE_MODULAR = (
    "**路径约定**：本文档中 `{skill_dir}` 指本 skill 目录（自带 `references/`）；"
    "兄弟模块经 `{skill_dir}/../wewrite-<模块>/` 访问（安装目录里各 skill 互为同级链接，"
    "路径经符号链接解析仍指回仓库）。**{repo}** = 仓库根，需要时用 "
    "`REPO=\"$(cd \"$(dirname \"$(realpath \"{skill_dir}/SKILL.md\")\")/../..\" && pwd)\"` 定位。"
)
PATH_NOTE_MERGED = (
    "**路径约定**：本文档中 `{skill_dir}` 与 `{repo}` 均指本 SKILL.md 所在的目录"
    "（即 WeWrite 单体版根目录，references/ 与 personas/ 在其下）。"
)

# prompt 层资产自 v3.0 起归位在各 skill 目录内；合并单体时收拢到 dist 的
# references/（各模块文件名不重复）、personas/、platforms/ 平铺目录。
COLLECT_DIR_NAMES = ["references", "personas", "platforms"]

# Files to copy alongside SKILL.md（(源路径, dist 内文件名)）
COPY_FILES = [
    ("config.example.yaml", "config.example.yaml"),
    ("skills/wewrite-style/style.example.yaml", "style.example.yaml"),
    ("writing-config.example.yaml", "writing-config.example.yaml"),
    ("VERSION", "VERSION"),
    ("install.sh", "install.sh"),  # 无 pyproject 时自动改为从 git 安装 wewrite CLI
]

# Frontmatter keys to strip (OpenClaw ignores allowed-tools)
STRIP_FRONTMATTER_KEYS = {"allowed-tools"}


def transform_frontmatter(frontmatter: str) -> str:
    """Remove Claude Code-specific frontmatter keys."""
    lines = frontmatter.split("\n")
    result = []
    skip_block = False
    for line in lines:
        # Check if this line starts a key we want to strip
        stripped = line.lstrip()
        if any(stripped.startswith(f"{key}:") for key in STRIP_FRONTMATTER_KEYS):
            skip_block = True
            continue
        # If we're in a skip block, skip indented continuation lines (list items)
        if skip_block:
            if stripped.startswith("- ") or stripped == "":
                continue
            skip_block = False
        result.append(line)
    return "\n".join(result)


def transform_body(body: str) -> str:
    """Apply all body transformations."""
    # 1. {skill_dir} → {baseDir}
    body = body.replace("{skill_dir}", "{baseDir}")

    # 2. WebSearch references in instructions (preserve in bash code blocks)
    #    "WebSearch:" as instruction prefix → "web_search:"
    #    "WebSearch " in prose → "web_search "
    body = re.sub(r'(?m)^WebSearch:', 'web_search:', body)
    body = re.sub(r'(?<![`/])WebSearch(?=[ "：，）])', 'web_search', body)
    #    WebSearch in parentheses/tables: "（WebSearch）"
    body = re.sub(r'(?<=（)WebSearch(?=）)', 'web_search', body)

    # 3. Path convention note
    body = body.replace(
        "本文档中 `{baseDir}` 指本 SKILL.md 所在的目录（即 WeWrite 的根目录）",
        "本文档中 `{baseDir}` 指本 SKILL.md 所在的目录（即 WeWrite 的根目录）",
    )

    return body


def split_frontmatter(text: str) -> tuple[str, str]:
    """Split YAML frontmatter from body. Returns (frontmatter, body)."""
    if not text.startswith("---"):
        return "", text
    end = text.find("\n---", 3)
    if end == -1:
        return "", text
    # +4 to skip the closing "---\n"
    fm = text[3:end].strip()
    body = text[end + 4:]  # skip "\n---"
    return fm, body


def _demote_headings(body: str) -> str:
    """Demote every heading one level so module H1s nest under the main entry.

    Fenced code blocks are skipped — bash comments also start with '#'.
    """
    out, in_fence = [], False
    for line in body.split("\n"):
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
        elif not in_fence and re.match(r"#{1,5} ", line):
            line = "#" + line
        out.append(line)
    return "\n".join(out)


def module_body(name: str) -> str:
    """Module SKILL.md body: frontmatter + standalone boilerplate stripped."""
    text = (SKILLS_DIR / name / "SKILL.md").read_text(encoding="utf-8")
    _, body = split_frontmatter(text)
    body = STANDALONE_RE.sub("", body)
    return _demote_headings(body.strip())


def merge_monolith() -> str:
    """Merge skills/wewrite + module bodies into one monolithic SKILL.md text."""
    text = (SKILLS_DIR / "wewrite" / "SKILL.md").read_text(encoding="utf-8")
    fm, body = split_frontmatter(text)
    if PATH_NOTE_MODULAR not in body:
        raise SystemExit(
            "build: 路径约定 line drifted in skills/wewrite/SKILL.md — "
            "update PATH_NOTE_MODULAR in build_openclaw.py")
    body = body.replace(PATH_NOTE_MODULAR, PATH_NOTE_MERGED)
    body = MODULAR_RE.sub("", body)
    for marker in ("<!-- wewrite:inline-pipeline -->", "<!-- wewrite:inline-aux -->"):
        if marker not in body:
            raise SystemExit(f"build: marker {marker} missing in skills/wewrite/SKILL.md")
    pipeline = "\n\n---\n\n".join(module_body(m) for m in PIPELINE_MODULES)
    aux = ("## 辅助模块\n\n（上方「路由」表中的模块名对应本节下方的同名小节，"
           "命中路由后直接执行对应小节）\n\n"
           + "\n\n---\n\n".join(module_body(m) for m in AUX_MODULES))
    body = body.replace("<!-- wewrite:inline-pipeline -->", pipeline)
    body = body.replace("<!-- wewrite:inline-aux -->", "---\n\n" + aux)
    # 兄弟模块引用在单体里都平铺到同一目录
    body = re.sub(r"\{skill_dir\}/\.\./wewrite(?:-[a-z]+)?/", "{skill_dir}/", body)
    return f"---\n{fm}\n---\n\n{body.lstrip()}"


def build(output_dir: Path):
    text = merge_monolith()

    fm, body = split_frontmatter(text)
    fm = transform_frontmatter(fm)
    body = transform_body(body)

    out_skill = output_dir / "SKILL.md"
    output_dir.mkdir(parents=True, exist_ok=True)
    out_skill.write_text(f"---\n{fm}\n---{body}", encoding="utf-8")
    print(f"  SKILL.md → {out_skill}")

    # Collect per-skill prompt assets into flat dist dirs
    for name in COLLECT_DIR_NAMES:
        dst = output_dir / name
        if dst.exists():
            shutil.rmtree(dst)
        count = 0
        for skill_dir in sorted(SKILLS_DIR.iterdir()):
            src = skill_dir / name
            if not src.is_dir():
                continue
            dst.mkdir(parents=True, exist_ok=True)
            for item in sorted(src.iterdir()):
                if item.name.startswith(".") or item.name == "__pycache__":
                    continue
                if item.is_file():
                    if (dst / item.name).exists():
                        raise SystemExit(f"build: {name}/{item.name} 在多个 skill 中重名，无法平铺")
                    shutil.copy2(item, dst / item.name)
                    count += 1
        if count:
            print(f"  {name}/ ← skills/*/{name} ({count} files)")

    # Copy supporting files
    for src_rel, dst_name in COPY_FILES:
        src = REPO_ROOT / src_rel
        if src.is_file():
            shutil.copy2(src, output_dir / dst_name)
            print(f"  {dst_name} → {output_dir / dst_name}")

    print(f"\nDone. OpenClaw skill at: {output_dir}")


def main():
    parser = argparse.ArgumentParser(description="Build OpenClaw-compatible WeWrite skill")
    parser.add_argument(
        "-o", "--output",
        default=str(REPO_ROOT / "dist" / "openclaw"),
        help="Output directory (default: dist/openclaw/)",
    )
    args = parser.parse_args()
    build(Path(args.output))


if __name__ == "__main__":
    main()
