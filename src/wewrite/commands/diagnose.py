#!/usr/bin/env python3
"""
Diagnose which writing-quality (humanness) measures are active in this WeWrite installation.

Checks: Python deps, config.yaml, style.yaml, learning files, dimension variance.
Outputs a human-readable report or structured JSON.

Usage:
    wewrite diagnose              # text report
    wewrite diagnose --json       # JSON for agent consumption
"""

import argparse
import importlib
import json
import os
import stat
import sys
from pathlib import Path

import yaml

from ..history import load_history
from .. import paths

# 内置写作人格预设（prompt 层数据，随 skill 仓库分发；CLI 只做名字校验）
BUILTIN_PERSONAS = {
    "cold-analyst", "humor-storyteller", "industry-observer",
    "midnight-friend", "sharp-journalist", "tech-coder", "warm-editor",
}

# Modules to check (import_name, package_name_for_pip)
REQUIRED_MODULES = [
    ("markdown", "markdown"),
    ("bs4", "beautifulsoup4"),
    ("cssutils", "cssutils"),
    ("requests", "requests"),
    ("yaml", "pyyaml"),
    ("pygments", "Pygments"),
    ("PIL", "Pillow"),
]

# Humanness weight per check (0 = no humanness impact, higher = more important)
# JSON keys keep the legacy anti_ai_* names for compatibility.
WEIGHTS = {
    "style_file": 3,
    "writing_persona": 3,
    "persona_file": 2,
    "playbook": 2,
    "history_articles": 1,
    "dimension_variance": 1,
    # These have 0 weight (no humanness impact)
    "python_packages": 0,
    "config_file": 0,
    "wechat_credentials": 0,
    "image_api_key": 0,
    "config_permissions": 0,
}

MAX_ANTI_AI_SCORE = sum(v for v in WEIGHTS.values() if v > 0)  # 12


def make_check(group, name, status, detail=None, impact=None):
    """Create a check result dict."""
    c = {"group": group, "name": name, "status": status}
    if detail is not None:
        c["detail"] = detail
    if impact is not None:
        c["impact"] = impact
    return c


def check_dependencies():
    """Group 1: Check Python package imports."""
    missing = []
    for mod_name, pip_name in REQUIRED_MODULES:
        try:
            importlib.import_module(mod_name)
        except ImportError:
            missing.append(pip_name)

    if not missing:
        return [make_check("dependencies", "python_packages", "pass", "all installed")]
    return [make_check(
        "dependencies", "python_packages", "fail",
        f"missing: {', '.join(missing)}. Reinstall CLI (uv tool install --force wewrite) "
        f"or: pip install {' '.join(missing)}",
    )]


def _env_set(*names):
    """True if all named env vars are non-empty (container injects secrets via env)."""
    return all(os.environ.get(n, "").strip() for n in names)


def check_config():
    """Group 2: Check config.yaml + env-injected secrets.

    线上容器把密钥经环境变量注入（WECHAT_*/WEWRITE_IMAGE_*/WEWRITE_WRITER_*），
    config.yaml 往往只有非敏感默认值。所以这里 config 与 env **任一**满足即算配置好，
    避免把已注入的密钥误判成缺失而错误置 skip_*。
    """
    checks = []
    config_path = paths.config_path()
    cfg = {}
    if config_path.exists():
        checks.append(make_check("config", "config_file", "pass", "found"))
        mode = stat.S_IMODE(config_path.stat().st_mode)
        if mode & 0o077:
            checks.append(make_check(
                "config", "config_permissions", "warn",
                "config.yaml may contain secrets; run chmod 600",
            ))
        with open(config_path, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}
    else:
        checks.append(make_check("config", "config_file", "warn",
                                 "no config.yaml → 仅按环境变量判断"))

    # WeChat credentials: config.yaml 或 env 任一齐全即可
    wechat = cfg.get("wechat", {}) or {}
    if (wechat.get("appid") and wechat.get("secret")) or _env_set("WECHAT_APPID", "WECHAT_SECRET"):
        checks.append(make_check("config", "wechat_credentials", "pass", "configured"))
    else:
        checks.append(make_check("config", "wechat_credentials", "warn",
                                 "missing appid/secret", impact="skip_publish"))

    # Image: legacy key, provider chain, or env key — any valid source enables images.
    image = cfg.get("image", {}) or {}
    providers = image.get("providers") or []
    provider_chain_configured = isinstance(providers, list) and any(
        isinstance(entry, dict) and entry.get("provider") and entry.get("api_key")
        for entry in providers
    )
    if image.get("api_key") or provider_chain_configured or _env_set("WEWRITE_IMAGE_API_KEY"):
        checks.append(make_check("config", "image_api_key", "pass", "configured"))
    else:
        checks.append(make_check("config", "image_api_key", "warn",
                                 "missing → image generation will be skipped", impact="skip_image_gen"))

    return checks


def runtime_flags(checks):
    """管道运行标记，供 SKILL.md Step 1 一次性读取（env 优先，与 check_config 同源）。"""
    def warned(name):
        return any(c["name"] == name and c["status"] != "pass" for c in checks)
    return {
        # 没有微信凭证 → 跳过发布；没有图片 key → 跳过生图
        "skip_publish": warned("wechat_credentials"),
        "skip_image_gen": warned("image_api_key"),
        # 配了写作模型（混合路由）→ Step 4 走 llm_write.py；否则编排器自写
        "use_writer_model": _env_set("WEWRITE_WRITER_API_KEY"),
        # 首次使用是正常设置流程，不是安装失败。
        "needs_onboard": warned("style_file"),
    }


def check_style():
    """Group 3: Check style.yaml and persona configuration."""
    checks = []
    style_path = paths.style_path()

    if not style_path.exists():
        checks.append(make_check("style", "style_file", "warn", "not found → first-run onboard required"))
        return checks

    checks.append(make_check("style", "style_file", "pass", "found"))

    with open(style_path, "r", encoding="utf-8") as f:
        style = yaml.safe_load(f) or {}

    # writing_persona field
    persona_name = style.get("writing_persona")
    if persona_name:
        checks.append(make_check("style", "writing_persona", "pass", persona_name))
    else:
        persona_name = "midnight-friend"
        checks.append(make_check("style", "writing_persona", "warn", "not set → defaults to midnight-friend"))

    # Persona 存在性：内置预设名单，或 $WEWRITE_HOME/personas/ 下的自定义人格
    custom = paths.home() / "personas" / f"{persona_name}.yaml"
    if persona_name in BUILTIN_PERSONAS:
        checks.append(make_check("style", "persona_file", "pass", f"{persona_name}（内置预设）"))
    elif custom.exists():
        checks.append(make_check("style", "persona_file", "pass", f"{custom}（自定义）"))
    else:
        checks.append(make_check("style", "persona_file", "fail",
                                 f"{persona_name} 不是内置人格，且 {custom} 不存在"))

    return checks


def check_enhancements():
    """Group 4: Check playbook and history."""
    checks = []

    # playbook.md
    if paths.playbook_path().exists():
        checks.append(make_check("enhancement", "playbook", "pass", "found"))
    else:
        checks.append(make_check(
            "enhancement", "playbook", "warn",
            'not found → no learned style (say "学习我的修改" after editing)',
        ))

    # history.yaml
    history_path = paths.history_path()
    if history_path.exists():
        articles = load_history(history_path)["articles"]
        if articles:
            checks.append(make_check("enhancement", "history_articles", "pass", f"{len(articles)} articles"))
        else:
            checks.append(make_check("enhancement", "history_articles", "warn", "file exists but empty"))
    else:
        checks.append(make_check("enhancement", "history_articles", "warn", "not found → no dedup, no dimension tracking"))

    return checks


def check_dimensions():
    """Group 5: Check dimension diversity across recent articles."""
    history_path = paths.history_path()
    if not history_path.exists():
        return [make_check("dimensions", "dimension_variance", "skip", "no history.yaml")]

    articles = load_history(history_path)["articles"]
    # Get last 3 articles that have dimensions
    recent = [a for a in articles if a.get("dimensions")][-3:]

    if len(recent) < 3:
        return [make_check("dimensions", "dimension_variance", "skip", f"only {len(recent)} articles with dimensions (need 3)")]

    # Compare dimension sets — stringify and check uniqueness
    dim_sets = [tuple(sorted(a["dimensions"])) for a in recent]
    if len(set(dim_sets)) == len(dim_sets):
        return [make_check("dimensions", "dimension_variance", "pass", "last 3 articles have distinct dimensions")]

    return [make_check("dimensions", "dimension_variance", "warn", "dimension overlap in recent articles → cross-article fingerprint risk")]


def compute_summary(checks):
    """Compute pass/warn/fail counts, humanness score, and recommendations."""
    passed = sum(1 for c in checks if c["status"] == "pass")
    warnings = sum(1 for c in checks if c["status"] == "warn")
    failures = sum(1 for c in checks if c["status"] == "fail")
    skipped = sum(1 for c in checks if c["status"] == "skip")

    score = sum(WEIGHTS.get(c["name"], 0) for c in checks if c["status"] == "pass")
    pct = score / MAX_ANTI_AI_SCORE if MAX_ANTI_AI_SCORE else 0
    if pct >= 0.76:
        level = "HIGH"
    elif pct >= 0.41:
        level = "MODERATE"
    else:
        level = "LOW"

    # Build recommendations ordered by weight (highest first)
    recs = []
    non_pass = [c for c in checks if c["status"] in ("warn", "fail") and WEIGHTS.get(c["name"], 0) > 0]
    non_pass.sort(key=lambda c: WEIGHTS.get(c["name"], 0), reverse=True)
    for c in non_pass:
        name = c["name"]
        if name == "style_file":
            recs.append('Run the skill once to trigger onboard（重新设置风格）')
        elif name == "writing_persona":
            recs.append('Add a writing_persona to style.yaml so the account voice stays consistent')
        elif name == "persona_file":
            recs.append(f'Persona file missing — check personas/ directory')
        elif name == "playbook":
            recs.append('Edit a generated article, then say "学习我的修改" to build playbook.md')
        elif name == "history_articles":
            recs.append("Generate your first article to start building history")
        elif name == "dimension_variance":
            recs.append("Recent articles reuse same dimensions — the pipeline will auto-fix on next run")

    return {
        "passed": passed,
        "warnings": warnings,
        "failures": failures,
        "skipped": skipped,
        "anti_ai_score": score,
        "anti_ai_max": MAX_ANTI_AI_SCORE,
        "anti_ai_level": level,
        "style_setup_score": score,
        "style_setup_max": MAX_ANTI_AI_SCORE,
        "style_setup_level": level,
    }, recs


def file_status_map(checks):
    """Build a quick file-existence map for agent use."""
    # Extract persona name from checks instead of re-reading style.yaml
    persona_name = "midnight-friend"
    for c in checks:
        if c["name"] == "writing_persona" and c["status"] == "pass" and c.get("detail"):
            persona_name = c["detail"]
            break

    exemplars = sorted(paths.exemplars_dir().glob("*.md")) if paths.exemplars_dir().is_dir() else []
    return {
        "home": str(paths.home()),
        "config_yaml": paths.config_path().exists(),
        "style_yaml": paths.style_path().exists(),
        "playbook_md": paths.playbook_path().exists(),
        "history_yaml": paths.history_path().exists(),
        "persona": persona_name,
        "exemplars": [f.name for f in exemplars],
    }


def format_text(checks, summary, recs):
    """Format human-readable text report."""
    lines = ["WeWrite Writing-Quality Diagnostic", "=" * 33, ""]

    current_group = None
    group_labels = {
        "dependencies": "Dependencies",
        "config": "Config",
        "style": "Style",
        "enhancement": "Enhancement",
        "dimensions": "Dimension Variance",
    }
    for c in checks:
        if c["group"] != current_group:
            if current_group is not None:
                lines.append("")
            current_group = c["group"]
            lines.append(group_labels.get(current_group, current_group))
        tag = c["status"].upper()
        label = c["name"].replace("_", " ").title()
        detail = f": {c['detail']}" if c.get("detail") else ""
        lines.append(f"  [{tag:4s}] {label}{detail}")
    lines.append("")

    p, w, f_ = summary["passed"], summary["warnings"], summary["failures"]
    sk = summary.get("skipped", 0)
    skipped_part = f", {sk} skipped" if sk > 0 else ""
    lines.append(f"Summary: {p} passed, {w} warnings, {f_} failures{skipped_part}")

    score = summary["anti_ai_score"]
    mx = summary["anti_ai_max"]
    filled = round(score / mx * 12) if mx else 0
    bar = "\u2588" * filled + "\u2591" * (12 - filled)
    lines.append(f"Style setup: {bar} {summary['style_setup_level']} ({score}/{mx})")

    if recs:
        lines.append("")
        lines.append("Top recommendations:")
        for i, r in enumerate(recs, 1):
            lines.append(f"  {i}. {r}")

    return "\n".join(lines)


def format_json(checks, summary, recs):
    """Format JSON output."""
    return json.dumps({
        "checks": checks,
        "summary": summary,
        "recommendations": recs,
        "files": file_status_map(checks),
        "flags": runtime_flags(checks),
    }, ensure_ascii=False, indent=2)


def run_all_checks():
    """Run all check groups and return combined list."""
    checks = []
    checks.extend(check_dependencies())
    checks.extend(check_config())
    checks.extend(check_style())
    checks.extend(check_enhancements())
    checks.extend(check_dimensions())
    return checks


def main():
    parser = argparse.ArgumentParser(
        description="Diagnose which writing-quality (humanness) measures are active in this WeWrite installation.",
    )
    parser.add_argument("--json", action="store_true", help="Output structured JSON")
    args = parser.parse_args()

    paths.ensure_home()  # 首个管道命令，顺手把状态目录立起来
    checks = run_all_checks()
    summary, recs = compute_summary(checks)

    if args.json:
        print(format_json(checks, summary, recs))
    else:
        print(format_text(checks, summary, recs))

    # Exit code: 1 if any failures, 0 otherwise
    sys.exit(1 if summary["failures"] > 0 else 0)


if __name__ == "__main__":
    main()
