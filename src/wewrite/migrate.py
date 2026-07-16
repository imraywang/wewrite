"""`wewrite migrate` —— 把 v2.1 之前散在 skill 仓库根的用户状态迁到 $WEWRITE_HOME。

幂等：目标已存在的条目一律跳过（绝不覆盖），可重复执行。
默认只复制不删除源文件；确认无误后可自行清理仓库内旧状态。
"""

import argparse
import shutil
import sys
from pathlib import Path

from . import paths

# (仓库内旧位置, 状态目录内新位置)。目录整体复制，文件单个复制。
_ENTRIES = [
    ("config.yaml", "config.yaml"),
    ("style.yaml", "style.yaml"),
    ("history.yaml", "history.yaml"),
    ("playbook.md", "playbook.md"),
    ("references/exemplars", "exemplars"),
    ("corpus", "corpus"),
    ("lessons", "lessons"),
    ("output", "output"),
]


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(prog="wewrite migrate",
                                 description="迁移旧版仓库内用户状态到状态目录（幂等，只复制不删除）")
    ap.add_argument("--from", dest="src", default=".",
                    help="旧 WeWrite 仓库路径（默认当前目录）")
    args = ap.parse_args(argv)

    src_root = Path(args.src).expanduser().resolve()
    if not (src_root / "skills").is_dir() and not (src_root / "SKILL.md").exists():
        print(f"⚠ {src_root} 不像 WeWrite 仓库（没有 skills/ 或 SKILL.md），仍按给定路径尝试", file=sys.stderr)

    dest_root = paths.ensure_home()
    copied, skipped, missing = [], [], []

    for old_rel, new_rel in _ENTRIES:
        src, dest = src_root / old_rel, dest_root / new_rel
        if not src.exists():
            missing.append(old_rel)
            continue
        if src.is_dir():
            dest.mkdir(exist_ok=True)
            moved_any = False
            for item in src.rglob("*"):
                if not item.is_file() or item.name == ".gitkeep":
                    continue
                target = dest / item.relative_to(src)
                if target.exists():
                    skipped.append(str(target.relative_to(dest_root)))
                    continue
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(item, target)
                moved_any = True
            (copied if moved_any else skipped).append(new_rel + "/")
        else:
            if dest.exists():
                skipped.append(new_rel)
                continue
            shutil.copy2(src, dest)
            copied.append(new_rel)

    print(f"状态目录: {dest_root}")
    if copied:
        print("✓ 已迁移: " + ", ".join(copied))
    if skipped:
        print("• 已存在跳过: " + ", ".join(sorted(set(skipped))[:10]) + (" …" if len(set(skipped)) > 10 else ""))
    if missing:
        print("• 源中不存在: " + ", ".join(missing))
    if not copied:
        print("（没有新内容需要迁移）")
