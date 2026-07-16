"""WeWrite 状态目录解析 —— 用户状态与代码/skill 仓库解耦的唯一枢纽。

所有用户状态（凭证、风格、历史、学习产物、输出文件）统一放在
`$WEWRITE_HOME`（默认 `~/.wewrite`），CLI 与 skill 都通过本模块解析路径。
v2.x 之前状态散在 skill 仓库根，`wewrite migrate` 负责一次性迁移。
"""

import os
from pathlib import Path

# 状态目录下的子目录（ensure_home 时创建）
_SUBDIRS = ["output", "runs", "exemplars", "corpus", "lessons", "themes", "personas"]


def home() -> Path:
    """状态目录：$WEWRITE_HOME 或 ~/.wewrite。不保证存在（写操作前用 ensure_home）。"""
    return Path(os.environ.get("WEWRITE_HOME", "") or (Path.home() / ".wewrite"))


def ensure_home() -> Path:
    """创建状态目录及标准子目录（幂等），返回状态目录。"""
    h = home()
    h.mkdir(parents=True, exist_ok=True)
    for sub in _SUBDIRS:
        (h / sub).mkdir(exist_ok=True)
    return h


def config_path() -> Path:
    return home() / "config.yaml"


def style_path() -> Path:
    return home() / "style.yaml"


def history_path() -> Path:
    return home() / "history.yaml"


def playbook_path() -> Path:
    return home() / "playbook.md"


def output_dir() -> Path:
    return home() / "output"


def runs_dir() -> Path:
    return home() / "runs"


def current_run_path() -> Path:
    return home() / "current_run"


def exemplars_dir() -> Path:
    return home() / "exemplars"


def corpus_dir() -> Path:
    return home() / "corpus"


def lessons_dir() -> Path:
    return home() / "lessons"


def user_themes_dir() -> Path:
    """learn-theme 学到的用户主题；load_theme 在包内置主题之前先查这里。"""
    return home() / "themes"
