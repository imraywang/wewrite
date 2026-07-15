"""README 与 CLI 命令清单的同步守卫。

真源 = cli.py 的 _COMMANDS / _TOOLKIT_PASSTHROUGH。新增或改名子命令时
若忘了同步 README，本测试在 CI 直接红——README 漂移无法合入 main。
"""

import sys
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = str(ROOT / "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from wewrite.cli import _COMMANDS, _TOOLKIT_PASSTHROUGH


def test_every_cli_command_documented_in_readme():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    all_commands = [*_COMMANDS, *sorted(_TOOLKIT_PASSTHROUGH)]
    missing = [name for name in all_commands if name not in readme]
    assert not missing, (
        f"README.md 缺少以下 CLI 命令的说明，请同步（通常加在「核心能力」表和「CLI 独立使用」代码块）: {missing}"
    )


def test_readme_matches_optional_visual_workflow_and_theme_catalog():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "写一篇公众号文章                → 审过的本地成稿（默认不生图、不发布）" in readme
    assert "配图、排版、发布都能在文章完成后单独执行" in readme
    assert "排版和发布不会偷偷触发生图" in readme
    assert "已完成文章可以继续\n配图、排版或发布，原始正文不被覆盖" in readme
    assert "自动比对版本" not in readme
    assert "$0.04/篇" not in readme

    themes = sorted(path.stem for path in (ROOT / "src/wewrite/toolkit/themes").glob("*.yaml"))
    assert f"全部 {len(themes)} 个主题" in readme
    for theme in themes:
        assert f"`{theme}`" in readme


def test_content_quality_evals_match_current_workflow():
    data = json.loads((ROOT / "docs/evals.json").read_text(encoding="utf-8"))
    names = {item["name"] for item in data["evals"]}
    assert {
        "analysis-with-sources",
        "practical-guide-actionability",
        "no-personal-material-no-fabrication",
        "user-provided-story",
        "weak-draft-must-revise",
    }.issubset(names)
    serialized = json.dumps(data, ensure_ascii=False)
    assert "review-report.json" in serialized
    assert "publishable=true" in serialized
    assert "破句" not in serialized
    assert "随机维度" not in serialized
    assert "7 层去 AI" not in serialized
    assert "output/" not in serialized
