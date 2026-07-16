#!/usr/bin/env python3
"""
Learn from human edits by diffing AI draft vs published final.

Compares the original AI-generated article with the human-edited version,
computes structured diffs, and saves typed lessons to lessons/.

Each lesson has:
  - type: word_sub / para_delete / para_add / structure / title / tone
  - occurrences: how many times this pattern has been seen across all lessons
  - first_seen / last_seen: timestamps for confidence decay
  - confidence: auto-computed from occurrences + recency

When summarizing, outputs all patterns with aggregated confidence scores.
The Agent uses this to write structured playbook.md rules.

Usage:
    wewrite learn-edits --draft path/to/draft.md --final path/to/final.md
    wewrite learn-edits --from-wechat         # auto-sync from WeChat draft box
    wewrite learn-edits --summarize           # all lessons with confidence
    wewrite learn-edits --summarize --json    # JSON output for agent
"""

import argparse
import difflib
import json
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

import yaml

from ..history import load_history
from ..paths import (config_path as _config_path, history_path as _history_path,
                     lessons_dir as _lessons_dir, home as _home)

# Pattern types with descriptions
PATTERN_TYPES = {
    "word_sub": "用词替换",
    "para_delete": "段落删除",
    "para_add": "段落新增",
    "structure": "结构调整",
    "title": "标题修改",
    "tone": "语气调整",
    "expression": "表达偏好",
}


def load_text(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def markdown_to_plaintext(md: str) -> str:
    """Strip markdown formatting to plain text for diff comparison."""
    text = md
    # Remove HTML comments (editing anchors etc.)
    text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)
    # Remove markdown headers markers
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
    # Remove bold/italic markers
    text = re.sub(r"\*{1,3}(.*?)\*{1,3}", r"\1", text)
    # Remove inline code
    text = re.sub(r"`([^`]+)`", r"\1", text)
    # Remove link syntax [text](url) → text
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    # Remove image syntax
    text = re.sub(r"!\[([^\]]*)\]\([^)]+\)", r"\1", text)
    # Collapse whitespace
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def fetch_wechat_draft() -> tuple[str, str, str]:
    """
    Fetch the latest draft from WeChat and find the corresponding local file.
    Returns (draft_plaintext, final_plaintext, draft_path).
    """
    # Load config
    config_path = _config_path()
    if not config_path.exists():
        raise FileNotFoundError("config.yaml not found — need WeChat API credentials")

    with open(config_path) as f:
        config = yaml.safe_load(f)

    wechat = config.get("wechat", {})
    appid = wechat.get("appid", "")
    secret = wechat.get("secret", "")
    if not appid or not secret:
        raise ValueError("config.yaml missing wechat.appid or wechat.secret")

    # Load history to find latest article with media_id
    history_path = _history_path()
    if not history_path.exists():
        raise FileNotFoundError("history.yaml not found — no articles to compare")

    history = load_history(history_path)["articles"]

    # Find most recent article with media_id
    latest = None
    for article in reversed(history):
        if article.get("media_id"):
            latest = article
            break

    if not latest:
        raise ValueError("No article with media_id found in history.yaml")

    media_id = latest["media_id"]
    title = latest.get("title", "")

    # Use the immutable, exact article path recorded for this published run.
    output_file = latest.get("output_file", "")
    draft_path = None
    if output_file:
        candidate = _home() / output_file if not Path(output_file).is_absolute() else Path(output_file)
        if candidate.exists():
            draft_path = candidate

    if not draft_path or not draft_path.exists():
        raise FileNotFoundError(
            f"Cannot find the exact local draft for '{title}'. "
            "Choose it explicitly with --draft instead of guessing by filename."
        )

    # Get access token and fetch draft from WeChat
    from ..toolkit.wechat_api import get_access_token
    from ..toolkit.publisher import get_draft, html_to_plaintext

    token = get_access_token(appid, secret)
    html = get_draft(token, media_id)
    wechat_text = html_to_plaintext(html)

    # Convert local draft to plaintext
    local_md = load_text(str(draft_path))
    local_text = markdown_to_plaintext(local_md)

    print(f"本地文件: {draft_path}")
    print(f"微信草稿: media_id={media_id}")
    print(f"文章标题: {title}")
    print(f"本地字数: {len(local_text)}, 微信字数: {len(wechat_text)}")

    return local_text, wechat_text, str(draft_path)


def split_sections(text: str) -> list[dict]:
    """Split markdown into sections by H2 headers."""
    sections = []
    current = {"header": "(intro)", "lines": []}
    for line in text.split("\n"):
        if line.strip().startswith("## "):
            if current["lines"] or current["header"] != "(intro)":
                sections.append(current)
            current = {"header": line.strip(), "lines": []}
        else:
            current["lines"].append(line)
    sections.append(current)
    return sections


def extract_title(text: str) -> str:
    for line in text.split("\n"):
        if line.strip().startswith("# ") and not line.strip().startswith("## "):
            return line.strip()[2:].strip()
    return ""


def compute_diff(draft: str, final: str) -> dict:
    """Compute structured diff between draft and final."""
    draft_lines = draft.split("\n")
    final_lines = final.split("\n")

    differ = difflib.unified_diff(draft_lines, final_lines, lineterm="")
    diff_lines = list(differ)

    additions = [l[1:].strip() for l in diff_lines
                 if l.startswith("+") and not l.startswith("+++") and l[1:].strip()]
    deletions = [l[1:].strip() for l in diff_lines
                 if l.startswith("-") and not l.startswith("---") and l[1:].strip()]

    draft_title = extract_title(draft)
    final_title = extract_title(final)

    draft_sections = split_sections(draft)
    final_sections = split_sections(final)
    draft_h2s = [s["header"] for s in draft_sections if s["header"] != "(intro)"]
    final_h2s = [s["header"] for s in final_sections if s["header"] != "(intro)"]

    draft_chars = len(draft.replace("\n", "").replace(" ", ""))
    final_chars = len(final.replace("\n", "").replace(" ", ""))

    return {
        "title_changed": draft_title != final_title,
        "draft_title": draft_title,
        "final_title": final_title,
        "structure_changed": draft_h2s != final_h2s,
        "draft_h2s": draft_h2s,
        "final_h2s": final_h2s,
        "lines_added": len(additions),
        "lines_deleted": len(deletions),
        "draft_chars": draft_chars,
        "final_chars": final_chars,
        "char_diff": final_chars - draft_chars,
        "additions_sample": additions[:20],
        "deletions_sample": deletions[:20],
    }


def save_lesson(diff_result: dict, draft_path: str, final_path: str) -> Path:
    """Save structured lesson data for Agent to analyze."""
    lessons_dir = _lessons_dir()
    lessons_dir.mkdir(parents=True, exist_ok=True)

    date_str = datetime.now().strftime("%Y-%m-%d")
    lesson_file = lessons_dir / f"{date_str}-diff.yaml"

    counter = 1
    while lesson_file.exists():
        lesson_file = lessons_dir / f"{date_str}-diff-{counter}.yaml"
        counter += 1

    data = {
        "date": date_str,
        "timestamp": datetime.now().isoformat(),
        "draft_file": str(draft_path),
        "final_file": str(final_path),
        "diff_summary": {
            "title_changed": diff_result["title_changed"],
            "draft_title": diff_result["draft_title"],
            "final_title": diff_result["final_title"],
            "structure_changed": diff_result["structure_changed"],
            "lines_added": diff_result["lines_added"],
            "lines_deleted": diff_result["lines_deleted"],
            "char_diff": diff_result["char_diff"],
        },
        # Agent fills these after analyzing the draft and final:
        "patterns": [],
        # Pattern format (Agent writes):
        # - type: "word_sub"        # one of PATTERN_TYPES keys
        #   key: "avoid_jiangzhen"  # short unique identifier
        #   description: "把'讲真'替换为'坦白说'"
        #   rule: "不要使用'讲真'，用'坦白说'代替"  # imperative, executable
    }

    with open(lesson_file, "w", encoding="utf-8") as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False)

    return lesson_file


def load_all_lessons() -> list[dict]:
    """Load all lesson files."""
    lessons_dir = _lessons_dir()
    if not lessons_dir.exists():
        return []
    lessons = []
    for f in sorted(lessons_dir.glob("*-diff*.yaml")):
        with open(f, "r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
            if data:
                lessons.append(data)
    return lessons


def compute_confidence(occurrences: int, first_seen: str, last_seen: str) -> float:
    """Compute confidence score from frequency and recency.

    Confidence = base_from_occurrences + recency_bonus - age_decay.

    - 1 occurrence = 3 (low, might be one-off)
    - 2 occurrences = 5 (moderate, likely a preference)
    - 3+ occurrences = 7+ (high, confirmed preference)
    - Recency bonus: +0.5 for repeated patterns seen within 7 days
    - Age decay: -1 per 30 days since last_seen (user style evolves)
    - Clamped to 1-10
    """
    if occurrences <= 1:
        base = 3.0
    elif occurrences == 2:
        base = 5.0
    else:
        base = min(8.0, 1.0 + occurrences * 2)

    try:
        last = datetime.fromisoformat(last_seen)
        days_since = (datetime.now() - last).days
    except (ValueError, TypeError):
        days_since = 0

    recency_bonus = 0.5 if occurrences >= 2 and days_since <= 7 else 0.0
    age_decay = max(0, days_since // 30)

    return max(1.0, min(10.0, base + recency_bonus - age_decay))


def aggregate_patterns(lessons: list[dict]) -> list[dict]:
    """Aggregate patterns across all lessons. Returns sorted by confidence."""
    pattern_map = {}  # (key, scope, scope_value) → aggregated data

    for lesson in lessons:
        date = lesson.get("date", "")
        timestamp = lesson.get("timestamp", date)
        for p in lesson.get("patterns", []):
            key = p.get("key", "")
            if not key:
                continue
            scope = p.get("scope", "global")
            scope_value = p.get("scope_value", "")
            if scope not in {"global", "content_type", "framework", "persona"}:
                scope = "global"
                scope_value = ""
            pattern_id = (key, scope, scope_value)
            if pattern_id not in pattern_map:
                pattern_map[pattern_id] = {
                    "key": key,
                    "scope": scope,
                    "scope_value": scope_value,
                    "type": p.get("type", "expression"),
                    "description": p.get("description", ""),
                    "rule": p.get("rule", ""),
                    "occurrences": 0,
                    "first_seen": timestamp,
                    "last_seen": timestamp,
                    "confirmed": False,
                }
            entry = pattern_map[pattern_id]
            entry["occurrences"] += 1
            entry["confirmed"] = entry["confirmed"] or bool(p.get("confirmed", False))
            # Keep the most recent description/rule (may evolve)
            if p.get("description"):
                entry["description"] = p["description"]
            if p.get("rule"):
                entry["rule"] = p["rule"]
            # Update timestamps
            if timestamp < entry["first_seen"]:
                entry["first_seen"] = timestamp
            if timestamp > entry["last_seen"]:
                entry["last_seen"] = timestamp

    # Compute confidence for each
    results = []
    for entry in pattern_map.values():
        entry["confidence"] = round(compute_confidence(
            entry["occurrences"], entry["first_seen"], entry["last_seen"]
        ), 1)
        entry["hard"] = bool(entry["confirmed"] or (
            entry["occurrences"] >= 2 and entry["confidence"] >= 5
        ))
        results.append(entry)

    # Sort by confidence descending
    results.sort(key=lambda x: x["confidence"], reverse=True)
    return results


def summarize_lessons(as_json: bool = False):
    """Load all lessons, aggregate patterns, output with confidence scores."""
    lessons = load_all_lessons()
    if not lessons:
        if as_json:
            print(json.dumps({
                "total_lessons": 0,
                "total_patterns": 0,
                "patterns": [],
            }, ensure_ascii=False, indent=2))
        else:
            print("No lessons found.")
        return

    patterns = aggregate_patterns(lessons)

    if as_json:
        print(json.dumps({
            "total_lessons": len(lessons),
            "total_patterns": len(patterns),
            "patterns": patterns,
        }, ensure_ascii=False, indent=2))
        return

    print(f"Total lessons: {len(lessons)}")
    print(f"Unique patterns: {len(patterns)}")
    print()

    for p in patterns:
        type_label = PATTERN_TYPES.get(p["type"], p["type"])
        conf_bar = "█" * int(p["confidence"]) + "░" * (10 - int(p["confidence"]))
        print(f"  {conf_bar} {p['confidence']:4.1f}  [{type_label}] {p['key']}")
        print(f"         {p['description']}")
        if p["rule"]:
            print(f"         → {p['rule']}")
        print(f"         scope {p['scope']}:{p['scope_value'] or '*'}, "
              f"seen {p['occurrences']}x, hard={str(p['hard']).lower()}, "
              f"first {p['first_seen'][:10]}, last {p['last_seen'][:10]}")
        print()


def main():
    parser = argparse.ArgumentParser(description="Learn from human edits")
    parser.add_argument("--draft", help="Path to AI draft")
    parser.add_argument("--final", help="Path to human-edited final")
    parser.add_argument("--from-wechat", action="store_true",
                        help="Auto-fetch edited version from WeChat draft box")
    parser.add_argument("--summarize", action="store_true", help="Summarize all lessons")
    parser.add_argument("--json", action="store_true", help="JSON output (with --summarize)")
    args = parser.parse_args()

    if args.summarize:
        summarize_lessons(as_json=args.json)
        return

    if args.from_wechat:
        local_text, wechat_text, draft_path = fetch_wechat_draft()
        if local_text == wechat_text:
            print("\n微信草稿与本地文件内容一致，没有修改。")
            return
        diff_result = compute_diff(local_text, wechat_text)
        # Save with special marker for wechat source
        lesson_file = save_lesson(diff_result, draft_path, f"wechat:{draft_path}")
        print(f"\nLesson saved to: {lesson_file}")
        print(f"\n检测到 {diff_result['lines_added']} 处新增, {diff_result['lines_deleted']} 处删除")
        print(f"字数变化: {diff_result['char_diff']:+d}")
        print(f"\nAgent 接下来读取 {draft_path} 和微信草稿内容，分析修改模式并写入 {lesson_file}")
        return

    if not args.draft or not args.final:
        print("Error: --draft and --final required (or use --from-wechat)", file=sys.stderr)
        sys.exit(1)

    draft = load_text(args.draft)
    final = load_text(args.final)
    diff_result = compute_diff(draft, final)

    # Print summary
    print("=" * 60)
    print("EDIT ANALYSIS")
    print("=" * 60)

    if diff_result["title_changed"]:
        print(f"\n标题修改:")
        print(f"  AI:   {diff_result['draft_title']}")
        print(f"  人工: {diff_result['final_title']}")

    if diff_result["structure_changed"]:
        print(f"\n结构修改:")
        print(f"  AI H2:   {diff_result['draft_h2s']}")
        print(f"  人工 H2: {diff_result['final_h2s']}")

    print(f"\n数量变化:")
    print(f"  新增 {diff_result['lines_added']} 行, 删除 {diff_result['lines_deleted']} 行")
    print(f"  字数变化: {diff_result['char_diff']:+d} ({diff_result['draft_chars']} → {diff_result['final_chars']})")

    if diff_result["deletions_sample"]:
        print(f"\n被删除的内容（采样）:")
        for line in diff_result["deletions_sample"][:10]:
            print(f"  - {line[:80]}")

    if diff_result["additions_sample"]:
        print(f"\n新增的内容（采样）:")
        for line in diff_result["additions_sample"][:10]:
            print(f"  + {line[:80]}")

    # Save lesson
    lesson_file = save_lesson(diff_result, args.draft, args.final)
    print(f"\nLesson saved to: {lesson_file}")

    # Auto-grow exemplar library from edited finals
    final_title = extract_title(final)
    try:
        from . import extract_exemplar
        exemplar = extract_exemplar.extract_exemplar(
            final,
            source=final_title or "user-edited",
            ownership="user",
            authenticity="user_edited",
        )
        if exemplar["quality_score"] >= 50:
            exemplar_path = extract_exemplar.save_exemplar(exemplar)
            print(f"\n✓ 终稿已加入范文库: {exemplar_path}")
            print(f"  Quality: {exemplar['quality_score']:.1f}/100, Category: {exemplar['category']}")
        else:
            print(f"\n⚠ 终稿机械语言风险较高，先复审后再加入范文库")
    except Exception as e:
        print(f"\n⚠ 范文提取跳过: {e}")

    lesson_count = len(load_all_lessons())
    print(f"Total lessons: {lesson_count}")

    print(f"\n{'=' * 60}")
    print("PLAYBOOK UPDATE REQUIRED")
    print(f"{'=' * 60}")
    print(f"{lesson_count} lesson(s). After filling this lesson's patterns, run:")
    print("  wewrite learn-edits --summarize --json")
    print("Then update playbook.md so this edit affects the next article.")

    # Instructions for Agent
    print(f"""
{'=' * 60}
INSTRUCTIONS FOR AGENT
{'=' * 60}

Read the draft and final versions, then for each meaningful edit:

1. Read: {args.draft}
2. Read: {args.final}
3. For each edit, add a pattern entry to {lesson_file}:

   patterns:
     - type: "word_sub"           # {' / '.join(PATTERN_TYPES.keys())}
       key: "short_unique_id"     # e.g. "avoid_jiangzhen", "shorter_paragraphs"
       description: "把'讲真'替换为'坦白说'"
       rule: "不要使用'讲真'，用'坦白说'代替"  # imperative, executable
       scope: "content_type"       # global / content_type / framework / persona
       scope_value: "观点"         # global 时留空
       confirmed: false             # 用户明确确认这是长期偏好时才设 true

4. Rules must be imperative (可执行的指令), not descriptive.
   BAD:  "用户偏好简短段落"
   GOOD: "段落不超过 80 字，长段必须在 3 句内换行"

5. If pattern already exists in previous lessons with the same key and scope,
   confidence will auto-increase on next --summarize. A one-off edit stays soft.
""")


if __name__ == "__main__":
    main()
