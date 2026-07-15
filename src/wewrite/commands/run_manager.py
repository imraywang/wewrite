"""Manage isolated, resumable WeWrite article runs."""

from __future__ import annotations

import argparse
import json
import sys

from ..runs import (
    create_run,
    finish_run,
    list_runs,
    load_run,
    mark_step,
    resume_run,
    set_publish_permission,
    state_as_json,
    update_run,
)


def _json_object(value: str) -> dict:
    data = json.loads(value)
    if not isinstance(data, dict):
        raise argparse.ArgumentTypeError("patch must be a JSON object")
    return data


def main(argv=None):
    ap = argparse.ArgumentParser(description="管理独立、可恢复的 WeWrite 文章任务")
    sub = ap.add_subparsers(dest="action", required=True)

    start = sub.add_parser("start", help="开始一篇新文章")
    start.add_argument("--topic", default="")
    start.add_argument("--mode", choices=["draft", "complete", "publish"], default="draft")
    start.add_argument("--visual-mode", choices=["none", "cover", "full", "prompts"])
    start.add_argument("--max-images", type=int, default=4)
    start.add_argument("--max-image-cost", type=float)
    start.add_argument("--allow-publish", action="store_true")

    show = sub.add_parser("show", help="查看任务")
    show.add_argument("run_id", nargs="?")

    ls = sub.add_parser("list", help="列出任务")
    ls.add_argument("--all", action="store_true")

    resume = sub.add_parser("resume", help="恢复未完成任务")
    resume.add_argument("run_id")

    permission = sub.add_parser("permission", help="记录或撤回外部动作授权")
    permission.add_argument("permission", choices=["publish"])
    permission.add_argument("value", choices=["allow", "deny"])
    permission.add_argument("--run-id")

    update = sub.add_parser("update", help="合并更新任务状态")
    update.add_argument("--run-id")
    update.add_argument("--patch", required=True, type=_json_object)

    step = sub.add_parser("step", help="记录步骤状态")
    step.add_argument("step")
    step.add_argument("status", choices=["pending", "in_progress", "completed", "failed", "skipped"])
    step.add_argument("--run-id")
    step.add_argument("--error")

    finish = sub.add_parser("finish", help="完成任务并写入历史")
    finish.add_argument("--run-id")
    finish.add_argument("--patch", type=_json_object)

    args = ap.parse_args(argv)
    try:
        if args.action == "start":
            state = create_run(
                topic=args.topic,
                mode=args.mode,
                visual_mode=args.visual_mode,
                max_images=args.max_images,
                max_image_cost=args.max_image_cost,
                allow_publish=args.allow_publish,
            )
        elif args.action == "show":
            state = load_run(args.run_id)
        elif args.action == "list":
            states = list_runs()
            if not args.all:
                states = [s for s in states if s.get("status") != "completed"]
            print(json.dumps(states, ensure_ascii=False, indent=2))
            return
        elif args.action == "resume":
            state = resume_run(args.run_id)
        elif args.action == "permission":
            state = set_publish_permission(args.value == "allow", args.run_id)
        elif args.action == "update":
            state = update_run(args.patch, args.run_id)
        elif args.action == "step":
            state = mark_step(args.step, args.status, args.run_id, args.error)
        else:
            state = finish_run(args.patch, args.run_id)
        print(state_as_json(state))
    except (ValueError, FileNotFoundError, json.JSONDecodeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
