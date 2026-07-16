#!/usr/bin/env python3
"""
Measure the doc-context load of a normal full WeWrite pipeline run (issue #16).

Since v2.0 the skill is modular: a full run loads the main entry
(skills/wewrite/SKILL.md) plus the five pipeline module SKILL.mds. This
script sums those files and the happy-path `读取:` reference docs they load,
and reports lines / chars / estimated tokens. Doubles as a CI regression
guard so the pipeline cannot silently re-bloat (e.g. re-adding
wechat-constraints.md).

Usage:
    python3 scripts/context_budget.py                      # human table
    python3 scripts/context_budget.py --json               # machine output
    python3 scripts/context_budget.py --budget-tokens 12000  # exit 1 if over
"""
import argparse
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# References NOT on the normal generate-an-article happy path
# (auxiliary / conditional / fallback / dev-reference). Everything else
# matched in a 读取 directive is treated as ON_PATH.
AUXILIARY = {
    "onboard.md",          # first-run / 重新设置风格 only (wewrite-style)
    "learn-edits.md",      # 学习我的修改 (wewrite-learn)
    "effect-review.md",    # 看看文章数据 (wewrite-stats)
    "multiplatform-rewrite.md",  # 多平台改写 (wewrite-rewrite)
    "style-template.md",   # only referenced inside onboard.md
    "pipeline-state.md",   # maintainer contract doc, not loaded at runtime
    "wechat-constraints.md",  # dev-reference (key limits inlined in wewrite-publish)
}

# A normal full run loads the main entry + the five pipeline modules.
PIPELINE_SKILLS = [
    "skills/wewrite/SKILL.md",
    "skills/wewrite-topic/SKILL.md",
    "skills/wewrite-write/SKILL.md",
    "skills/wewrite-review/SKILL.md",
    "skills/wewrite-visual/SKILL.md",
    "skills/wewrite-publish/SKILL.md",
]

# Step 4.2 always loads exactly one persona; midnight-friend is the default.
DEFAULT_PERSONA = "skills/wewrite-write/personas/midnight-friend.yaml"

# The current first-run path no longer injects synthetic exemplars or a second
# sentence-level checklist. All mandatory references are explicit in SKILL.md.
DEFAULT_FIRST_RUN_REFS = []

LOAD_RE = re.compile(r"读取:\s*\{(?:skill_dir|root)\}/(references/[\w./-]+\.(?:md|yaml))")


def parse_onpath_refs(skill_md_text: str) -> list:
    """Return ON_PATH reference relative paths (de-duped, order-preserving)."""
    seen = []
    for m in LOAD_RE.finditer(skill_md_text):
        rel = m.group(1)
        base = rel.split("/")[-1]
        if base in AUXILIARY:
            continue
        if rel not in seen:
            seen.append(rel)
    return seen


def _stats(path: Path) -> tuple:
    text = path.read_text(encoding="utf-8")
    lines = text.count("\n") + (1 if text and not text.endswith("\n") else 0)
    return lines, len(text)


def measure(skill_dir: Path) -> dict:
    entries = []
    seen_paths = []
    for rel in PIPELINE_SKILLS:
        skill_md = skill_dir / rel
        l, c = _stats(skill_md)
        entries.append({"name": rel, "lines": l, "chars": c})
        # v3.0：references 归位在各 skill 目录内，相对 SKILL.md 所在目录解析
        for ref in parse_onpath_refs(skill_md.read_text(encoding="utf-8")):
            p = (skill_md.parent / ref).resolve()
            if p in seen_paths or not p.exists():
                continue
            seen_paths.append(p)
            l, c = _stats(p)
            entries.append({"name": str(p.relative_to(skill_dir.resolve())), "lines": l, "chars": c})
    persona = skill_dir / DEFAULT_PERSONA
    if persona.exists():
        l, c = _stats(persona)
        entries.append({"name": DEFAULT_PERSONA, "lines": l, "chars": c})
    for rel in DEFAULT_FIRST_RUN_REFS:
        path = skill_dir / rel
        if path.exists() and path.resolve() not in seen_paths:
            seen_paths.append(path.resolve())
            l, c = _stats(path)
            entries.append({"name": rel, "lines": l, "chars": c})
    total_lines = sum(e["lines"] for e in entries)
    total_chars = sum(e["chars"] for e in entries)
    return {
        "entries": entries,
        "peak_lines": total_lines,
        "peak_chars": total_chars,
        "peak_tokens": round(total_chars / 3.5),
    }


def main():
    ap = argparse.ArgumentParser(description="Measure WeWrite pipeline context load")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--budget-tokens", type=int, default=None)
    args = ap.parse_args()
    r = measure(REPO_ROOT)
    if args.json:
        print(json.dumps(r, ensure_ascii=False, indent=2))
    else:
        print(f"{'file':<45}{'lines':>7}{'chars':>8}{'~tok':>7}")
        print("-" * 67)
        for e in r["entries"]:
            print(f"{e['name']:<45}{e['lines']:>7}{e['chars']:>8}{round(e['chars']/3.5):>7}")
        print("-" * 67)
        print(f"{'STATIC FIRST-RUN DOCS':<45}{r['peak_lines']:>7}{r['peak_chars']:>8}{r['peak_tokens']:>7}")
    if args.budget_tokens is not None and r["peak_tokens"] > args.budget_tokens:
        print(f"\n✗ context budget exceeded: {r['peak_tokens']} > {args.budget_tokens}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
