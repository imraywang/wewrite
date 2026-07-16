#!/usr/bin/env python3
"""
Extract style exemplars from human-written articles for SICO-style few-shot injection.

Takes a markdown article, analyzes it for style fingerprints, extracts key
segments (opening hook, emotional peak, transition/self-correction, closing),
and saves structured exemplar files to references/exemplars/.

Usage:
    wewrite exemplar article.md
    wewrite exemplar article.md --category tech-opinion --source "公众号名"
    wewrite exemplar article1.md article2.md article3.md  # batch
    wewrite exemplar --list                                # list all exemplars
"""

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

import yaml

# Reuse analysis functions from humanness_score
from . import humanness_score as hs
from ..paths import exemplars_dir

EXEMPLARS_DIR = exemplars_dir()
INDEX_FILE = EXEMPLARS_DIR / "index.yaml"

CATEGORIES = ["tech-opinion", "story-emotional", "list-practical", "hot-take", "general"]

# Category detection markers
STORY_MARKERS = [
    "我", "我们", "那天", "那年", "记得", "后来", "当时",
    "第一次", "最后", "突然", "终于",
]


# ============================================================
# Segment Extraction
# ============================================================

def extract_headings(text):
    """Extract H2 headings from markdown."""
    return re.findall(r'^##\s+(.+)$', text, re.MULTILINE)


def extract_title(text):
    """Extract H1 title from markdown."""
    m = re.search(r'^#\s+(.+)$', text, re.MULTILINE)
    return m.group(1).strip() if m else ""


def extract_opening(paragraphs, max_chars=250):
    """Extract opening hook — first non-empty paragraph(s) up to max_chars."""
    result = []
    total = 0
    for p in paragraphs:
        if total + len(p) > max_chars and result:
            break
        result.append(p)
        total += len(p)
    return "\n\n".join(result)


def extract_emotional_peak(paragraphs):
    """Find paragraph with highest negative emotion density."""
    best_para, best_density = "", -1.0
    for p in paragraphs:
        if len(p) < 20:
            continue
        count = sum(1 for m in hs.NEGATIVE_MARKERS if m in p)
        density = count / len(p) * 100
        if density > best_density:
            best_density = density
            best_para = p
    return best_para if best_density > 0 else ""


def extract_transition(paragraphs):
    """Find paragraph with most self-correction / transition patterns."""
    transition_words = [
        "但是", "不过", "然而", "话说回来", "换个角度",
        "说回来", "但话又说回来", "不对", "算了",
    ]
    best_para, best_count = "", 0
    for p in paragraphs:
        if len(p) < 20:
            continue
        count = sum(len(re.findall(pat, p)) for pat in hs.SELF_CORRECTION_PATTERNS)
        count += sum(p.count(w) for w in transition_words)
        if count > best_count:
            best_count = count
            best_para = p
    return best_para if best_count > 0 else ""


def extract_closing(paragraphs, max_chars=250):
    """Extract closing paragraph(s), reading backwards."""
    result = []
    total = 0
    for p in reversed(paragraphs):
        if total + len(p) > max_chars and result:
            break
        result.insert(0, p)
        total += len(p)
    return "\n\n".join(result)


# ============================================================
# Category Detection
# ============================================================

def detect_category(text, paragraphs, headings):
    """Auto-detect article category from content features."""
    data_count = sum(len(re.findall(p, text)) for p in hs.REAL_SOURCE_PATTERNS)
    story_count = sum(text.count(m) for m in STORY_MARKERS)
    h2_count = len(headings)
    neg_count = sum(1 for m in hs.NEGATIVE_MARKERS if m in text)

    scores = {
        "tech-opinion": data_count * 2,
        "story-emotional": story_count * 1.5,
        "list-practical": h2_count * 3 if h2_count >= 5 else 0,
        "hot-take": neg_count * 2 + data_count if len(text) < 2000 else 0,
        "general": 5,
    }
    return max(scores, key=scores.get)


# ============================================================
# Statistical Fingerprint
# ============================================================

def compute_vocab_temperature(text):
    """Compute vocabulary temperature band distribution."""
    counts = {
        "cold": sum(text.count(w) for w in hs.COLD_WORDS),
        "warm": sum(text.count(w) for w in hs.WARM_WORDS),
        "hot": sum(text.count(w) for w in hs.HOT_WORDS),
        "wild": sum(text.count(w) for w in hs.WILD_WORDS),
    }
    total = sum(counts.values())
    if total == 0:
        return {k: 0.25 for k in counts}
    return {k: round(v / total, 2) for k, v in counts.items()}


def compute_paragraph_cv(paragraphs):
    """Coefficient of variation for paragraph lengths."""
    if len(paragraphs) < 3:
        return 0.0
    lengths = [len(p) for p in paragraphs]
    mean = sum(lengths) / len(lengths)
    if mean == 0:
        return 0.0
    variance = sum((l - mean) ** 2 for l in lengths) / len(lengths)
    return round((variance ** 0.5) / mean, 2)


def count_short_paragraphs(text):
    """Count single-sentence short paragraphs (1-10 chars, non-heading)."""
    return sum(1 for l in text.split('\n')
               if l.strip() and 1 <= len(l.strip()) <= 10
               and not l.strip().startswith('#'))


# ============================================================
# Main Extraction
# ============================================================

def extract_exemplar(
    text, category=None, source=None, *, ownership="unknown", authenticity="unverified"
):
    """Analyze article and return structured exemplar dict."""
    clean = re.sub(r'^#+\s+.*$', '', text, flags=re.MULTILINE).strip()
    paragraphs = hs._split_paragraphs(text)
    sentences = hs._split_sentences(clean)
    headings = extract_headings(text)
    title = extract_title(text) or source or ""

    if not category:
        category = detect_category(clean, paragraphs, headings)

    score_result = hs.score_article(text)

    # Sentence length stats
    lengths = [len(s) for s in sentences]
    if len(lengths) >= 2:
        mean = sum(lengths) / len(lengths)
        variance = sum((l - mean) ** 2 for l in lengths) / len(lengths)
        sentence_stddev = round(variance ** 0.5, 1)
    else:
        sentence_stddev = 0.0

    neg_count = sum(1 for s in sentences if any(m in s for m in hs.NEGATIVE_MARKERS))
    negative_ratio = round(neg_count / len(sentences), 2) if sentences else 0.0

    return {
        "title": title,
        "source": source or title,
        "category": category,
        "ownership": ownership,
        "authenticity": authenticity,
        "allowed_uses": ["style", "structure"],
        "personal_materials_reusable": False,
        "quality_score": score_result["quality_score"],
        "fingerprint": {
            "sentence_stddev": sentence_stddev,
            "vocab_temperature": compute_vocab_temperature(clean),
            "negative_ratio": negative_ratio,
            "paragraph_cv": compute_paragraph_cv(paragraphs),
            "short_paragraphs": count_short_paragraphs(text),
        },
        "segments": {
            "opening": extract_opening(paragraphs),
            "emotional_peak": extract_emotional_peak(paragraphs),
            "transition": extract_transition(paragraphs),
            "closing": extract_closing(paragraphs),
        },
        "extracted_at": datetime.now().strftime("%Y-%m-%d"),
        "char_count": len(clean),
    }


# ============================================================
# Persistence
# ============================================================

def save_exemplar(exemplar):
    """Save exemplar to markdown file and update index.yaml. Returns filepath."""
    EXEMPLARS_DIR.mkdir(parents=True, exist_ok=True)

    category = exemplar["category"]
    num = 1
    while (EXEMPLARS_DIR / f"{category}-{num:03d}.md").exists():
        num += 1
    filename = f"{category}-{num:03d}.md"
    filepath = EXEMPLARS_DIR / filename

    fp = exemplar["fingerprint"]
    seg = exemplar["segments"]

    frontmatter = {
        "source": exemplar["source"],
        "category": category,
        "quality_score": exemplar["quality_score"],
        "ownership": exemplar.get("ownership", "unknown"),
        "authenticity": exemplar.get("authenticity", "unverified"),
        "allowed_uses": exemplar.get("allowed_uses", ["style", "structure"]),
        "personal_materials_reusable": False,
        "sentence_stddev": fp["sentence_stddev"],
        "vocab_temperature": fp["vocab_temperature"],
        "negative_ratio": fp["negative_ratio"],
        "paragraph_cv": fp["paragraph_cv"],
        "short_paragraphs": fp["short_paragraphs"],
        "extracted_at": exemplar["extracted_at"],
    }

    content = "---\n"
    content += yaml.dump(frontmatter, allow_unicode=True, default_flow_style=False)
    content += "---\n\n"

    section_map = [
        ("opening", "开头钩子"),
        ("emotional_peak", "情绪高峰"),
        ("transition", "转折/自纠"),
        ("closing", "收尾"),
    ]
    for key, label in section_map:
        if seg.get(key):
            content += f"## {label}\n\n{seg[key]}\n\n"

    filepath.write_text(content, encoding="utf-8")
    _update_index(filename, exemplar)
    return filepath


def _update_index(filename, exemplar):
    """Add or update entry in index.yaml."""
    index = []
    if INDEX_FILE.exists():
        with open(INDEX_FILE, "r", encoding="utf-8") as f:
            index = yaml.safe_load(f) or []

    entry = {
        "file": filename,
        "source": exemplar["source"],
        "category": exemplar["category"],
        "quality_score": exemplar["quality_score"],
        "ownership": exemplar.get("ownership", "unknown"),
        "authenticity": exemplar.get("authenticity", "unverified"),
        "extracted_at": exemplar["extracted_at"],
    }
    index = [e for e in index if e.get("file") != filename]
    index.append(entry)
    index.sort(key=lambda x: (x["category"], -_entry_quality(x)))

    with open(INDEX_FILE, "w", encoding="utf-8") as f:
        yaml.dump(index, f, allow_unicode=True, default_flow_style=False)


# ============================================================
# List / CLI
# ============================================================

def list_exemplars():
    """Print all exemplars in the library."""
    if not INDEX_FILE.exists():
        print("范文库为空。用法: wewrite exemplar article.md")
        return

    with open(INDEX_FILE, "r", encoding="utf-8") as f:
        index = yaml.safe_load(f) or []

    if not index:
        print("范文库为空。")
        return

    print(f"\n{'=' * 60}")
    print(f"范文库 ({len(index)} 篇)")
    print(f"{'=' * 60}")

    by_cat = {}
    for e in index:
        by_cat.setdefault(e["category"], []).append(e)

    for cat, entries in sorted(by_cat.items()):
        print(f"\n  [{cat}] ({len(entries)} 篇)")
        for e in entries:
            score = _entry_quality(e)
            bar = "█" * int(score / 10) + "░" * (10 - int(score / 10))
            print(f"    {bar} {score:5.1f}  {e['source'][:40]}")


def _entry_quality(entry):
    """Read canonical quality score or convert a pre-v4 risk score."""
    if "quality_score" in entry:
        return float(entry["quality_score"])
    return 100.0 - float(entry.get("humanness_score", 50))


def main():
    parser = argparse.ArgumentParser(description="Extract style exemplars from articles")
    parser.add_argument("inputs", nargs="*", help="Markdown article file(s)")
    parser.add_argument("--category", "-c", choices=CATEGORIES,
                        help="Article category (auto-detected if omitted)")
    parser.add_argument("--source", "-s", help="Source name (e.g. account name)")
    parser.add_argument("--user-authored", action="store_true",
                        help="标记为用户本人创作；仍不得复用其中的个人经历")
    parser.add_argument("--list", "-l", action="store_true", help="List all exemplars")
    parser.add_argument("--json", action="store_true", help="JSON output")
    args = parser.parse_args()

    if args.list:
        list_exemplars()
        return

    if not args.inputs:
        parser.print_help()
        sys.exit(1)

    for input_path in args.inputs:
        path = Path(input_path)
        if not path.exists():
            print(f"Error: {input_path} not found", file=sys.stderr)
            continue

        text = path.read_text(encoding="utf-8")
        source = args.source or path.stem  # fallback to filename without extension
        exemplar = extract_exemplar(
            text,
            category=args.category,
            source=source,
            ownership="user" if args.user_authored else "third_party",
            authenticity="user_authored" if args.user_authored else "published",
        )
        filepath = save_exemplar(exemplar)

        if args.json:
            print(json.dumps(exemplar, ensure_ascii=False, indent=2))
        else:
            print(f"✓ {path.name}")
            print(f"  Category:  {exemplar['category']}")
            print(f"  Quality:   {exemplar['quality_score']:.1f}/100")
            print(f"  Segments:  {sum(1 for v in exemplar['segments'].values() if v)}/4")
            fp = exemplar["fingerprint"]
            print(f"  Stddev:    {fp['sentence_stddev']}")
            print(f"  Neg ratio: {fp['negative_ratio']:.0%}")
            print(f"  Para CV:   {fp['paragraph_cv']}")
            temp = fp["vocab_temperature"]
            print(f"  Temp:      cold={temp['cold']} warm={temp['warm']} hot={temp['hot']} wild={temp['wild']}")
            print(f"  Saved to:  {filepath}")
            print()


if __name__ == "__main__":
    main()
