"""Create a deterministic editorial report from an editor assessment."""

from __future__ import annotations

import argparse
import difflib
import json
import re
import sys
from pathlib import Path

import yaml


DIMENSIONS = ("accuracy", "viewpoint", "usefulness", "voice", "readability")
DECISIONS = {"pass", "revise", "needs_input"}


def _load_mapping(path: str) -> dict:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("assessment must be a YAML or JSON object")
    return data


def _headings(text: str) -> list[str]:
    return re.findall(r"^##\s+(.+)$", text, re.MULTILINE)


def build_report(draft: str, final: str, assessment: dict) -> dict:
    if not draft.strip() or not final.strip():
        raise ValueError("draft and final must both be non-empty")
    decision = assessment.get("decision")
    if decision not in DECISIONS:
        raise ValueError("decision must be pass, revise, or needs_input")

    dimensions = assessment.get("dimensions")
    if not isinstance(dimensions, dict):
        raise ValueError("assessment.dimensions must contain five scores")
    normalized = {}
    for name in DIMENSIONS:
        score = dimensions.get(name)
        if not isinstance(score, (int, float)) or isinstance(score, bool) or not 1 <= score <= 5:
            raise ValueError(f"dimension {name} must be between 1 and 5")
        normalized[name] = float(score)

    blockers = assessment.get("blockers", [])
    major_issues = assessment.get("major_issues", [])
    if not isinstance(blockers, list) or not isinstance(major_issues, list):
        raise ValueError("blockers and major_issues must be lists")

    pass_number = assessment.get("pass_number", 1)
    if not isinstance(pass_number, int) or isinstance(pass_number, bool) or pass_number not in {1, 2}:
        raise ValueError("pass_number must be 1 or 2")

    ratio = difflib.SequenceMatcher(None, draft, final, autojunk=False).ratio()
    average = round(sum(normalized.values()) / len(normalized), 2)
    minimum = min(normalized.values())
    publishable = decision == "pass" and not blockers and minimum >= 3 and average >= 4

    return {
        "version": 1,
        "decision": decision,
        "pass_number": pass_number,
        "publishable": publishable,
        "dimensions": normalized,
        "dimension_average": average,
        "blockers": blockers,
        "major_issues": major_issues,
        "notes": assessment.get("notes", ""),
        "draft_chars": len(draft),
        "final_chars": len(final),
        "edit_ratio": round(1 - ratio, 4),
        "structure_changed": _headings(draft) != _headings(final),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description="汇总文章编辑判断与修改幅度")
    parser.add_argument("--draft", required=True, help="初稿 Markdown")
    parser.add_argument("--final", required=True, help="终稿 Markdown")
    parser.add_argument("--assessment", required=True, help="编辑判断 YAML/JSON")
    parser.add_argument("--output", help="报告 JSON 输出路径")
    parser.add_argument("--json", action="store_true", help="在标准输出打印 JSON")
    args = parser.parse_args(argv)

    try:
        draft = Path(args.draft).read_text(encoding="utf-8")
        final = Path(args.final).read_text(encoding="utf-8")
        report = build_report(draft, final, _load_mapping(args.assessment))
        rendered = json.dumps(report, ensure_ascii=False, indent=2)
        if args.output:
            output = Path(args.output)
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(rendered + "\n", encoding="utf-8")
        if args.json or not args.output:
            print(rendered)
    except (OSError, ValueError, yaml.YAMLError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(2)


if __name__ == "__main__":
    main()
